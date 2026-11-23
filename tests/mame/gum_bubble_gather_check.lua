-- Gum Games Bubble Gather check (make test-gum-bubble-gather): UniBIOS 4.0, one coin, Down to the PARTY event list, Right twice picks Bubble Gather, Start:
--   B1. the game is PLAYING in GAME_MODE_GUM with the gather running (gg_gather 1);
--   B2. the hero is moved onto live bubbles each frame: the HUD line (fix row 7) is lit and at least one bubble is caught;
--   B3. the run ends: the result shows, A leaves it, the flow reaches GAME_OVER, score >= caught * 300 and the record equals the caught count.
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_BLOW_LAYOUT (gum_bubble_gather_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_BLOW_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { state = L[1], mode = L[2], gather = L[3], caught = L[4], score = L[5], record = L[6], res = L[7], hx = L[8], hy = L[9],
            live = L[10], bx = L[11], by = L[12], stride = L[13], spawned = L[14] }
local K = { playing = L[15], gum = L[16], over = L[17] }
local mem = manager.machine.devices[":maincpu"].spaces["program"]
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
if not (coin and start1 and up and abtn and pick) then finish(false, "missing ports") end

local n, phase, t0, hud, maxcaught = 0, "boot", 0, false, 0
emu.register_frame_done(function()
  n = n + 1
  if n > 30000 then finish(false, "watchdog in phase " .. phase) return end
  local playing = b(O.state) == K.playing
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    -- the shared sequence presses Down at +70..+78 (the PARTY event list); Right taps at +80..+83 and +88..+91 reach Bubble Gather (third event) before Start at +100
    local k = n - t0
    if ss.step(n, playing, 1) then phase = "gather"; t0 = n; pick:set_value(0) end
    ss.menu(n - t0, 6, abtn, pick)
  elseif phase == "gather" then
    if b(O.mode) ~= K.gum or b(O.gather) ~= 1 then finish(false, string.format("mode %d gather %d, want GAME_MODE_GUM %d and gather 1", b(O.mode), b(O.gather), K.gum)) return end
    if lit(7) >= 8 then hud = true end
    if b(O.res) == 1 then phase = "result"; t0 = n; abtn:set_value(0) return end
    local c = mem:read_u8(flow_addr + O.caught)
    if c > maxcaught then maxcaught = c end
    -- park the hero on the first live bubble (bubble box is x..x+16 wide, y16 is its top); the hero centre is what the catcher box is built around
    for i = 0, 3 do
      local base = flow_addr + i * O.stride
      if mem:read_u8(base + O.live) == 1 then
        mem:write_u32(flow_addr + O.hx, ((mem:read_i16(base + O.bx) + 8) << 16) & 0xffffffff)
        mem:write_u32(flow_addr + O.hy, (mem:read_u32(base + O.by) + (8 << 16)) & 0xffffffff)
        break
      end
    end
    abtn:set_value(((n - t0) % 6) < 2 and 1 or 0)
    if n - t0 > 6000 then finish(false, string.format("run never reached the result (caught %d)", c)) end
  elseif phase == "result" then
    abtn:set_value(((n - t0) % 4) == 0 and 1 or 0)
    if b(O.state) == K.over then
      local caught, score, rec = mem:read_u8(flow_addr + O.caught), mem:read_u32(flow_addr + O.score), mem:read_u32(flow_addr + O.record)
      if not hud then finish(false, "HUD row never lit") return end
      if maxcaught < 1 then finish(false, "no bubble caught") return end
      local want = maxcaught * 300 + (maxcaught >= 12 and 500 or 0) -- 12 of 20 qualifies: +500 (GG_GATHER_QUALIFY, GG_QUALIFY_POINTS)
      if score < want then finish(false, string.format("score %d for %d caught, want >= %d", score, maxcaught, want)) return end
      if rec ~= maxcaught then finish(false, string.format("record %d, caught %d", rec, maxcaught)) return end
      finish(true, string.format("Bubble Gather: PARTY event list + Right x2 starts it; HUD lit, %d caught, score %d, record saved", maxcaught, score))
    elseif n - t0 > 1500 then finish(false, "result never led to game over") end
  end
end)
