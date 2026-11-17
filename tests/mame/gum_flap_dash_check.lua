-- Gum Games Flap Dash check (make test-gum-flap-dash): UniBIOS 4.0, one coin, Down to the GUM GAMES row, Left once (wraps from Big Blow) picks Flap Dash, Start:
--   D1. the game is PLAYING in GAME_MODE_GUM with the dash running (gg_dash 1);
--   D2. alternating A and B presses fly the bird: the HUD line (fix row 7) is lit and the first lap is counted;
--   D3. the third lap ends the run: done set, score 800 (stage 3 + qualifying mark) or 300, the result shows, the flow reaches GAME_OVER and the record equals the run time.
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_BLOW_LAYOUT (gum_flap_dash_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_BLOW_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { state = L[1], mode = L[2], dash = L[3], laps = L[4], done = L[5], frames = L[6], score = L[7], record = L[8] }
local K = { playing = L[9], gum = L[10], over = L[11] }
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, match)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname:find(match, 1, true) then return f end end
end
local coin, start1, up = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start"), field(":edge:joy:JOY1", "P1 Up")
local abtn, bbtn, right = field(":edge:joy:JOY1", "P1 A"), field(":edge:joy:JOY1", "P1 B"), field(":edge:joy:JOY1", "P1 Left")
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
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and up and abtn and bbtn and right) then finish(false, "missing ports") end

local n, phase, t0, hud, press, lap1 = 0, "boot", 0, false, 0, false
emu.register_frame_done(function()
  n = n + 1
  if n > 30000 then finish(false, "watchdog in phase " .. phase) return end
  local playing = b(O.state) == K.playing
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    -- the shared sequence presses Down at +70..+78 (the GUM GAMES row); one Left tap at +80..+83 wraps from Big Blow to Flap Dash before Start at +100
    local k = n - t0
    right:set_value((k >= 80 and k < 84) and 1 or 0)
    if ss.step(n, playing, 1) then phase = "dash"; t0 = n; right:set_value(0) end
  elseif phase == "dash" then
    if b(O.mode) ~= K.gum or b(O.dash) ~= 1 then finish(false, string.format("mode %d dash %d, want GAME_MODE_GUM %d and dash 1", b(O.mode), b(O.dash), K.gum)) return end
    local k = (n - t0) % 3
    abtn:set_value((k == 0 and press % 2 == 0) and 1 or 0)
    bbtn:set_value((k == 0 and press % 2 == 1) and 1 or 0)
    if k == 0 then press = press + 1 end
    if lit(7) >= 8 then hud = true end
    if b(O.laps) >= 1 then lap1 = true end
    if mem:read_u8(flow_addr + O.done) == 1 then
      abtn:set_value(0); bbtn:set_value(0)
      phase = "result"; t0 = n
    elseif n - t0 > 4000 then finish(false, string.format("run never finished (laps %d, frames %d)", b(O.laps), mem:read_u32(flow_addr + O.frames))) end
  elseif phase == "result" then
    if b(O.state) == K.over then
      local frames, score, rec = mem:read_u32(flow_addr + O.frames), mem:read_u32(flow_addr + O.score), mem:read_u32(flow_addr + O.record)
      if not (hud and lap1) then finish(false, string.format("hud lit %s, lap counted %s", tostring(hud), tostring(lap1))) return end
      if score ~= 300 and score ~= 800 then finish(false, "score " .. score .. ", want 300 or 800") return end
      if rec ~= frames or frames == 0 then finish(false, string.format("record %d, run time %d", rec, frames)) return end
      finish(true, string.format("Flap Dash: GUM GAMES row + Left starts the dash; HUD lit, lap counted, 3 laps in %d frames, score %d, record saved", frames, score))
    elseif n - t0 > 600 then finish(false, "result never led to game over") end
  end
end)
