-- Small Sootling reachability (make test-small-sootling): the 24 x 32 sheet is what the real ROM draws for the player.
-- Spec numbers are written out here (not read from the build) so a stale sheet fails:
--   art 24 x 32, 248 tiles in the Sootling C-ROM range (160 before the walk, landing and breathing clips; the old 32 x 48 sheet has 296), sprite 32 wide (2 columns),
--   hit box offset 14 ((32 - 24) / 2 + box first column 10).
-- Timeline: coin, start, wait for PLAYING, settle on the island, flap 8 times, settle again. Checks:
--   1. probe values (what the ROM was built with) equal the spec numbers; g_soot_range holds the same tile count;
--   2. hero SCB3 height is 2 tiles (32 px); the hero strips' SCB1 tile words lie in [base, base + count);
--   3. sentinel: g_soot_player_tile (set in hero_show) stays in range and takes at least 2 values over the flaps
--      (the frame select ran);
--   4. standing still (on the ground, position and camera unchanged for 3 frames): sprite top y = feet - 32 with
--      feet = y + 5.5 px, and the hero SCB4 x = camera_screen_x(flier x - half width - 14).
-- Env: BRAWL_FLOW_ADDR, BRAWL_FRAME_ADDR, BRAWL_SOOT_ADDR (g_soot_range), BRAWL_CAM_ADDR (g_cam_px), BRAWL_FLIER_LAYOUT
-- (flier_probe.c), BRAWL_SOOT_LAYOUT (small_sootling_probe.c), BRAWL_RESULT.
local flow_addr  = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local frame_addr = tonumber(os.getenv("BRAWL_FRAME_ADDR"), 16)
local soot_addr  = tonumber(os.getenv("BRAWL_SOOT_ADDR"), 16)
local cam_addr   = tonumber(os.getenv("BRAWL_CAM_ADDR"), 16)
local result     = os.getenv("BRAWL_RESULT")
local function nums(name) local t = {} for v in (os.getenv(name) or ""):gmatch("%d+") do t[#t + 1] = tonumber(v) end return t end
local flay, slay = nums("BRAWL_FLIER_LAYOUT"), nums("BRAWL_SOOT_LAYOUT")
local O_STATE, O_X, O_Y, O_VX, O_GROUND = flay[1], flay[6], flay[7], flay[8], flay[12]
local P_ART_W, P_ART_H, P_TILES, P_SPRITE_W, P_BOX_DX, HERO, HALF_W, HALF_H16, ARENA_W, SCREEN_W, POOL_BASE, POOL_COUNT = table.unpack(slay)
local SPEC = { art_w = 24, art_h = 32, tiles = 248, sprite_w = 32, box_dx = 14 }
local FLOW_PLAYING = 3

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

-- VRAM shadow through a write tap on the video port, as sprite_peak_check.lua
local vram, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "smallsootvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then vram[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
  elseif r == 4 then vmod = data end
end)

local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

local function s32(v) return v >= 0x80000000 and v - 0x100000000 or v end
local function g32(o) return mem:read_u32(flow_addr + o) end
-- the same maths as src/core/camera.c camera_screen_x, written out independently (as camera_check.lua)
local function screen_x(world, cam, w)
  local x = (world % ARENA_W) - cam
  while x < -w do x = x + ARENA_W end
  while x >= ARENA_W - w do x = x - ARENA_W end
  return x
end

local n, phase, fc0, coin_at, tick, flaps = 0, "boot", nil, nil, 0, 0
local tiles_seen, checked, last_pos, still = {}, 0, nil, 0
local flapped = false

