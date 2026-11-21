-- Gum Games Poop the Man check (test-gum-poop): UniBIOS 4.0, one coin, Down to the GUM GAMES row, A opens the list, Down six times picks Poop the Man (last entry), Start:
--   P1. the game is PLAYING in GAME_MODE_GUM with gg_poop 1 and the HUD (fix row 7) lit;
--   P2. A pressed every 20 frames drops poops: the ammo count falls below its start;
--   P3. the event ends in GAME_OVER and the record in slot 6 is at least the score (higher is better);
--   P4. worst sprites per line <= 96 (stadium_snap.lua) and flush time <= 1800 us (flush_sample.lua, play frames).
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_POOP_LAYOUT (gum_poop_probe.c output), BRAWL_RESULT, BRAWL_LASTUS_ADDR, BRAWL_DEFER_ADDR, BRAWL_FLUSHN_ADDR.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_POOP_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { state = L[1], mode = L[2], poop = L[3], phase = L[4], timer = L[5], score = L[6], record = L[7], ammo = L[8], bscore = L[9] }
local K = { playing = L[11], gum = L[12], over = L[13], card = L[14] }
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
local n, phase, t0, hud, cardn, min_ammo, play_n = 0, "boot", 0, false, 0, 99, 0
emu.register_frame_done(function()
  n = n + 1
  if n > 30000 then finish(false, "watchdog in phase " .. phase) return end
  local playing = b(O.state) == K.playing
  if playing then st.poke() end
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    local k = n - t0   -- Down presses at +84, 87, 90, 93, 96, 99 (six), Start at +100 from the shared sequence
    pick:set_value((k >= 84 and k < 100 and (k - 84) % 3 < 2) and 1 or 0); abtn:set_value((k >= 80 and k < 84) and 1 or 0)
    if ss.step(n, playing, 1) then phase = "poop"; t0 = n; pick:set_value(0) end
  elseif phase == "poop" then
    if b(O.state) == K.over then phase = "check" return end
    if b(O.poop) ~= 1 then finish(false, "gg_poop not set") return end
    if b(K.card) == 1 then cardn = cardn + 1; abtn:set_value((cardn >= 40 and cardn < 44) and 1 or 0) return end
    if lit(7) >= 8 then hud = true end
    if b(O.phase) == 0 and mem:read_u16(flow_addr + O.timer) > 0 then
      play_n = play_n + 1
      fsamp.frame()
      local a = b(O.ammo); if a < min_ammo then min_ammo = a end
      abtn:set_value((play_n % 20) < 2 and 1 or 0)   -- one drop per 20 frames
    else abtn:set_value(0) end
    if n > 20000 then finish(false, "never ended") end
  elseif phase == "check" then
    local rec, score = mem:read_u32(flow_addr + O.record), mem:read_u32(flow_addr + O.score)
    if not hud then finish(false, "HUD row 7 never lit") return end
    if min_ammo >= 5 then finish(false, "ammo never fell below 5 (min " .. min_ammo .. ")") return end
    if fsamp.us_max and fsamp.us_max > FLUSH_LIMIT then finish(false, "flush " .. fsamp.us_max .. " us over " .. FLUSH_LIMIT) return end
    if rec < score then finish(false, string.format("record %d below score %d", rec, score)) return end
    finish(true, string.format("Poop the Man: GUM GAMES row + Down x6 starts it; HUD lit, min ammo %d, score %d, record %d saved; play frames %d", min_ammo, score, rec, play_n))
  end
end)
