-- Gum Games Big Blow check (make test-gum-big-blow): UniBIOS 4.0, one coin, Up to the GUM GAMES row (the list wraps up from ARENA), Start:
--   G1. the game is PLAYING in GAME_MODE_GUM and the intro hands over to the blow phase;
--   G2. alternating A and B presses (A and B reach the mash counter in this mode) grow the bubble: size rises and the fix-layer power bar
--       (row 26, columns 12..27) shows a filled first cell and an empty last cell;
--   G3. the press loop holds the size near the top; when the clock ends the result shows: qualified, size >= 48, score 800 (stage 3 + mark),
--       status and tickets lines lit on fix rows 7 and 9, and one ticket spent (2 left) as the next attempt's intro begins.
-- Not covered here (host test_gumgames covers the logic): burst, attempts 2 and 3, the final game over and return to the title.
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_BLOW_LAYOUT (gum_big_blow_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_BLOW_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { state = L[1], mode = L[2], phase = L[3], size = L[4], last = L[5], tickets = L[6], qual = L[7], score = L[8] }
local K = { playing = L[9], gum = L[10], intro = L[11], play = L[12], res = L[13] }
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local st = dofile("tests/mame/stadium_snap.lua")(mem, flow_addr)
local ports = manager.machine.ioport.ports
local function field(tag, match)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname:find(match, 1, true) then return f end end
end
local coin, start1, up = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start"), field(":edge:joy:JOY1", "P1 Up")
local abtn, bbtn = field(":edge:joy:JOY1", "P1 A"), field(":edge:joy:JOY1", "P1 B")
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
  msg = msg .. st.peak_text(); if ok and st.peak_max() > 96 then ok = false end   -- stadium_snap.lua: sprites per line over every slot
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and up and abtn and bbtn) then finish(false, "missing ports") end

local n, phase, t0, grew, bar_ok, press = 0, "boot", 0, 0, false, 0
emu.register_frame_done(function()
  n = n + 1
  if n > 30000 then finish(false, "watchdog in phase " .. phase) return end
  local playing = b(O.state) == K.playing
  if playing then st.poke() end
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    if ss.step(n, playing, 1) then phase = "intro"; t0 = n end
  elseif phase == "intro" then
    if b(O.mode) ~= K.gum then finish(false, "mode " .. b(O.mode) .. ", want GAME_MODE_GUM " .. K.gum) return end
    if b(O.phase) == K.play then phase = "blow"; t0 = n
    elseif n - t0 > 400 then finish(false, "intro never reached the blow phase (phase " .. b(O.phase) .. ")") end
  elseif phase == "blow" then
    if n - t0 == 70 then st.shot() end
    local sz = b(O.size)
    if sz > grew then grew = sz end
    if sz >= 8 and cell(12, 26) ~= cell(27, 26) then bar_ok = true end
    -- press A and B in turn every 4 frames while the bubble is below 54, none above (the leak brings it down again)
    local k = (n - t0) % 4
    local want = sz < 54
    abtn:set_value((want and k == 0 and press % 2 == 0) and 1 or 0)
    bbtn:set_value((want and k == 0 and press % 2 == 1) and 1 or 0)
    if want and k == 0 then press = press + 1 end
    if b(O.phase) == K.res then
      abtn:set_value(0); bbtn:set_value(0)
      phase = "result"; t0 = n
    elseif n - t0 > 1200 then finish(false, "blow phase never ended") end
  elseif phase == "result" then
    local k = n - t0
    if k == 20 then
      local score = mem:read_u32(flow_addr + O.score)
      if grew < 20 or not bar_ok then finish(false, string.format("bubble did not grow (max size %d) or bar not drawn (bar_ok %s)", grew, tostring(bar_ok))) return end
      if b(O.qual) ~= 1 or b(O.last) < 48 then finish(false, string.format("result qualified %d size %d, want 1 and >= 48", b(O.qual), b(O.last))) return end
      if score ~= 800 then finish(false, "score " .. score .. ", want 800") return end
      if lit(7) < 8 or lit(9) < 8 then finish(false, string.format("result rows 7/9 lit %d/%d", lit(7), lit(9))) return end
      phase = "next"; t0 = n
    end
  elseif phase == "next" then
    if n - t0 > 400 then finish(false, "next attempt never began") return end
    if b(O.phase) == K.intro then
      if b(O.tickets) ~= 2 then finish(false, "tickets " .. b(O.tickets) .. " after the first attempt, want 2") return end
      finish(true, string.format("Big Blow: GUM GAMES row starts the event; bubble grew to %d, bar drawn; qualified at size %d, score 800, result rows lit, 2 tickets left", grew, b(O.last)))
    end
  end
end)
