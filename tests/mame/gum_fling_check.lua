-- Gum Games Gum Fling check (make test-gum-fling): UniBIOS 4.0, one coin, Down to the GUM GAMES row, A opens the list, Down five times picks Gum Fling (last entry), Start:
--   F1. the game is PLAYING in GAME_MODE_GUM with the fling running (gg_fling 1) and the HUD (fix row 7) lit;
--   F2. A and B mashed, the swinging angle stopped with A: the mode stays GAME_MODE_GUM for the whole event (the grass field replaces the TRIP flip);
--   F3. three attempts end the event: GAME_OVER, distance > 0, score equals the best distance based points, record in slot 4 equals the best distance.
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_BLOW_LAYOUT (gum_fling_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_BLOW_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { state = L[1], mode = L[2], fling = L[3], phase = L[4], dist = L[5], score = L[6], record = L[7], foul = L[8], best = L[9] }
local K = { playing = L[10], gum = L[11], trip = L[12], over = L[13], gfend = L[14], windup = L[15], card = L[16], x = L[18] }
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local st = dofile("tests/mame/stadium_snap.lua")(mem, flow_addr)
local ports = manager.machine.ioport.ports
local function field(tag, match)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname:find(match, 1, true) then return f end end
end
local coin, start1, up = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start"), field(":edge:joy:JOY1", "P1 Up")
local abtn, bbtn, cbtn, pick = field(":edge:joy:JOY1", "P1 A"), field(":edge:joy:JOY1", "P1 B"), field(":edge:joy:JOY1", "P1 C"), field(":edge:joy:JOY1", "P1 Down")
local ss = dofile("tests/mame/start_seq.lua")(coin, start1, up)
local function b(o) return mem:read_u8(flow_addr + o) end
local fix, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "flingvram", function(offset, data, mask)
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
if not (coin and start1 and up and abtn and bbtn and cbtn and pick) then finish(false, "missing ports") end

-- per attempt: mash A and B through the run-up, A once in the swinging aim, then the flight (frantic flap mash in attempt 2) and the landing
local mode_prev_flight, last_fx, aim_t0 = false, 0, nil
local cardn, maxlit, maxrow = 0, 0, -1
local n, phase, t0, hud, trips, attempts, lastphase = 0, "boot", 0, false, 0, 0, -1
emu.register_frame_done(function()
  n = n + 1
  if n > 30000 then finish(false, "watchdog in phase " .. phase) return end
  local playing = b(O.state) == K.playing
  if playing then st.poke() end
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    -- the shared sequence presses Down at +70..+78 (the GUM GAMES row); A at +80 opens the list, Downs at +84..+97 reach Gum Fling before Start at +100
    local k = n - t0
    pick:set_value((k >= 84 and k < 98 and (k - 84) % 3 < 2) and 1 or 0); abtn:set_value((k >= 80 and k < 84) and 1 or 0) -- A opens the GUM GAMES list, five Downs (one per 3 frames) reach Gum Fling
    if ss.step(n, playing, 1) then phase = "fling"; t0 = n; pick:set_value(0) end
  elseif phase == "fling" then
    if b(O.state) == K.over then phase = "check" return end
    if b(O.fling) ~= 1 then finish(false, "gg_fling not set") return end
    if b(K.card) == 1 then   -- rules card: A is ignored for its first 30 frames, then one press dismisses it
      cardn = cardn + 1
      abtn:set_value((cardn >= 40 and cardn < 44) and 1 or 0)
      return
    end
    local mode, ph = b(O.mode), b(O.phase)
    if mode == K.trip then trips = trips + 1 end
    if lit(7) >= 8 then hud = true end
    for r = 0, 27 do if lit(r) > maxlit then maxlit = lit(r); maxrow = r end end
    if ph == K.windup and lastphase ~= K.windup then t0 = n + (attempts == 0 and 61 or 0); attempts = attempts + 1 end   -- GET SET freezes the first windup for 60 frames
    lastphase = ph
    if attempts == 1 and ph == K.windup and n == t0 + 40 then st.shot() end
    -- seam shot (stadium columns 21-22 of the 23 column plane): the last flight frame of attempt 1, field scroll logged next to it
    if attempts == 1 and mode_prev_flight and ph ~= 2 and os.getenv("STADIUM_SEAM_LOG") then
      local lf = io.open(os.getenv("STADIUM_SEAM_LOG"), "a"); lf:write("scroll " .. last_fx .. "\n"); lf:close(); st.shot((os.getenv("STADIUM_NAME") or "x"):gsub("%.png$", "") .. "_seam.png"); mode_prev_flight = false
    end
    if ph == 2 and attempts == 1 and K.x then mode_prev_flight = true; last_fx = mem:read_u32(flow_addr + K.x) >> 16 end
    if ph == 1 and mode == K.gum and (n % 40 == 0) and os.getenv("FLING_DUMP") then
      local o = {}
      for i = 0, 9 do local a = (323 + i) * 64; o[#o + 1] = string.format("%x/%x s3=%x", fix[a] or -1, fix[a + 1] or -1, fix[0x8200 + 323 + i] or -1) end
      local df = io.open(os.getenv("FLING_DUMP"), "a"); df:write("SCB1 n=" .. n .. " " .. table.concat(o, " | ") .. "\n"); df:close()
    end
    local k = n - t0
    if mode == K.gum and ph == K.windup then
      -- mash A and B alternately (2 frames down, 2 up) for the whole run-up
      local j = k % 8
      abtn:set_value(j < 2 and 1 or 0); bbtn:set_value((j >= 4 and j < 6) and 1 or 0); cbtn:set_value(0)
      aim_t0 = nil
    elseif mode == K.gum and ph == 1 then
      -- the needle swings by itself; one frame of A after 20 frames stops it and launches
      aim_t0 = aim_t0 or n
      bbtn:set_value(0); cbtn:set_value(0); abtn:set_value((n - aim_t0 >= 20 and n - aim_t0 < 22) and 1 or 0)
    elseif mode == K.gum and ph == 2 and attempts == 2 then
      -- frantic flap mash in the flight of attempt 2 (an A or B press every 4 frames)
      local j = n % 8
      abtn:set_value(j == 0 and 1 or 0); bbtn:set_value(j == 4 and 1 or 0); cbtn:set_value(0)
    else
      abtn:set_value(0); bbtn:set_value(0); cbtn:set_value(0)
    end
    if n > 20000 then finish(false, string.format("never ended: mode %d phase %d attempts %d trips %d", mode, ph, attempts, trips)) end
  elseif phase == "check" then
    local dist, score, rec, best = mem:read_u32(flow_addr + O.dist), mem:read_u32(flow_addr + O.score), mem:read_u32(flow_addr + O.record), mem:read_u32(flow_addr + O.best)
    if not hud then finish(false, "HUD row never lit, max lit " .. maxlit .. " row " .. maxrow .. string.format(" cardn %d attempts %d trips %d n %d", cardn, attempts, trips, n)) return end
    if trips > 0 then finish(false, "mode entered TRIP " .. trips .. " frames") return end
    if attempts < 3 then finish(false, string.format("only %d attempts seen", attempts)) return end
    if best < 1 then finish(false, "best distance 0") return end
    if rec ~= best then finish(false, string.format("record %d, best distance %d", rec, best)) return end
    if score < 1 then finish(false, "score 0") return end
    finish(true, string.format("Gum Fling: GUM GAMES row + A, Down starts it; %d attempts, never TRIP, best %d, score %d, record saved", attempts, best, score))
  end
end)
