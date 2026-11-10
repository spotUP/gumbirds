-- Headless camera check (make test-camera). Sentinel-driven timeline, no fixed frame numbers:
--   1. coin, start; wait for PLAYING;
--   2. drive the human right (hold Right, flap to stay airborne) until the camera pixel sentinel g_cam_px (src/main.c)
--      goes 0 -> ARENA_CAM_MAX (64), then keep going until the human wraps across the arena seam (world x 384 -> 0),
--      then 60 more frames;
--   3. every frame: the hero SCB4 x (read from the VRAM writes) equals camera_screen_x for the (camera, flier x) pair of
--      the last 3 frames; the camera moves at most 2 px per frame; the hazard head SCB4 x equals -camera; the hazard
--      SCB4 is written only within 2 frames after the camera pixel changed; zero VRAM writes outside vblank.
--   4. background planes (slots, factors, column counts from camera_probe.c): with the camera still for more than 2 frames
--      every column of every plane sits at x = -((camera * k) >> 4) + 16 * column, so the near plane follows the camera
--      1:1, the far plane a quarter, the sky never moves; plane SCB4 words are written only within 2 frames after a camera
--      change, the sky never; the sentinel g_bg_x_writes proves bg_update ran (it moves only on camera-move frames).
-- Env: BRAWL_FLOW_ADDR, BRAWL_CAM_ADDR, BRAWL_BGX_ADDR, BRAWL_FLIER_LAYOUT (flier_probe.c), BRAWL_CAMERA_LAYOUT
-- (camera_probe.c), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local cam_addr  = tonumber(os.getenv("BRAWL_CAM_ADDR"), 16)
local result    = os.getenv("BRAWL_RESULT")
local function nums(name) local t = {} for v in (os.getenv(name) or ""):gmatch("%d+") do t[#t + 1] = tonumber(v) end return t end
local flay, lay = nums("BRAWL_FLIER_LAYOUT"), nums("BRAWL_CAMERA_LAYOUT")
local O_STATE, O_X, O_Y, O_FSTATE = flay[1], flay[6], flay[7], flay[10]
local HERO, HAZ, HAZ_COLS, ARENA_W, SCREEN_W, HALF_W, CAM_MAX = lay[1], lay[2], lay[3], lay[4], lay[5], lay[6], lay[7]
local SOOT_W, SOOT_BOX_DX = lay[8], lay[9] -- frame width and hit box offset from frames.json (camera_probe.c)
local PLANES = {} -- first sprite slot, parallax factor in sixteenths, column count, in draw order
for p = 1, 5 do PLANES[p] = { slot = lay[9 + p], k = lay[14 + p], cols = lay[19 + p] } end
local bgx_addr = tonumber(os.getenv("BRAWL_BGX_ADDR"), 16)
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
local abtn  = field(":edge:joy:JOY1", "P1 A")
local rbtn  = field(":edge:joy:JOY1", "P1 Right")
local lbtn  = field(":edge:joy:JOY1", "P1 Left")
local function s32(v) return v >= 0x80000000 and v - 0x100000000 or v end

-- the same maths as src/core/camera.c camera_screen_x, written out independently
local function screen_x(world, cam, w)
  local x = (world % ARENA_W) - cam
  while x < -w do x = x + ARENA_W end
  while x >= ARENA_W - w do x = x - ARENA_W end
  return x
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
local HERO4, HAZ4_0, HAZ4_1 = 0x8400 + HERO, 0x8400 + HAZ, 0x8400 + HAZ + HAZ_COLS
tap_vram = mem:install_write_tap(0x3c0000, 0x3c000f, "cam", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 4 then vmod = data
  elseif r == 2 then
    vram[vaddr] = data
    if watching then
      total = total + 1
      if not to_end_in_vblank() then bad_vram = bad_vram + 1 end
      if vaddr == HAZ4_0 or vaddr == HAZ4_1 then cur_haz_writes = cur_haz_writes + 1 end
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
local bgx_first, bgx_last, bgx_still_moved, plane_x_checked, plane_bad = nil, nil, 0, 0, 0
local tick, END_AFTER = 0, nil
local function bad(msg) first_msg = first_msg or msg end

emu.register_frame_done(function() local ok_, err_ = pcall(function()
  n = n + 1
  if n > 6000 then finish(false, string.format("watchdog: phase %s cam_max %d seam %s", phase, cam_max, tostring(seam_at))) return end
  if not (coin and start and abtn and rbtn and lbtn and flay[10] and lay[7] and bgx_addr and lay[24]) then finish(false, "missing input or layout") return end
  local state = mem:read_u8(flow_addr + O_STATE)
  if phase == "boot" then
    if n >= 300 then phase = "coin"; phase_at = n; coin:set_value(1) end
    return
  elseif phase == "coin" then
    if n == phase_at + 15 then coin:set_value(0) end
    if n >= phase_at + 40 then phase = "start"; phase_at = n; start:set_value(1) end
    return
  elseif phase == "start" then
    if state ~= 3 then return end
    start:set_value(0); phase = "run"; phase_at = n
    return
  end
  if state ~= 3 then
    finish(false, string.format("flow left PLAYING (state %d, flier state %d) with cam_max %d seam %s", state,
      mem:read_u8(flow_addr + O_FSTATE), cam_max, tostring(seam_at)))
    return
  end
  local cam = mem:read_u8(cam_addr)
  local fx = s32(mem:read_u32(flow_addr + O_X)) >> 16
  local fy = s32(mem:read_u32(flow_addr + O_Y)) / 65536
  -- drive: right, flap to stay airborne
  rbtn:set_value(1); lbtn:set_value(0)
  abtn:set_value((fy > 70 and tick % 2 == 0) and 1 or 0)
  tick = tick + 1
  if phase_at + 20 < n then watching = true end
  if not watching then cam_prev = cam; last_wx = fx; return end

  -- camera step
  if cam > cam_max then cam_max = cam end
  if cam ~= cam_prev then
    local d = math.abs(cam - cam_prev)
    if d > max_step then max_step = d end
    last_cam_change = n
  end
  cam_prev = cam
  -- seam: the human world x drops by more than half the arena in one frame
  if last_wx and last_wx - fx > ARENA_W // 2 and not seam_at then seam_at = n end
  last_wx = fx
  hist[#hist + 1] = { cam, fx }
  if #hist > 3 then table.remove(hist, 1) end

  -- hazard: shadow x equals -camera; a write only within 2 frames after a camera change
  if cur_haz_writes > 0 and n - last_cam_change > 2 then haz_stray = haz_stray + 1; bad("hazard SCB4 written without a camera change at frame " .. n) end
  cur_haz_writes = 0
  if n - last_cam_change > 2 then
    local want = (-cam) & 0x1ff
    for _, a in ipairs({ HAZ4_0, HAZ4_1 }) do
      haz_x_checked = haz_x_checked + 1
      if ((vram[a] or 0) >> 7) & 0x1ff ~= want then haz_bad = haz_bad + 1; bad(string.format("hazard SCB4 x %d, want %d (camera %d)", ((vram[a] or 0) >> 7) & 0x1ff, want, cam)) end
    end
  end
  -- planes: x per column once the camera is still; writes only after a camera change
  local bgx = mem:read_u32(bgx_addr)
  bgx_first = bgx_first or bgx
  if bgx_last and bgx ~= bgx_last and n - last_cam_change > 2 then bgx_still_moved = bgx_still_moved + 1; bad("g_bg_x_writes moved without a camera change at frame " .. n) end
  bgx_last = bgx
  for p, pl in ipairs(PLANES) do
    if cur_plane_writes[p] > 0 then
      plane_writes[p] = plane_writes[p] + cur_plane_writes[p]
      if p == 1 then sky_writes = sky_writes + cur_plane_writes[p]; bad("sky plane SCB4 written at frame " .. n) end
      if n - last_cam_change > 2 then plane_stray = plane_stray + 1; bad("plane " .. p .. " SCB4 written without a camera change at frame " .. n) end
    end
    cur_plane_writes[p] = 0
    if n - last_cam_change > 2 then
      for c = 0, pl.cols - 1 do
        local want = (-((cam * pl.k) >> 4) + 16 * c) & 0x1ff
        local got = ((vram[0x8400 + pl.slot + c] or 0) >> 7) & 0x1ff
        plane_x_checked = plane_x_checked + 1
        if got ~= want then plane_bad = plane_bad + 1; bad(string.format("plane %d column %d SCB4 x %d, want %d (camera %d)", p, c, got, want, cam)) end
      end
    end
  end
  -- hero: the SCB4 x matches the helper for one of the last 3 (camera, x) pairs; hidden while off screen is fine
  if n - last_cam_change > 2 or true then
    local sx_word = ((vram[HERO4] or 0) >> 7) & 0x1ff
    local shown = (vram[0x8200 + HERO] or 0) & 0x3f ~= 0
    local vis_now = false
    local match = false
    for _, h in ipairs(hist) do
      local sx = screen_x(h[2] - HALF_W - SOOT_BOX_DX, h[1], SOOT_W)
      if sx > -SOOT_W and sx < SCREEN_W then vis_now = true end
      if (sx & 0x1ff) == sx_word then match = true end
    end
    if shown then
      hero_checked = hero_checked + 1
      if not match then hero_bad = hero_bad + 1; bad(string.format("hero SCB4 x %d matches none of the last 3 frames (cam %d, flier x %d)", sx_word, cam, fx)) end
    else
      hero_hidden = hero_hidden + 1
    end
  end
  if seam_at and not END_AFTER then END_AFTER = n + 60 end
  if END_AFTER and n >= END_AFTER then
    local ok = cam_max >= CAM_MAX and seam_at and max_step <= 2 and hero_bad == 0 and hero_checked > 100 and haz_bad == 0
      and haz_stray == 0 and haz_x_checked > 100 and bad_vram == 0 and total > 0
      and plane_bad == 0 and plane_stray == 0 and sky_writes == 0 and bgx_still_moved == 0 and plane_x_checked > 1000
      and plane_writes[5] > 0 and plane_writes[2] > 0 and bgx_last > bgx_first
    local msg = string.format("camera 0 -> %d (want %d), seam crossed %s, max camera step %d px (want <= 2), hero x checked %d frames (%d hidden), bad %d (want 0), hazard x checked %d, bad %d, stray writes %d (want 0), plane columns checked %d, bad %d, stray plane writes %d, sky writes %d (want 0), plane SCB4 words written far %d near %d, g_bg_x_writes %d -> %d, VRAM writes outside vblank %d of %d (want 0)%s",
      cam_max, CAM_MAX, tostring(seam_at ~= nil), max_step, hero_checked, hero_hidden, hero_bad, haz_x_checked, haz_bad, haz_stray, plane_x_checked, plane_bad, plane_stray, sky_writes, plane_writes[2], plane_writes[5], bgx_first, bgx_last, bad_vram, total, first_msg and ("; first: " .. first_msg) or "")
    finish(ok and true or false, msg)
  end
end) if not ok_ then print('LUAERR ' .. tostring(err_)); finish(false, 'lua error: ' .. tostring(err_)) end end)
