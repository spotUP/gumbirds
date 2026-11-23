-- Gum Games P2 takeover check (make test-gum-join-p2): UniBIOS 4.0, one coin, the PARTY event list entry EV (2 Toss, 3 Tug, 4 Big Blow, 5 Burst Race,
-- 6 Bubble Gather, 7 Pop Drop, 8 Flap Dash, 9 Gum Fling, 10 Poop the Man), Start. Then a second coin and P2 Start in the GO! frames of the countdown
-- (game_can_join_p2 must still say yes there: the owner pressed P2 Start in GO! and nothing happened) or, for Toss and Tug that have no countdown,
-- 30 frames in. PASS when Game.players is 2 and the computer is off (cpu_level CPU_OFF) afterwards. A P1 A press dismisses the rules card.
-- Env: BRAWL_FLOW_ADDR (hex, g_flow), BRAWL_BLOW_LAYOUT (gum_join_p2_probe.c output), BRAWL_RESULT, EV.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local idx = tonumber(os.getenv("EV"))
local L = {}
for v in (os.getenv("BRAWL_BLOW_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { state = L[1], players = L[3], cpu = L[4], cd = L[5], card = L[6], frame = L[19] }
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, match)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname:find(match, 1, true) then return f end end
end
local coin, start1, up = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start"), field(":edge:joy:JOY1", "P1 Up")
local start2 = field(":edge:joy:START", "2 Players Start")
local abtn, pick = field(":edge:joy:JOY1", "P1 A"), field(":edge:joy:JOY1", "P1 Down")
local ss = dofile("tests/mame/start_seq.lua")(coin, start1, up)
local function b(o) return mem:read_u8(flow_addr + o) end
local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and start2 and up and abtn and pick and idx) then finish(false, "missing ports or EV") end
local n, phase, t0, pressed, f0, f1 = 0, "boot", 0, nil, 0, 0
emu.register_frame_done(function()
  n = n + 1
  if n > 4000 then finish(false, string.format("event %d: watchdog in phase %s, players %d", idx, phase, b(O.players))) return end
  local playing = b(O.state) == L[16]
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    if ss.step(n, playing, 1) then phase = "join"; t0 = n; pick:set_value(0) end
    ss.menu(n - t0, idx, abtn, pick)
  elseif phase == "join" then
    local k = n - t0
    local cd = mem:read_u16(flow_addr + O.cd)
    abtn:set_value((k >= 40 and k < 46) and 1 or 0)   -- dismiss the rules card (ignored in its first 30 frames)
    coin:set_value((k >= 2 and k < 10) and 1 or 0)
    if not pressed and ((idx <= 3 and k >= 30) or (idx > 3 and cd >= 62 and cd < 90 and b(O.card) == 0)) then pressed = k; f0 = mem:read_u32(flow_addr + O.frame) end
    start2:set_value((pressed and k >= pressed and k < pressed + 8) and 1 or 0)
    if pressed and k == pressed + 10 then f1 = mem:read_u32(flow_addr + O.frame) end   -- sampled early: 40 frames of a restarted event could pass the old count (Toss/Tug press at frame 30)
    if pressed and k == pressed + 40 then
      if b(O.players) ~= 2 or b(O.cpu) ~= L[18] then finish(false, string.format("event %d: P2 Start at frame %d (countdown %d): Game.players %d cpu_level %d, want 2 and %d", idx, pressed, cd, b(O.players), b(O.cpu), L[18])) return end
      -- GO! join (events 4..10 pressed at cd 62..90, Toss/Tug in round 1): the event restarted, so Game.frame (zeroed by game_reset) is below its value at the press
      if f1 >= f0 then finish(false, string.format("event %d: no restart after the join: Game.frame %d at the press, %d 10 frames later", idx, f0, f1)) return end
      finish(true, string.format("event %d: P2 took the computer seat (players 2, cpu off) with Start at frame %d", idx, pressed))
    end
  end
end)
