-- Gum Games Poop the Man check (test-gum-poop): UniBIOS 4.0, one coin, Down to PARTY, A opens the event list, ss.menu picks entry 10 (Poop the Man), Start:
--   P1. the game is PLAYING in GAME_MODE_GUM with gg_poop 1 and the HUD (fix row 7) lit;
--   P2. B pressed every 20 frames drops poops, A is tapped whenever the bird sinks below y 100 to stay up (flap): the bird rises (y falls) on at least 10 frames and splats start;
--   P3. the event ends on the RESULT-SCREEN (Game.res.active) within 30 frames of the play end, never on GAME OVER and never through the
--       title first (owner 2026-11-22: a stall, then the title, a fade and GAME OVER); A dismisses it; the record in slot 6 is at least the score, or stays 0 when the computer P2 wins (no human record);
--       the frame timeline (state / poop phase / res.active / BIOS user mode changes, frames from the play end) is in the result line;
--   P3b. at least one splat started (poop splat_n); bounce/berry sfx count is reported (a drop that misses every umbrella may leave it 0);
--   P4. worst sprites per line <= 96 (stadium_snap.lua) and flush time <= 1800 us (flush_sample.lua, play frames).
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_POOP_LAYOUT (gum_poop_probe.c output), BRAWL_RESULT, BRAWL_LASTUS_ADDR, BRAWL_DEFER_ADDR, BRAWL_FLUSHN_ADDR.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_POOP_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { state = L[1], mode = L[2], poop = L[3], phase = L[4], timer = L[5], score = L[6], record = L[7], y = L[8], bscore = L[9] }
local K = { playing = L[11], gum = L[12], over = L[13], card = L[14], splat = L[15], sfxn = L[16], res = L[17], title = L[18], entry = L[19] }
local RES_LIMIT = 30   -- frames from the play end to the first result screen frame
local FLUSH_LIMIT = 1800
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local st = dofile("tests/mame/stadium_snap.lua")(mem, flow_addr)
local fsamp = dofile("tests/mame/flush_sample.lua")(mem)
local ports = manager.machine.ioport.ports
local function field(tag, match)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname:find(match, 1, true) then return f end end
end
local coin, start1, up = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start"), field(":edge:joy:JOY1", "P1 Up")
local bbtn = field(":edge:joy:JOY1", "P1 B")
local abtn, pick = field(":edge:joy:JOY1", "P1 A"), field(":edge:joy:JOY1", "P1 Down")
local ss = dofile("tests/mame/start_seq.lua")(coin, start1, up)
local function b(o) return mem:read_u8(flow_addr + o) end
local fix, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "poopvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then fix[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
  elseif r == 4 then vmod = data end
end)
local function lit(row)
  local blank, n = (fix[0x7000 + 0 * 32 + 27] or 0) & 0xfff, 0
  for c = 0, 39 do if ((fix[0x7000 + c * 32 + row] or 0) & 0xfff) ~= blank then n = n + 1 end end
  return n