emu.register_frame_done(function() local ok_, err_ = pcall(function()
  if done then return end
  n = n + 1
  if n > 4000 then finish(false, "watchdog in phase " .. phase) return end
  if not (coin and start and abtn and frame_addr and soot_addr and cam_addr and #slay == 12 and O_GROUND) then
    finish(false, "missing input field, address or probe layout") return
  end
  local state = mem:read_u8(flow_addr + O_STATE)
  local fc = mem:read_u32(frame_addr)
  if phase == "boot" then
    if fc ~= 0 then fc0 = fc0 or fc end
    if fc0 and fc - fc0 >= 30 then phase = "coin"; coin_at = n; ss.begin(n) end
    return
  elseif phase == "coin" then
    if ss.step(n, state == FLOW_PLAYING) then phase = "start" else return end
  end
  if phase == "start" then
    -- 1. spec numbers against the build
    local sbase, scount = mem:read_u16(soot_addr), mem:read_u16(soot_addr + 2)
    if P_ART_W ~= SPEC.art_w or P_ART_H ~= SPEC.art_h or P_TILES ~= SPEC.tiles or P_SPRITE_W ~= SPEC.sprite_w or P_BOX_DX ~= SPEC.box_dx then
      finish(false, string.format("built with art %d x %d, %d tiles, sprite width %d, box dx %d; spec is %d x %d, %d tiles, %d, %d (stale sheet?)",
        P_ART_W, P_ART_H, P_TILES, P_SPRITE_W, P_BOX_DX, SPEC.art_w, SPEC.art_h, SPEC.tiles, SPEC.sprite_w, SPEC.box_dx)) return
    end
    if scount ~= SPEC.tiles then finish(false, string.format("g_soot_range tile count %d, spec %d", scount, SPEC.tiles)) return end
    phase = "settle"; tick = 0
    return
  end
  if state ~= FLOW_PLAYING then finish(false, "left PLAYING in phase " .. phase) return end

  local sbase, scount = mem:read_u16(soot_addr), mem:read_u16(soot_addr + 2)
  local ptile = mem:read_u16(soot_addr + 6)
  if ptile < sbase or ptile >= sbase + scount then
    finish(false, string.format("player sprite tile %d outside Sootling range %d+%d", ptile, sbase, scount)) return
  end
  tiles_seen[ptile] = true
  local w3 = vram[0x8200 + HERO] or 0
  local h = w3 & 0x3f
  if h ~= 0 then
    if h ~= SPEC.art_h // 16 then finish(false, string.format("hero SCB3 height %d tiles, spec %d (32 px)", h, SPEC.art_h // 16)) return end
    for c = 0, SPEC.sprite_w // 16 - 1 do
      for r = 0, h - 1 do
        local t = (vram[(HERO + c) * 64 + 2 * r] or 0)
        if t < sbase or t >= sbase + scount then
          finish(false, string.format("hero strip %d row %d tile word %d outside Sootling range %d+%d", c, r, t, sbase, scount)) return
        end
      end
    end
  end

  local x, y = g32(O_X), g32(O_Y)
  local cam = mem:read_u16(cam_addr)
  local on_ground = mem:read_u8(flow_addr + O_GROUND) == 1
  local pos = x .. ":" .. y .. ":" .. cam
  if pos == last_pos then still = still + 1 else still = 0 end
  last_pos = pos
  if on_ground and still >= 3 and h ~= 0 then
    local feet = (y + HALF_H16) >> 16
    local top = (496 - (w3 >> 7)) & 0x1ff
    if top ~= feet - SPEC.art_h then finish(false, string.format("hero sprite top %d, want feet %d - 32 = %d", top, feet, feet - SPEC.art_h)) return end
    local sx = ((vram[0x8400 + HERO] or 0) >> 7) & 0x1ff
    local want = screen_x((x >> 16) - HALF_W - SPEC.box_dx, cam, SPEC.sprite_w) & 0x1ff
    if sx ~= want then finish(false, string.format("hero screen x %d, want %d (flier x %d, camera %d)", sx, want, x >> 16, cam)) return end
    checked = checked + 1
  end

  if phase == "settle" then
    tick = tick + 1
    if on_ground and still >= 3 and (flapped or tick > 10) then
      if flapped then
        local kinds = 0
        for _ in pairs(tiles_seen) do kinds = kinds + 1 end
        -- ground braking is now linear (FLIER_GROUND_ACCEL), so a landed flier stands still a little later: wait for the standing frames before judging (the same asserts, up to 300 ticks).
        if (checked < 3 or kinds < 2) and tick < 300 then return end
        if checked < 3 or kinds < 2 then
          finish(false, string.format("standing checks %d (want >= 3), distinct player tiles %d (want >= 2)", checked, kinds)) return
        end
        local cpu_draws = mem:read_u16(soot_addr + 10)
        local cpu_tile = mem:read_u16(soot_addr + 8)
        if cpu_draws == 0 then finish(false, "no computer flier drawn (g_soot_cpu_draws 0)") return end
        if cpu_tile < sbase or cpu_tile >= sbase + scount then
          finish(false, string.format("computer sprite tile %d outside Sootling range %d+%d", cpu_tile, sbase, scount)) return
        end
        local seen = 0
        for slot = POOL_BASE, POOL_BASE + POOL_COUNT - 1, 3 do
          local hh = (vram[0x8200 + slot] or 0) & 0x3f
          if hh ~= 0 then
            if hh ~= SPEC.art_h // 16 then finish(false, string.format("computer sprite slot %d SCB3 height %d tiles, spec %d", slot, hh, SPEC.art_h // 16)) return end
            seen = seen + 1
          end
        end
        if seen == 0 then finish(false, "no pool slot has a Sootling sized SCB3") return end
        finish(true, string.format("small Sootling on screen: art %dx%d, %d tiles, hero SCB3 height %d tiles, %d distinct player tiles, %d standing frames matched top = feet - 32 and screen x",
          P_ART_W, P_ART_H, scount, SPEC.art_h // 16, kinds, checked))
        return
      end
      phase = "flap"; tick = 0; flaps = 0
    elseif tick > 900 then finish(false, "flier never settled on the island") end
    return
  elseif phase == "flap" then
    local k = tick % 6
    abtn:set_value(k < 2 and 1 or 0)
    if k == 0 then flaps = flaps + 1 end
    tick = tick + 1
    if flaps > 8 and k == 5 then abtn:set_value(0); flapped = true; phase = "settle"; tick = 0 end
  end
end) if not ok_ then print("BRAWL_TEST ERROR " .. tostring(err_)); finish(false, "Lua error: " .. tostring(err_)) end end)
