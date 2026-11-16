-- Co-op join check (make test-coop): the real BIOS start path under UniBIOS 4.0. Two coins, 1P arcade Start, then P2 Start in play:
--   C1. the BIOS takes the credit (BCD byte 0x10FE00: 1 -> 0), Game.players 1 -> 2, hero[1] drops in as PARACHUTE at the top, lives[1] PLAY;
--   C1b. after join the P2 body and parachute palettes sit in palette RAM and differ from the P1 ones;
--   C2. P2 flap releases the parachute (ALIVE) and hero[1] flies (y changes);
--   C3. a second P2 Start while P2 is active is refused: credit kept (insert a third coin first so the byte is non-zero);
--   C4. P1 Start in play is still refused: credit kept, players stays 2.
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_COOP_LAYOUT (coop_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_COOP_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { flow = L[1], players = L[2], hstate = L[3], hy = L[4], szf = L[5], szl = L[6], lstate = L[7], mode = L[9] }
local K = { playing = L[12], alive = L[13], chute = L[14], gone = L[15], life_play = L[16], arcade = L[17] }
local PAL = { soot = L[18], soot2 = L[19], chute = L[20], chute2 = L[21] }
local CREDIT = 0x10fe00
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, match)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname:find(match, 1, true) then return f end end
end
local coin, start1 = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start")
local start2 = field(":edge:joy:START", "2 Players Start") or field(":edge:joy:START", "2 Player")
local down, p2a = field(":edge:joy:JOY1", "P1 Down"), field(":edge:joy:JOY2", "P2 A")
local ss = dofile("tests/mame/start_seq.lua")(coin, start1, down)
local function b(o) return mem:read_u8(flow_addr + o) end
local function s32(o) local v = mem:read_u32(flow_addr + o); return v >= 0x80000000 and v - 0x100000000 or v end
-- Palette RAM (0x400000, 16 words a slot): the P2 slot must be loaded (not all black) and differ from the P1 slot.
local function pal_ok(a, b)
  local differ, lit = false, false
  for i = 0, 15 do
    local x, y = mem:read_u16(0x400000 + (a * 16 + i) * 2), mem:read_u16(0x400000 + (b * 16 + i) * 2)
    if x ~= y then differ = true end
    if i > 0 and y & 0x0fff ~= 0 then lit = true end
  end
  return differ and lit
end
local function credit() return mem:read_u8(CREDIT) end
local function hero1(o) return mem:read_u8(flow_addr + o + O.szf) end
local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and start2 and p2a) then finish(false, "missing ports: " .. tostring(start2) .. tostring(p2a)) end

local n, phase, t0, fc0 = 0, "boot", 0, nil
local c_before, y0, nflap = nil, nil, 0
local function press(f, k, from) f:set_value((k >= from and (k - from) < 15) and 1 or 0) end
emu.register_frame_done(function()
  n = n + 1
  local playing = b(O.flow) == K.playing and b(O.mode) == K.arcade
  if n > 30000 then finish(false, "watchdog in phase " .. phase) return end
  local k = n - t0
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    if ss.step(n, playing, 2) then phase = "settle"; t0 = n end
  elseif phase == "settle" then
    if k < 130 and b(O.players) ~= 1 then finish(false, "players " .. b(O.players) .. " before P2 Start") return end
    if k == 5 then coin:set_value(1) end
    if k == 20 then coin:set_value(0) end
    if k == 120 then c_before = credit() end
    if k >= 120 then press(start2, k, 130) end
    if k == 200 then
      local c = credit()
      if c_before ~= 1 then finish(false, "credit before P2 Start " .. tostring(c_before) .. ", want 1 (two coins, P1 took one)") return end
      if c ~= 0 then finish(false, "credit after P2 Start " .. c .. ", want 0") return end
      if b(O.players) ~= 2 then finish(false, "players " .. b(O.players) .. " after P2 Start, want 2") return end
      local st = hero1(O.hstate)
      if st ~= K.chute then finish(false, "hero[1] state " .. st .. ", want PARACHUTE " .. K.chute) return end
      if mem:read_u32(flow_addr + O.lstate + O.szl) ~= K.life_play then finish(false, "lives[1] not in PLAY") return end
      if not pal_ok(PAL.soot, PAL.soot2) then finish(false, "P2 body palette slot " .. PAL.soot2 .. " empty or equal to P1") return end
      if not pal_ok(PAL.chute, PAL.chute2) then finish(false, "P2 parachute palette slot " .. PAL.chute2 .. " empty or equal to P1") return end
      y0 = s32(O.hy + O.szf); phase = "flap"; t0 = n
    end
  elseif phase == "flap" then
    press(p2a, k, 5)
    if k == 40 then
      local st = hero1(O.hstate)
      if st ~= K.alive then finish(false, "hero[1] state " .. st .. " after P2 flap, want ALIVE " .. K.alive) return end
      phase = "refuse"; t0 = n
    end
  elseif phase == "refuse" then
    if k == 1 then coin:set_value(1) end
    if k == 20 then coin:set_value(0) end
    if k == 60 then c_before = credit() end
    if k >= 60 then press(start2, k, 70); if k >= 150 then press(start1, k, 160) end end
    if k == 250 then
      if credit() ~= c_before then finish(false, "credit " .. c_before .. " -> " .. credit() .. " on refused Starts, want kept") return end
      if c_before == 0 then finish(false, "third coin not credited, refusal untested") return end
      if b(O.players) ~= 2 then finish(false, "players changed to " .. b(O.players)) return end
      finish(true, string.format("join ok: credit 1 -> 0, PARACHUTE then ALIVE, refused Starts kept credit %d, y0 %d", c_before, y0))
    end
  end
end)
