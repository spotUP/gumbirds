-- Headless ring check (make test-ring). The arena is a ring (ARENA_W px); the player must stay on screen across the seam.
-- Timeline, sentinel driven (modelled on tests/mame/camera_check.lua: input fields, VRAM write tap, finish()):
--   1. coin, start, wait for PLAYING;
--   2. hold LEFT (A flaps when the flier sinks below y 70) until the player's world x has wrapped from near 0 to near
--      ARENA_W-1 (a seam crossing), then hold RIGHT until it wraps back; then 30 frames more.
--   3. every PLAYING frame after a short settle:
--      A1. screen x of the flier centre = ((world x - g_cam_px) mod ARENA_W) lies in 0..SCREEN_W-1;
--      A2. the hero sprite SCB3 height word (VRAM 0x8200 + HERO_SPRITE) & 0x3f is non-zero once control starts (round-start
--          freeze over, spawn protection spawn_inv 0);
--      A2b. while spawn_inv > 0 a hidden hero frame must match the blink of flier_view_visible: (game.frame / BLINK) odd;
--      the computer fliers are parked on the far side of the ring every frame (test side only) so they cannot stomp the hero;
--      A3. g_cam_px moves at most CAM_MAX_STEP_PX per frame, as a ring distance;
--      A4. sentinel: the world x wrapped at least once left (near 0 -> near ARENA_W) and once right.
-- (BLINK = FLIER_BLINK_HALF_PERIOD from ring_probe.c.)
-- Env: BRAWL_FLOW_ADDR, BRAWL_CAM_ADDR, BRAWL_CAM_SIZE (hex bytes of g_cam_px from nm -S: 1 = u8, 2 = u16),
-- BRAWL_FLIER_LAYOUT (flier_probe.c), BRAWL_RING_LAYOUT (ring_probe.c), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local cam_addr  = tonumber(os.getenv("BRAWL_CAM_ADDR"), 16)
local cam_size  = tonumber(os.getenv("BRAWL_CAM_SIZE") or "", 16)
local result    = os.getenv("BRAWL_RESULT")
local function nums(name) local t = {} for v in (os.getenv(name) or ""):gmatch("%d+") do t[#t + 1] = tonumber(v) end return t end
local flay, rlay = nums("BRAWL_FLIER_LAYOUT"), nums("BRAWL_RING_LAYOUT")
local O_STATE, O_X, O_Y, O_FSTATE = flay[1], flay[6], flay[7], flay[10]
local SCREEN_W, ARENA_W, MAX_STEP, HERO, BLINK = rlay[1], rlay[2], rlay[3], rlay[4], rlay[5]
local O_FRAME, O_CPUN, O_C0X, O_C0Y, O_C1X, O_SPAWN = flay[2], flay[13], flay[17], flay[18], flay[20], flay[26]
local CPU_STRIDE = (O_C1X or 0) - (O_C0X or 0)
local mem   = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
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

local function finish(ok, msg)
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

local vram, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c000f, "ring", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 4 then vmod = data
  elseif r == 2 then vram[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff end
end)

local function read_cam() if cam_size == 2 then return mem:read_u16(cam_addr) else return mem:read_u8(cam_addr) end end
local function ring_dist(a, b) local d = (a - b) % ARENA_W; if d > ARENA_W // 2 then d = d - ARENA_W end return d end

local n, phase, phase_at, tick = 0, "boot", 0, 0
local last_wx, cam_prev
local checked, off_screen, hidden, max_step, step_bad = 0, 0, 0, 0, 0
local seam_left, seam_right, end_at = 0, 0, nil
local first_off, first_hidden, first_step, first_blink
local blink_bad, blink_seen = 0, 0
local min_sx, max_sx = 1e9, -1e9

emu.register_frame_done(function() local ok_, err_ = pcall(function()
  n = n + 1
  if n > 7000 then finish(false, string.format("watchdog: phase %s seams left %d right %d", phase, seam_left, seam_right)) return end
  if not (coin and start and abtn and rbtn and lbtn and flay[26] and CPU_STRIDE > 0 and rlay[5] and cam_addr and (cam_size == 1 or cam_size == 2)) then finish(false, "missing input, layout or sentinel size") return end
  local state = mem:read_u8(flow_addr + O_STATE)
  if phase == "boot" then
    if n >= 300 then phase = "coin"; phase_at = n; ss.begin(n) end
    return
  elseif phase == "coin" then
    if ss.step(n, state == 3) then phase = "left"; phase_at = n end
    return
  end
  local cam = read_cam()
  local fx = (s32(mem:read_u32(flow_addr + O_X)) >> 16) % ARENA_W
  local fy = s32(mem:read_u32(flow_addr + O_Y)) / 65536
  if state ~= 3 then
    finish(false, string.format("flow left PLAYING (state %d, flier state %d) in phase %s at world x %d, seams left %d right %d; checked %d frames, off screen %d (first: %s), sprite hidden %d (first: %s)",
      state, mem:read_u8(flow_addr + O_FSTATE), phase, fx, seam_left, seam_right, checked, off_screen, tostring(first_off), hidden, tostring(first_hidden)))
    return
  end
  -- keep the hero alive: park every computer flier half a ring away at the hero's height (no invincibility, it blinks)
  hold_rivals(fx, { ARENA_W // 2 })
  local left = (phase == "left")
  lbtn:set_value(left and 1 or 0); rbtn:set_value(left and 0 or 1)
  abtn:set_value((fy > 70 and tick % 2 == 0) and 1 or 0)
  tick = tick + 1
  -- A4 seam crossings: world x jumps by more than half the ring in one frame
  if last_wx then
    local j = fx - last_wx
    if j > ARENA_W // 2 then seam_left = seam_left + 1 elseif j < -ARENA_W // 2 then seam_right = seam_right + 1 end
  end
  last_wx = fx
  if phase == "left" and seam_left >= 1 then phase = "right"; phase_at = n end
  if phase == "right" and seam_right >= 1 and not end_at then end_at = n + 30 end
  if n < 5 + phase_at and checked == 0 then cam_prev = cam; return end
  -- A3 camera step, ring distance
  if cam_prev then
    local d = math.abs(ring_dist(cam, cam_prev))
    if d > max_step then max_step = d end
    if d > MAX_STEP then step_bad = step_bad + 1; first_step = first_step or string.format("cam %d -> %d at frame %d", cam_prev, cam, n) end
  end
  cam_prev = cam
  -- A1 body on screen
  local sx = (fx - cam) % ARENA_W
  if sx < min_sx then min_sx = sx end
  if sx > max_sx then max_sx = sx end
  checked = checked + 1
  if sx > SCREEN_W - 1 then
    off_screen = off_screen + 1
    first_off = first_off or string.format("screen x %d (world x %d, cam %d) at frame %d", sx, fx, cam, n)
  end
  -- A2 hero sprite shown
  local protected = mem:read_u16(flow_addr + O_SPAWN) > 0
  if (vram[0x8200 + HERO] or 0) & 0x3f == 0 then
    local gf = mem:read_u32(flow_addr + O_FRAME)
    if protected then
      blink_seen = blink_seen + 1
      -- the VRAM tap sees the sprites drawn from the previous game frame (one frame of display lag)
      if (((gf - 1) // BLINK) & 1) == 0 then blink_bad = blink_bad + 1; first_blink = first_blink or string.format("frame %d (game frame %d)", n, gf) end
    else
      hidden = hidden + 1
      first_hidden = first_hidden or string.format("frame %d (world x %d, cam %d)", n, fx, cam)
    end
  end
  if end_at and n >= end_at then
    local ok = off_screen == 0 and hidden == 0 and blink_bad == 0 and blink_seen >= 1 and step_bad == 0 and seam_left >= 1 and seam_right >= 1 and checked > 100
    local msg = string.format("ring: checked %d PLAYING frames, flier screen x %d..%d (want 0..%d), off screen %d (want 0, first: %s), hero SCB3 height zero %d (want 0, first: %s), hidden outside the blink while protected %d (want 0, first: %s), hidden frames seen while protected %d (want >= 1), camera max step %d px (want <= %d), steps over %d (first: %s), seam crossings left %d right %d (want >= 1 each), camera sentinel %d bytes",
      checked, min_sx, max_sx, SCREEN_W - 1, off_screen, tostring(first_off), hidden, tostring(first_hidden), blink_bad, tostring(first_blink), blink_seen, max_step, MAX_STEP, step_bad, tostring(first_step), seam_left, seam_right, cam_size)
    finish(ok, msg)
  end
end) if not ok_ then print('LUAERR ' .. tostring(err_)); finish(false, 'lua error: ' .. tostring(err_)) end end)
