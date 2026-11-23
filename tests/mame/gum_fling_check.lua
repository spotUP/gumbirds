-- Gum Games Gum Fling check (make test-gum-fling): UniBIOS 4.0, one coin, Down to the PARTY event list, A opens the list, Down five times picks Gum Fling (last entry), Start:
--   F1. the game is PLAYING in GAME_MODE_GUM with the fling running (gg_fling 1) and the HUD (fix row 7) lit;
--   F2. A and B mashed, the swinging angle stopped with A: the mode stays GAME_MODE_GUM for the whole event (the grass field replaces the TRIP flip);
--   F4. under the rules card only the world (slots 1..160) and the card's own example (arcade element slots 309..323) show:
--       no hero, pool, hazard, title or other-mode sprite (owner 2026-11-22: birds drawn on top of each other);
--   F5. the game logic keeps the video rate in every Fling phase: game frames per MAME frame >= 0.95 (g_frame_counter), and
--       g_vb_busy (vblanks that found the frame logic still running) tells a real overrun from a drain wait.
--   F3. three attempts end the event: GAME_OVER, distance > 0, score equals the best distance based points, record in slot 4 equals the best distance, or stays 0 when the computer P2 wins (no human record).
-- Env: BRAWL_FLOW_ADDR, BRAWL_FRAME_ADDR, BRAWL_VBBUSY_ADDR (hex), BRAWL_BLOW_LAYOUT (gum_fling_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_BLOW_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { state = L[1], mode = L[2], fling = L[3], phase = L[4], dist = L[5], score = L[6], record = L[7], foul = L[8], best = L[9] }
local K = { playing = L[10], gum = L[11], trip = L[12], over = L[13], gfend = L[14], windup = L[15], card = L[16], x = L[18], h = L[19], power = L[20], deg = L[21] }
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
local function fingerprint(c0, c1, r0, r1)   -- the fix tile codes of a rectangle as one string (meter tube / dial change detection)
  local t = {}
  for r = r0, r1 do for c = c0, c1 do t[#t + 1] = cell(c, r) end end
  return table.concat(t, ",")
end
local tube_seen, tube_n = {}, 0   -- distinct tube fingerprints: the fill tile changes with the power
local function tube_watch(row)
  local f = fingerprint(11, 28, row, row + 1)
  if not tube_seen[f] then tube_seen[f] = true; tube_n = tube_n + 1 end
end
local dial_seen, dial_n = {}, 0   -- distinct dial looks: the needle tile changes with the angle
local done = false
local frame_addr, busy_addr = tonumber(os.getenv("BRAWL_FRAME_ADDR") or "", 16), tonumber(os.getenv("BRAWL_VBBUSY_ADDR") or "", 16)
local rate, rate_fc, rate_busy = {}, nil, nil   -- per Fling phase: MAME frames, game frames, busy vblanks
local function rate_step(key)
  local fc, busy = mem:read_u32(frame_addr), mem:read_u16(busy_addr)
  if rate_fc then
    local r = rate[key] or { m = 0, g = 0, b = 0 }
    rate[key] = r
    r.m = r.m + 1; r.g = r.g + ((fc - rate_fc) & 0xffffffff); r.b = r.b + ((busy - rate_busy) & 0xffff)
  end
  rate_fc, rate_busy = fc, busy
end
local function rate_text()
  local t = {}
  for _, k in ipairs({ "card", "ph0", "ph1", "ph2", "ph3", "ph4", "ph5", "ph6" }) do
    local r = rate[k]
    if r then t[#t + 1] = string.format("%s %d/%d busy %d", k, r.g, r.m, r.b) end
  end
  local ma = tonumber(os.getenv("BRAWL_MOOD_ADDR") or "", 16)   -- g_bg_mood at finish: separates a storm world (rain fix traffic) from a calm one
  return " [game/MAME frames " .. table.concat(t, ", ") .. "]" .. (ma and (" [mood " .. mem:read_u8(ma) .. "]") or "")
end
local card_leak, card_leak_n = nil, 0   -- first sprite shown under the rules card outside the allowed set, and the frames with one
local function finish(ok, msg)
  if done then return end
  done = true
  msg = msg .. rate_text() .. st.peak_text() .. st.busy_text(); if ok and (st.peak_max() > 96 or st.busy_bad(6)) then ok = false end   -- stadium_snap.lua: sprites per line over every slot, crowd busy vblanks
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and up and abtn and bbtn and cbtn and pick) then finish(false, "missing ports") end
if not (frame_addr and busy_addr) then finish(false, "BRAWL_FRAME_ADDR / BRAWL_VBBUSY_ADDR missing") end

-- per attempt: mash A and B through the run-up, A once in the swinging aim, then the flight (frantic flap mash in attempt 2) and the landing
local mode_prev_flight, last_fx, aim_t0 = false, 0, nil
local cardn, maxlit, maxrow = 0, 0, -1
local ground_top, lift, air = nil, {}, {}   -- per attempt: peak hero lift px, flight frames
local n, phase, t0, hud, trips, attempts, lastphase = 0, "boot", 0, false, 0, 0, -1
emu.register_frame_done(function()
  n = n + 1
  if n > 30000 then finish(false, "watchdog in phase " .. phase) return end
  local playing = b(O.state) == K.playing
  if playing then st.poke() end
  if phase == "boot" then
    if n == (tonumber(os.getenv("FLING_COIN_AT") or "") or 600) then phase = "start"; t0 = n; ss.begin(n) end   -- FLING_COIN_AT: coin later (title / table / attract demo first)
  elseif phase == "start" then
    -- the shared sequence presses Down at +70..+78 (the PARTY event list); A at +80 opens the list, Downs at +84..+97 reach Gum Fling before Start at +100
    local k = n - t0
    if ss.step(n, playing, 1) then phase = "fling"; t0 = n; pick:set_value(0) end
    ss.menu(n - t0, 9, abtn, pick)
  elseif phase == "fling" then
    if b(O.state) ~= K.playing then phase = "check" return end
    if b(O.fling) ~= 1 then finish(false, "gg_fling not set") return end
    if os.getenv("FLING_SPR_LOG") and n % 4 == 0 then   -- every shown sprite column: slot, x, top, height
      local o = {}
      for s = 1, 380 do
        local w3 = fix[0x8200 + s] or 0
        if (w3 & 0x3f) > 0 and (w3 & 0x40) == 0 then o[#o + 1] = string.format("%d:%d,%d,%d", s, (fix[0x8400 + s] or 0) >> 7, (496 - (w3 >> 7)) & 0x1ff, w3 & 0x3f) end
      end
      local df = io.open(os.getenv("FLING_SPR_LOG"), "a"); df:write(string.format("n=%d card=%d att=%d ph=%d x=%d h=%d pw=%d deg=%d ", n, b(K.card), attempts, b(O.phase), mem:read_u32(flow_addr + K.x) >> 16, mem:read_u32(flow_addr + K.h) >> 16, b(K.power), b(K.deg)) .. table.concat(o, " ") .. "\n"); df:close()
    end
    rate_step(b(K.card) == 1 and "card" or ("ph" .. b(O.phase)))
    if b(K.card) == 1 then   -- rules card: A is ignored for its first 30 frames, then one press dismisses it
      cardn = cardn + 1
      if cardn > 2 then   -- the entry frame's ops land on the next vblank
        local bad
        for s = 1, 380 do
          local w3 = fix[0x8200 + s] or 0
          if (w3 & 0x3f) > 0 and (w3 & 0x40) == 0 and not (s <= 160 or (s >= 309 and s <= 323)) then bad = s; break end
        end
        if bad then
          card_leak_n = card_leak_n + 1
          card_leak = card_leak or string.format("slot %d at x=%d y=%d (card frame %d)", bad, (fix[0x8400 + bad] or 0) >> 7, (496 - ((fix[0x8200 + bad] or 0) >> 7)) & 0x1ff, cardn)
        end
      end
      abtn:set_value((cardn >= 40 and cardn < 44) and 1 or 0)
      return
    end
    local mode, ph = b(O.mode), b(O.phase)
    if mode == K.trip then trips = trips + 1 end
    if lit(7) >= 8 then hud = true end
    if ph == K.windup or ph == 1 then
      tube_watch(25)
      local d = fingerprint(7, 9, 24, 26)
      if not dial_seen[d] then dial_seen[d] = true; dial_n = dial_n + 1 end
    end
    for r = 0, 27 do if lit(r) > maxlit then maxlit = lit(r); maxrow = r end end
    if ph == K.windup and lastphase ~= K.windup then t0 = n + (attempts == 0 and 61 or 0); attempts = attempts + 1 end   -- GET SET freezes the first windup for 60 frames
    lastphase = ph
    if attempts == 1 and ph == K.windup and n == t0 + 40 then st.shot() end
    if os.getenv("FLING_SHOTS") and attempts == 1 and (n == t0 + 40 or (ph == 2 and (air[1] or 0) == 30)) then   -- debug shots into MAME's snap/ dir
      manager.machine.screens[":screen"]:snapshot("fling_" .. n .. ".png")
    end
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
    do   -- hero lift: slot 257 top on the ground (wind-up) against its highest flight top, per attempt
      local w3 = fix[0x8200 + 257] or 0
      local top = (496 - (w3 >> 7)) & 0x1ff
      if ph == K.windup then ground_top = top end
      if ph == 2 and ground_top and ground_top - top > (lift[attempts] or 0) then lift[attempts] = ground_top - top end
      if ph == 2 then air[attempts] = (air[attempts] or 0) + 1 end
    end
    local k = n - t0
    if mode == K.gum and ph == K.windup then
      -- mash A and B alternately (2 frames down, 2 up) for the whole run-up
      local j = k % 8
      abtn:set_value(j < 2 and 1 or 0); bbtn:set_value((j >= 4 and j < 6) and 1 or 0); cbtn:set_value(0)
      aim_t0 = nil
    elseif mode == K.gum and ph == 1 then
      -- the needle swings by itself after the 30-frame hold (A in the hold is ignored); A 20 frames after the hold stops it mid range and launches
      aim_t0 = aim_t0 or n
      bbtn:set_value(0); cbtn:set_value(0); abtn:set_value((b(K.deg) >= 30 and n - aim_t0 < 400 and n % 2 == 0) and 1 or 0)   -- A once the needle moves (frames are MAME frames, the game may run slower: never count them)
    elseif mode == K.gum and ph == 2 and attempts == 2 then
      -- frantic flap mash in the flight of attempt 2 (an A or B press every 4 frames)
      local j = n % 8
      abtn:set_value(j == 0 and 1 or 0); bbtn:set_value(j == 4 and 1 or 0); cbtn:set_value(0)
    elseif ph == K.gfend then
      abtn:set_value(n % 4 == 0 and 1 or 0); bbtn:set_value(0); cbtn:set_value(0)   -- the result screen waits for A
    else
      abtn:set_value(0); bbtn:set_value(0); cbtn:set_value(0)
    end
    if n > 20000 then finish(false, string.format("never ended: mode %d phase %d attempts %d trips %d", mode, ph, attempts, trips)) end
  elseif phase == "check" then
    local dist, score, rec, best = mem:read_u32(flow_addr + O.dist), mem:read_u32(flow_addr + O.score), mem:read_u32(flow_addr + O.record), mem:read_u32(flow_addr + O.best)
    if card_leak then finish(false, string.format("sprite under the rules card outside the world and card slots: %s, %d frames", card_leak, card_leak_n)) return end
    for _, k in ipairs({ "card", "ph0", "ph1", "ph2" }) do
      local r = rate[k]
      if r and r.m >= 30 and r.g * 100 < r.m * 95 then finish(false, string.format("Fling %s runs %d game frames in %d MAME frames (busy vblanks %d), want >= 0.95 per frame", k, r.g, r.m, r.b)) return end
    end
    if not hud then finish(false, "HUD row never lit, max lit " .. maxlit .. " row " .. maxrow .. string.format(" cardn %d attempts %d trips %d n %d", cardn, attempts, trips, n)) return end
    if trips > 0 then finish(false, "mode entered TRIP " .. trips .. " frames") return end
    if tube_n < 6 then finish(false, "power tube changed only " .. tube_n .. " times (fix rows 25-26), want >= 6") return end
    if dial_n < 3 then finish(false, "angle dial changed only " .. dial_n .. " times (fix columns 7..9 rows 24-26), want >= 3") return end
    if attempts < 3 then finish(false, string.format("only %d attempts seen", attempts)) return end
    if (lift[1] or 0) < 24 then finish(false, string.format("hero lift %d px in attempt 1, want >= 24 (an aimed throw)", lift[1] or 0)) return end
    if (air[2] or 0) * 100 < (air[1] or 0) * 110 then finish(false, string.format("flight %d frames with the flap mash (attempt 2), %d without, want +10 percent", air[2] or 0, air[1] or 0)) return end
    if best < 1 then finish(false, "best distance 0") return end
    if rec ~= best and rec ~= 0 then finish(false, string.format("record %d, best distance %d", rec, best)) return end
    if score < 1 then finish(false, "score 0") return end
    finish(true, string.format("Gum Fling: PARTY event list + A, Down starts it; %d attempts, never TRIP, best %d, score %d, record saved, lift %d px, flight %d frames / %d flapping", attempts, best, score, lift[1], air[1], air[2]))
  end
end)
