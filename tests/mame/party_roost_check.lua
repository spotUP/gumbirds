-- PARTY Roost Rule check (make test-party-roost): UniBIOS 4.0, Arena 1P Start, the script sets the flow to Party mode with rule ROOST (the title menu choice) and joins P2
-- (the join restarts the match, so match_start picks the roost), then:
--   R1. the round runs: Roost.idx is a real island and Roost.timer counts down from ROOST_ROUND_FRAMES;
--   R2. a sole human standing on the roost scores: with the computer fliers parked, hero[0] is dropped on the island centre and
--       Roost.ticks[0] and Game.score rise (SCORE_ROOST_TICK each) within 240 frames.
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_PLAT_ADDR (hex, stage_platforms), BRAWL_ROOST_LAYOUT (party_roost_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local plat_addr = tonumber(os.getenv("BRAWL_PLAT_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_ROOST_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { flow = L[1], players = L[2], mode = L[3], rule = L[4], score = L[5], cpus = L[6], idx = L[7], timer = L[8], ticks = L[9],
            hx = L[10], hy = L[11], hvx = L[12], hvy = L[13], szp = L[14], fmode = L[20], frule = L[21], cy = L[23], fsz = L[24] }
local K = { playing = L[15], arena = L[16], roost = L[17], frames = L[18], plats = L[19] , party = L[22] }
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
local function w32(o) return mem:read_u32(flow_addr + o) end
local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and start2) then finish(false, "missing ports") end

local n, phase, t0, timer0, score0, ticks0 = 0, "boot", 0, 0, 0, 0
local px, py, pw = 0, 0, 0
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
    if k == 100 then mem:write_u8(flow_addr + O.fmode, K.party); mem:write_u8(flow_addr + O.frule, K.roost) end
    if k >= 110 then press(start2, k, 110) end
    if k == 400 then
      if b(O.players) ~= 2 or b(O.rule) ~= K.roost then finish(false, "players " .. b(O.players) .. " rule " .. b(O.rule) .. " after join, want 2 and " .. K.roost) return end
      local t = w16(O.timer)
      if b(O.idx) >= K.plats or t == 0 or t >= K.frames then finish(false, "roost idx " .. b(O.idx) .. " timer " .. t .. ", want idx < " .. K.plats .. " and 0 < timer < " .. K.frames) return end
      timer0 = t
    end
    if k == 460 then
      if w16(O.timer) >= timer0 then finish(false, "roost timer not counting down: " .. timer0 .. " -> " .. w16(O.timer)) return end
      phase = "stand"; t0 = n
    end
  elseif phase == "stand" then
    -- computer fliers parked, hero[0] over the island centre, at rest: it falls onto the island and stands there
    if k == 1 then
      local p = plat_addr + b(O.idx) * O.szp
      px, py, pw = mem:read_i16(p), mem:read_i16(p + 2), mem:read_i16(p + 4)
      mem:write_u32(flow_addr + O.hx, (px + pw // 2) * 65536); mem:write_u32(flow_addr + O.hy, (py - 40) * 65536)
      mem:write_u32(flow_addr + O.hvx, 0); mem:write_u32(flow_addr + O.hvy, 0)
      score0, ticks0 = w32(O.score), b(O.ticks)
    end
    mem:write_u32(flow_addr + O.hy + O.fsz, 0xFF380000) -- player 2 parked too: shared standing pays nobody
    for c = 0, b(O.cpus) - 1 do mem:write_u32(flow_addr + O.cy + c * O.fsz, 0xFF380000) end -- computer fliers parked above the screen (y = -200 px) every frame; cpu_count 0 would restart the match
    if w32(O.score) > score0 and b(O.ticks) > ticks0 then
      finish(true, "sole stander paid: ticks " .. ticks0 .. " -> " .. b(O.ticks) .. ", score " .. score0 .. " -> " .. w32(O.score) .. ", roost " .. b(O.idx))
    elseif k > 240 then
      finish(false, "no tick in 240 frames: ticks " .. b(O.ticks) .. " score " .. w32(O.score) .. " hero x " .. (w32(O.hx) // 65536) .. " y " .. (w32(O.hy) // 65536) .. " island x " .. px .. " y " .. py .. " w " .. pw .. " idx " .. b(O.idx) .. " timer " .. w16(O.timer))
    end
  end
end)
