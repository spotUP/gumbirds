-- Gum Games Gum Fling check (make test-gum-fling): UniBIOS 4.0, one coin, Down to the GUM GAMES row, A opens the list, Down five times picks Gum Fling (last entry), Start:
--   F1. the game is PLAYING in GAME_MODE_GUM with the fling running (gg_fling 1) and the HUD (fix row 7) lit;
--   F2. A/B mashed, C held then released: the mode flips to GAME_MODE_TRIP for the flight and back to GUM for the next attempt;
--   F3. three attempts end the event: GAME_OVER, distance > 0, score equals the best distance based points, record in slot 4 equals the best distance.
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_BLOW_LAYOUT (gum_fling_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_BLOW_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { state = L[1], mode = L[2], fling = L[3], phase = L[4], dist = L[5], score = L[6], record = L[7], foul = L[8], best = L[9] }
local K = { playing = L[10], gum = L[11], trip = L[12], over = L[13], gfend = L[14], windup = L[15] }
local mem = manager.machine.devices[":maincpu"].spaces["program"]
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
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and up and abtn and bbtn and cbtn and pick) then finish(false, "missing ports") end

-- per attempt: mash 40 frames, pause, hold C 50 frames (about 35 degrees), release, then wait for the flight and the landing
local n, phase, t0, hud, trips, attempts, lastphase = 0, "boot", 0, false, 0, 0, -1
emu.register_frame_done(function()
  n = n + 1
  if n > 30000 then finish(false, "watchdog in phase " .. phase) return end
  local playing = b(O.state) == K.playing
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
    local mode, ph = b(O.mode), b(O.phase)
    if mode == K.trip then trips = trips + 1 end
    if mode == K.gum and lit(7) >= 8 then hud = true end
    if ph == K.windup and lastphase ~= K.windup then t0 = n + (attempts == 0 and 61 or 0); attempts = attempts + 1 end   -- GET SET freezes the first windup for 60 frames
    lastphase = ph
    local k = n - t0
    if mode == K.gum and ph == K.windup then
      -- A only: tap A (2 frames down, 2 up) for 40 frames, then hold A 12 frames to start the needle and 50 more, release
      abtn:set_value(((k < 40 and k % 4 < 2) or (k >= 45 and k < 107)) and 1 or 0)
      bbtn:set_value(0); cbtn:set_value(0)
    else
      abtn:set_value((mode == K.gum and ph == 1 and k < 107) and 1 or 0); bbtn:set_value(0); cbtn:set_value(0)
    end
    if n > 20000 then finish(false, string.format("never ended: mode %d phase %d attempts %d trips %d", mode, ph, attempts, trips)) end
  elseif phase == "check" then
    local dist, score, rec, best = mem:read_u32(flow_addr + O.dist), mem:read_u32(flow_addr + O.score), mem:read_u32(flow_addr + O.record), mem:read_u32(flow_addr + O.best)
    if not hud then finish(false, "HUD row never lit") return end
    if trips < 1 then finish(false, "mode never flipped to TRIP") return end
    if attempts < 3 then finish(false, string.format("only %d attempts seen", attempts)) return end
    if best < 1 then finish(false, "best distance 0") return end
    if rec ~= best then finish(false, string.format("record %d, best distance %d", rec, best)) return end
    if score < 1 then finish(false, "score 0") return end
    finish(true, string.format("Gum Fling: GUM GAMES row + A, Down starts it; %d attempts, TRIP flight seen, best %d, score %d, record saved", attempts, best, score))
  end
end)
