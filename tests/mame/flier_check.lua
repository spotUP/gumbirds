-- Headless flier reachability check (make test-flier). Sentinel-driven timeline, no fixed frame numbers:
--   1. coin once the main loop runs (g_frame_counter advanced), hold start until the flow state is PLAYING;
--   2. settle: no input, the flier falls onto the middle island (on_ground);
--   3. flap: press A eight times (edge each time); flier y must rise above the standing y;
--   4. drown: walk right off the island, steer back over the gap between islands with left+flap until vx <= 0, then
--      no input: the flier falls to the water (y 180), state DROWNED, and the flow leaves PLAYING for GAME_OVER;
--   5. sentinel: Game.flier_steps (counts flier_step calls) must track the game loop frames spent in PLAYING.
-- The frame cap is only a hang watchdog. Env: ROOFLINE_FLOW_ADDR, ROOFLINE_FRAME_ADDR (hex), ROOFLINE_FLIER_LAYOUT
-- (flier_probe.c output), ROOFLINE_RESULT (file).
local flow_addr  = tonumber(os.getenv("ROOFLINE_FLOW_ADDR"), 16)
local frame_addr = tonumber(os.getenv("ROOFLINE_FRAME_ADDR") or "", 16)
local result     = os.getenv("ROOFLINE_RESULT")
local lay = {}
for v in (os.getenv("ROOFLINE_FLIER_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local O_STATE, O_FRAME, O_STEPS, O_OVER, O_SCORE, O_X, O_Y, O_VX, O_VY, O_FSTATE, O_BAL, O_GROUND =
  lay[1], lay[2], lay[3], lay[4], lay[5], lay[6], lay[7], lay[8], lay[9], lay[10], lay[11], lay[12]
local mem    = manager.machine.devices[":maincpu"].spaces["program"]
local ports  = manager.machine.ioport.ports

local FLOW_PLAYING, FLOW_GAME_OVER = 3, 4
local FL_DROWNED = 3
local WATER_Y = 180
local WATCHDOG = 6000

local function field(tag, pred)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if pred(fname) then return f end end
end
local coin  = field(":AUDIO_COIN", function(nm) return nm == "Coin 1" end)
local start = field(":edge:joy:START", function(nm) return nm == "1 Player Start" end)
local abtn  = field(":edge:joy:JOY1", function(nm) return nm == "P1 A" end)
local rbtn  = field(":edge:joy:JOY1", function(nm) return nm == "P1 Right" end)
local lbtn  = field(":edge:joy:JOY1", function(nm) return nm == "P1 Left" end)

local function s32(v) return v >= 0x80000000 and v - 0x100000000 or v end
local function g32(o) return mem:read_u32(flow_addr + o) end
local function gs32(o) return s32(g32(o)) end

local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("ROOFLINE_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

local n, phase, fc0, coin_at = 0, "boot", nil, nil
local play_fc0, steps0 = nil, nil
local stand_y, flaps, tick, min_y = nil, 0, 0, nil
local settle_at = nil

local function release() abtn:set_value(0); rbtn:set_value(0); lbtn:set_value(0) end

emu.register_frame_done(function()
  if done then return end
  n = n + 1
  if n > WATCHDOG then
    finish(false, string.format("watchdog: phase %s (steps %d, flier state %d, y %.1f)", phase,
      O_STEPS and g32(O_STEPS) or -1, O_FSTATE and mem:read_u8(flow_addr + O_FSTATE) or -1,
      O_Y and gs32(O_Y) / 65536 or -1))
    return
  end
  if not (coin and start and abtn and rbtn and lbtn) then finish(false, "missing input field") return end
  if not frame_addr or not O_GROUND then finish(false, "missing ROOFLINE_FRAME_ADDR or probe layout") return end
  local state = mem:read_u8(flow_addr + O_STATE)
  local fc = mem:read_u32(frame_addr)

  if phase == "boot" then
    if fc ~= 0 then fc0 = fc0 or fc end
    if fc0 and fc - fc0 >= 30 then phase = "coin"; coin_at = n; coin:set_value(1) end
    return
  elseif phase == "coin" then
    if n == coin_at + 15 then coin:set_value(0) end
    if n >= coin_at + 30 then phase = "start"; start:set_value(1) end
    return
  elseif phase == "start" then
    if state ~= FLOW_PLAYING then return end
    start:set_value(0)
    play_fc0, steps0 = fc, g32(O_STEPS)
    phase = "settle"; settle_at = n
    return
  end

  local on_ground = mem:read_u8(flow_addr + O_GROUND)
  local fy = gs32(O_Y) / 65536
  local fx = gs32(O_X) / 65536
  local vx = gs32(O_VX) / 65536

  if phase == "settle" then
    if state ~= FLOW_PLAYING then finish(false, "left PLAYING while settling") return end
    if on_ground == 1 then stand_y = fy; phase = "flap"; tick = 0 end
    if n > settle_at + 600 then finish(false, "flier never landed on the island") end
    return
  elseif phase == "flap" then
    -- press for 2 frames, release for 4: eight edges
    local k = tick % 6
    abtn:set_value(k < 2 and 1 or 0)
    if k == 0 then flaps = flaps + 1 end
    tick = tick + 1
    min_y = math.min(min_y or fy, fy)
    if flaps > 8 and k == 5 then
      release()
      if min_y >= stand_y - 4 then
        finish(false, string.format("flier did not rise after flaps: stand y %.1f, min y %.1f", stand_y, min_y))
        return
      end
      phase = "walk"
    end
    return
  elseif phase == "walk" then
    -- right off the middle island (right edge x 208); wait to land first, then walk
    if on_ground == 1 or fx < 212 then
      rbtn:set_value(1); abtn:set_value(0); lbtn:set_value(0)
      return
    end
    phase = "steer"; tick = 0
  end
  if phase == "steer" then
    -- back over the gap with left + flap until vx <= 0, then no input
    if vx <= 0 then release() else
      rbtn:set_value(0); lbtn:set_value(1)
      abtn:set_value((tick % 6) < 2 and 1 or 0)
      tick = tick + 1
    end
    if state ~= FLOW_PLAYING then phase = "ended" end
    return
  end
  if phase == "ended" then
    release()
    local fstate = mem:read_u8(flow_addr + O_FSTATE)
    local steps = g32(O_STEPS) - steps0
    local frames = fc - play_fc0
    local over = mem:read_u8(flow_addr + O_OVER)
    if state ~= FLOW_GAME_OVER then finish(false, "flow state after play is " .. state .. ", want GAME_OVER (4)") return end
    if fstate ~= FL_DROWNED then finish(false, "flier state " .. fstate .. ", want DROWNED (3)") return end
    if fy + 6 < WATER_Y then finish(false, string.format("flier y %.1f is not at the water", fy)) return end
    if over ~= 1 then finish(false, "game.over not set") return end
    if steps < 100 or math.abs(frames - steps) > 3 then
      finish(false, string.format("sentinel: flier_steps %d vs game loop frames %d in PLAYING", steps, frames)) return
    end
    finish(true, string.format("flier rose %.1f px after %d flaps, drowned at y %.1f, flow GAME_OVER, flier_steps %d of %d frames, score %d",
      stand_y - min_y, flaps - 1, fy, steps, frames, g32(O_SCORE)))
  end
end)
