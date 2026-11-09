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
-- Env: ROOFLINE_FLOW_ADDR, ROOFLINE_FRAME_ADDR (hex), ROOFLINE_HIT_LAYOUT (hit_probe.c output, first value = flow state offset),
-- ROOFLINE_RESULT (file).
local flow_addr = tonumber(os.getenv("ROOFLINE_FLOW_ADDR"), 16)
local frame_addr = tonumber(os.getenv("ROOFLINE_FRAME_ADDR"), 16)
local result    = os.getenv("ROOFLINE_RESULT")
local lay = {}
for v in (os.getenv("ROOFLINE_HIT_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local O_STATE = lay[1]
local POOL_MAX = lay[9]

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

local function finish(ok, msg)
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("ROOFLINE_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
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

-- Taps: the handles are globals, a tap whose handle is collected stops firing.
tap_vram = mem:install_write_tap(0x3c0000, 0x3c000f, "vram", function(offset, data, mask)
  if not counting then return end
  total_vram = total_vram + 1
  local inv, since = vblank_state()
  if not inv then
    bad_vram = bad_vram + 1
    if not first_bad then
      first_bad = string.format("VRAM reg+%x at %.1f lines before vblank start", offset, screen:time_until_vblank_start():as_double() / LINE_S)
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
tap_fc = mem:install_write_tap(frame_addr, frame_addr + 3, "fc", function(offset, data, mask)
  if not counting then return end
  -- lines after vblank end = active lines - lines left to vblank start; a write inside vblank is an overrun (999)
  local inv = vblank_state()
  local l = inv and 999 or (ACTIVE_LINES - screen:time_until_vblank_start():as_double() / LINE_S)
  if l > logic_end then logic_end = l end
  if full_now and l > logic_end_full then logic_end_full = l end
end)

local playing_frames = 0
local pool_frames_before, full_frames, missed_full = nil, 0, 0
local prev_fc, missed, steps = nil, 0, 0
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
  if n == 320 and coin then coin:set_value(1)
  elseif n == 335 and coin then coin:set_value(0)
  elseif n == 360 and start then start:set_value(1)
  elseif n == 375 and start then start:set_value(0) end
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
    finish(bad_vram == 0 and bad_pal == 0 and total_vram > 0 and playing_frames >= MIN_PLAYING and missed <= MAX_MISSED and pool_ok, msg .. pmsg)
  end
end)
