-- Headless vblank-write reachability check (make test-vblank). Runs the real game (coin, start, run with
-- scrolling) and taps every access to the LSPC VRAM registers (0x3C0000-0x3C000F: VRAMADDR, VRAMRW, VRAMMOD)
-- and every palette RAM write (0x400000-0x401FFF). For each write it reads screen:vblank() and the screen
-- position. Asserts: after the boot settle frame, every VRAM register write and every palette write lands
-- inside the vblank window (the 40 lines outside the 224 visible lines). Also records words written per
-- frame (data port 0x3C0002) and the time span of the per-frame write burst, to calibrate the vblank
-- capacity. Writes before SETTLE_FRAME are the BIOS and the game init, not counted.
-- Also asserts the main loop runs one game step per video frame while PLAYING: g_frame_counter, read at every
-- frame end, advances by exactly 1 (a frame logic overrun shows as steps of 0, the game at 30 Hz).
-- Object pool (src/core/obj_pool.h, drawn by src/main.c): asserts the pool view ran in normal play (g_pool_frames > 0
-- before the stress phase, the obstacles draw through it), then sets the g_pool_stress test hook so the pool fills to
-- POOL_MAX moving objects, and asserts at least MIN_FULL PLAYING frames at the max object count with the frame-step
-- check still passing. Reports the latest frame logic end (write of g_frame_counter, lines after vblank end; it must stay
-- below the 224 visible lines or the flush is skipped) and the queue backlog after a flush (g_gfx_backlog_max) in that phase.
-- Sentinel addresses come from the ELF map (nm path from config.mk, as the Makefile derives it), because make test-vblank
-- only passes the env below.
-- Env: BRAWL_FLOW_ADDR, BRAWL_FRAME_ADDR (hex), BRAWL_HIT_LAYOUT (hit_probe.c output, first value = flow state offset),
-- BRAWL_RESULT (file).
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local frame_addr = tonumber(os.getenv("BRAWL_FRAME_ADDR"), 16)
local result    = os.getenv("BRAWL_RESULT")
local palmax_addr = tonumber(os.getenv("BRAWL_PALMAX_ADDR"), 16)
local PAL_WORDS_MAX = 112 -- g_pal_words_frame_max: the most palette words one flush may write over a whole run (measured, see the notes)
local lay = {}
for v in (os.getenv("BRAWL_HIT_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local O_STATE = lay[1]
local POOL_MAX = lay[2]
local VQ = {}   -- tests/mame/vq_probe.c values: queue field offsets and sprite slot range starts, in the order of that file
for v in (os.getenv("BRAWL_VQ_LAYOUT") or ""):gmatch("%d+") do VQ[#VQ + 1] = tonumber(v) end

-- Demo run (BRAWL_DEMO=1, no input): the attract demos of all three modes with the how-to-play overlay. Class 4 "demo" is every logic frame
-- whose flow state is FLOW_ATTRACT_DEMO; same limits as the play classes. Env as attract_check.lua: BRAWL_ATTRACT_LAYOUT (attract_probe.c output).
local DEMO_RUN = os.getenv("BRAWL_DEMO") == "1"
local AL = {}
for v in (os.getenv("BRAWL_ATTRACT_LAYOUT") or ""):gmatch("%d+") do AL[#AL + 1] = tonumber(v) end
local O_AMODE, K_DEMO, K_ARENA, K_TRIP, K_ARCADE = AL[4], AL[6], AL[7], AL[8], AL[9]
local O_AFLOW = AL[1]
local DEMO_MIN_FRAMES = 150   -- logic frames sampled per mode before the demo run may end
local LOGIC_LIMIT = 224       -- logic end must stay below the visible lines, else the flush is skipped
local FLUSH_BUDGET_US = 2000  -- GFX_FLUSH_BUDGET_US
local demo_mode = {}          -- per mode (arena/trip/arcade): frames, logic end max, flush us max, vram words max, palette words max
for _, m in ipairs({ K_ARENA or -1, K_TRIP or -2, K_ARCADE or -3 }) do demo_mode[m] = { frames = 0, lmax = 0, us = 0, vwords = 0, pwords = 0, us_late = 0, vw_late = 0, over = 0, first_over = nil, lmax_late = 0, idx_lmax = 0 } end
local prev_demo_mode, demo_idx, prev_idx = nil, 0, 0   -- demo_idx: logic frame number inside the current demo

local function sym_addrs()
  local gcc
  for line in io.lines("config.mk") do gcc = gcc or line:match("^M68KGCC=(.*)$") end
  local nm = (gcc or "m68k-neogeo-elf-gcc"):gsub("gcc$", "nm")
  local t = {}
  local h = io.popen(nm .. " build/rom.elf")
  for line in h:lines() do
    local a, name = line:match("^(%x+) %a (%S+)$")
    if a then t[name] = tonumber(a, 16) end
  end
  h:close()
  return t
end
local syms = sym_addrs()
local A_STRESS, A_LIVE, A_PFRAMES = syms.g_pool_stress, syms.g_pool_live, syms.g_pool_frames
local A_BACKLOG, A_FLUSHMAX = syms.g_gfx_backlog_max, syms.g_gfx_flush_max
local A_GFXQ, A_CAM, A_LASTUS = syms.g_gfx_q, syms.g_cam_px, syms.g_last_us   -- queue, camera x (src/main.c), last flush us (src/gfx.c)
local stress_frame = nil     -- set 30 frames after the first frame the obstacles drew through the pool
local MIN_FULL = 100          -- PLAYING frames with POOL_MAX live objects
local STATE_PLAYING = 3
local SETTLE_FRAME = 200      -- boot and first flow init are done well before the first coin (frame 320)
local END_FRAME = 1800        -- the idle hero dies in a few hundred frames; attract, run and game over are all observed
local MIN_PLAYING = 150       -- the run must have scrolled for at least this many frames
local MAX_MISSED = 2          -- PLAYING frames without a game step allowed (state change frames)
local mem    = manager.machine.devices[":maincpu"].spaces["program"]
local screen = manager.machine.screens[":screen"]
local ports  = manager.machine.ioport.ports

local function field(tag, name)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname == name then return f end end
end
local coin  = field(":AUDIO_COIN", "Coin 1")
local start = field(":edge:joy:START", "1 Player Start")
local ss = dofile("tests/mame/start_seq.lua")(coin, start)

local FO1_DRIVE = os.getenv("BRAWL_FO1_DRIVE") == "1"
local rbtn = field(":edge:joy:JOY1", "P1 Right")
local abtn = field(":edge:joy:JOY1", "P1 A")
local function finish(ok, msg, extra)
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n" .. (extra or ""))
  f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  if extra then print(extra) end
  manager.machine:exit()
end

local LINE_S = screen.scan_period      -- 64 us per line
local cpu = manager.machine.devices[":maincpu"]
local n = 0
local counting = false
local bad_vram, bad_pal, total_vram, total_pal = 0, 0, 0, 0
local first_bad = nil
local vb_lines = nil                   -- vblank length in lines, read at the first frame end
local worst_late = 0                   -- latest write, in lines after vblank start
local words, first_t, last_t = 0, nil, nil
local max_words, max_span = 0, 0
local VB_LEN_S = nil

-- MAME 0.286 has no screen:vblank(): inside vblank the next vblank END is nearer than the next START.
-- Returns in_vblank, seconds since vblank start (only meaningful inside vblank).
local function vblank_state()
  local to_end = screen:time_until_vblank_end():as_double()
  local to_start = screen:time_until_vblank_start():as_double()
  return to_end < to_start, (VB_LEN_S or 0) - to_end
end

-- FO1 bucketed measurement (thoughts/spot/2026-11-11-frame-overrun-fo1-patch.md). Measurement only: nothing here is asserted.
local LINES_ACTIVE = 224
local HAVE_BUCKETS = A_GFXQ ~= nil and A_CAM ~= nil and #VQ == 24
local names, slot_bucket = { "unowned" }, {}
local function range(name, first, stop)
  names[#names + 1] = name
  for s = first, stop - 1 do slot_bucket[s] = #names end
end
local row_names, ROW_FIX, ROW_OTHER, ROW_PAL = {}, 0, 0, 0
if HAVE_BUCKETS then
  range("bg_sky", VQ[6], VQ[7]);   range("bg_far", VQ[7], VQ[8]);   range("bg_mida", VQ[8], VQ[9])
  range("bg_midb", VQ[9], VQ[10]); range("bg_near", VQ[10], VQ[11])
  range("island", VQ[12], VQ[13]); range("pool", VQ[14], VQ[15]);   range("hero", VQ[16], VQ[17])
  range("hazard", VQ[18], VQ[19]); range("fg_rain", VQ[20], VQ[21]); range("fg_spray", VQ[21], VQ[22])
  range("trip_strip", VQ[22], VQ[23]); range("trip_pickup", VQ[23], VQ[24])
  for i, nm in ipairs(names) do row_names[(i - 1) * 2 + 1] = nm .. "/tiles"; row_names[(i - 1) * 2 + 2] = nm .. "/scb" end
  ROW_FIX = #row_names + 1; row_names[ROW_FIX] = "fix"
  ROW_OTHER = ROW_FIX + 1;  row_names[ROW_OTHER] = "vram_other"
  ROW_PAL = ROW_OTHER + 1;  row_names[ROW_PAL] = "palette"
end
local R = #row_names
local function sprite_row(sprite, scb) return ((slot_bucket[sprite] or 1) - 1) * 2 + (scb and 2 or 1) end
-- VRAM address (SCB1 sprite*64, fix 0x7000.., SCB2/3/4 0x8000/0x8200/0x8400 + sprite) to a row
local function vram_row(addr)
  if addr < 0x7000 then return sprite_row(addr >> 6, false)
  elseif addr < 0x7500 then return ROW_FIX
  elseif addr >= 0x8000 and addr < 0x8600 then return sprite_row((addr - 0x8000) & 0x1ff, true)
  end
  return ROW_OTHER
end

-- per-frame accumulators (flush side and queue side), folded into the per-class stats at the next logic end
local function new_acc() local t = { w = {}, first = {}, last = {}, inv = {} } for r = 1, R do t.w[r], t.inv[r] = 0, 0 end return t end
local acc = { flush = new_acc(), queue = new_acc() }
local function new_stat()
  local rows = {}
  for r = 1, R do rows[r] = { words = 0, wmax = 0, nz = 0, fsum = 0, fmin = 1e9, lsum = 0, lmax = -1, inv = 0, invframes = 0 } end
  return { frames = 0, rows = rows, lsum = 0, lcnt = 0, lmax = 0, n999 = 0, us_sum = 0, us_max = 0, skipped = 0 }
end
local stat = { flush = {}, queue = {} }
local NCLS = 4
for c = 1, NCLS do stat.flush[c], stat.queue[c] = new_stat(), new_stat() end
local CLASS = { "cam moved (PLAYING)", "cam still (PLAYING)", "not PLAYING", "demo" }

local function note(side, row, line, inv)
  local a = acc[side]
  if inv then a.inv[row] = a.inv[row] + 1; return end
  a.w[row] = a.w[row] + 1
  if not a.first[row] or line < a.first[row] then a.first[row] = line end
  if not a.last[row] or line > a.last[row] then a.last[row] = line end
end
local function lines_after_vblank_start()   -- raster line since vblank start, also past the end of vblank
  local inv, since = vblank_state()
  if inv then return since / LINE_S end
  return VB_LEN_S / LINE_S + (LINES_ACTIVE - screen:time_until_vblank_start():as_double() / LINE_S)
end
local function note_flush_vram(addr) if HAVE_BUCKETS and VB_LEN_S then note("flush", vram_row(addr), lines_after_vblank_start(), false) end end
local function note_flush_pal() if HAVE_BUCKETS and VB_LEN_S then note("flush", ROW_PAL, lines_after_vblank_start(), false) end end
local function note_queue(row)               -- CPU queue write: line = lines after vblank end; inside vblank = written during an overrun
  local inv = vblank_state()
  note("queue", row, inv and 0 or (LINES_ACTIVE - screen:time_until_vblank_start():as_double() / LINE_S), inv)
end

local vaddr, vmod, flush_seen = 0, 1, false
local prev_cam, prev_cls = nil, nil
local first_overruns = 0
local fe_calls, fc_calls, fe_read_bad = 0, 0, 0
local q_offsets, q_first_words = {}, {}      -- runtime check records: first queue tap offsets, first frame_end reads
local function fold(side, cls, a)
  local s = stat[side][cls]
  s.frames = s.frames + 1
  for r = 1, R do
    local row, nw = s.rows[r], a.w[r]
    row.words = row.words + nw
    if nw > row.wmax then row.wmax = nw end
    if nw > 0 then
      row.nz = row.nz + 1
      row.fsum = row.fsum + a.first[r]; row.lsum = row.lsum + a.last[r]
      if a.first[r] < row.fmin then row.fmin = a.first[r] end
      if a.last[r] > row.lmax then row.lmax = a.last[r] end
    end
    if a.inv[r] > 0 then row.inv = row.inv + a.inv[r]; row.invframes = row.invframes + 1 end
    a.w[r], a.inv[r], a.first[r], a.last[r] = 0, 0, nil, nil
  end
end
-- Called from the g_frame_counter write tap (the logic end). l = lines after vblank end, or 999 if the write is inside vblank.
local function frame_end(l)
  if not HAVE_BUCKETS then return end
  fe_calls = fe_calls + 1
  local st = mem:read_u8(flow_addr + O_STATE)
  local cam = mem:read_u16(A_CAM)
  if #q_first_words < 3 then q_first_words[#q_first_words + 1] = string.format("state %d cam %d", st, cam) end
  local playing = st == STATE_PLAYING
  local in_demo = DEMO_RUN and K_DEMO ~= nil and mem:read_u8(flow_addr + O_AFLOW) == K_DEMO
  local cls = in_demo and 4 or (not playing) and 3 or ((prev_cam ~= nil and cam ~= prev_cam) and 1 or 2)
  prev_cam = cam
  if prev_cls then   -- the flush that ran between the previous logic end and this one belongs to the previous frame's class
    local fs = stat.flush[prev_cls]
    if not flush_seen then fs.skipped = fs.skipped + 1 end
    local us = A_LASTUS and mem:read_u16(A_LASTUS) or 0
    fs.us_sum = fs.us_sum + us
    if us > fs.us_max then fs.us_max = us end
    if prev_cls == 4 and prev_demo_mode and demo_mode[prev_demo_mode] then   -- flush of the previous demo frame: VRAM data words and palette words
      local dm, vw = demo_mode[prev_demo_mode], 0
      for r = 1, ROW_PAL - 1 do vw = vw + acc.flush.w[r] end
      dm.vwords = math.max(dm.vwords, vw); dm.pwords = math.max(dm.pwords, acc.flush.w[ROW_PAL]); dm.us = math.max(dm.us, us)
      if prev_idx > 3 then dm.us_late = math.max(dm.us_late, us); dm.vw_late = math.max(dm.vw_late, vw) end
    end
    fold("flush", prev_cls, acc.flush)
  end
  prev_idx = demo_idx
  demo_idx = in_demo and (prev_demo_mode and demo_idx + 1 or 1) or 0
  prev_demo_mode = in_demo and mem:read_u8(flow_addr + O_AMODE) or nil
  if in_demo and demo_mode[prev_demo_mode] then
    local dm = demo_mode[prev_demo_mode]
    dm.frames = dm.frames + 1
    if l >= LOGIC_LIMIT then dm.over = dm.over + 1; dm.first_over = dm.first_over or demo_idx end
    if l > dm.lmax then dm.lmax = l; dm.idx_lmax = demo_idx end
    if demo_idx > 3 and l > dm.lmax_late then dm.lmax_late = l end   -- worst after the first 3 frames of a demo
  end
  flush_seen = false
  local qs = stat.queue[cls]
  if l == 999 then
    qs.n999 = qs.n999 + 1
    local any_inv = false
    for r = 1, R do if acc.queue.inv[r] > 0 then any_inv = true end end
    if not any_inv then qs.n999_noword = (qs.n999_noword or 0) + 1 end
    if first_overruns < 10 then
      first_overruns = first_overruns + 1
      local live = A_LIVE and mem:read_u8(A_LIVE) or -1
      local who = {}
      for r = 1, R do if acc.queue.inv[r] > 0 then who[#who + 1] = row_names[r] .. "=" .. acc.queue.inv[r] end end
      print(string.format("VBLANK_OVERRUN frame %d class %s live %d wrote inside vblank: %s", n, CLASS[cls], live, table.concat(who, " ")))
    end
  else
    qs.lsum = qs.lsum + l; qs.lcnt = qs.lcnt + 1
    if l > qs.lmax then qs.lmax = l end
  end
  fold("queue", cls, acc.queue)
  prev_cls = cls
end

-- Queue-side taps (RAM, no game change). A tap handle must stay a global. scb_hw[i] is written once per queued changed SCB word
-- (src/core/vram_queue.c), i = vram address - 0x8000; strip[sprite] once per queued strip (first field = 4 byte tile pointer).
if HAVE_BUCKETS then
  local scb_base, strip_base = A_GFXQ + VQ[1], A_GFXQ + VQ[2]
  tap_q_scb = mem:install_write_tap(scb_base, scb_base + VQ[4] * 2 - 1, "qscb", function(offset, data, mask)
    if not counting then return end
    if #q_offsets < 3 then q_offsets[#q_offsets + 1] = string.format("0x%x (array 0x%x..0x%x)", offset, scb_base, scb_base + VQ[4] * 2 - 1) end
    local rel = offset - scb_base   -- MAME passes the absolute address
    note_queue(sprite_row((rel // 2) & 0x1ff, true))
  end)
  tap_q_strip = mem:install_write_tap(strip_base, strip_base + VQ[5] * VQ[3] - 1, "qstrip", function(offset, data, mask)
    if not counting then return end
    local rel = offset - strip_base
    if rel % VQ[3] < 2 then note_queue(sprite_row(rel // VQ[3], false)) end
  end)
end

-- The background planes go out as VQ_RAMP ops that write no shadow word, so the scb_hw tap above sees none of them. bg_update stores
-- g_bg_plane_x[p] right after it queues the plane's ramp op: that store is the queue-side event, counted as one word per column of the
-- plane (the words the flush will generate), so the bg_* rows still name the planes. Measurement attribution only: the overrun count
-- (logic end 999) is taken from the frame end and does not depend on this tap.
local A_BGX = syms.g_bg_plane_x
if HAVE_BUCKETS and A_BGX then
  tap_q_bgx = mem:install_write_tap(A_BGX, A_BGX + 9, "qbgx", function(offset, data, mask)
    if not counting then return end
    local p = ((offset - A_BGX) // 2)          -- plane index 0..4 (sky 0 never written after init)
    if p < 0 or p > 4 then return end
    local first, stop = VQ[6 + p], VQ[7 + p]
    for _ = first, stop - 1 do note_queue(sprite_row(first, true)) end
  end)
end

-- Taps: the handles are globals, a tap whose handle is collected stops firing.
tap_vram = mem:install_write_tap(0x3c0000, 0x3c000f, "vram", function(offset, data, mask)
  if not counting then return end
  total_vram = total_vram + 1
  flush_seen = true
  local reg = offset & 0xf
  if reg < 2 then vaddr = data & 0xffff                                          -- VRAMADDR
  elseif reg < 4 then note_flush_vram(vaddr); vaddr = (vaddr + vmod) & 0xffff    -- VRAMRW data word, address steps by VRAMMOD
  elseif reg < 6 then vmod = data & 0xffff end                                   -- VRAMMOD
  local inv, since = vblank_state()
  if not inv then
    bad_vram = bad_vram + 1
    if not first_bad then
      first_bad = string.format("VRAM reg+%x data %04x at %.1f lines before vblank start, frame %d, flow state %d, pc %06x", offset, data & 0xffff,
        screen:time_until_vblank_start():as_double() / LINE_S, n, mem:read_u8(flow_addr + O_STATE), cpu.state["PC"].value)
    end
  end
  if inv and since / LINE_S > worst_late then worst_late = since / LINE_S end
  if (offset & 0xf) == 2 or (offset & 0xf) == 3 then   -- data port 0x3C0002 (MAME passes the absolute address)
    words = words + 1
    local t = manager.machine.time:as_double()
    if not first_t then first_t = t end
    last_t = t
  end
end)
tap_pal = mem:install_write_tap(0x400000, 0x401fff, "pal", function(offset, data, mask)
  if not counting then return end
  total_pal = total_pal + 1
  note_flush_pal()
  if not vblank_state() then
    bad_pal = bad_pal + 1
    if not first_bad then first_bad = string.format("palette+%x", offset) end
  end
end)

-- Frame logic end: the main loop writes g_frame_counter right before it parks for vblank.
local ACTIVE_LINES = 224
local logic_end, logic_end_full = 0, 0
local stress_on = false
local full_now = false
local fe_frame = -1
tap_fc = mem:install_write_tap(frame_addr, frame_addr + 3, "fc", function(offset, data, mask)
  if not counting then return end
  fc_calls = fc_calls + 1
  -- lines after vblank end = active lines - lines left to vblank start; a write inside vblank is an overrun (999)
  local inv = vblank_state()
  local l = inv and 999 or (ACTIVE_LINES - screen:time_until_vblank_start():as_double() / LINE_S)
  if l > logic_end then logic_end = l end
  if full_now and l > logic_end_full then logic_end_full = l end
  if fe_frame ~= n then fe_frame = n; frame_end(l) end
end)

local playing_frames = 0
local pool_frames_before, full_frames, missed_full = nil, 0, 0
local prev_fc, missed, steps = nil, 0, 0
local function bucket_report()
  if not HAVE_BUCKETS then return "VBLANK_BUCKET not measured: BRAWL_VQ_LAYOUT or g_gfx_q/g_cam_px missing (" .. #VQ .. " layout values)\n" end
  local out = {}
  local function add(s) out[#out + 1] = s end
  add("VBLANK_BUCKET units: queue side = CPU enqueue of changed words, line = lines after vblank end (0..224); flush side = VRAM words written by gfx_flush, line = lines after vblank start (0..39 is vblank). words = per frame; mean over all frames of the class; first/last over frames that wrote.")
  add(string.format("VBLANK_RUNTIME input drive %s; fc tap calls %d, frame_end calls %d, first queue tap offsets: %s; first frame_end reads: %s; probe values %d",
    FO1_DRIVE and "right+A" or "none", fc_calls, fe_calls, table.concat(q_offsets, ", "), table.concat(q_first_words, ", "), #VQ))
  for c = 1, NCLS do
    local q, f = stat.queue[c], stat.flush[c]
    add(string.format("VBLANK_CLASS %s: logic frames %d, logic end mean %.1f max %.1f lines, frames with write inside vblank (999) %d (of these without any queued word inside vblank %d), flush frames %d, flush us mean %.0f max %d, vblanks with flush skipped %d",
      CLASS[c], q.frames, q.lcnt > 0 and q.lsum / q.lcnt or 0, q.lmax, q.n999, q.n999_noword or 0, f.frames, f.frames > 0 and f.us_sum / f.frames or 0, f.us_max, f.skipped))
  end
  for _, side in ipairs({ "queue", "flush" }) do
    for r = 1, R do
      local any = false
      for c = 1, NCLS do if stat[side][c].rows[r].words > 0 or stat[side][c].rows[r].inv > 0 then any = true end end
      if any then
        local parts = {}
        for c = 1, NCLS do
          local s = stat[side][c]
          local row = s.rows[r]
          parts[#parts + 1] = string.format("%s: words max %d mean %.1f, first %s last %s (mean %s / %s)", c == 1 and "moved" or (c == 2 and "still" or (c == 3 and "other" or "demo")),
            row.wmax, s.frames > 0 and row.words / s.frames or 0,
            row.nz > 0 and string.format("%.1f", row.fmin) or "-", row.nz > 0 and string.format("%.1f", row.lmax) or "-",
            row.nz > 0 and string.format("%.1f", row.fsum / row.nz) or "-", row.nz > 0 and string.format("%.1f", row.lsum / row.nz) or "-")
        end
        add(string.format("VBLANK_BUCKET %-5s %-22s | %s", side, row_names[r], table.concat(parts, " | ")))
      end
    end
  end
  for c = 1, NCLS do   -- frames whose logic wrote inside vblank, by the bucket that wrote there
    for r = 1, R do
      local row = stat.queue[c].rows[r]
      if row.inv > 0 then add(string.format("VBLANK_OVERRUN_BUCKET class %s bucket %s: frames %d, words %d", CLASS[c], row_names[r], row.invframes, row.inv)) end
    end
  end
  return table.concat(out, "\n") .. "\n"
end
emu.register_frame_done(function()
  n = n + 1
  if not VB_LEN_S then VB_LEN_S = screen:time_until_vblank_end():as_double() end  -- frame_done is at vblank start
  if words > max_words then max_words = words end
  if first_t and last_t and words > 1 then
    local span = last_t - first_t
    if span > max_span then max_span = span end
  end
  words, first_t, last_t = 0, nil, nil
  if n == SETTLE_FRAME then counting = true end
  -- one coin at 320; one Start press begins the game, later presses are retries (BG4; start_seq.lua)
  if coin and start and not DEMO_RUN then
    if n == 320 then ss.begin(n) end
    if n >= 320 then ss.step(n, n >= 450) end
  end
  -- FO1 measurement only: BRAWL_FO1_DRIVE=1 holds Right and taps A so the camera scrolls (the default idle run never moves it)
  if FO1_DRIVE and n > 400 then
    if rbtn then rbtn:set_value(1) end
    if abtn then if n % 10 == 0 then abtn:set_value(1) elseif n % 10 == 3 then abtn:set_value(0) end end
  end
  local fc = mem:read_u32(frame_addr)
  if mem:read_u8(flow_addr + O_STATE) == STATE_PLAYING then
    playing_frames = playing_frames + 1
    if prev_fc then
      if fc == prev_fc then
        missed = missed + 1
        if full_now then missed_full = missed_full + 1 end
      end
      steps = steps + 1
    end
    prev_fc = fc
  else
    prev_fc = nil
  end
  if not stress_frame and A_PFRAMES and counting and mem:read_u16(A_PFRAMES) > 0 then stress_frame = n + 30 end
  if n == stress_frame and A_STRESS then
    pool_frames_before = mem:read_u16(A_PFRAMES)
    mem:write_u16(A_BACKLOG, 0)
    mem:write_u16(A_FLUSHMAX, 0)
    mem:write_u8(A_STRESS, 1)
    stress_on = true
  end
  local live = A_LIVE and mem:read_u8(A_LIVE) or 0
  full_now = stress_on and live == POOL_MAX and mem:read_u8(flow_addr + O_STATE) == STATE_PLAYING
  if full_now then full_frames = full_frames + 1 end
  if DEMO_RUN then
    local ready = n > 9000
    if not ready then
      ready = true
      for _, dm in pairs(demo_mode) do if dm.frames < DEMO_MIN_FRAMES then ready = false end end
    end
    if ready then
      local ok, parts = bad_vram == 0 and bad_pal == 0 and total_vram > 0, {}
      for name, m in pairs({ arena = K_ARENA, trip = K_TRIP, arcade = K_ARCADE }) do
        local dm = demo_mode[m]
        local bad = dm.frames < DEMO_MIN_FRAMES or dm.lmax >= LOGIC_LIMIT or dm.us > FLUSH_BUDGET_US or dm.pwords > PAL_WORDS_MAX
        if bad then ok = false end
        parts[#parts + 1] = string.format("demo %s: frames %d, logic end max %.1f at demo frame %d (limit %d; frames over %d, first at demo frame %s; max after frame 3: %.1f), flush max %d us (limit %d; after frame 3: %d), VRAM data words per frame max %d (after frame 3: %d), palette words per flush max %d (limit %d)%s",
          name, dm.frames, dm.lmax, dm.idx_lmax, LOGIC_LIMIT, dm.over, tostring(dm.first_over), dm.lmax_late, dm.us, FLUSH_BUDGET_US, dm.us_late, dm.vwords, dm.vw_late, dm.pwords, PAL_WORDS_MAX, bad and " [OVER]" or "")
      end
      local palmax = mem:read_u16(palmax_addr)   -- g_pal_words_frame_max over the whole demo run, boot included
      if palmax > PAL_WORDS_MAX then ok = false end
      parts[#parts + 1] = string.format("demo run: palette words per flush max %d (limit %d)%s", palmax, PAL_WORDS_MAX, palmax > PAL_WORDS_MAX and " [OVER]" or "")
      table.sort(parts)
      finish(ok, string.format("demo run at frame %d, vram writes %d (outside vblank %d), palette writes %d (outside vblank %d)%s\n%s", n, total_vram, bad_vram, total_pal, bad_pal,
        first_bad and (", first bad: " .. first_bad) or "", table.concat(parts, "\n")), bucket_report())
    end
    return
  end
  if n >= END_FRAME then
    local backlog = A_BACKLOG and mem:read_u16(A_BACKLOG) or -1
    local flushmax = A_FLUSHMAX and mem:read_u16(A_FLUSHMAX) or -1
    local pool_ok = A_STRESS ~= nil and POOL_MAX ~= nil and (pool_frames_before or 0) > 0 and full_frames >= MIN_FULL and missed_full == 0
    local pmsg = string.format(
      "; pool: stress from frame %s, frames drawn before stress %d, frames at %s objects %d (missed steps %d), logic end max %.1f lines after vblank end (at max objects %.1f), queue backlog after flush max %d ops, flush max %d us",
      tostring(stress_frame), pool_frames_before or -1, tostring(POOL_MAX), full_frames, missed_full, logic_end, logic_end_full, backlog, flushmax)
    local msg = string.format(
      "vram writes %d (outside vblank %d), palette writes %d (outside vblank %d), vblank length %.0f lines, latest write %.1f lines into vblank, max data words per frame %d, max burst span %.1f lines, PLAYING frames %d, frames without a game step %d of %d, screen %dx%d%s",
      total_vram, bad_vram, total_pal, bad_pal, VB_LEN_S / LINE_S, worst_late, max_words, max_span / LINE_S, playing_frames, missed, steps,
      screen.width, screen.height,
      first_bad and (", first bad: " .. first_bad) or "")
    local palmax = mem:read_u16(palmax_addr)
    msg = msg .. string.format(", palette words per flush max %d (limit %d)", palmax, PAL_WORDS_MAX)
    finish(bad_vram == 0 and bad_pal == 0 and palmax <= PAL_WORDS_MAX and total_vram > 0 and playing_frames >= MIN_PLAYING and missed <= MAX_MISSED and pool_ok, msg .. pmsg, bucket_report())
  end
end)
