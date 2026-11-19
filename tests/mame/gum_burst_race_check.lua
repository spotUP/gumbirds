-- Gum Games Burst Race check (make test-gum-burst-race): UniBIOS 4.0, one coin, Up to the GUM GAMES row, A opens the list, Down picks Burst Race, Start:
--   R1. the game is PLAYING in GAME_MODE_GUM with the race running (gg_race 1) and the intro hands over to the pump phase;
--   R2. alternating A and B presses grow the player's bubble; both fix-layer power bars (rows 26 and 24, columns 12..27) show a filled first cell
--       and an empty last cell;
--   R2b. the computer bird is a sprite beside the player's (VRAM shadow, as leak_check.lua): its SCB3 height is not 0, its first tile is set,
--       it sits right of the hero on the same line and its tiles change as its bubble grows (pump frames);
--   R3. the player bursts first against the computer bird: winner 0, score 900 (stage 4 + mark), status line lit on fix row 7.
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_BLOW_LAYOUT (gum_burst_race_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_BLOW_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { state = L[1], mode = L[2], race = L[3], phase = L[4], size = L[5], rival = L[6], winner = L[7], score = L[8] }
local K = { playing = L[9], gum = L[10], intro = L[11], play = L[12], res = L[13] }
local RIVAL, HERO, GUM0, GUM1, CARD = L[14], L[15], L[16], L[17], L[18]
local cardn = 0
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local st = dofile("tests/mame/stadium_snap.lua")(mem, flow_addr)
local ports = manager.machine.ioport.ports
local function field(tag, match)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname:find(match, 1, true) then return f end end
end
local coin, start1, up = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start"), field(":edge:joy:JOY1", "P1 Up")
local abtn, bbtn, pick = field(":edge:joy:JOY1", "P1 A"), field(":edge:joy:JOY1", "P1 B"), field(":edge:joy:JOY1", "P1 Down")
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
if not (coin and start1 and up and abtn and bbtn and pick) then finish(false, "missing ports") end

local n, phase, t0, grew, bar_ok, press = 0, "boot", 0, 0, false, 0
local rival_ok, rival_tiles, rival_bad = 0, {}, nil
local bub0, bub1 = 0, 0   -- pump frames where the player's / the rival's gum bubble sprite has height and a tile
emu.register_frame_done(function()
  n = n + 1
  if n > 30000 then finish(false, "watchdog in phase " .. phase) return end
  local playing = b(O.state) == K.playing
  if playing then st.poke() end
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    -- the shared sequence presses Down at +70..+78 (the GUM GAMES row); A at +80 opens the list, Down at +88..+95 picks Burst Race before Start at +100
    local k = n - t0
    pick:set_value((k >= 88 and k < 96) and 1 or 0); abtn:set_value((k >= 80 and k < 84) and 1 or 0) -- A opens the GUM GAMES list, Down picks
    if ss.step(n, playing, 1) then phase = "intro"; t0 = n; pick:set_value(0) end
  elseif phase == "intro" then
    if b(CARD) == 1 then   -- rules card: A is ignored for its first 30 frames, then one press dismisses it
      cardn = cardn + 1; t0 = n
      abtn:set_value((cardn >= 40 and cardn < 44) and 1 or 0)
      return
    end
    if b(O.mode) ~= K.gum or b(O.race) ~= 1 then finish(false, string.format("mode %d race %d, want GAME_MODE_GUM %d and race 1", b(O.mode), b(O.race), K.gum)) return end
    if b(O.phase) == K.play then phase = "pump"; t0 = n
    elseif n - t0 > 400 then finish(false, "intro never reached the pump phase (phase " .. b(O.phase) .. ")") end
  elseif phase == "pump" then
    local sz = b(O.size)
    if sz > grew then grew = sz end
    if sz >= 8 and cell(12, 26) ~= cell(27, 26) and cell(12, 24) ~= cell(27, 24) then bar_ok = true end
    local r3, r4, h3, h4 = fix[0x8200 + RIVAL] or 0, fix[0x8400 + RIVAL] or 0, fix[0x8200 + HERO] or 0, fix[0x8400 + HERO] or 0
    local rx, hx, tile = r4 >> 7, h4 >> 7, fix[RIVAL * 64] or 0
    if rx >= 448 then rx = rx - 512 end   -- SCB4 x is 9 bits and wraps: left of the screen edge reads as 448..511
    if hx >= 448 then hx = hx - 512 end
    if n - t0 > 4 then
      if (fix[0x8200 + GUM0] or 0) & 63 ~= 0 and (fix[GUM0 * 64] or 0) ~= 0 then bub0 = bub0 + 1 end
      if (fix[0x8200 + GUM1] or 0) & 63 ~= 0 and (fix[GUM1 * 64] or 0) ~= 0 then bub1 = bub1 + 1 end
    end
    if n - t0 > 4 then   -- the queue has flushed the first frame of the pump phase
      if r3 & 63 == 0 or tile == 0 or rx <= hx or rx > 288 or hx < 0 then rival_bad = rival_bad or string.format("rival sprite %d scb3 %x x %d tile %x, hero x %d at pump frame %d", RIVAL, r3, rx, tile, hx, n - t0)
      else
        local key = {}   -- every tile of the 3 columns: a pump frame changes the body, not always the top-left tile
        for c = 0, 2 do for r = 0, 3 do key[#key + 1] = fix[(RIVAL + c) * 64 + r * 2] or 0 end end
        rival_ok = rival_ok + 1; rival_tiles[table.concat(key, ",")] = true
      end
    end
    if n - t0 == 60 and (os.getenv("BRAWL_SNAP") or "") ~= "" then manager.machine.screens[":screen"]:snapshot("burst_race.png") end   -- make test-gum-burst-race RACE_SNAP=<dir>
    if n - t0 == 70 then st.shot() end
    local k = (n - t0) % 4
    abtn:set_value((k == 0 and press % 2 == 0) and 1 or 0)
    bbtn:set_value((k == 0 and press % 2 == 1) and 1 or 0)
    if k == 0 then press = press + 1 end
    if b(O.phase) == K.res then
      abtn:set_value(0); bbtn:set_value(0)
      phase = "result"; t0 = n
    elseif n - t0 > 1200 then finish(false, "pump phase never ended") end
  elseif phase == "result" then
    if n - t0 == 20 then
      local score = mem:read_u32(flow_addr + O.score)
      if grew < 20 or not bar_ok then finish(false, string.format("bubble did not grow (max size %d) or bars not drawn (bar_ok %s)", grew, tostring(bar_ok))) return end
      local frames = 0
      for _ in pairs(rival_tiles) do frames = frames + 1 end
      if rival_bad or rival_ok < 30 or frames < 2 then finish(false, rival_bad or string.format("rival sprite seen %d frames with %d pump frames", rival_ok, frames)) return end
      if bub0 < 30 or bub1 < 30 then finish(false, string.format("gum bubble sprites on screen for %d (player) and %d (rival) pump frames, want 30 each", bub0, bub1)) return end
      if b(O.winner) ~= 0 then finish(false, "winner " .. b(O.winner) .. ", want 0 (the player)") return end
      if score ~= 900 then finish(false, "score " .. score .. ", want 900") return end
      if lit(7) < 8 then finish(false, "result row 7 lit " .. lit(7)) return end
      finish(true, string.format("Burst Race: GUM GAMES row + Right starts the race; bubble grew to %d, both bars drawn, rival bird sprite on screen, both gum bubbles drawn; player burst first, score 900, status line lit", grew))
    end
  end
end)
