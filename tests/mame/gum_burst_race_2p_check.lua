-- Gum Games Burst Race 2P check (make test-gum-burst-race-2p): UniBIOS 4.0, one coin, Up to the PARTY event list, Right to pick Burst Race, Start;
-- then a second coin and P2 Start in the intro (the real join path, game_can_join_p2):
--   Q1. players 2 and race.players 2 after the join, still the intro of GAME_MODE_GUM with gg_race 1;
--   Q2. P2 is the rival, not the computer: with both humans idle for 90 pump frames both bubbles stay at size 0 (the computer bird would pump);
--   Q3. P2 mashing (A/B every 4 frames) against a slow P1 bursts first: winner 1, phase RESULT, status line lit on fix row 7.
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_BLOW_LAYOUT (gum_burst_race_2p_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_BLOW_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { state = L[1], mode = L[2], race = L[3], phase = L[4], size0 = L[5], size1 = L[6], winner = L[7], score = L[8], players = L[9], rplayers = L[10] }
local K = { playing = L[11], gum = L[12], intro = L[13], play = L[14], res = L[15], card = L[16] }
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, match)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname:find(match, 1, true) then return f end end
end
local coin, start1, start2, up = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start"), field(":edge:joy:START", "2 Players Start") or field(":edge:joy:START", "2 Player"), field(":edge:joy:JOY1", "P1 Up")
local a1, b1, pick = field(":edge:joy:JOY1", "P1 A"), field(":edge:joy:JOY1", "P1 B"), field(":edge:joy:JOY1", "P1 Down")
local a2, b2 = field(":edge:joy:JOY2", "P2 A"), field(":edge:joy:JOY2", "P2 B")
local ss = dofile("tests/mame/start_seq.lua")(coin, start1, up)
local function b(o) return mem:read_u8(flow_addr + o) end
local fix, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "blowvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then fix[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
  elseif r == 4 then vmod = data end
end)
local function cell(col, row) return (fix[0x7000 + col * 32 + row] or 0) & 0xfff end
local function lit(row)
  local blank, n = cell(0, 27), 0
  for c = 0, 39 do if cell(c, row) ~= blank then n = n + 1 end end
  return n
end
local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and start2 and up and a1 and b1 and pick and a2 and b2) then finish(false, "missing ports") end

local n, phase, t0, press1, press2, idle_max = 0, "boot", 0, 0, 0, 0
emu.register_frame_done(function()
  n = n + 1
  if n > 30000 then finish(false, "watchdog in phase " .. phase) return end
  local playing = b(O.state) == K.playing
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    local k = n - t0
    if ss.step(n, playing, 1) then phase = "join"; t0 = n; pick:set_value(0) end
    ss.menu(n - t0, 5, a1, pick)
  elseif phase == "join" then
    -- second credit, then P2 Start while the intro still runs (150 frames)
    local k = n - t0
    if b(O.mode) ~= K.gum or b(O.race) ~= 1 then finish(false, "not in Burst Race after Start") return end
    coin:set_value((k >= 2 and k < 10) and 1 or 0)
    start2:set_value((k >= 30 and k < 38) and 1 or 0)
    if k == 60 then
      if b(O.players) ~= 2 or b(O.rplayers) ~= 2 then finish(false, string.format("after P2 Start: Game.players %d race.players %d, want 2 and 2 (P2 cannot join Burst Race through the entry point)", b(O.players), b(O.rplayers))) return end
      if b(O.phase) ~= K.intro then finish(false, "phase " .. b(O.phase) .. " at join check, want intro") return end
    end
    if k > 60 then a1:set_value((b(K.card) == 1 and k % 8 < 4) and 1 or 0) end   -- rules card: one A press dismisses it (ignored for its first 30 frames)
    if b(O.phase) == K.play then
      if b(O.players) ~= 2 then finish(false, "players " .. b(O.players) .. " at pump start, want 2") return end
      phase = "idle"; t0 = n
    elseif k > 400 then finish(false, "intro never ended after the join") end
  elseif phase == "idle" then
    -- nobody presses: a computer rival would pump meanwhile
    local s0, s1 = b(O.size0), b(O.size1)
    if s0 > idle_max then idle_max = s0 end
    if s1 > idle_max then idle_max = s1 end
    if idle_max ~= 0 then finish(false, string.format("bubbles grew with both humans idle (size %d/%d): the rival is not P2", s0, s1)) return end
    if n - t0 >= 90 then phase = "mash"; t0 = n end
  elseif phase == "mash" then
    local k = n - t0
    if k % 4 == 0 then a2:set_value(press2 % 2 == 0 and 1 or 0); b2:set_value(press2 % 2 == 1 and 1 or 0); press2 = press2 + 1 else a2:set_value(0); b2:set_value(0) end
    if k % 16 == 0 then a1:set_value(press1 % 2 == 0 and 1 or 0); b1:set_value(press1 % 2 == 1 and 1 or 0); press1 = press1 + 1 else a1:set_value(0); b1:set_value(0) end
    if b(O.phase) == K.res then a1:set_value(0); b1:set_value(0); a2:set_value(0); b2:set_value(0); phase = "result"; t0 = n
    elseif k > 1200 then finish(false, "race never ended") end
  elseif phase == "result" then
    if n - t0 == 20 then
      if b(O.winner) ~= 1 then finish(false, "winner " .. b(O.winner) .. ", want 1 (P2)") return end
      if lit(7) < 8 then finish(false, "result row 7 lit " .. lit(7)) return end
      finish(true, "Burst Race 2P: coin + P2 Start in the intro joins (players 2); both bubbles stayed 0 while idle (rival is P2, not the computer); P2 burst first, result shown")
    end
  end
end)
