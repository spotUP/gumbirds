-- Headless Gum Trip view check (make test-trip). Real ROM: coin, Down on the title (selects GUM TRIP), Start, then at least
-- MIN_PLAYING PLAYING frames. Asserts from RAM:
--   T1. Game.mode is TRIP;
--   T2. trip distance (px*65536+frac) grows every frame by the scroll speed (TRIP_SCROLL_START..TRIP_SCROLL_MAX, the previous
--       or the current Trip.speed); the first growth is TRIP_SCROLL_START (49152 raw at distance 0) and never falls;
--   T3. g_cam_px changes every frame or every second frame (never two frames still), by at most 1 px, and the total camera
--       travel equals the distance scrolled (+-1 px);
--   T4. the flier screen x (Flier.x >> 16) stays 0..SCREEN_W-1;
--   T5. zero PLAYING frames without a game step (g_frame_counter advances by 1 and Trip.steps by 1), main loop parked at vblank;
--   T6. the frame logic ends before the visible lines end (write of g_frame_counter, lines after vblank end < 224);
--   T7. (step V2) kill strips: the visible strip sprites (slots TRIP_STRIP_SPRITE.., 22 floor then 22 ceiling) are exactly the 16 px
--       world columns on screen at the scroll, at x = 16 j - px, floor from win_bottom to the screen bottom, ceiling up to win_top,
--       their tiles are tripstrip tiles (rim animated, fill not, palette TRIPSTRIP_PAL_SLOT, flips by column), all hidden in the
--       run-start hold, the LSPC auto-animation speed register reads 5 ticks, and the draw counter g_trip_strip_draws advances.
-- Reports the max VRAM data words per frame. Ends PASS/FAIL with the numbers.
-- Env: BRAWL_FLOW_ADDR, BRAWL_FRAME_ADDR, BRAWL_CAM_ADDR, BRAWL_CAM_SIZE (hex), BRAWL_FLIER_LAYOUT, BRAWL_TRIP_LAYOUT, BRAWL_RIVAL_LAYOUT, BRAWL_RESULT.
local flow_addr  = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local frame_addr = tonumber(os.getenv("BRAWL_FRAME_ADDR"), 16)
local cam_addr   = tonumber(os.getenv("BRAWL_CAM_ADDR"), 16)
local cam_size   = tonumber(os.getenv("BRAWL_CAM_SIZE") or "", 16)
local result     = os.getenv("BRAWL_RESULT")
local function nums(name) local t = {} for v in (os.getenv(name) or ""):gmatch("%d+") do t[#t + 1] = tonumber(v) end return t end
local flay, tlay = nums("BRAWL_FLIER_LAYOUT"), nums("BRAWL_TRIP_LAYOUT")
local O_FX, O_FY = flay[6], flay[7]
local O_STATE, O_MODE, O_PX, O_FRAC, O_SPEED, O_STEPS = tlay[1], tlay[2], tlay[3], tlay[4], tlay[5], tlay[6]
local SPEED_MIN, SPEED_MAX, SCREEN_W, ARENA_W = tlay[7], tlay[8], tlay[9], tlay[10]
local O_HOLD, O_MADE = tlay[11], tlay[12]   -- Game.trip_hold (run-start hold steps taken), Game.trip_gen.made (chunks built)
local R_RING, R_CSIZE, R_HEAD, R_COUNT = tlay[13], tlay[14], tlay[15], tlay[16]            -- Game.trip_gen.ring, sizeof(TripChunk), head, count
local C_WX, C_IPRES, C_IX, C_IY, C_IW = tlay[17], tlay[18], tlay[19], tlay[20], tlay[21]    -- TripChunk.wx, island.present/x/y/w
local BLOCK, RING, ISLAND_SPRITE, ISLAND_COUNT, LINE_ROW = tlay[22], tlay[23], tlay[24], tlay[25], tlay[26]
local TRIPDRAWS_ADDR = tonumber(os.getenv("BRAWL_TRIPDRAWS_ADDR"), 16)   -- g_island_trip_draws (u16), the draw code's sentinel
local ARENADRAWS_ADDR = tonumber(os.getenv("BRAWL_ISLANDDRAWS_ADDR"), 16) -- g_island_draws (u16), the arena island code's sentinel
local R_NEXTWX = tlay[27]   -- Game.trip_gen.next_wx
local S_BASE, S_TILES, S_PAL, S_SPRITE, S_COUNT, S_STEP = tlay[28], tlay[29], tlay[30], tlay[31], tlay[32], tlay[33]
local C_WTOP, C_WBOT, CHUNK_PX, S_BOTTOM, S_COLS = tlay[34], tlay[35], tlay[36], tlay[37], tlay[38]
local P_BASE, P_TILES, P_PAL, P_SPRITE, P_COUNT = tlay[39], tlay[40], tlay[41], tlay[42], tlay[43]   -- trip pickup tiles, palette slot, sprites
local C_PPRES, C_PX, C_PY, P_LEFT, P_TOP, P_TICKS, P_FRAMES = tlay[44], tlay[45], tlay[46], tlay[47], tlay[48], tlay[49], tlay[50]
local HZ = { base = tlay[51], tiles = tlay[52], pal = tlay[53], paln = tlay[54], sprite = tlay[55], cols = tlay[56],   -- trip hazard tiles, palette slots, first pool sprite, sprites per object
  nhaz = tlay[57], haz = tlay[58], size = tlay[59], kind = tlay[60], x = tlay[61], y = tlay[62], amp = tlay[63], phase = tlay[64],
  near = tlay[65], near_n = tlay[66], step = tlay[67],
  rlay = nums("BRAWL_RIVAL_LAYOUT"),
  draws_addr = tonumber(os.getenv("BRAWL_HAZDRAWS_ADDR"), 16) }   -- g_trip_haz_draws (u16)
local METERDRAWS_ADDR = tonumber(os.getenv("BRAWL_METERDRAWS_ADDR"), 16)   -- g_meter_draws (u16)
local METERTAB_ADDR = tonumber(os.getenv("BRAWL_METERTAB_ADDR"), 16)   -- tripmeter_cell[step][cell] (u16 each, in the cart ROM)
local PICKUPDRAWS_ADDR = tonumber(os.getenv("BRAWL_PICKUPDRAWS_ADDR"), 16)   -- g_trip_pickup_draws (u16)
-- Pickup idle bob and collect effect (step V6). The bob table is restated from the art spec (draft, per idle frame); the collect sprite
-- shows frame f = (steps - start) >> 2 of the collect clip (32 x 32, top = pickup.y - 16) after the pickup is taken, tiles read from the ROM.
local PK = { tiles = tonumber(os.getenv("BRAWL_PICKUPTILES_ADDR"), 16), frames = tonumber(os.getenv("BRAWL_PICKUPFRAMES_ADDR"), 16),
  fsize = tlay[73], toff = tlay[74], cframes = tlay[75], cticks = tlay[76], ctop = 16,
  bob = { [0] = -2, -1, 0, 1, 3, 3, 3, 2, 1, 0, -1, -1, -2, -2, -2, -2 },
  fx = {}, fx_checked = 0, fx_vis = 0, fx_bad = 0, fx_first = nil, fx_tile_bad = 0, fx_seen = {}, fx_n = 0, bob_seen = {}, bob_n = 0 }
local STRIPDRAWS_ADDR = tonumber(os.getenv("BRAWL_STRIPDRAWS_ADDR"), 16)   -- g_trip_strip_draws (u16)
local MAX_HOLD = 3
local MODE_TRIP = 1
local MIN_PLAYING = 400
SPLASH_T = { live = 0 }   -- Gum Trip floor death splash check (phase done)
local MAX_MISSED = 0
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
local down  = field(":edge:joy:JOY1", "P1 Down")
local abtn  = field(":edge:joy:JOY1", "P1 A")
local function s32(v) return v >= 0x80000000 and v - 0x100000000 or v end
local function finish(ok, msg)
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  if PC_DUMP then PC_DUMP() end   -- opt-in PC profile (BRAWL_PC_LOG), defined at the end of this file
  manager.machine:exit()
end

local LINE_S = screen.scan_period
local VB_LEN_S = nil
local function in_vblank()
  return screen:time_until_vblank_end():as_double() < screen:time_until_vblank_start():as_double()
end
local counting = false
local logic_end = 0
local frame_l = 0   -- logic end of the frame being finished (reset every frame)
local cat_max, cat_at, since_ready = { hold = 0, early = 0, steady = 0 }, {}, 0
local EARLY_FRAMES = 30   -- frames after the hold counted as the first frames after ready
local words, max_words = 0, 0
local lspc_mode = nil   -- last write of REG_LSPCMODE (bits 15..8 = auto-animation ticks - 1)
local vram, vaddr, vmod = {}, 0, 1   -- shadow of the sprite control RAM, rebuilt from the LSPC writes
-- Flush probe (measurement only, nothing here reaches the verdict): per flush (VRAM data writes between two logic-end taps) the emulated time span
-- of the writes, the model value g_last_us, words per vq_probe bucket, binned by Trip.steps & 3 read at the tap that opened the flush.
-- Optional env: BRAWL_LASTUS_ADDR (g_last_us), BRAWL_VQ_LAYOUT (vq_probe.c); without them the probe is off.
local PF = { lastus = tonumber(os.getenv("BRAWL_LASTUS_ADDR") or "", 16), vq = nums("BRAWL_VQ_LAYOUT"), n = 0, steps = nil,
  words = 0, t0 = nil, t1 = nil, buckets = {}, bins = {}, measured = 0, skipped = 0, late = 0, first_ts = nil, max = nil, dmin = nil, prev_t = nil, off64 = 0, over = 0, worst = 0 }
PF.on = PF.lastus ~= nil and #PF.vq == 24
PF.names, PF.slot = { "unowned" }, {}
function PF.range(name, a, b) PF.names[#PF.names + 1] = name; for s = a, b - 1 do PF.slot[s] = #PF.names end end
if PF.on then
  local V = PF.vq
  PF.range("bg_sky", V[6], V[7]); PF.range("bg_far", V[7], V[8]); PF.range("bg_mida", V[8], V[9]); PF.range("bg_midb", V[9], V[10])
  PF.range("bg_near", V[10], V[11]); PF.range("island", V[12], V[13]); PF.range("pool", V[14], V[15]); PF.range("hero", V[16], V[17])
  PF.range("hazard", V[18], V[19]); PF.range("fg_rain", V[20], V[21]); PF.range("fg_spray", V[21], V[22])
  PF.range("trip_strip", V[22], V[23]); PF.range("trip_pickup", V[23], V[24])
end
function PF.bucket(a)   -- VRAM address to a bucket name (same address split as vblank_check.lua vram_row)
  if a < 0x7000 then return PF.names[PF.slot[a >> 6] or 1] .. "/tiles"
  elseif a < 0x7500 then return "fix"
  elseif a >= 0x8000 and a < 0x8600 then return PF.names[PF.slot[(a - 0x8000) & 0x1ff] or 1] .. "/scb" end
  return "other"
end
function PF.write(a)
  local t = manager.machine.time:as_double()
  if not PF.t0 then PF.t0 = t end
  if PF.prev_t and t > PF.prev_t and (not PF.dmin or t - PF.prev_t < PF.dmin) then PF.dmin = t - PF.prev_t end
  PF.prev_t = t; PF.t1 = t; PF.words = PF.words + 1
  local b = PF.bucket(a); PF.buckets[b] = (PF.buckets[b] or 0) + 1
end
function PF.close(late)   -- called at a logic-end tap; closes the flush opened by the previous tap
  if PF.steps ~= nil then
    if late then PF.late = PF.late + 1 end
    -- first flush that carries any trip_strip word = the first Gum Trip frame's queue (boot owns the sprite setup, see trip_strip_init)
    if PF.first_ts == nil and ((PF.buckets["trip_strip/scb"] or 0) > 0 or (PF.buckets["trip_strip/tiles"] or 0) > 0) then PF.first_ts = PF.buckets["trip_strip/scb"] or 0 end
    if late or PF.words == 0 then PF.skipped = PF.skipped + 1 else
      local span = (PF.t1 - PF.t0) * 1e6
      if math.abs(span / 64 - math.floor(span / 64 + 0.5)) > 0.02 then PF.off64 = PF.off64 + 1 end
      local model = mem:read_u16(PF.lastus)
      local bin = PF.bins[PF.steps & 3] or { n = 0, span = 0, smax = 0, model = 0, mmax = 0, wmax = 0, bsum = {} }
      PF.bins[PF.steps & 3] = bin
      bin.n = bin.n + 1; bin.span = bin.span + span; bin.model = bin.model + model
      if span > bin.smax then bin.smax = span end
      if model > bin.mmax then bin.mmax = model end
      if PF.words > bin.wmax then bin.wmax = PF.words end
      for k, v in pairs(PF.buckets) do bin.bsum[k] = (bin.bsum[k] or 0) + v end
      PF.measured = PF.measured + 1
      if span > model * 1.03 + 70 then PF.over = PF.over + 1; PF.worst = math.max(PF.worst, span - model * 1.03 - 70) end   -- modeled cost must not undercut the measured span
      if not PF.max or span > PF.max.span then PF.max = { span = span, model = model, n = PF.n, steps = PF.steps, words = PF.words, buckets = PF.buckets } end
    end
  end
  PF.words, PF.t0, PF.t1, PF.prev_t, PF.buckets = 0, nil, nil, nil, {}
end
function PF.row(b, div) local t = {} for k, v in pairs(b) do t[#t + 1] = string.format("%s=%.1f", k, v / div) end table.sort(t) return table.concat(t, " ") end
PF_FIRST_TS_LIMIT, PF_SPAN_LIMIT = 88, 2000   -- limits: SCB words of the first Trip frame (was 88 before trip_strip_init), GFX_FLUSH_BUDGET_US
function PF.ok()
  if not PF.on then return true end
  return PF.first_ts ~= nil and PF.first_ts < PF_FIRST_TS_LIMIT and PF.max ~= nil and PF.max.span <= PF_SPAN_LIMIT and PF.over == 0
end
function PF.report()
  if not PF.on then return "; TRIP_FLUSH off (BRAWL_LASTUS_ADDR / BRAWL_VQ_LAYOUT missing)" end
  local o = { string.format("; logic end max %.1f at %s", PF.le_max or -1, tostring(PF.le_at)), string.format("; TRIP_FLUSH measured %d skipped %d late %d, first Trip frame trip_strip/scb words %s (want < %d), max span %.0f us (want <= %d), smallest nonzero gap between write times %.3f us, spans not a multiple of 64 us: %d, flushes with span > model*1.03+70: %d (worst excess %.0f us)", PF.measured, PF.skipped, PF.late, tostring(PF.first_ts), PF_FIRST_TS_LIMIT, PF.max and PF.max.span or -1, PF_SPAN_LIMIT, (PF.dmin or 0) * 1e6, PF.off64, PF.over, PF.worst) }
  for b = 0, 3 do local x = PF.bins[b]; if x then
    o[#o + 1] = string.format("; TRIP_FLUSH steps&3=%d: count %d, span mean %.0f max %.0f us, model mean %.0f max %d us, words max %d, mean words per bucket: %s", b, x.n, x.span / x.n, x.smax, x.model / x.n, x.mmax, x.wmax, PF.row(x.bsum, x.n))
  end end
  local m = PF.max
  if m then o[#o + 1] = string.format("; TRIP_FLUSH max span %.0f us at frame %d, steps %d (&3=%d), words %d, model %d us, span/model %.2f, buckets: %s", m.span, m.n, m.steps, m.steps & 3, m.words, m.model, m.span / math.max(m.model, 1), PF.row(m.buckets, 1)) end
  return table.concat(o, "")
end
tap_vram = mem:install_write_tap(0x3c0000, 0x3c000f, "tripvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 4 then vmod = data
  elseif r == 6 then lspc_mode = data
  elseif r == 2 then if counting and PF.on then PF.write(vaddr) end vram[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff end
  if (offset & 0xf) == 2 or (offset & 0xf) == 3 then words = words + 1 end
end)
tap_fc = mem:install_write_tap(frame_addr, frame_addr + 3, "tripfc", function(offset, data, mask)
  if not counting or (offset & 2) == 0 then return end   -- the u32 frame counter is two bus writes: count the second (low word) only
  local l = in_vblank() and 999 or (224 - screen:time_until_vblank_start():as_double() / LINE_S)
  if PF.on then PF.close(l == 999); PF.steps = mem:read_u32(flow_addr + O_STEPS) end
  if l > logic_end then logic_end = l end
  if l > frame_l then frame_l = l end
end)

local function read_cam() if cam_size == 2 then return mem:read_u16(cam_addr) else return mem:read_u8(cam_addr) end end
local function dist() return (mem:read_u32(flow_addr + O_PX)) * 65536 + mem:read_u32(flow_addr + O_FRAC) end

local n, phase, phase_at = 0, "boot", 0
local playing, missed = 0, 0
local prev_fc, prev_steps, prev_dist, prev_speed, prev_cam
local grow_bad, first_grow = 0, nil
local ramp_bad, ramp_checked, first_g, prev_g = 0, 0, nil, nil
local still_run, max_still, cam_bad, first_cam = 0, 0, 0, nil
local cam_total, dist_total = 0, 0
local min_sx, max_sx, off_screen, first_off = 1e9, -1e9, 0, nil
local mode_bad, steps_bad = 0, 0
local left_early, left_msg = false, nil
local prev_hold, prev_made = nil, nil
local hold_frames, hold_bad = 0, 0
local isl_checked, isl_vis, isl_bad, isl_first = 0, 0, 0, nil
local draws0, arena0, draws1, arena1
local want_prev, strip_prev, strip_prev_px
local strip0, strip1
local function s16(v) return v >= 0x8000 and v - 0x10000 or v end
-- Expected state of the island sprite slots (0..ISLAND_COUNT-1) from the core state in RAM: a table slot -> {x, y} for every
-- generated island column that is on screen at scroll px, nothing for the others.
local function island_expect(px)
  local want = {}
  -- the view reads no chunk until game_trip_ready (tripgen_covers: next_wx >= px + 320): nothing is shown before
  if mem:read_u32(flow_addr + R_NEXTWX) < px + SCREEN_W then return want end
  local head, count = mem:read_u8(flow_addr + R_HEAD), mem:read_u8(flow_addr + R_COUNT)
  for k = 0, count - 1 do
    local r = (head + k) % RING
    local base = flow_addr + R_RING + r * R_CSIZE
    if mem:read_u8(base + C_IPRES) ~= 0 then
      local wx, ix, iy, w = mem:read_u32(base + C_WX), s16(mem:read_u16(base + C_IX)), s16(mem:read_u16(base + C_IY)), mem:read_u8(base + C_IW)
      for c = 0, ((w + 15) >> 4) - 1 do
        local sx = wx + ix + 16 * c - px
        if sx > -16 and sx < SCREEN_W then want[r * BLOCK + c] = { x = sx, y = iy - LINE_ROW } end
      end
    end
  end
  return want
end

-- Kill strip expectation (an independent restatement of the spec, not the core code): for every 16 px world column j inside a live
-- chunk and on screen (x = 16 j - px in -15..319): floor rows (224 - win_bottom + 15) // 16 from y win_bottom, ceiling rows
-- (win_top + 15) // 16 ending at y win_top. Keyed "side x y rows", counted as a multiset.
local function strip_expect(px)
  local want, n = {}, 0
  if mem:read_u32(flow_addr + R_NEXTWX) < px + SCREEN_W then return want, px end
  local head, count = mem:read_u8(flow_addr + R_HEAD), mem:read_u8(flow_addr + R_COUNT)
  for k = 0, count - 1 do
    local base = flow_addr + R_RING + ((head + k) % RING) * R_CSIZE
    local wx, wt, wb = mem:read_u32(base + C_WX), s16(mem:read_u16(base + C_WTOP)), s16(mem:read_u16(base + C_WBOT))
    for j = wx // 16, (wx + CHUNK_PX) // 16 - 1 do
      local x = 16 * j - px
      if x > -16 and x < SCREEN_W then
        local fr = wb < S_BOTTOM and math.min(14, (S_BOTTOM - math.max(wb, 0) + 15) // 16) or 0
        local cr = wt > 0 and math.min(14, (wt + 15) // 16) or 0
        if fr > 0 then local key = string.format("F %d %d %d", x, wb, fr); want[key] = (want[key] or 0) + 1 end
        if cr > 0 then local key = string.format("C %d %d %d", x, wt - 16 * cr, cr); want[key] = (want[key] or 0) + 1 end
      end
    end
  end
  return want, px
end

-- Pickup expectation (restated from the spec, not the core code): a live chunk with pickup.present shows 2 sprite columns of 2 tiles at
-- x = wx + pickup.x - px - 16 (+16 for the second), top y = pickup.y - 20, when -32 < x < 320; nothing before the course is ready.
-- The ring slot r owns sprites P_SPRITE + 2 r and + 1. Keyed by slot so a collected pickup's slot must read hidden.
local pk_prev, pk_checked, pk_vis, pk_bad, pk_first, pk_tile_bad, pk_tile_first, pk_hold_vis = nil, 0, 0, 0, nil, 0, nil, 0
local pk_seen, pk_collected, pk_anim = {}, 0, {}
local pk_draws0, pk_draws1
-- Hazard expectation (restated from the spec, not the core code): hazard i of the chunk in ring slot r is pool object 3 r + i, drawn
-- from sprite HZ.sprite + 3 * (3 r + i) on (one sprite per 16 px column, art cell cols x rows tiles: coal 2x2, vent 2x3, cloud 3x3
-- for kind 0, 1, 2). Art left = wx + haz.x - px - cx, top = swept y - cy, (cx, cy) = gameplay centre inside the art cell, swept y =
-- haz.y + ((round(32767 sin(2 pi a / 256)) * amp) // 32768 (floor; Lua >> is logical)), a = (phase + steps * HZ.step) & 255. Shown when left > -16 cols and
-- left < 320; all other objects and everything before the course is ready read hidden.
local HZ_ART = { [0] = { cols = 2, rows = 2, cx = 13, cy = 18 }, [1] = { cols = 2, rows = 3, cx = 16, cy = 18 }, [2] = { cols = 3, rows = 3, cx = 25, cy = 20 } }
local hz_checked, hz_vis, hz_bad, hz_first, hz_tile_bad, hz_tile_first, hz_hold_vis, hz_kinds, hz_tops = 0, 0, 0, nil, 0, nil, 0, {}, {}
local hz_prev, hz_draws0, hz_draws1
local near_trip_vis, near_title_vis = 0, 0
local function near_visible()
  local c = 0
  for i = 0, HZ.near_n - 1 do if ((vram[0x8200 + HZ.near + i] or 0) & 0x3f) ~= 0 then c = c + 1 end end
  return c
end
-- Far background plane (src/sprite_slots.h BG_FAR_SPRITE 21, BG_FAR_COUNT 21): Gum Trip hides it (bg_trip_planes), height 0 in every SCB3 word.
HZ.far_first, HZ.far_count, HZ.far_trip, HZ.far_title = 21, 21, 0, 0   -- in HZ: the main chunk is at its 200 local variable limit
-- Option D (thoughts/spot/2026-11-11-trip-holes-option-d-plan.md): in Gum Trip the backdrop (palette RAM entry 4095, 0x401FFE) is the sky plane
-- colour (115,82,165) = 5 bit (14,10,20) = NG word 0x075A; every other state keeps #1a1238 = 0x5113. The mid B bottom row that only the hidden
-- near plane covered is drawn again: SCB3 heights below (importer, near is not cover for mid B) and a tile in the last row of every column.
HZ.BD_ADDR, HZ.BD_ARENA, HZ.BD_TRIP = 0x401FFE, 0x5113, 0x075A
HZ.START_FC = tonumber(os.getenv("BRAWL_TRIP_START_FC") or "") or 400   -- g_frame_counter at which Start is pressed (course seed pin)
HZ.midb_rows = { 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 3, 4, 4, 4, 4, 4, 4, 4, 4 }   -- SCB3 height of mid B column 0..22 (sum 89 with the looping planes art; was 76 before near stopped covering mid B)
HZ.midb_row0 = { 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0 }   -- first tile row of each column (column 21 now starts at row 0 with the looping planes art)
HZ.bd_title, HZ.bd_trip_bad, HZ.bd_trip_n, HZ.midb_bad, HZ.midb_first = nil, 0, 0, 0, nil
function HZ.midb_check()
  for c = 0, tlay[78] - 1 do
    local slot = tlay[77] + c
    local h = (vram[0x8200 + slot] or 0) & 0x3f
    local last = (vram[slot * 64 + 2 * (h - 1)] or 0)   -- SCB1 tile word of the column's last drawn row
    if h ~= HZ.midb_rows[c + 1] or last == 0 then
      HZ.midb_bad = HZ.midb_bad + 1
      HZ.midb_first = HZ.midb_first or string.format("column %d height %d want %d, last row tile 0x%04x", c, h, HZ.midb_rows[c + 1], last)
    end
  end
end
function HZ.far_visible()
  local c = 0
  for i = 0, HZ.far_count - 1 do if ((vram[0x8200 + HZ.far_first + i] or 0) & 0x3f) ~= 0 then c = c + 1 end end
  return c
end
-- Sprites per scanline in the real ROM (printed, not asserted yet): every PLAYING frame the SCB3/SCB4 shadow of sprites 0..380 is
-- counted per line by the shared counter of the sprite peak check (tests/mame/sprite_line_count.lua), split by slot range.
local LN = { frame_worst = 0 }   -- one local for the whole block (the main chunk is at the 200 locals limit)
do
local line_count = dofile(((debug and debug.getinfo and debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")) or "tests/mame") .. "/sprite_line_count.lua")
local LINE_RANGES = {   -- name, first, last + 1 (src/sprite_slots.h; hazards are pool objects 0..14, rivals the later pool objects)
  { "reserved", 0, 1 }, { "planes", 1, 111 }, { "islands", 120, 161 }, { "hazards", 161, 206 }, { "pool_rest", 206, 257 }, { "hero", 257, 260 },
  { "arena_strip", 260, 323 }, { "trip_strip", 323, 367 }, { "pickups", 367, 377 }, { "tail", 377, 381 } }
local line_worst = { v = 0, y = 0, frame = 0, split = {}, screen = 0 }   -- screen: worst line counting only sprites on screen in x (printed)
local line_class = {}
for _, r in ipairs(LINE_RANGES) do line_class[r[1]] = 0 end
local line_frames = 0
function LN.count(frame)
  local per, tot, tot_scr = {}, {}, {}
  for y = 0, 223 do tot[y] = 0; tot_scr[y] = 0 end
  for i, r in ipairs(LINE_RANGES) do
    local scr
    per[i], scr = line_count.count(vram, r[2], r[3])
    for y = 0, 223 do
      tot[y] = tot[y] + per[i][y]
      tot_scr[y] = tot_scr[y] + scr[y]
      if per[i][y] > line_class[r[1]] then line_class[r[1]] = per[i][y] end
    end
  end
  line_frames = line_frames + 1
  LN.frame_worst = 0
  for y = 0, 223 do
    if tot[y] > LN.frame_worst then LN.frame_worst = tot[y] end
    local gp = per[4][y] + per[5][y] + per[6][y]   -- the gameplay budget row (pool + hero, 161..259) on one line, against SB_GAMEPLAY_PER_LINE
    if gp > (LN.gp_max or 0) then LN.gp_max = gp end
    if tot_scr[y] > line_worst.screen then line_worst.screen = tot_scr[y] end
    if tot[y] > line_worst.v then
      line_worst.v, line_worst.y, line_worst.frame = tot[y], y, frame
      for i, r in ipairs(LINE_RANGES) do line_worst.split[i] = per[i][y] end
    end
  end
end
-- Gum meter (HUD row 6, fix cells 2..6, replaces the Balloons row in Gum Trip): the five cells in the fix layer must be the table
-- entries for the step of the gum value of the previous sample (the draw of a frame is flushed before the next sample), the cells where
-- the Balloons text and number used to be must stay blank, and g_meter_draws must have moved once per observed step change.
LN.meter = { checked = 0, bad = 0, first = nil, blank_bad = 0, changes = 0, steps = {}, last = nil, draws0 = nil, draws1 = 0, prev_gum = nil }
function LN.meter_sample(playing)
  local M = LN.meter
  local gum = mem:read_u16(flow_addr + tlay[69])
  if M.prev_gum and playing >= 3 then
    local g = M.prev_gum
    if g > 1024 then g = 1024 end
    local step = (g + 127) // 128                       -- independent of trip_view_meter_step: spec "ceil(gum / 128), 1024 = 8"
    local bad
    for c = 0, tlay[71] - 1 do
      local want = (tlay[72] << 12) | mem:read_u16(METERTAB_ADDR + (step * tlay[71] + c) * 2)
      local got = vram[0x7000 + (2 + c) * 32 + 6]
      if got ~= want then bad = bad or string.format("cell %d at frame %d: got 0x%04x want 0x%04x (gum %d step %d)", c, playing, got or -1, want, g, step) end
    end
    M.checked = M.checked + 1
    if bad then M.bad = M.bad + 1; M.first = M.first or bad end
    for c = 7, 11 do if ((vram[0x7000 + c * 32 + 6] or 255) & 0xfff) ~= 255 then M.blank_bad = M.blank_bad + 1 end end
    if M.last and step ~= M.last then M.changes = M.changes + 1 end
    M.last = step
    M.steps[step] = true
  end
  M.prev_gum = gum
  if playing == 1 then M.draws0 = mem:read_u16(METERDRAWS_ADDR) end
  M.draws1 = mem:read_u16(METERDRAWS_ADDR)
end
function LN.meter_result()
  local M = LN.meter
  local n = 0
  for _ in pairs(M.steps) do n = n + 1 end
  local dr = (M.draws1 - (M.draws0 or 0)) % 65536
  local ok = M.bad == 0 and M.blank_bad == 0 and M.checked >= 400 and n >= 3 and M.changes >= 2 and dr >= M.changes
  return ok, string.format("; gum meter: frames checked %d (want >= 400), bad %d (want 0; first: %s), Balloons cells not blank %d (want 0), steps seen %d (want >= 3), step changes %d (want >= 2), draws %d (want >= changes)",
    M.checked, M.bad, tostring(M.first), M.blank_bad, n, M.changes, dr)
end
function LN.message(kinds)
  local parts = {}
  for i, r in ipairs(LINE_RANGES) do parts[#parts + 1] = string.format("%s %d (alone max %d)", r[1], line_worst.split[i] or 0, line_class[r[1]]) end
  return string.format("; gameplay range (pool + hero) per line max %d (printed; SB_GAMEPLAY_PER_LINE)", LN.gp_max or 0) .. string.format("; ROM sprites per line (printed, not asserted): worst %d (every sprite with height > 0) at line %d, PLAYING frame %d of %d counted; worst counting only sprites on screen in x %d; split %s; hazard kinds seen on screen %s; hardware limit 96, SB_LIMIT 90",
    line_worst.v, line_worst.y, line_worst.frame, line_frames, line_worst.screen, table.concat(parts, ", "), kinds)
end
-- Gum Trip rivals (tests/mame/rival_probe.c layout, BRAWL_RIVAL_LAYOUT): all state in HZ.rv (the main chunk is at the 200 locals limit).
HZ.rv = (function()
local rlay = HZ.rlay
local RV = { seen = {}, sprites_seen = 0, worst_line = 0, pop_ok = nil, pop_msg = "no pop tried",
             forced = false, was_act = {}, bad = {}, bands = {}, next_pop_try = 0, rpop0 = nil }
local R_MODE, R_BONUS, R_HX, R_HY, R_HSTATE, R_HBAL, R_NEXT, R_SPAWNED, R_POPPED, R_RETIRED = table.unpack(rlay, 1, 10)
local R_BASE, R_SIZE, R_ACTIVE, R_VAR, R_FX, R_FY, R_FBAL, R_FSTATE = table.unpack(rlay, 11, 18)
local R_MAX, R_POP, R_BONE, R_BRUISER, R_OBJBASE, R_SPRBASE, R_COLS, R_LIMIT, R_HVY = table.unpack(rlay, 19, 27)
local function rv8(o) return mem:read_u8(flow_addr + o) end
local function rv32(o) return mem:read_u32(flow_addr + o) end
-- T8 window clamp: in Gum Trip the tunnel rock above win_top and below win_bottom is solid for the hero and the rivals. At every
-- PLAYING sample the hero and each active rival below FLIER_FALLING must have their body box (half height (flier_half_h >> 16) + 1,
-- half width FLIER_HALF_W) inside the intersection of the windows of the chunks the box overlaps (TripChunk.wx, win_top, win_bottom
-- read from RAM; the constants come from trip_probe.c, nothing copied).
local W_BAL, W_NOBAL, W_HALFW, W_FALLING = tlay[79], tlay[80], tlay[81], tlay[82]
local W_CEIL, W_DROP = tlay[83], tlay[84]   -- FLIER_CEILING_FEET_Y: the flier's feet stop at win_top + this (the whole flier with its gum stays under the rock); FLIER_RIVAL_CEILING_DROP is printed only
local WINCALLS_ADDR = tonumber(os.getenv("BRAWL_WINCALLS_ADDR") or "", 16)    -- g_trip_window_calls (u16)
local WINCLAMP_ADDR = tonumber(os.getenv("BRAWL_WINCLAMP_ADDR") or "", 16)    -- g_trip_window_clamps (u16)
local WN = { checked = 0, riv_checked = 0, bad = 0, first = nil, calls0 = nil, calls1 = nil, clamps0 = nil, clamps1 = nil, frames = 0, empty = 0 }
local function win_check(x16, y16, bal, state, who, frame)
  if state >= W_FALLING then return end
  local fh = ((bal ~= 0) and W_BAL or W_NOBAL) // 65536 + 1
  local px = mem:read_u32(flow_addr + O_PX)
  local head, count = mem:read_u8(flow_addr + R_HEAD), mem:read_u8(flow_addr + R_COUNT)
  local top, bot, any = -32768, 32767, false
  local fx = s32(x16) // 65536
  for k = 0, count - 1 do
    local base = flow_addr + R_RING + ((head + k) % RING) * R_CSIZE
    local rel = (px - mem:read_u32(base + C_WX)) + fx
    if not (rel + W_HALFW < 0 or rel - W_HALFW > CHUNK_PX - 1) then
      top = math.max(top, s16(mem:read_u16(base + C_WTOP)))
      bot = math.min(bot, s16(mem:read_u16(base + C_WBOT)))
      any = true
    end
  end
  -- lowest allowed centre: feet line win_top + FLIER_CEILING_FEET_Y minus the half height (exact 16.16, was top + fh). A computer flier
  -- may stand on the hero line (window too small for the drop, or began above its lowered line), so the hero line bounds both.
  local lo16 = (top + W_CEIL) * 65536 - ((bal ~= 0) and W_BAL or W_NOBAL)
  if not any or lo16 > (bot - 1 - fh) * 65536 then WN.empty = WN.empty + 1 return end
  local y = s32(y16)
  WN.checked = WN.checked + 1
  if who ~= "hero" then WN.riv_checked = WN.riv_checked + 1 end
  if y < lo16 or y > (bot - 1 - fh) * 65536 then
    WN.bad = WN.bad + 1
    WN.first = WN.first or string.format("%s y %.2f outside rows %.2f..%d (win_top %d win_bottom %d, half height %d) at frame %d", who, y / 65536, lo16 / 65536, bot - 1 - fh, top, bot, fh, frame)
  end
end
function RV.rival(i) return R_BASE + i * R_SIZE end
-- sprite range of rival slot i: pool object R_OBJBASE + i owns sprites R_SPRBASE + (R_OBJBASE+i)*R_COLS .. +R_COLS-1
function RV.visible(i)
  local first = R_SPRBASE + (R_OBJBASE + i) * R_COLS
  local per = line_count.count(vram, first, first + R_COLS)
  local n = 0
  for y = 0, 223 do if per[y] > 0 then n = n + 1 end end
  return n > 0
end
-- Called once per PLAYING frame (Gum Trip), next to LN.meter_sample(playing) (trip_check.lua ~line 560).
function RV.sample(playing)
  if rv8(R_MODE) ~= 1 then return end
  WN.frames = WN.frames + 1
  if WINCALLS_ADDR then
    if WN.frames == 1 then WN.calls0, WN.clamps0 = mem:read_u16(WINCALLS_ADDR), mem:read_u16(WINCLAMP_ADDR) end
    WN.calls1, WN.clamps1 = mem:read_u16(WINCALLS_ADDR), mem:read_u16(WINCLAMP_ADDR)
  end
  if playing > 3 then
    win_check(rv32(R_HX), rv32(R_HY), rv8(R_HBAL), rv8(R_HSTATE), "hero", playing)
    for i = 0, R_MAX - 1 do
      if rv8(RV.rival(i) + R_ACTIVE) ~= 0 then win_check(rv32(RV.rival(i) + R_FX), rv32(RV.rival(i) + R_FY), rv8(RV.rival(i) + R_FBAL), rv8(RV.rival(i) + R_FSTATE), "rival " .. i, playing) end
    end
  end
  -- force the first spawn early: next_px = 0 makes trip_rivals_step spawn on its next call (one time)
  if not RV.forced and playing == 60 then mem:write_u32(flow_addr + R_NEXT, 0); RV.forced = true end
  local any_active = false
  for i = 0, R_MAX - 1 do
    local act = rv8(RV.rival(i) + R_ACTIVE)
    local vis = RV.visible(i)
    if act ~= 0 then
      any_active = true
      RV.seen[i] = true
      local var = rv8(RV.rival(i) + R_VAR)
      RV.bands[var] = (RV.bands[var] or 0) + 1
      if vis then RV.sprites_seen = RV.sprites_seen + 1 end
    elseif vis and playing > 5 and not RV.was_act[i] then
      -- VRAM shows the previous frame's draw: the frame a rival retires still shows it, so only a rival inactive for 2 samples counts
      RV.bad[#RV.bad + 1] = string.format("rival %d sprites visible while inactive (frame %d)", i, playing)
    end
    RV.was_act[i] = (act ~= 0)
  end
  -- pop result: judged on the sample after each teleport (the stomp runs in the game step, the rival has lost its balloon by now);
  -- baseline is re-taken at every teleport so a pickup between tries cannot skew the bonus delta
  if RV.pop_ok == nil and RV.rpop0 and RV.rpop0.try > 0 then
    if rv32(R_POPPED) == RV.rpop0.popped + 1 then
      local dbonus = rv32(R_BONUS) - RV.rpop0.bonus
      RV.pop_ok = (dbonus == R_POP)
      RV.pop_msg = string.format("pop: popped +1 after %d tries, bonus delta %d (want %d)", RV.rpop0.try, dbonus, R_POP)
    elseif RV.rpop0.try > 120 then
      RV.pop_ok = false
      RV.pop_msg = "pop: no stomp registered after 120 teleports next to the rival"
    end
  end
  -- pop: put the hero 25 px above rival 0 (stomp window dy -30..-21), falling; expect popped +1 and bonus +R_POP
  if RV.pop_ok == nil and any_active and rv8(RV.rival(0) + R_ACTIVE) ~= 0 and rv8(RV.rival(0) + R_VAR) == 0
     and rv8(RV.rival(0) + R_FBAL) == 1 and playing >= RV.next_pop_try then
    if RV.rpop0 == nil then RV.rpop0 = { try = 0 } end
    RV.rpop0.popped, RV.rpop0.bonus = rv32(R_POPPED), rv32(R_BONUS)
    RV.rpop0.try = RV.rpop0.try + 1
    RV.dbg = string.format("last try %d: hero x %.1f y %.1f vy %d state %d bal %d | rival x %.1f y %.1f state %d bal %d", RV.rpop0.try,
      rv32(R_HX) / 65536, rv32(R_HY) / 65536, s32(rv32(R_HVY)), rv8(R_HSTATE), rv8(R_HBAL),
      rv32(RV.rival(0) + R_FX) / 65536, rv32(RV.rival(0) + R_FY) / 65536, rv8(RV.rival(0) + R_FSTATE), rv8(RV.rival(0) + R_FBAL))
    mem:write_u32(flow_addr + R_HX, mem:read_u32(flow_addr + RV.rival(0) + R_FX))
    mem:write_u32(flow_addr + R_HY, mem:read_u32(flow_addr + RV.rival(0) + R_FY) - 25 * 65536)
    mem:write_u32(flow_addr + R_HVY, 65536)
    RV.next_pop_try = playing + 1
  end
  -- hardware line limit while rivals show: the combined worst line (LN, includes every range) must stay <= 90
  if any_active and LN.frame_worst > RV.worst_line then RV.worst_line = LN.frame_worst end
end
-- Band check is a static source property of the spawn distance; the run can only reach the first band in 1700 frames.
-- Hornet below R_BONE is asserted live (variant 0 at first spawn, distance < 2700). Bone/Bruiser: see the host test (test_trip_rival.c).
function RV.result()
  local first_ok = RV.seen[0] == true
  local bands_ok = (RV.bands[1] or 0) == 0 and (RV.bands[2] or 0) == 0 and (RV.bands[0] or 0) > 0   -- distance < 2700 in this run
  local sprites_ok = RV.sprites_seen > 0 and #RV.bad == 0
  local line_ok = RV.worst_line <= R_LIMIT and RV.worst_line > 0
  local pop = RV.pop_ok == true
  local win_calls = WN.calls1 and (WN.calls1 - WN.calls0) % 65536 or 0
  local win_ok = WN.bad == 0 and WN.checked >= 1000 and WN.riv_checked >= 1 and WN.calls1 ~= nil and win_calls >= WN.frames
  local ok = first_ok and bands_ok and sprites_ok and line_ok and pop and win_ok
  local win_msg = string.format("; window clamp (T8): boxes inside the window %d checked (hero and rivals; want >= 1000), rival boxes %d (want >= 1), outside %d (want 0; first: %s), empty or missing windows skipped %d, g_trip_window_calls +%d (want >= %d PLAYING frames), g_trip_window_clamps +%d (printed, not asserted: shows whether the run touched rock)",
    WN.checked, WN.riv_checked, WN.bad, tostring(WN.first), WN.empty, win_calls, WN.frames, WN.calls1 and (WN.clamps1 - WN.clamps0) % 65536 or -1)
  print("TRIP_WINDOW " .. win_msg)
  return ok, win_msg .. string.format("; rivals: seen[0] %s, active frames by variant H%d/B%d/R%d (want H>0, B=R=0 below 2700 px), pool sprites frames %d (want >0), bad %d (%s), worst sprite line %d (want <= SB_LIMIT %d), %s",
    tostring(first_ok), RV.bands[0] or 0, RV.bands[1] or 0, RV.bands[2] or 0, RV.sprites_seen, #RV.bad, RV.bad[1] or "-", RV.worst_line, R_LIMIT, RV.pop_msg .. " [" .. (RV.dbg or "-") .. "]")
end
return RV
end)()
end

-- Input bot: aim at the middle of the safe window (win_top..win_bottom) of the chunk under the flier, flapping on every second frame
-- while below it. The old fixed "flap below y 70" overshot into the ceiling of windows that start near y 42, which killed the run
-- at 303 px in 122 of 300 host course seeds (probe: tripHaz/probe5.c) so the hazards (from 600 px) were never reached; the course
-- seed comes from the boot timing, so any change that shifts it flipped this section. Defaults to y 90 before the course is ready.
function HZ.aim(px, fx)
  local head, count = mem:read_u8(flow_addr + R_HEAD), mem:read_u8(flow_addr + R_COUNT)
  for k = 0, count - 1 do
    local base = flow_addr + R_RING + ((head + k) % RING) * R_CSIZE
    local rel = px - mem:read_u32(base + C_WX) + fx
    if rel >= 0 and rel < CHUNK_PX then return (s16(mem:read_u16(base + C_WTOP)) + s16(mem:read_u16(base + C_WBOT))) // 2 end
  end
  return 90
end
local function haz_expect(px, steps)
  local want = {}
  if mem:read_u32(flow_addr + R_NEXTWX) < px + SCREEN_W then return want end
  local head, count = mem:read_u8(flow_addr + R_HEAD), mem:read_u8(flow_addr + R_COUNT)
  for k = 0, count - 1 do
    local r = (head + k) % RING
    local base = flow_addr + R_RING + r * R_CSIZE
    local wx, nh = mem:read_u32(base + C_WX), mem:read_u8(base + HZ.nhaz)
    for i = 0, nh - 1 do
      local h = base + HZ.haz + i * HZ.size
      local kind, amp, phase = mem:read_u8(h + HZ.kind), mem:read_u8(h + HZ.amp), mem:read_u8(h + HZ.phase)
      local a = (phase + steps * HZ.step) & 255
      local sn = math.floor(32767 * math.sin(2 * math.pi * a / 256) + 0.5)
      local y = s16(mem:read_u16(h + HZ.y)) + ((sn * amp) // 32768)
      local art = HZ_ART[kind]
      local left = wx + s16(mem:read_u16(h + HZ.x)) - px - art.cx
      if left > -16 * art.cols and left < SCREEN_W then want[3 * r + i] = { left = left, top = y - art.cy, cols = art.cols, rows = art.rows, kind = kind } end
    end
  end
  return want
end
local function haz_compare(want)
  for o = 0, 14 do
    local e, s0 = want[o], HZ.sprite + 3 * o
    local scb3, scb4 = vram[0x8200 + s0] or 0, vram[0x8400 + s0] or 0
    local bad = false
    hz_checked = hz_checked + 1
    if e then
      hz_vis = hz_vis + 1; hz_kinds[e.kind] = true; hz_tops[e.kind .. ":" .. e.top] = true
      local y = (496 - ((scb3 >> 7) & 0x1ff)) & 0x1ff
      if y >= 0x100 then y = y - 512 end
      local x = (scb4 >> 7) & 0x1ff
      if x >= 0x1f0 then x = x - 512 end
      bad = (scb3 & 0x3f) ~= e.rows or y ~= e.top or x ~= e.left
      for c = 0, e.cols - 1 do
        local sp = s0 + c
        if c > 0 and ((vram[0x8200 + sp] or 0) & 0x40) == 0 then bad = true end
        for row = 0, e.rows - 1 do
          local tile, attr = vram[sp * 64 + row * 2] or 0, vram[sp * 64 + row * 2 + 1] or 0
          if tile < HZ.base or tile >= HZ.base + HZ.tiles or (attr >> 8) < HZ.pal or (attr >> 8) >= HZ.pal + HZ.paln then
            hz_tile_bad = hz_tile_bad + 1; hz_tile_first = hz_tile_first or string.format("sprite %d row %d tile %d attr 0x%04x", sp, row, tile, attr)
          end
        end
      end
      for c = e.cols, HZ.cols - 1 do if ((vram[0x8200 + s0 + c] or 0) & 0x3f) ~= 0 and ((vram[0x8200 + s0 + c] or 0) & 0x40) == 0 then bad = true end end
    else
      bad = (scb3 & 0x3f) ~= 0
    end
    if bad then hz_bad = hz_bad + 1; hz_first = hz_first or string.format("object %d at frame %d: SCB3 0x%04x SCB4 0x%04x, want %s", o, n, scb3, scb4, e and string.format("x %d y %d height %d", e.left, e.top, e.rows) or "hidden") end
  end
end
local function pickup_expect(px, steps)
  local want = {}
  if mem:read_u32(flow_addr + R_NEXTWX) < px + SCREEN_W then PK.fx = {} return want end
  local live = {}
  local head, count = mem:read_u8(flow_addr + R_HEAD), mem:read_u8(flow_addr + R_COUNT)
  for k = 0, count - 1 do
    local r = (head + k) % RING
    local base = flow_addr + R_RING + r * R_CSIZE
    local wx = mem:read_u32(base + C_WX)
    local present = mem:read_u8(base + C_PPRES) ~= 0
    live[r] = true
    if PK.fx[r] and PK.fx[r].wx0 ~= wx then PK.fx[r] = nil end   -- a new chunk in the slot ends the effect
    if pk_seen[r] and pk_seen[r].wx == wx and pk_seen[r].present and not present then
      pk_collected = pk_collected + 1
      PK.fx[r] = { wx0 = wx, wcx = wx + s16(mem:read_u16(base + C_PX)), cy = s16(mem:read_u16(base + C_PY)), start = steps }
    end
    pk_seen[r] = { wx = wx, present = present }
    if present then
      local x = wx + s16(mem:read_u16(base + C_PX)) - px - P_LEFT
      local frame = (steps >> 2) % P_FRAMES
      if x > -32 and x < SCREEN_W then want[r] = { x = x, y = s16(mem:read_u16(base + C_PY)) - P_TOP + PK.bob[frame], frame = frame } end
    elseif PK.fx[r] then
      local f = (steps - PK.fx[r].start) >> 2
      local x = PK.fx[r].wcx - px - P_LEFT
      if f < PK.cframes and x > -32 and x < SCREEN_W then want[r] = { x = x, y = PK.fx[r].cy - PK.ctop, collect = f } end
    end
  end
  for r in pairs(PK.fx) do if not live[r] then PK.fx[r] = nil end end
  return want
end
local function pickup_compare(want)
  for r = 0, RING - 1 do
    for c = 0, 1 do
      local i = P_SPRITE + 2 * r + c
      local scb3, scb4 = vram[0x8200 + i] or 0, vram[0x8400 + i] or 0
      local e, bad = want[r], false
      pk_checked = pk_checked + 1
      if e then
        pk_vis = pk_vis + 1
        local y = (496 - ((scb3 >> 7) & 0x1ff)) & 0x1ff
        if y >= 0x100 then y = y - 512 end
        local x = (scb4 >> 7) & 0x1ff
        if x >= 0x1e0 then x = x - 512 end
        bad = (scb3 & 0x3f) ~= 2 or y ~= e.y or x ~= e.x + 16 * c
        if e.collect then
          PK.fx_checked = PK.fx_checked + 1
          if c == 0 then PK.fx_seen[e.collect] = true end
        elseif c == 0 then PK.bob_seen[e.y] = true end
        for row = 0, 1 do
          local tile, attr = vram[i * 64 + row * 2] or 0, vram[i * 64 + row * 2 + 1] or 0
          if e.collect then   -- the collect frame's own tiles, from the ROM index table
            local off = mem:read_u16(PK.frames + (P_FRAMES + e.collect) * PK.fsize + PK.toff)
            local want_tile = P_BASE + mem:read_u16(PK.tiles + (off + c * 2 + row) * 2)
            if tile ~= want_tile then PK.fx_tile_bad = PK.fx_tile_bad + 1; PK.fx_first = PK.fx_first or string.format("collect frame %d sprite %d row %d tile %d want %d at frame %d", e.collect, i, row, tile, want_tile, n) end
          end
          if tile < P_BASE or tile >= P_BASE + P_TILES or (attr >> 8) ~= P_PAL then
            pk_tile_bad = pk_tile_bad + 1; pk_tile_first = pk_tile_first or string.format("sprite %d row %d tile %d attr 0x%04x", i, row, tile, attr)
          end
          if c == 0 and row == 0 then pk_anim[tile] = true end
        end
      else
        bad = (scb3 & 0x3f) ~= 0
      end
      if bad then pk_bad = pk_bad + 1; pk_first = pk_first or string.format("sprite %d at frame %d: SCB3 0x%04x SCB4 0x%04x, want %s", i, n, scb3, scb4, e and string.format("x %d y %d", e.x + 16 * c, e.y) or "hidden") end
    end
  end
end

local strip_checked, strip_vis, strip_bad, strip_first, strip_hold_vis, tile_bad, tile_first, speed_bad, speed_first = 0, 0, 0, nil, 0, 0, nil, 0, nil
STRIP_X = { bad = 0, ok = 0 }  -- global: the main chunk is at the 200 local limit;  -- visible strip sprites off / on the world column grid
local rim_group = {}   -- rim role (A: j&3 is 0 or 3, B: 1 or 2) -> tile group (tile & ~7) seen first, later ones must match
local fill_tile = nil
local strip_started, strip_settle = false, 0   -- frames between the course being ready and the first visible strip column
local MAX_SETTLE = 4
-- Compares the strip sprites in the VRAM shadow with the expectation; also checks each visible sprite's tiles.
local function strip_compare(want, wpx)
  local got = {}
  for i = 0, S_COUNT - 1 do
    local scb3, scb4 = vram[0x8200 + S_SPRITE + i] or 0, vram[0x8400 + S_SPRITE + i] or 0
    local rows = scb3 & 0x3f
    if rows > 0 then
      local y = (496 - ((scb3 >> 7) & 0x1ff)) & 0x1ff
      if y >= 0x100 then y = y - 512 end
      local x = (scb4 >> 7) & 0x1ff
      if x >= 0x1f0 then x = x - 512 end
      local ceiling = i >= S_COLS
      local key = string.format("%s %d %d %d", ceiling and "C" or "F", x, y, rows)
      got[key] = (got[key] or 0) + 1
      strip_vis = strip_vis + 1
      local j = (x + wpx) // 16
      if (x + wpx) & 15 ~= 0 then STRIP_X.bad = STRIP_X.bad + 1 else STRIP_X.ok = STRIP_X.ok + 1 end   -- a visible column sits on a 16 px world grid at the current scroll
      local m = j & 3
      local role = (m == 0 or m == 3) and "A" or "B"
      for r = 0, rows - 1 do
        local tile, attr = vram[(S_SPRITE + i) * 64 + r * 2] or 0, vram[(S_SPRITE + i) * 64 + r * 2 + 1] or 0
        local is_rim = (not ceiling and r == 0) or (ceiling and r == rows - 1)
        local bad = tile < S_BASE or tile >= S_BASE + S_TILES or (attr >> 8) ~= S_PAL or ((attr >> 1) & 1) ~= (ceiling and 1 or 0)
        if is_rim then
          bad = bad or (attr & 0x08) == 0 or (attr & 1) ~= (m & 1)
          local grp = tile & ~7
          if rim_group[role] == nil then rim_group[role] = grp end
          bad = bad or rim_group[role] ~= grp
        else
          bad = bad or (attr & 0x08) ~= 0
          fill_tile = fill_tile or tile
          bad = bad or tile ~= fill_tile
        end
        if bad then tile_bad = tile_bad + 1; tile_first = tile_first or string.format("sprite %d row %d tile %d attr 0x%04x", i, r, tile, attr) end
      end
    end
  end
  if next(got) == nil and not strip_started and next(want) ~= nil then strip_settle = strip_settle + 1; return end   -- still loading after the course became ready
  if next(got) ~= nil then strip_started = true end
  local bad = false
  for k, v in pairs(want) do if got[k] ~= v then bad = true; strip_first = strip_first or ("missing " .. k) end end
  for k, v in pairs(got) do if want[k] ~= v then bad = true; strip_first = strip_first or ("unexpected " .. k) end end
  strip_checked = strip_checked + 1
  if bad then strip_bad = strip_bad + 1 end
end

emu.register_frame_done(function() local ok_, err_ = pcall(function()
  n = n + 1; PF.n = n
  local fl = frame_l; frame_l = 0
  if counting and fl > (PF.le_max or -1) then PF.le_max = fl; PF.le_at = string.format("frame %d phase %s state %d playing %d", n, phase, mem:read_u8(flow_addr + O_STATE), playing) end   -- where the logic end max sits (any phase)
  if not VB_LEN_S then VB_LEN_S = screen:time_until_vblank_end():as_double() end
  if words > max_words and counting then max_words = words end
  words = 0
  if n > 3000 then finish(false, string.format("watchdog: phase %s, PLAYING frames %d", phase, playing)) return end
  if not (coin and start and down and abtn and tlay[78] and PK.tiles and PK.frames and METERDRAWS_ADDR and METERTAB_ADDR and HZ.draws_addr and PICKUPDRAWS_ADDR and STRIPDRAWS_ADDR and TRIPDRAWS_ADDR and ARENADRAWS_ADDR and flay[6] and cam_addr and (cam_size == 1 or cam_size == 2)) then finish(false, "missing input, layout or sentinel size") return end
  local state = mem:read_u8(flow_addr + O_STATE)
  if phase == "boot" then
    if n >= 300 then phase = "coin"; phase_at = n; coin:set_value(1) end
    return
  elseif phase == "coin" then
    if n == phase_at + 15 then coin:set_value(0) end
    if n >= phase_at + 40 and state == 0 then phase = "down"; phase_at = n; down:set_value(1) end
    return
  elseif phase == "down" then
    if n == phase_at + 4 then down:set_value(0) end
    if n == phase_at + 11 then near_title_vis = near_visible(); HZ.far_title = HZ.far_visible(); HZ.bd_title = mem:read_u16(HZ.BD_ADDR) end
    -- Course seed pin: the run's seed is g_frame_counter at the flow step that sees Start (src/core/flow.c start_game), and the
    -- hazards (from TRIP_DENSITY_START_PX) only appear for some seeds within the run. Pressing Start at a fixed g_frame_counter
    -- value instead of a fixed MAME frame makes the course independent of the boot length, which any ROM change shifts
    -- (thoughts/spot/2026-11-11-test-trip-hazard-failure.md).
    -- Coin item (2026-11-13): with a credit ONE Start begins the highlighted mode, so no Start tap before the pinned frame
    -- (the old select-opening tap started the run about 110 frames early and the pin below passed on a run already under way).
    if n >= phase_at + 24 then
      local fc = mem:read_u32(frame_addr)
      if fc > HZ.START_FC then finish(false, string.format("title reached at g_frame_counter %d, after the pinned Start frame %d: raise HZ.START_FC", fc, HZ.START_FC)) return end
      if fc == HZ.START_FC then phase = "start"; phase_at = n; start:set_value(1) end
    end
    return
  elseif phase == "start" then
    if state ~= 3 then return end
    start:set_value(0); phase = "play"; phase_at = n; counting = true
    -- the flow step that sees the Start set at START_FC enters PLAYING with g_frame_counter still START_FC (the seed is that
    -- counter value; no symbol exposes the seed itself), so the first PLAYING read is exactly START_FC
    local sfc = mem:read_u32(frame_addr)
    if sfc ~= HZ.START_FC then finish(false, string.format("course seed not pinned: PLAYING first read at g_frame_counter %d, want %d (HZ.START_FC)", sfc, HZ.START_FC)) end
    return
  end
  if state ~= 3 then
    if playing >= MIN_PLAYING then phase = "done" else
      finish(false, string.format("flow left PLAYING (state %d) after %d frames; mode %d", state, playing, mem:read_u8(flow_addr + O_MODE)))
      return
    end
  end
  if phase == "play" then
    playing = playing + 1
    local fy = s32(mem:read_u32(flow_addr + O_FY)) / 65536
    local aim = HZ.aim(mem:read_u32(flow_addr + O_PX), s32(mem:read_u32(flow_addr + O_FX)) >> 16)
    abtn:set_value((fy > aim and playing % 2 == 0) and 1 or 0)   -- flap to stay in the middle of the safe window
    local fc, steps = mem:read_u32(frame_addr), mem:read_u32(flow_addr + O_STEPS)
    local d, speed, cam = dist(), mem:read_u32(flow_addr + O_SPEED), read_cam()
    if mem:read_u8(flow_addr + O_MODE) ~= MODE_TRIP then mode_bad = mode_bad + 1 end
    local sx = s32(mem:read_u32(flow_addr + O_FX)) >> 16
    if sx < min_sx then min_sx = sx end
    if sx > max_sx then max_sx = sx end
    if sx < 0 or sx > SCREEN_W - 1 then off_screen = off_screen + 1; first_off = first_off or string.format("x %d at frame %d", sx, n) end
    local hold, made = mem:read_u8(flow_addr + O_HOLD), mem:read_u32(flow_addr + O_MADE)
    -- a hold frame is read from the game state: trip_hold went up, so game_step_trip only built one chunk and nothing moved
    local is_hold = prev_hold ~= nil and hold ~= prev_hold
    do   -- where the logic end peak sits: run-start hold, first frames after ready, steady state
      local cat = "hold"
      if not is_hold then since_ready = since_ready + 1; cat = since_ready <= EARLY_FRAMES and "early" or "steady" end
      if fl > cat_max[cat] then cat_max[cat] = fl; cat_at[cat] = string.format("frame %d (playing %d, since ready %d, made %d)", n, playing, since_ready, made) end
    end
    if is_hold then
      hold_frames = hold_frames + 1
      if steps ~= prev_steps or d ~= prev_dist or cam ~= prev_cam or made ~= prev_made + 1 then hold_bad = hold_bad + 1 end
      if fc == prev_fc then missed = missed + 1 end
    elseif prev_fc then
      if fc == prev_fc then missed = missed + 1 end
      if steps ~= prev_steps + 1 then steps_bad = steps_bad + 1 end
      local g = d - prev_dist
      if g < SPEED_MIN or g > SPEED_MAX or (g ~= prev_speed and g ~= speed) then
        grow_bad = grow_bad + 1; first_grow = first_grow or string.format("growth %d, speed %d (was %d) at frame %d", g, speed, prev_speed, n)
      end
      -- the speed ramps continuously from SPEED_MIN at distance 0: the first growth is SPEED_MIN (+ one ramp step) and never decreases
      ramp_checked = ramp_checked + 1
      if not first_g then first_g = g; if g < SPEED_MIN or g > SPEED_MIN + 64 then ramp_bad = ramp_bad + 1 end end
      if prev_g and g < prev_g then ramp_bad = ramp_bad + 1 end
      prev_g = g
      dist_total = dist_total + g
      local cd = (cam - prev_cam) % ARENA_W
      if cd > 1 then cam_bad = cam_bad + 1; first_cam = first_cam or string.format("cam %d -> %d at frame %d", prev_cam, cam, n) end
      cam_total = cam_total + cd
      if cd == 0 then still_run = still_run + 1; if still_run > max_still then max_still = still_run end else still_run = 0 end
    end
    prev_fc, prev_steps, prev_dist, prev_speed, prev_cam = fc, steps, d, speed, cam
    prev_hold, prev_made = hold, made
    if playing == 1 then strip0 = mem:read_u16(STRIPDRAWS_ADDR) end
    strip1 = mem:read_u16(STRIPDRAWS_ADDR)
    if is_hold then for i = 0, S_COUNT - 1 do if ((vram[0x8200 + S_SPRITE + i] or 0) & 0x3f) ~= 0 then strip_hold_vis = strip_hold_vis + 1 end end end
    if playing > 2 and lspc_mode and (lspc_mode >> 8) + 1 ~= S_STEP then speed_bad = speed_bad + 1; speed_first = speed_first or string.format("LSPC mode 0x%04x at frame %d", lspc_mode, n) end
    if is_hold then for i = 0, P_COUNT - 1 do if ((vram[0x8200 + P_SPRITE + i] or 0) & 0x3f) ~= 0 then pk_hold_vis = pk_hold_vis + 1 end end end
    if is_hold then for o = 0, 14 do if ((vram[0x8200 + HZ.sprite + 3 * o] or 0) & 0x3f) ~= 0 then hz_hold_vis = hz_hold_vis + 1 end end end
    if playing >= 6 then near_trip_vis = near_trip_vis + near_visible(); HZ.far_trip = HZ.far_trip + HZ.far_visible()
      local bd = mem:read_u16(HZ.BD_ADDR); HZ.bd_trip_n = HZ.bd_trip_n + 1; if bd ~= HZ.BD_TRIP then HZ.bd_trip_bad = HZ.bd_trip_bad + 1; HZ.bd_first = HZ.bd_first or bd end
      HZ.midb_check() end
    LN.count(playing)
    LN.meter_sample(playing)
    HZ.rv.sample(playing)
    if playing == 1 then hz_draws0 = mem:read_u16(HZ.draws_addr) end
    hz_draws1 = mem:read_u16(HZ.draws_addr)
    if hz_prev then haz_compare(hz_prev) end
    hz_prev = haz_expect(mem:read_u32(flow_addr + O_PX), mem:read_u32(flow_addr + O_STEPS))
    if playing == 1 then pk_draws0 = mem:read_u16(PICKUPDRAWS_ADDR) end
    pk_draws1 = mem:read_u16(PICKUPDRAWS_ADDR)
    if pk_prev then pickup_compare(pk_prev) end
    pk_prev = pickup_expect(mem:read_u32(flow_addr + O_PX), steps)
    if strip_prev then strip_compare(strip_prev, strip_prev_px) end
    strip_prev, strip_prev_px = strip_expect(mem:read_u32(flow_addr + O_PX))
    if playing == 1 then draws0, arena0 = mem:read_u16(TRIPDRAWS_ADDR), mem:read_u16(ARENADRAWS_ADDR) end
    draws1, arena1 = mem:read_u16(TRIPDRAWS_ADDR), mem:read_u16(ARENADRAWS_ADDR)
    -- islands: every island sprite slot is either an expected generated island column (x, y, one tile high) or hidden (SCB3 height 0);
    -- the arena platforms use these same slots, so "all other slots hidden" is the arena islands being off. Nothing is expected
    -- before the course is ready (hold frames), as game_trip_ready is still 0 then.
    -- The VRAM at this sample is the flush of the previous frame's queue, so it is compared with the expectation computed from
    -- the RAM state at the previous sample (a hold frame expects nothing shown).
    local want = want_prev
    want_prev = island_expect(mem:read_u32(flow_addr + O_PX))
    if want then
      for i = 0, ISLAND_COUNT - 1 do
        local scb3, scb4 = vram[0x8200 + ISLAND_SPRITE + i] or 0, vram[0x8400 + ISLAND_SPRITE + i] or 0
        local e, ok = want[i], true
        isl_checked = isl_checked + 1
        if e then
          isl_vis = isl_vis + 1
          ok = (scb3 & 0x3f) == 1 and ((scb3 >> 7) & 0x1ff) == ((496 - e.y) & 0x1ff) and ((scb4 >> 7) & 0x1ff) == (e.x & 0x1ff)
        else
          ok = (scb3 & 0x3f) == 0
        end
        if not ok then
          isl_bad = isl_bad + 1
          isl_first = isl_first or string.format("slot %d at frame %d: SCB3 0x%04x SCB4 0x%04x, want %s", i, n, scb3, scb4, e and string.format("x %d y %d height 1", e.x, e.y) or "hidden")
        end
      end
    end
    -- hazards only start after TRIP_DENSITY_START_PX (600) of distance, so play on until 60 hazard sightings are compared (or 1700 frames)
    if playing >= MIN_PLAYING + 100 and ((hz_vis >= 60 and HZ.rv.pop_ok ~= nil) or playing >= 1700) then phase = "done" end
  end
  if phase == "done" and not SPLASH_T.over then
    -- Gum Trip has no liquid: a flier dying at the floor must not start the arena splash (SPLASH_SPRITE 113..115, src/main.c splash_enabled)
    if SPLASH_T.k == nil then
      if state ~= 3 then finish(false, "trip splash check: not PLAYING when the floor death was due") return end
      mem:write_u32(flow_addr + O_FY, 215 * 65536); mem:write_u32(flow_addr + flay[9], 0)   -- below the lowest kill line (HAZARD_KILL_WATER 208)
      SPLASH_T.k = 0
    end
    SPLASH_T.k = SPLASH_T.k + 1
    if SPLASH_T.k >= 4 and mem:read_u8(flow_addr + flay[10]) ~= 3 and SPLASH_T.k < 8 then finish(false, "trip splash check: flier not DROWNED after the poke below the kill line") return end
    for s_ = 113, 115 do if ((vram[0x8200 + s_] or 0) & 0x3f) ~= 0 then SPLASH_T.live = SPLASH_T.live + 1 end end
    if SPLASH_T.k >= 40 then
      if SPLASH_T.live ~= 0 then finish(false, string.format("a splash sprite was live in %d slot-frames after a Gum Trip floor death (want 0, no liquid)", SPLASH_T.live)) return end
      SPLASH_T.over = true
    end
    return
  end
  if phase == "done" then
    local pk_anim_n = 0
    for _ in pairs(pk_anim) do pk_anim_n = pk_anim_n + 1 end
    local fxn, bobn = 0, 0
    for _ in pairs(PK.fx_seen) do fxn = fxn + 1 end
    for _ in pairs(PK.bob_seen) do bobn = bobn + 1 end
    local pk_ok = PK.fx_tile_bad == 0 and fxn >= PK.cframes and PK.fx_checked >= 2 * PK.cframes and bobn >= 5 and pk_bad == 0 and pk_vis >= 20 and pk_tile_bad == 0 and pk_hold_vis == 0 and (pk_draws1 - pk_draws0) % 65536 >= 10 and pk_anim_n >= 4
    local pk_msg = string.format("; pickups: checked %d visible %d bad %d (want 0, first: %s), bad tiles %d (first: %s), visible in hold %d (want 0), draws %d, collected seen %d, idle frames seen %d, collect frames seen %d of %d (want all), collect sprites checked %d, collect tile mismatches %d (want 0, first: %s), bob heights seen %d (want 5 or more)",
      pk_checked, pk_vis, pk_bad, tostring(pk_first), pk_tile_bad, tostring(pk_tile_first), pk_hold_vis, (pk_draws1 - pk_draws0) % 65536, pk_collected, pk_anim_n, fxn, PK.cframes, PK.fx_checked, PK.fx_tile_bad, tostring(PK.fx_first), bobn)
    local hz_kind_n, hz_top_n = 0, 0
    for _ in pairs(hz_kinds) do hz_kind_n = hz_kind_n + 1 end
    for _ in pairs(hz_tops) do hz_top_n = hz_top_n + 1 end
    local hz_dr = (hz_draws1 - hz_draws0) % 65536
    local hz_ok = hz_bad == 0 and hz_vis >= 30 and hz_tile_bad == 0 and hz_hold_vis == 0 and hz_dr >= 30 and hz_kind_n >= 1 and hz_top_n >= 10 and near_trip_vis == 0 and near_title_vis > 0 and HZ.far_trip == 0 and HZ.far_title > 0 and HZ.bd_title == HZ.BD_ARENA and HZ.bd_trip_n > 0 and HZ.bd_trip_bad == 0 and HZ.midb_bad == 0
    local hz_msg = string.format("; hazards: pool objects compared %d, shown %d (want >= 30), bad %d (want 0; first: %s), bad tiles %d (want 0; first: %s), visible in hold %d (want 0), kinds seen %d (want >= 1; only coal appears within the run, vent and cloud are unverified in the ROM), distinct kind/top pairs %d (want >= 10), g_trip_haz_draws +%d (want >= 30); near plane sprites visible on the title %d (want > 0), during the trip %d (want 0); far plane sprites visible on the title %d (want > 0), during the trip %d (want 0); backdrop word on the title 0x%04x (want 0x%04x), during the trip %d of %d frames not 0x%04x (want 0; first read 0x%04x); mid B columns off the restored heights or with a blank last row %d (want 0; first: %s)",
      hz_checked, hz_vis, hz_bad, tostring(hz_first), hz_tile_bad, tostring(hz_tile_first), hz_hold_vis, hz_kind_n, hz_top_n, hz_dr, near_title_vis, near_trip_vis, HZ.far_title, HZ.far_trip, HZ.bd_title or 0, HZ.BD_ARENA, HZ.bd_trip_bad, HZ.bd_trip_n, HZ.BD_TRIP, HZ.bd_first or 0, HZ.midb_bad, tostring(HZ.midb_first))
    local base_finish = finish
    local kind_names = {}
    for k in pairs(hz_kinds) do kind_names[#kind_names + 1] = tostring(k) end
    table.sort(kind_names)
    local ln_msg = LN.message("[" .. table.concat(kind_names, ",") .. "] (TripHazKind index: 0 coal, 1 vent, 2 cloud)")
    print("TRIP_LINES " .. ln_msg)
    local mt_ok, mt_msg = LN.meter_result()
    local rv_ok, rv_msg = HZ.rv.result()
    local function finish(ok, msg) base_finish(ok and pk_ok and hz_ok and mt_ok and rv_ok and PF.ok(), msg .. pk_msg .. hz_msg .. mt_msg .. rv_msg .. ln_msg .. PF.report()) end
    local travel_ok = math.abs(cam_total - dist_total / 65536) <= 1.5
    local ok = mode_bad == 0 and grow_bad == 0 and ramp_bad == 0 and cam_bad == 0 and max_still <= 1 and travel_ok
      and off_screen == 0 and missed <= MAX_MISSED and steps_bad == 0 and logic_end < 224 and playing >= MIN_PLAYING
      and hold_bad == 0 and hold_frames >= 1 and hold_frames <= MAX_HOLD
      and strip_bad == 0 and STRIP_X.bad == 0 and STRIP_X.ok > 0 and strip_settle <= MAX_SETTLE and strip_checked >= 400 and strip_vis >= 4000 and tile_bad == 0 and strip_hold_vis == 0 and speed_bad == 0 and (strip1 - strip0) % 65536 >= 100 and isl_bad == 0 and isl_vis >= 20 and (draws1 - draws0) % 65536 >= 100 and arena1 == arena0
    finish(ok, string.format("trip: PLAYING frames %d, mode not TRIP %d (want 0), distance growth outside speed %d (want 0, first: %s), first growth %s (want %d..%d) or a falling growth: %d of %d bad (want 0), camera step >1: %d (first: %s), longest still camera run %d (want <= 1), camera travel %d vs distance %.1f px, flier screen x %d..%d (want 0..%d), off screen %d (first: %s), frames without a game step %d (want %d), Trip.steps off %d (want 0), logic end max %.1f lines after vblank end (want < 224; hold max %.1f at %s; first %d frames after ready max %.1f at %s; steady max %.1f at %s), hold frames %d (want 1..%d, nothing moved but one chunk built: bad %d, want 0), max VRAM data words per frame %d, vblank %.0f lines, island slots checked %d (generated island columns expected on screen: %d, want >= 20), bad %d (want 0; first: %s), g_island_trip_draws +%d (want >= 100), g_island_draws +%d (arena island code, want 0), kill strips: frames compared %d, frames from ready to the first visible column %d (want <= %d), visible strip columns seen %d (want >= 4000), frames whose columns differ from the spec %d (want 0; first: %s), tile errors %d (want 0; first: %s), strip sprites visible in the hold %d (want 0), auto-animation speed errors %d (want 0; first: %s; register reads %s, want %d), g_trip_strip_draws +%d (want >= 100)",
      playing, mode_bad, grow_bad, tostring(first_grow), tostring(first_g), SPEED_MIN, SPEED_MIN + 64, ramp_bad, ramp_checked, cam_bad, tostring(first_cam), max_still,
      cam_total, dist_total / 65536, min_sx, max_sx, SCREEN_W - 1, off_screen, tostring(first_off), missed, MAX_MISSED, steps_bad, logic_end, cat_max.hold, tostring(cat_at.hold), EARLY_FRAMES, cat_max.early, tostring(cat_at.early), cat_max.steady, tostring(cat_at.steady), hold_frames, MAX_HOLD, hold_bad, max_words, VB_LEN_S / LINE_S,
      isl_checked, isl_vis, isl_bad, tostring(isl_first), (draws1 - draws0) % 65536, (arena1 - arena0) % 65536,
      strip_checked, strip_settle, MAX_SETTLE, strip_vis, strip_bad, tostring(strip_first), tile_bad, tostring(tile_first), strip_hold_vis, speed_bad, tostring(speed_first), lspc_mode and ((lspc_mode >> 8) + 1) or "nil", S_STEP, (strip1 - strip0) % 65536))
  end
end) if not ok_ then print('LUAERR ' .. tostring(err_)); finish(false, 'lua error: ' .. tostring(err_)) end end)

-- PC profile (measurement only, opt-in: BRAWL_PC_LOG=<file> and BRAWL_PC_SYMS=<nm -n -S output>, set by `make test-trip TRIP_PC_LOG=<file>`;
-- without them nothing below runs and no assert is touched). emu.wait(one scan line) resumes this chunk once per line of emulated time;
-- each resume reads the 68000 PC and counts it for the function whose [address, address + size) holds it. Frame = vblank end to vblank end,
-- only frames with phase "play". gfx_wait_vblank samples are idle. Samples inside vblank (the frame logic starts there, after the flush) are in the counts and also in the "in vblank" column.
-- (wrapped in a function: the main chunk is at the 200 local limit)
if os.getenv("BRAWL_PC_LOG") ~= nil and os.getenv("BRAWL_PC_LOG") ~= "" and (os.getenv("BRAWL_PC_SYMS") or "") ~= "" then (function()
  local PCLOG, PCSYMS = os.getenv("BRAWL_PC_LOG"), os.getenv("BRAWL_PC_SYMS")
  local cpu = manager.machine.devices[":maincpu"]
  local starts, sizes, names = {}, {}, {}
  for line in io.lines(PCSYMS) do   -- "addr size type name", sorted by address
    local a, z, t, nm = line:match("^(%x+) (%x+) (%a) (%S+)")
    if a and t:lower() == "t" then starts[#starts + 1] = tonumber(a, 16); sizes[#sizes + 1] = tonumber(z, 16); names[#names + 1] = nm end
  end
  local function fname(pc)
    local lo, hi = 1, #starts
    while lo < hi do local mid = (lo + hi + 1) // 2; if starts[mid] <= pc then lo = mid else hi = mid - 1 end end
    if starts[lo] and pc >= starts[lo] and pc < starts[lo] + math.max(sizes[lo], 1) then return names[lo] end
    return string.format("other_%x", pc & 0xffff00)
  end
  local IDLE = "gfx_wait_vblank"
  local frames, cur, prev_vb = {}, nil, true
  local nsamp = 0
  function PC_DUMP()
    local f = io.open(PCLOG, "w")
    local cls = { [0] = { n = 0 }, { n = 0 }, { n = 0 }, { n = 0 } }
    local all, tot, mx = {}, {}, {}
    for _, fr in ipairs(frames) do
      local c = cls[fr.steps & 3]; c.n = c.n + 1
      for k, v in pairs(fr.counts) do
        c[k] = (c[k] or 0) + v; tot[k] = (tot[k] or 0) + v; all[k] = true
        if v > (mx[k] or 0) then mx[k] = v end
      end
    end
    local keys = {}
    for k in pairs(all) do if k ~= IDLE then keys[#keys + 1] = k end end
    local vbsum = {}
    for _, fr in ipairs(frames) do for k, v in pairs(fr.vb) do vbsum[k] = (vbsum[k] or 0) + v end end
    table.sort(keys, function(a, b) return tot[a] > tot[b] end)
    local nf = #frames
    local worst, sumsamp, summax = nil, 0, 0
    for _, fr in ipairs(frames) do
      if not worst or fr.last > worst.last then worst = fr end
      sumsamp = sumsamp + fr.total; if fr.total > summax then summax = fr.total end
    end
    f:write(string.format("frames %d (steps&3 = 0: %d, 1: %d, 2: %d, 3: %d); samples per frame mean %.2f max %d (want 264); 1 sample = 1 line = 64 us\n", nf, cls[0].n, cls[1].n, cls[2].n, cls[3].n, nf > 0 and sumsamp / nf or 0, summax))
    f:write("function | mean lines | max lines | steps&3=0 mean/max | =1 mean/max | =2 mean/max | =3 mean/max | in vblank mean\n")
    local function row(k)
      local t = { string.format("%s | %.2f | %d", k, (tot[k] or 0) / math.max(nf, 1), mx[k] or 0) }
      for b = 0, 3 do
        local m = 0
        for _, fr in ipairs(frames) do if (fr.steps & 3) == b and (fr.counts[k] or 0) > m then m = fr.counts[k] end end
        t[#t + 1] = string.format("%.2f/%d", (cls[b][k] or 0) / math.max(cls[b].n, 1), m)
      end
      t[#t + 1] = string.format("%.2f", (vbsum[k] or 0) / math.max(nf, 1))
      return table.concat(t, " | ")
    end
    for _, k in ipairs(keys) do f:write(row(k), "\n") end
    f:write(row(IDLE), "\n")
    if worst then
      f:write(string.format("worst frame: PLAYING frame %d, steps %d (&3=%d), last non-idle sample at line %d after vblank end, split (lines):", worst.idx, worst.steps, worst.steps & 3, worst.last))
      local wk = {}
      for k in pairs(worst.counts) do wk[#wk + 1] = k end
      table.sort(wk, function(a, b) return worst.counts[a] > worst.counts[b] end)
      for _, k in ipairs(wk) do f:write(string.format(" %s=%d", k, worst.counts[k])) end
      f:write("\n")
    end
    f:close()
  end
  local function close_frame(steps)
    if cur and cur.ok then cur.steps = steps; cur.idx = #frames + 1; frames[#frames + 1] = cur end
    cur = nil
  end
  while true do
    emu.wait(LINE_S)
    local vb = in_vblank()
    local l = (not vb) and (224 - screen:time_until_vblank_start():as_double() / LINE_S) or nil
    if prev_vb and not vb then   -- vblank just ended: the previous frame is complete
      close_frame(mem:read_u32(flow_addr + O_STEPS))
      cur = { counts = {}, vb = {}, total = 0, last = -1, ok = (phase == "play" and counting) }
    end
    prev_vb = vb
    if cur then
      local nm = fname(cpu.state["PC"].value)
      cur.counts[nm] = (cur.counts[nm] or 0) + 1; cur.total = cur.total + 1
      if vb then cur.vb[nm] = (cur.vb[nm] or 0) + 1 end
      if l and nm ~= IDLE and l > cur.last then cur.last = math.floor(l) end
      if phase ~= "play" then cur.ok = false end
    end
  end
end)() end