end
local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  msg = msg .. st.peak_text() .. " " .. fsamp.report("poop")
  if ok and st.peak_max() > 96 then ok = false end
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and up and abtn and pick) then finish(false, "missing ports") end
local splats, sfxs, flapping, rises, prev_y = 0, 0, false, 0, nil
local n, phase, t0, hud, cardn, play_n = 0, "boot", 0, false, 0, 0
local t_end, res_at, over_at, title_at, after, last_key, line = 0, nil, nil, nil, nil, nil, {}
emu.register_frame_done(function()
  n = n + 1
  if n > 30000 then finish(false, "watchdog in phase " .. phase) return end
  local playing = b(O.state) == K.playing
  if playing then st.poke() end
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    if ss.step(n, playing, 1) then phase = "poop"; t0 = n; pick:set_value(0) end
    ss.menu(n - t0, 10, abtn, pick)
  elseif phase == "poop" then
    if play_n > 0 and b(O.phase) ~= 0 then phase = "end"; t_end = n; abtn:set_value(0); bbtn:set_value(0) return end
    if b(O.poop) ~= 1 then finish(false, "gg_poop not set: state " .. b(O.state) .. " mode " .. b(O.mode) .. " k " .. (n - t0)) return end
    if b(K.card) == 1 then cardn = cardn + 1; abtn:set_value((cardn >= 40 and cardn < 44) and 1 or 0) return end
    if lit(7) >= 8 then hud = true end
    if b(O.phase) == 0 and mem:read_u16(flow_addr + O.timer) > 0 then
      play_n = play_n + 1
      fsamp.frame()
      splats, sfxs = b(K.splat), b(K.sfxn)
      local y = mem:read_u16(flow_addr + O.y); if y >= 0x8000 then y = y - 0x10000 end
      if prev_y and y < prev_y and prev_y - y < 8 and y > 24 then rises = rises + 1 end   -- gravity only pulls down: a rise is a flap
      prev_y = y
      flapping = not flapping
      abtn:set_value((y > 100 and flapping) and 1 or 0)   -- A press edges: flap whenever the bird has sunk below y 100
      bbtn:set_value((play_n % 20) < 2 and 1 or 0)         -- one drop (B) per 20 frames
    else abtn:set_value(0); bbtn:set_value(0) end
    if n > 20000 then finish(false, "never ended") end
  elseif phase == "end" then
    local k, s = n - t_end, b(O.state)
    local key = string.format("s%d/p%d/r%d/u%d", s, b(O.phase), b(K.res), mem:read_u8(0x10fdae))
    if key ~= last_key then line[#line + 1] = k .. ":" .. key; last_key = key end
    if not res_at then
      if b(K.res) == 1 and s == K.playing then res_at = k
      elseif s == K.over and not over_at then over_at = k
      elseif s == K.title and not title_at then title_at = k end
    end
    abtn:set_value((res_at and k - res_at >= 40 and k % 8 < 2) and 1 or 0)   -- press edges once the result screen has been up 40 frames
    if res_at and s ~= K.playing then after = s; phase = "check" return end
    if k > 1200 then phase = "check" return end
  elseif phase == "check" then
    abtn:set_value(0)
    local tl = " timeline " .. table.concat(line, " ")
    if not res_at then finish(false, "no result screen after the play end (GAME OVER at " .. tostring(over_at) .. ", title at " .. tostring(title_at) .. ")" .. tl) return end
    if over_at or title_at then finish(false, "GAME OVER at " .. tostring(over_at) .. " / title at " .. tostring(title_at) .. " before the result screen" .. tl) return end
    if res_at > RES_LIMIT then finish(false, "result screen " .. res_at .. " frames after the play end (limit " .. RES_LIMIT .. ")" .. tl) return end
    if after == K.over then finish(false, "GAME OVER after the result screen" .. tl) return end
    local rec, score = mem:read_u32(flow_addr + O.record), mem:read_u32(flow_addr + O.bscore)   -- record is the raw bird score, Game.score is event points
    if splats == 0 then finish(false, "no splat started (pavement or head)") return end
    if not hud then finish(false, "HUD row 7 never lit") return end
    if rises < 10 then finish(false, "bird rose only " .. rises .. " frames: A flap does not lift") return end
    if fsamp.us_max and fsamp.us_max > FLUSH_LIMIT then finish(false, "flush " .. fsamp.us_max .. " us over " .. FLUSH_LIMIT) return end
    if rec ~= 0 and rec < score then finish(false, string.format("record %d below score %d", rec, score)) return end
    finish(true, string.format("Poop the Man: PARTY event list starts it; result screen %d frames after the play end, then state %d; HUD lit, rising frames %d, score %d, record %d saved; splats %d, bounce sfx %d; play frames %d", res_at, after, rises, score, rec, splats, sfxs, play_n) .. tl)
  end
end)
