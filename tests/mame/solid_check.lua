-- Headless solid-platform reachability check (make test-solid). Platform bodies are solid: a flier rising into an island
-- underside, or flying into its side, bounces off instead of passing through.
--   1. coin, start, wait for PLAYING;
--   2. underside: put the hero under the middle island (platform 2) and hold flap; the hero box must never overlap the
--      solid box taken from the ROM table, vy must turn positive (down) after the contact, g_flier_solid_hits must rise;
--   3. side: put the hero left of the middle island (platform 2) inside its height band, hold Right and flap; same asserts.
-- Env: BRAWL_FLOW_ADDR, BRAWL_STAGE_ADDR (stage_platforms), BRAWL_HITS_ADDR (g_flier_solid_hits), BRAWL_FLIER_LAYOUT,
-- BRAWL_SOLID_LAYOUT (solid_probe.c output), BRAWL_RESULT.
local flow_addr  = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local stage_addr = tonumber(os.getenv("BRAWL_STAGE_ADDR"), 16)
local hits_addr  = tonumber(os.getenv("BRAWL_HITS_ADDR"), 16)
local result     = os.getenv("BRAWL_RESULT")
local lay, sl = {}, {}
for v in (os.getenv("BRAWL_FLIER_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
for v in (os.getenv("BRAWL_SOLID_LAYOUT") or ""):gmatch("%d+") do sl[#sl + 1] = tonumber(v) end
local O_STATE, O_X, O_Y, O_VX, O_VY, O_FSTATE = lay[1], lay[6], lay[7], lay[8], lay[9], lay[10]
local HALF_W, HALF_H, PLAT_H = sl[1], (sl[2] or 0) / 65536, sl[3]
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

local function s32(v) return v >= 0x80000000 and v - 0x100000000 or v end
local function s16(v) return v >= 0x8000 and v - 0x10000 or v end
local function gpx(o) return s32(mem:read_u32(flow_addr + o)) / 65536 end
local function put(o, px) mem:write_u32(flow_addr + o, math.floor(px * 65536 + 0.5) & 0xffffffff) end
local function plat(i)
  local a = stage_addr + i * 8
  return s16(mem:read_u16(a)), s16(mem:read_u16(a + 2)), s16(mem:read_u16(a + 4)), s16(mem:read_u16(a + 6))
end
local function hits() return mem:read_u16(hits_addr) end

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

local n, phase, tick = 0, "boot", 0
local phase_at = 0
local sx, sy, sw, sh            -- solid box of the scenario under test
local hits0, overlaps, max_pen, vy_flip, vx_flip, run_frames = 0, 0, 0, false, false, 0
local under_hits

local function begin(name, plat_i, x, y)
  sx, sy, sw, sh = plat(plat_i)
  put(O_X, x); put(O_Y, y); put(O_VX, 0); put(O_VY, 0)
  hits0, overlaps, max_pen, vy_flip, vx_flip, run_frames = hits(), 0, 0, false, false, 0
  phase, phase_at, tick = name, n, 0
end

emu.register_frame_done(function() local ok_, err_ = pcall(function()
  n = n + 1
  if n > 4000 then finish(false, "watchdog in phase " .. phase) return end
  if not (coin and start and abtn and rbtn and lay[10] and sl[4] == 8 and stage_addr and hits_addr) then finish(false, "missing input, layout or address") return end
  local state = mem:read_u8(flow_addr + O_STATE)
  if phase == "boot" then
    if n >= 300 then phase = "coin"; phase_at = n; ss.begin(n) end
    return
  elseif phase == "coin" then
    if not ss.step(n, state == 3) then return end
    phase = "start"; phase_at = n
    return
  elseif phase == "start" then
    begin("under", 2, 192, 144)    -- platform 2 is x 128..240, y 108..120; hero 24 px below its bottom
    if sh ~= PLAT_H then finish(false, "ROM platform h " .. sh .. " differs from STAGE_PLATFORM_H " .. PLAT_H) end
    return
  end
  if state ~= 3 or mem:read_u8(flow_addr + O_FSTATE) ~= 0 then
    finish(false, string.format("hero left ALIVE/PLAYING in phase %s (flow %d, flier %d)", phase, state, mem:read_u8(flow_addr + O_FSTATE)))
    return
  end
  local x, y, vy, vx = gpx(O_X), gpx(O_Y), gpx(O_VY), gpx(O_VX)
  run_frames = run_frames + 1
  -- box overlap depth (px) with the solid box: positive on both axes means inside
  local penx = math.min(x + HALF_W - sx, sx + sw - (x - HALF_W))
  local peny = math.min(y + HALF_H - sy, sy + sh - (y - HALF_H))
  if penx > 1 and peny > 1 then overlaps = overlaps + 1; if math.min(penx, peny) > max_pen then max_pen = math.min(penx, peny) end end
  if phase == "under" and vy > 0 and hits() > hits0 then vy_flip = true end
  if phase == "side" and vx < 0 and hits() > hits0 then vx_flip = true end
  if phase == "under" then
    abtn:set_value(tick % 2 == 0 and 1 or 0)
    tick = tick + 1
    if run_frames >= 120 then
      under_hits = hits() - hits0
      if not (overlaps == 0 and vy_flip and under_hits > 0) then
        finish(false, string.format("underside: overlaps %d (max %.2f px), vy flipped %s, hits %d", overlaps, max_pen, tostring(vy_flip), under_hits))
        return
      end
      abtn:set_value(0)
      begin("side", 2, 112, 114)   -- platform 2 is x 128..240, y 108..120; hero inside its height band
    end
  else
    rbtn:set_value(1)
    abtn:set_value((y > 113 and tick % 2 == 0) and 1 or 0)
    tick = tick + 1
    if run_frames >= 100 then
      rbtn:set_value(0); abtn:set_value(0)
      local h = hits() - hits0
      finish(overlaps == 0 and vx_flip and h > 0, string.format("underside hits %d, no overlap; side: overlaps %d (max %.2f px), vx flipped %s, hits %d, final x %.1f",
        under_hits, overlaps, max_pen, tostring(vx_flip), h, x))
    end
  end
end) if not ok_ then finish(false, "lua error: " .. tostring(err_)) end end)
