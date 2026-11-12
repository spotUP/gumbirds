-- Headless camera check (make test-camera). Sentinel-driven timeline, no fixed frame numbers:
--   1. coin, start; wait for PLAYING;
--   2. drive the human right (hold Right, flap to stay airborne) until the camera pixel sentinel g_cam_px (src/main.c)
--      passes ARENA_CAM_MAX (64: on the ring the camera follows the hero past 64, it is no longer clamped), then keep going
--      until the human wraps across the arena seam (world x 384 -> 0), then 60 more frames;
--   3. every frame: the hero SCB4 x (read from the VRAM writes) equals camera_screen_x for the (camera, flier x) pair of
--      the last 3 frames; the camera moves at most 2 px per frame; every hazard column (24 per bank, both banks) sits at its
--      ring x (hidden ones parked at x 320, like camera_column_x) once the camera is still; the hazard SCB4 words are written only
--      within 2 frames after the camera pixel changed; zero VRAM writes outside vblank.
--   4. background planes (slots, factors, column counts from camera_probe.c): with the camera still for more than 2 frames
--      every column of every plane sits at its looping x (offset = ((unwrapped camera g_cam_unwrapped * k) >> 4) mod plane width), so the near plane follows the camera
--      1:1, the far plane a quarter, the sky never moves; plane SCB4 words are written only within 2 frames after a camera
--      change, the sky never; the sentinel g_bg_x_writes proves bg_update ran (it moves only on camera-move frames).
--   5. island columns (plan R5): with the camera still for more than 2 frames every island column sprite is, by its own
--      maths, hidden (SCB3 height 0) or at x = camera_column_x with height 1 and y = platform y - ISLAND_LINE_ROW; the run must
--      check cameras above 65 and past the seam.
-- Env: BRAWL_FLOW_ADDR, BRAWL_STAGE_ADDR (stage_platforms), BRAWL_CAM_ADDR, BRAWL_BGX_ADDR, BRAWL_FLIER_LAYOUT (flier_probe.c), BRAWL_CAMERA_LAYOUT
-- (camera_probe.c), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local cam_addr  = tonumber(os.getenv("BRAWL_CAM_ADDR"), 16)
local result    = os.getenv("BRAWL_RESULT")
local function nums(name) local t = {} for v in (os.getenv(name) or ""):gmatch("%d+") do t[#t + 1] = tonumber(v) end return t end
local flay, lay = nums("BRAWL_FLIER_LAYOUT"), nums("BRAWL_CAMERA_LAYOUT")
local O_STATE, O_X, O_Y, O_FSTATE, O_VX = flay[1], flay[6], flay[7], flay[10], flay[8]
local HERO, HAZ, HAZ_COLS, ARENA_W, SCREEN_W, HALF_W, CAM_MAX = lay[1], lay[2], lay[3], lay[4], lay[5], lay[6], lay[7]
local REACH_PX = lay[35] // 2 -- FLIER_PAIR_REACH_HALF in px
local SOOT_W, SOOT_BOX_DX = lay[8], lay[9] -- frame width and hit box offset from frames.json (camera_probe.c)
local PLANES = {} -- first sprite slot, parallax factor in sixteenths, column count, in draw order
for p = 1, 5 do PLANES[p] = { slot = lay[9 + p], k = lay[14 + p], cols = lay[19 + p] } end
local stage_addr = tonumber(os.getenv("BRAWL_STAGE_ADDR") or "", 16)
local ISL_SLOT, ISL_N, ISL_ROW = lay[25], lay[26], lay[27]
local bgx_addr = tonumber(os.getenv("BRAWL_BGX_ADDR"), 16)
local ramp_addr = tonumber(os.getenv("BRAWL_RAMP_ADDR") or "", 16)  -- g_vq_ramp_ops: VQ_RAMP ops the flush wrote (sentinel: the plane x words came from the generated path)
local camu_addr = tonumber(os.getenv("BRAWL_CAMU_ADDR") or "", 16)   -- g_cam_unwrapped: what the looping planes follow
-- Rival fliers (step V6, seam review gap): the pool (g_pool) object i of a computer flier owns sprites POOL_BASE + i * POOL_COLS..; its head
-- SCB4 x must be the camera maths of its world x (PoolObj.x >> 16, minus FLIER_HALF_W and SOOT_BOX_DX, width SOOT_W) for one of the last 3 frames,
-- like the hero. RV_HERO is POOL_F_HERO, restated from src/main.c (computer flier). Counters live in RV (local limit).
local RV = { addr = tonumber(os.getenv("BRAWL_POOL_ADDR") or "", 16), base = lay[28], cols = lay[29], max = lay[30], size = lay[31], ox = lay[32], of = lay[33],
  live = lay[34], hero = 0x04, hist = {}, checked = 0, hidden = 0, bad = 0, wrapped = 0, wrapped_hi = 0, first = nil }
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
local abtn  = field(":edge:joy:JOY1", "P1 A")
local rbtn  = field(":edge:joy:JOY1", "P1 Right")
local lbtn  = field(":edge:joy:JOY1", "P1 Left")
local hold_rivals = dofile("tests/mame/hold_rivals.lua")(mem, flow_addr, flay, ARENA_W)
local function s32(v) return v >= 0x80000000 and v - 0x100000000 or v end

-- the same maths as src/core/camera.c camera_screen_x, written out independently
local function screen_x(world, cam, w)
  local x = (world % ARENA_W) - cam
  while x < -w do x = x + ARENA_W end
  while x >= ARENA_W - w do x = x - ARENA_W end
  return x
end

-- column left edge at world, screen x or nil when no pixel shows: the same maths as camera_column_x, written out independently
local function column_x(world, cam)
  local v = (world - cam) % ARENA_W
  if v >= ARENA_W - 16 then v = v - ARENA_W end
  if v > -16 and v < SCREEN_W then return v end
  return nil
end

local function finish(ok, msg)
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

local n, phase, phase_at = 0, "boot", 0
local vram, vaddr, vmod = {}, 0, 1
local watching, bad_vram, total = false, 0, 0
local haz_writes, cur_haz_writes = 0, 0
local plane_writes, cur_plane_writes, plane_stray, sky_writes = {}, {}, 0, 0
for p = 1, 5 do plane_writes[p] = 0; cur_plane_writes[p] = 0 end
local to_end_in_vblank = function()
  return screen:time_until_vblank_end():as_double() < screen:time_until_vblank_start():as_double()
end
local HERO4, HAZ4_0, HAZ4_END = 0x8400 + HERO, 0x8400 + HAZ, 0x8400 + HAZ + 2 * HAZ_COLS
tap_vram = mem:install_write_tap(0x3c0000, 0x3c000f, "cam", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 4 then vmod = data
  elseif r == 2 then
    vram[vaddr] = data
    if watching then
      total = total + 1
      if not to_end_in_vblank() then bad_vram = bad_vram + 1 end
      if vaddr >= HAZ4_0 and vaddr < HAZ4_END then cur_haz_writes = cur_haz_writes + 1 end
      for p, pl in ipairs(PLANES) do
        if vaddr >= 0x8400 + pl.slot and vaddr < 0x8400 + pl.slot + pl.cols then cur_plane_writes[p] = cur_plane_writes[p] + 1 end
      end
    end
    vaddr = (vaddr + vmod) & 0xffff
  end
end)

local hist = {}          -- last frames: { cam, flier world x }
local cam_prev, cam_max, max_step, seam_at, last_wx = nil, 0, 0, nil, nil
local hero_checked, hero_hidden, hero_bad, haz_bad, haz_stray, haz_x_checked = 0, 0, 0, 0, 0, 0
local last_cam_change, first_msg = -100, nil
local ramp_first, ramp_last = nil, 0
local bgx_first, bgx_last, bgx_still_moved, plane_x_checked, plane_bad = nil, nil, 0, 0, 0
local haz_cam_hi, haz_cam_seam = 0, 0
local isl_checked, isl_bad, isl_cam_hi, isl_cam_seam = 0, 0, 0, 0
local tick, END_AFTER = 0, nil
local function bad(msg) first_msg = first_msg or msg end

emu.register_frame_done(function() local ok_, err_ = pcall(function()
  n = n + 1
  if n > 6000 then finish(false, string.format("watchdog: phase %s cam_max %d seam %s", phase, cam_max, tostring(seam_at))) return end
  if not (coin and start and abtn and rbtn and lbtn and flay[10] and lay[7] and bgx_addr and camu_addr and lay[27] and stage_addr) then finish(false, "missing input or layout") return end
  local state = mem:read_u8(flow_addr + O_STATE)
  if phase == "boot" then
    if n >= 300 then phase = "coin"; phase_at = n; ss.begin(n) end
    return
  elseif phase == "coin" then
    if ss.step(n, state == 3) then phase = "run"; phase_at = n end
    return
  end
  if state ~= 3 then
    finish(false, string.format("flow left PLAYING (state %d, flier state %d) with cam_max %d seam %s", state,
      mem:read_u8(flow_addr + O_FSTATE), cam_max, tostring(seam_at)))
    return
  end
  local cam = mem:read_u16(cam_addr)
  local fx = s32(mem:read_u32(flow_addr + O_X)) >> 16
  local fy = s32(mem:read_u32(flow_addr + O_Y)) / 65536
  -- keep the hero alive: rivals stay on screen beside the hero, one each side, out of pair contact. flier_pair reaches
  -- FLIER_PAIR_REACH_HALF half pixels (src/core/flier.h:71, via camera_probe.c) = REACH_PX; twice that is clear of any one-frame hero move
  hold_rivals(fx, { 2 * REACH_PX, -2 * REACH_PX })
  -- drive: right, flap to stay airborne
  -- Right is held until the human has crossed the seam, then released so the camera comes to rest past the seam (the still-camera
  -- column checks need frames with the camera above 65 and after the seam; a held Right never lets it rest)
  -- the flight model has no air drag: after the seam, brake with Left until vx is not positive, or the hero laps the ring
  local vx = s32(mem:read_u32(flow_addr + O_VX)) / 65536
  rbtn:set_value(seam_at and 0 or 1); lbtn:set_value((seam_at and vx > 0) and 1 or 0)
  abtn:set_value((fy > 70 and tick % 2 == 0) and 1 or 0)
  tick = tick + 1
  if phase_at + 20 < n then watching = true end
  if not watching then cam_prev = cam; last_wx = fx; return end

  -- camera step
  if cam > cam_max then cam_max = cam end
  if cam ~= cam_prev then
    local d = math.abs(cam - cam_prev)
    if d > ARENA_W // 2 then d = ARENA_W - d end -- g_cam_px wraps at the seam: the step is the ring distance (as ring_check A3)
    if d > max_step then max_step = d end
    last_cam_change = n
  end
  cam_prev = cam
  -- seam: the human world x drops by more than half the arena in one frame
  if last_wx and last_wx - fx > ARENA_W // 2 and not seam_at then seam_at = n end
  last_wx = fx
  hist[#hist + 1] = { cam, fx }
  if #hist > 3 then table.remove(hist, 1) end

  -- hazard: every column of both banks at its ring x; a write only within 2 frames after a camera change
  if cur_haz_writes > 0 and n - last_cam_change > 2 then haz_stray = haz_stray + 1; bad("hazard SCB4 written without a camera change at frame " .. n) end
  cur_haz_writes = 0
  if n - last_cam_change > 2 then
    if cam > 65 then haz_cam_hi = haz_cam_hi + 1 end
    if seam_at then haz_cam_seam = haz_cam_seam + 1 end
    for b = 0, 1 do
      for c = 0, HAZ_COLS - 1 do
        local want = column_x(16 * c, cam) or SCREEN_W
        local got = ((vram[HAZ4_0 + b * HAZ_COLS + c] or 0) >> 7) & 0x1ff
        haz_x_checked = haz_x_checked + 1
        if got ~= (want & 0x1ff) then haz_bad = haz_bad + 1; bad(string.format("hazard bank %d column %d SCB4 x %d, want %d (camera %d)", b, c, got, want, cam)) end
      end
    end
  end
  -- planes: x per column once the camera is still; writes only after a camera change
  local bgx = mem:read_u32(bgx_addr)
  bgx_first = bgx_first or bgx
  if bgx_last and bgx ~= bgx_last and n - last_cam_change > 2 then bgx_still_moved = bgx_still_moved + 1; bad("g_bg_x_writes moved without a camera change at frame " .. n) end
  bgx_last = bgx
  ramp_last = ramp_addr and mem:read_u32(ramp_addr) or 0
  ramp_first = ramp_first or ramp_last
  local camu = mem:read_u32(camu_addr) & 0x7fffffff
  for p, pl in ipairs(PLANES) do
    if cur_plane_writes[p] > 0 then
      plane_writes[p] = plane_writes[p] + cur_plane_writes[p]
      if p == 1 then sky_writes = sky_writes + cur_plane_writes[p]; bad("sky plane SCB4 written at frame " .. n) end
      if n - last_cam_change > 2 then plane_stray = plane_stray + 1; bad("plane " .. p .. " SCB4 written without a camera change at frame " .. n) end
    end
    cur_plane_writes[p] = 0
    if n - last_cam_change > 2 then
      for c = 0, pl.cols - 1 do
        -- looping plane (bg_column_x): offset = ((unwrapped camera * k) >> 4) mod plane width; g_cam_px wraps at the ring seam, the planes do not
        local period = 16 * pl.cols
        local x = 16 * c - (((camu * pl.k) >> 4) % period)
        if x <= -16 then x = x + period end
        local want = x & 0x1ff
        local got = ((vram[0x8400 + pl.slot + c] or 0) >> 7) & 0x1ff
        plane_x_checked = plane_x_checked + 1
        if got ~= want then plane_bad = plane_bad + 1; bad(string.format("plane %d column %d SCB4 x %d, want %d (camera %d)", p, c, got, want, cam)) end
      end
    end
  end
  -- islands: every column sprite hidden or at its own ring x once the camera is still
  if n - last_cam_change > 2 then
    local slot = ISL_SLOT
    for i = 0, ISL_N - 1 do
      local px, py, pw = mem:read_i16(stage_addr + 8 * i), mem:read_i16(stage_addr + 8 * i + 2), mem:read_i16(stage_addr + 8 * i + 4)
      for c = 0, pw // 16 - 1 do
        local want = column_x(px + 16 * c, cam)
        local scb3, scb4 = vram[0x8200 + slot] or 0, vram[0x8400 + slot] or 0
        isl_checked = isl_checked + 1
        if want then
          local got = (scb4 >> 7) & 0x1ff
          if got ~= (want & 0x1ff) or (scb3 & 0x3f) ~= 1 or ((scb3 >> 7) & 0x1ff) ~= ((496 - (py - ISL_ROW)) & 0x1ff) or (scb3 & 0x40) ~= 0 then
            isl_bad = isl_bad + 1; bad(string.format("island %d column %d SCB4 x %d SCB3 0x%04x, want x %d height 1 (camera %d)", i, c, got, scb3, want, cam))
          end
        elseif (scb3 & 0x3f) ~= 0 then
          isl_bad = isl_bad + 1; bad(string.format("island %d column %d should be hidden, SCB3 0x%04x (camera %d)", i, c, scb3, cam))
        end
        slot = slot + 1
      end
    end
    if cam > 65 then isl_cam_hi = isl_cam_hi + 1 end
    if seam_at then isl_cam_seam = isl_cam_seam + 1 end
  end
  -- hero: the SCB4 x matches the helper for one of the last 3 (camera, x) pairs; hidden while off screen is fine
  if n - last_cam_change > 2 or true then
    local sx_word = ((vram[HERO4] or 0) >> 7) & 0x1ff
    local shown = (vram[0x8200 + HERO] or 0) & 0x3f ~= 0
    local vis_now = false
    local match = false
    local wants = {}
    for _, h in ipairs(hist) do
      local sx = screen_x(h[2] - HALF_W - SOOT_BOX_DX, h[1], SOOT_W)
      wants[#wants + 1] = string.format("cam %d fx %d -> %d", h[1], h[2], sx)
      if sx > -SOOT_W and sx < SCREEN_W then vis_now = true end
      if (sx & 0x1ff) == sx_word then match = true end
    end
    if shown and #hist < 3 then
      -- the first frames of the run have fewer than 3 (camera, x) pairs: the SCB4 word on screen comes from the frame before
      -- the first pair, so it cannot be compared yet (it was the 1 of 270 frames, wanted list of one pair)
    elseif shown then
      hero_checked = hero_checked + 1
      if not match then hero_bad = hero_bad + 1; bad(string.format("hero SCB4 x %d matches none of the last 3 frames (cam %d, flier x %d; wanted: %s)", sx_word, cam, fx, table.concat(wants, "; "))) end
    else
      hero_hidden = hero_hidden + 1
    end
  end
  -- rivals: every live computer flier object's head sprite, over the whole run (the seam included)
  do
    local cur = {}
    for i = 0, RV.max - 1 do
      local o = RV.addr + i * RV.size
      local fl = mem:read_u8(o + RV.of)
      if (fl & RV.live) ~= 0 and (fl & RV.hero) ~= 0 then cur[i] = s32(mem:read_u32(o + RV.ox)) >> 16 end
    end
    RV.hist[#RV.hist + 1] = { cam = cam, px = cur }
    if #RV.hist > 3 then table.remove(RV.hist, 1) end
    for i = 0, RV.max - 1 do
      local slot = RV.base + i * RV.cols
      local scb3, sx_word = vram[0x8200 + slot] or 0, ((vram[0x8400 + slot] or 0) >> 7) & 0x1ff
      if cur[i] and #RV.hist == 3 and (scb3 & 0x3f) ~= 0 then
        local match, wants = false, {}
        for _, h in ipairs(RV.hist) do
          if h.px[i] then
            local sx = screen_x(h.px[i] - HALF_W - SOOT_BOX_DX, h.cam, SOOT_W)
            wants[#wants + 1] = string.format("cam %d x %d -> %d", h.cam, h.px[i], sx)
            if (sx & 0x1ff) == sx_word then match = true end
          end
        end
        RV.checked = RV.checked + 1
        if RV.hist[3].cam + SCREEN_W > ARENA_W then RV.wrapped = RV.wrapped + 1 end
        if not match then RV.bad = RV.bad + 1; RV.first = RV.first or string.format("pool %d SCB4 x %d at frame %d matches none of: %s", i, sx_word, n, table.concat(wants, "; ")) end
      elseif cur[i] and #RV.hist == 3 then
        -- hidden: legal only when the rival is off screen in at least one of the last 3 frames
        local off = false
        for _, h in ipairs(RV.hist) do
          if h.px[i] then
            local sx = screen_x(h.px[i] - HALF_W - SOOT_BOX_DX, h.cam, SOOT_W)
            if sx <= -SOOT_W or sx >= SCREEN_W then off = true end
          end
        end
        RV.hidden = RV.hidden + 1
        if not off then RV.bad = RV.bad + 1; RV.first = RV.first or string.format("pool %d hidden at frame %d but on screen", i, n) end
      end
    end
  end
  if seam_at and not END_AFTER and haz_cam_seam > 20 and isl_cam_seam > 20 then END_AFTER = n + 30 end
  if END_AFTER and n >= END_AFTER then
    local ok = cam_max > CAM_MAX and seam_at and max_step <= 2 and hero_bad == 0 and hero_checked > 100 and haz_bad == 0
      and haz_stray == 0 and haz_x_checked > 1000 and haz_cam_hi > 10 and haz_cam_seam > 10 and bad_vram == 0 and total > 0
      and plane_bad == 0 and plane_stray == 0 and sky_writes == 0 and bgx_still_moved == 0 and plane_x_checked > 1000
      and isl_bad == 0 and isl_checked > 1000 and isl_cam_hi > 10 and isl_cam_seam > 10 and plane_writes[5] > 0 and plane_writes[2] > 0 and bgx_last > bgx_first and ramp_addr ~= nil and ramp_last > ramp_first and ramp_last - ramp_first >= bgx_last - bgx_first - 4
      and RV.addr ~= nil and RV.bad == 0 and RV.checked > 100 and RV.wrapped > 10
    local msg = string.format("camera max %d (want > %d), seam crossed %s, max camera step %d px (want <= 2), hero x checked %d frames (%d hidden), bad %d (want 0), hazard column x checked %d (still frames with camera > 65 %d, after the seam %d), bad %d, stray writes %d (want 0), plane columns checked %d, bad %d, stray plane writes %d, sky writes %d (want 0), plane SCB4 words written far %d near %d, g_bg_x_writes %d -> %d, VQ_RAMP ops flushed %d, VRAM writes outside vblank %d of %d (want 0), island columns checked %d, bad %d (want 0), still frames with camera > 65 %d, after the seam %d%s",
      cam_max, CAM_MAX, tostring(seam_at ~= nil), max_step, hero_checked, hero_hidden, hero_bad, haz_x_checked, haz_cam_hi, haz_cam_seam, haz_bad, haz_stray, plane_x_checked, plane_bad, plane_stray, sky_writes, plane_writes[2], plane_writes[5], bgx_first, bgx_last, ramp_last - (ramp_first or 0), bad_vram, total, isl_checked, isl_bad, isl_cam_hi, isl_cam_seam, first_msg and ("; first: " .. first_msg) or "")
    msg = msg .. string.format("; rival head x checked %d (%d hidden, %d with the view across the ring seam), bad %d (want 0)%s", RV.checked, RV.hidden, RV.wrapped, RV.bad, RV.first and (" first: " .. RV.first) or "")
    finish(ok and true or false, msg)
  end
end) if not ok_ then print('LUAERR ' .. tostring(err_)); finish(false, 'lua error: ' .. tostring(err_)) end end)
