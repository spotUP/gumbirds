-- PARTY Hot Gum check (make test-party-hot): UniBIOS 4.0, Arena 1P Start, the script sets the flow to Party mode with rule HOT and joins P2
-- (the join restarts the match, so match_start picks the first carrier), then:
--   H1. after the join the rule is Hot Gum with 2 players and a carrier index inside players + cpu_count;
--   H2. the fuse counts down while the round runs, and later it is reloaded (the gum moved on): proves hot_step runs in the real ROM.
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_HOT_LAYOUT (party_hot_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_HOT_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { flow = L[1], players = L[2], mode = L[3], rule = L[4], cpus = L[5], carrier = L[6], fuse = L[7], fmode = L[13], frule = L[14] }
local K = { playing = L[9], arena = L[10], hot = L[11], frames = L[12], party = L[15] }
local mem = manager.machine.devices[":maincpu"].spaces["program"]
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
local function w16(o) return mem:read_u16(flow_addr + o) end
local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and start2) then finish(false, "missing ports") end

local n, phase, t0, fuse0, t1 = 0, "boot", 0, 0, 0
local function press(f, k, from) f:set_value((k >= from and (k - from) < 15) and 1 or 0) end
emu.register_frame_done(function()
  n = n + 1
  local playing = b(O.flow) == K.playing and b(O.mode) == K.arena
  if n > 30000 then finish(false, "watchdog in phase " .. phase) return end
  local k = n - t0
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    if ss.step(n, playing, nil) then phase = "join"; t0 = n end
  elseif phase == "join" then
    if k == 5 then coin:set_value(1) end
    if k == 20 then coin:set_value(0) end
    if k == 100 then mem:write_u8(flow_addr + O.fmode, K.party); mem:write_u8(flow_addr + O.frule, K.hot) end
    if k >= 110 then press(start2, k, 110) end
    if k == 400 then
      if b(O.players) ~= 2 or b(O.rule) ~= K.hot then finish(false, "players " .. b(O.players) .. " rule " .. b(O.rule) .. " after join, want 2 and " .. K.hot) return end
    end
    -- the how-to demo and the round banner come first (fuse stays at its start value); the fuse then counts down
    if k > 400 and fuse0 == 0 and w16(O.fuse) > 0 and w16(O.fuse) < K.frames then
      if b(O.carrier) >= b(O.players) + b(O.cpus) then finish(false, "carrier " .. b(O.carrier) .. " outside " .. b(O.players) .. " + " .. b(O.cpus) .. " fliers") return end
      fuse0 = w16(O.fuse); t1 = k; phase = "burn"; t0 = n
    end
    if k > 3000 and fuse0 == 0 then finish(false, "hot fuse never counted down: " .. w16(O.fuse)) return end
  elseif phase == "burn" then
    -- the fuse reloads (the gum moved on) when it runs out; the carrier index stays valid all along
    if b(O.carrier) ~= 255 and b(O.carrier) >= b(O.players) + b(O.cpus) then finish(false, "carrier " .. b(O.carrier) .. " out of range") return end
    local fz = w16(O.fuse)
    if fz > fuse0 then
      finish(true, "fuse " .. fuse0 .. " counted down and reloaded to " .. fz .. " after " .. k .. " frames, carrier " .. b(O.carrier))
    elseif k > 2 * K.frames + 600 then
      finish(false, "fuse never reloaded: start " .. fuse0 .. " now " .. fz .. " carrier " .. b(O.carrier))
    end
  end
end)
