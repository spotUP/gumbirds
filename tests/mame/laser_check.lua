-- Headless laser reachability check (make test-laser). Sentinel-driven timeline, no fixed frame numbers:
--   1. coin once the game's main loop is running (g_frame_counter advanced), then hold start until the
--      flow state is PLAYING;
--   2. in PLAYING: hold button A only while a drone or bot is ahead and in range and the laser is not
--      locked out; jump vents and close bots (B), duck cables (C), so the hero survives until a kill;
--   3. snapshots: heat_zero.png before any shot, beam.png one frame after a bolt is seen in flight with
--      heat above zero (the screen shows the previous game step: VRAM is written in the next vblank),
--      kill.png two frames after the first kill (hit flash); <result>.laser holds the RAM numbers.
-- The frame cap below is only a watchdog against a hang; it does not drive the timeline.
-- Env: ROOFLINE_FLOW_ADDR, ROOFLINE_FRAME_ADDR (hex), ROOFLINE_LASER_LAYOUT (laser_probe.c output),
--      ROOFLINE_RESULT (file).
local flow_addr  = tonumber(os.getenv("ROOFLINE_FLOW_ADDR"), 16)
local frame_addr = tonumber(os.getenv("ROOFLINE_FRAME_ADDR") or "", 16)
local result     = os.getenv("ROOFLINE_RESULT")
local lay = {}
for v in (os.getenv("ROOFLINE_LASER_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local O_STATE, O_FRAME, O_BONUS, O_HEAT, O_LOCK, O_CHAIN, O_KILLS, O_SHOTS, O_KX, O_KY, O_KF =
  lay[1], lay[2], lay[3], lay[4], lay[5], lay[6], lay[7], lay[8], lay[9], lay[10], lay[11]
local O_BOLTS, BOLT_SZ, N_BOLTS, B_X, B_Y, B_ACT = lay[12], lay[13], lay[14], lay[15], lay[16], lay[17]
local O_OBS, OBS_SZ, N_OBS, E_X, E_Y, E_W, E_H, E_TYPE, E_ACT =
  lay[18], lay[19], lay[20], lay[21], lay[22], lay[23], lay[24], lay[25], lay[26]
local O_LIVES, O_HERO_H, O_HERO_VY, O_INVULN = lay[27], lay[28], lay[29], lay[30]
local mem    = manager.machine.devices[":maincpu"].spaces["program"]
local ports  = manager.machine.ioport.ports
local screen = manager.machine.screens[":screen"]

-- Game constants (src/core/tuning.h, game.h).
local FLOW_PLAYING = 3
local OB_VENT, OB_CABLE, OB_DRONE, OB_BOT = 0, 1, 2, 3
local HERO_RIGHT = 48 + 26         -- HERO_X + HERO_W
local FIRE_MIN, FIRE_MAX = 80, 300 -- enemy left edge on screen and ahead of the hero
local JUMP_AHEAD = 40              -- jump when a floor obstacle's left edge is this close to the hero
local DUCK_AHEAD = 40
local WATCHDOG = 6000              -- MAME frames; hang guard only

local function field(tag, pred)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if pred(fname) then return f end end
end
local coin  = field(":AUDIO_COIN", function(nm) return nm == "Coin 1" end)
local start = field(":edge:joy:START", function(nm) return nm == "1 Player Start" end)
local abtn  = field(":edge:joy:JOY1", function(nm) return nm == "P1 A" end)
local bbtn  = field(":edge:joy:JOY1", function(nm) return nm == "P1 B" end)
local cbtn  = field(":edge:joy:JOY1", function(nm) return nm == "P1 C" end)

local function s16(v) return v >= 0x8000 and v - 0x10000 or v end
local function g32(o) return mem:read_u32(flow_addr + o) end
local function g16(o) return mem:read_u16(flow_addr + o) end

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

local function obstacles()
  local list = {}
  for i = 0, N_OBS - 1 do
    local a = flow_addr + O_OBS + i * OBS_SZ
    if mem:read_u8(a + E_ACT) ~= 0 then
      list[#list + 1] = { t = mem:read_u8(a + E_TYPE), x = s16(mem:read_u32(a + E_X) // 256 & 0xFFFF),
                          w = s16(mem:read_u16(a + E_W)) }
    end
  end
  return list
end

-- Input plan for this frame: fire, jump, duck.
local function plan(list, can_fire)
  local fire, jump, duck = false, false, false
  for _, o in ipairs(list) do
    local ahead = o.x - HERO_RIGHT                     -- gap to the hero's right edge
    local behind = o.x + o.w < 48                      -- already past the hero
    if not behind then
      if (o.t == OB_DRONE or o.t == OB_BOT) and o.x > FIRE_MIN and o.x < FIRE_MAX and can_fire then
        fire = true
      end
      if (o.t == OB_VENT or o.t == OB_BOT) and ahead < JUMP_AHEAD then jump = true end
      if o.t == OB_CABLE and ahead < DUCK_AHEAD then duck = true end
    end
  end
  return fire, jump, duck
end

local n = 0
local phase = "boot"          -- boot, coin, start, play
local fc0, coin_at = nil, nil
local zero_done, beam_seen, beam_snap_at, kill_snap_at = false, nil, nil, nil
local prev_kills, prev_bonus, prev_chain = 0, 0, 0
local lines = {}
local heat0, heat1 = nil, nil
local lives0, hits, prev_invuln = nil, 0, 0
local b_prev = 0

emu.register_frame_done(function()
  if done then return end
  n = n + 1
  if n > WATCHDOG then
    finish(false, string.format("watchdog: phase %s at frame %d (shots %d, kills %d)", phase, n,
      O_SHOTS and g32(O_SHOTS) or -1, O_KILLS and g32(O_KILLS) or -1))
    return
  end
  if not (coin and start and abtn and bbtn and cbtn) then finish(false, "missing input field") return end
  if not frame_addr or not O_INVULN then finish(false, "missing ROOFLINE_FRAME_ADDR or probe layout") return end
  local state = mem:read_u8(flow_addr + O_STATE)

  -- 1. Boot: wait until the game loop runs (frame counter moved 30 steps), then coin, then start.
  if phase == "boot" then
    local fc = mem:read_u32(frame_addr)
    if fc ~= 0 then fc0 = fc0 or fc end
    if fc0 and fc - fc0 >= 30 then phase = "coin"; coin_at = n; coin:set_value(1) end
    return
  elseif phase == "coin" then
    if n == coin_at + 15 then coin:set_value(0) end
    if n >= coin_at + 30 then phase = "start"; start:set_value(1) end
    return
  elseif phase == "start" then
    if state == FLOW_PLAYING then start:set_value(0); phase = "play" else return end
  end

  -- 2. Playing.
  if state ~= FLOW_PLAYING then
    finish(false, string.format("left PLAYING (state %d) before a kill: hits %d, lives %d -> %d", state, hits,
      lives0 or -1, mem:read_u8(flow_addr + O_LIVES)))
    return
  end
  local kills, bonus, chain = g32(O_KILLS), g32(O_BONUS), mem:read_u8(flow_addr + O_CHAIN)
  local invuln = g16(O_INVULN)
  lives0 = lives0 or mem:read_u8(flow_addr + O_LIVES)
  if invuln > prev_invuln then hits = hits + 1 end
  prev_invuln = invuln

  -- Baseline: no shot yet, heat zero; the screen has shown PLAYING for a few frames.
  if not zero_done then
    if g32(O_SHOTS) == 0 and g16(O_HEAT) == 0 and g32(O_FRAME) >= 6 then
      zero_done = true
      heat0 = g16(O_HEAT)
      screen:snapshot("heat_zero.png")
    end
  end

  -- Kill: counter rose; python checks the bonus rose by 200 x multiplier.
  if beam_seen and beam_snap_at == nil and kills > prev_kills and not kill_snap_at then
    lines[#lines + 1] = string.format("kill %d %d %d %d %d %d", s16(g16(O_KX)), s16(g16(O_KY)),
      bonus - prev_bonus, prev_kills, kills, prev_chain)
    kill_snap_at = n + 2
  end
  if kill_snap_at and n == kill_snap_at then
    screen:snapshot("kill.png")
    local f = io.open(result .. ".laser", "w")
    f:write(string.format("heat %d %d\n", heat0 or -1, heat1 or -1))
    f:write(table.concat(lines, "\n") .. "\n")
    f:close()
    finish(true, string.format("laser run done: shots %d kills %d hits %d lives %d -> %d", g32(O_SHOTS), kills,
      hits, lives0, mem:read_u8(flow_addr + O_LIVES)))
    return
  end

  -- Beam: a bolt in flight on screen with heat above zero. The screen shows it one frame later.
  if beam_snap_at and n == beam_snap_at then
    screen:snapshot("beam.png")
    beam_snap_at = nil
  end
  if zero_done and not beam_seen then
    for i = 0, N_BOLTS - 1 do
      local a = flow_addr + O_BOLTS + i * BOLT_SZ
      if mem:read_u8(a + B_ACT) ~= 0 then
        local bx, by = mem:read_u32(a + B_X) // 256, s16(mem:read_u16(a + B_Y))
        if bx > 40 and bx < 250 and g16(O_HEAT) > 0 then
          beam_seen = n
          beam_snap_at = n + 1
          heat1 = g16(O_HEAT)
          lines[#lines + 1] = string.format("beam %d %d", bx, by)
          break
        end
      end
    end
  end

  -- Inputs: fire at enemies in range, jump floor obstacles, duck cables. B is an edge: press for one
  -- frame, release the next.
  local fire, jump, duck = plan(obstacles(), zero_done and g16(O_LOCK) == 0)
  abtn:set_value(fire and 1 or 0)
  cbtn:set_value((duck and not jump) and 1 or 0)
  local on_floor = mem:read_u32(flow_addr + O_HERO_H) == 0 and mem:read_u32(flow_addr + O_HERO_VY) == 0
  if jump and on_floor and b_prev == 0 then b_prev = 1 else b_prev = 0 end
  bbtn:set_value(b_prev)
  prev_kills, prev_bonus, prev_chain = kills, bonus, chain
end)
