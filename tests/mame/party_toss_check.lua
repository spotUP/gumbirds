-- PARTY Toss Gum check (make test-party-toss): UniBIOS 4.0, Arena 1P Start, the script sets the flow to Party mode with rule TOSS and joins P2
-- (the join restarts the match into Toss Gum), then:
--   T1. Toss Gum is running (mode GUM, gg_toss set) with four birds alive;
--   T2. a toss happens (phase FLIGHT), a burst happens (phase BURST), and a winner is declared (RESULT, one bird left, winner seat alive).
-- Humans never press anything, so the computers toss and a stalled human carrier bursts. BRAWL_SNAP=<dir> writes toss_mid.png (flight) and toss_burst.png.
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_TOSS_LAYOUT (party_toss_probe.c output), BRAWL_RESULT, BRAWL_SNAP.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local snap = (os.getenv("BRAWL_SNAP") or "") ~= ""
local L = {}
for v in (os.getenv("BRAWL_TOSS_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { flow = L[1], mode = L[2], on = L[3], phase = L[4], alive = L[5], carrier = L[6], winner = L[7], round = L[8], humans = L[9], fmode = L[15], frule = L[16] }
local K = { playing = L[10], gum = L[11], flight = L[12], burst = L[13], result = L[14], party = L[17], toss = L[18] }
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local screen = manager.machine.screens[":screen"]
local ports = manager.machine.ioport.ports
local function field(tag, match)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname:find(match, 1, true) then return f end end
end
local coin, start1 = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start")
local start2 = field(":edge:joy:START", "2 Players Start") or field(":edge:joy:START", "2 Player")
local ss = dofile("tests/mame/start_seq.lua")(coin, start1, nil)
local function b(o) return mem:read_u8(flow_addr + o) end
local function pop(m) local c = 0 while m > 0 do c = c + (m & 1); m = m >> 1 end return c end
local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and start2) then finish(false, "missing ports") end

local n, phase, t0 = 0, "boot", 0
local seen_flight, seen_burst, snap_mid, snap_burst, min_alive = false, false, false, false, 4
local function press(f, k, from) f:set_value((k >= from and (k - from) < 15) and 1 or 0) end
emu.register_frame_done(function()
  n = n + 1
  if n > 30000 then finish(false, "watchdog in phase " .. phase .. " flight " .. tostring(seen_flight) .. " burst " .. tostring(seen_burst)) return end
  local k = n - t0
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    if ss.step(n, b(O.flow) == K.playing, nil) then phase = "join"; t0 = n end
  elseif phase == "join" then
    if k == 5 then coin:set_value(1) end
    if k == 20 then coin:set_value(0) end
    if k == 100 then mem:write_u8(flow_addr + O.fmode, K.party); mem:write_u8(flow_addr + O.frule, K.toss) end
    if k >= 110 then press(start2, k, 110) end
    if k > 130 and b(O.flow) == K.playing and b(O.mode) == K.gum and b(O.on) == 1 then
      if pop(b(O.alive)) ~= 4 then finish(false, "alive mask " .. b(O.alive) .. " at Toss Gum start, want four birds") return end
      phase = "watch"; t0 = n
    end
    if k > 3000 then finish(false, "Toss Gum never started: flow " .. b(O.flow) .. " mode " .. b(O.mode) .. " gg_toss " .. b(O.on)) return end
  elseif phase == "watch" then
    local ph, al = b(O.phase), pop(b(O.alive))
    if ph == K.flight then
      seen_flight = true
      if snap and not snap_mid and (n - t0) % 7 == 0 then screen:snapshot("toss_mid.png"); snap_mid = true end
    end
    if ph == K.burst then
      seen_burst = true
      if snap and not snap_burst then screen:snapshot("toss_burst.png"); snap_burst = true end
    end
    if al < min_alive then min_alive = al end
    if ph == K.result then
      if not seen_flight then finish(false, "winner without any toss in flight") return end
      if not seen_burst or al ~= 1 then finish(false, "result with " .. al .. " birds, burst seen " .. tostring(seen_burst)) return end
      if (b(O.alive) >> b(O.winner)) & 1 ~= 1 then finish(false, "winner seat " .. b(O.winner) .. " not alive, mask " .. b(O.alive)) return end
      finish(true, "four birds, toss, burst (min alive " .. min_alive .. "), winner seat " .. b(O.winner) .. " after " .. (n - t0) .. " frames")
    end
  end
end)
