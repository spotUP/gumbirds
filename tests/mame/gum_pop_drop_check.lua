-- Gum Games Pop Drop check (make test-gum-pop-drop): UniBIOS 4.0, one coin, Down to the GUM GAMES row, Right three times picks Pop Drop, Start:
--   P1. the game is PLAYING in GAME_MODE_GUM with Pop Drop running (gg_pop 1) and the HUD row (fix row 7) is lit;
--   P2. each drop the target balloon is parked under the hero while it hangs, then C cuts the chute: five centred pops, total near the maximum;
--   P3. the run ends: the result shows, A leaves it, the flow reaches GAME_OVER, the record equals the total.
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_BLOW_LAYOUT (gum_pop_drop_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_BLOW_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { state = L[1], mode = L[2], pop = L[3], phase = L[4], pops = L[5], total = L[6], drop = L[7], score = L[8], record = L[9],
            hx = L[10], tx = L[11], res = L[12] }
local K = { playing = L[13], gum = L[14], over = L[15], hang = L[16], fall = L[17] }
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, match)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname:find(match, 1, true) then return f end end
end
local coin, start1, up = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start"), field(":edge:joy:JOY1", "P1 Up")
local abtn, cbtn, pick = field(":edge:joy:JOY1", "P1 A"), field(":edge:joy:JOY1", "P1 C"), field(":edge:joy:JOY1", "P1 Down")
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
if not (coin and start1 and up and abtn and cbtn and pick) then finish(false, "missing ports") end

local n, phase, t0, hud = 0, "boot", 0, false
emu.register_frame_done(function()
  n = n + 1
  if n > 30000 then finish(false, "watchdog in phase " .. phase) return end
  local playing = b(O.state) == K.playing
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    -- the shared sequence presses Down at +70..+78 (the GUM GAMES row); Right taps at +80..+83, +88..+91 and +96..+99 reach Pop Drop (fourth event) before Start
    local k = n - t0
    pick:set_value(((k >= 86 and k < 90) or (k >= 92 and k < 96) or (k >= 98 and k < 102)) and 1 or 0); abtn:set_value((k >= 80 and k < 84) and 1 or 0) -- A opens the GUM GAMES list, Down picks
    if ss.step(n, playing, 1) then phase = "pop"; t0 = n; pick:set_value(0) end
  elseif phase == "pop" then
    if b(O.mode) ~= K.gum or b(O.pop) ~= 1 then finish(false, string.format("mode %d pop %d, want GAME_MODE_GUM %d and pop 1", b(O.mode), b(O.pop), K.gum)) return end
    if lit(7) >= 8 then hud = true end
    if b(O.res) == 1 or b(O.state) == K.over then phase = "result"; t0 = n; cbtn:set_value(0) return end
    local ph = b(O.phase)
    if ph == K.hang or ph == K.fall then mem:write_u32(flow_addr + O.tx, mem:read_u32(flow_addr + O.hx)) end   -- park the balloon under the hero
    if ph == K.hang then
      cbtn:set_value(((n - t0) % 90) >= 60 and 1 or 0)                          -- press C once in a while; the edge cuts the chute
    else
      cbtn:set_value(0)
    end
    if n - t0 > 6000 then finish(false, "run never reached the result") end
  elseif phase == "result" then
    abtn:set_value(((n - t0) % 4) == 0 and 1 or 0)
    if b(O.state) == K.over then
      local pops, total, score, rec = b(O.pops), mem:read_u16(flow_addr + O.total), mem:read_u32(flow_addr + O.score), mem:read_u32(flow_addr + O.record)
      if not hud then finish(false, "HUD row never lit") return end
      if pops ~= 5 then finish(false, string.format("pops %d, want 5", pops)) return end
      if total < 50 then finish(false, string.format("total %d for 5 centred pops, want >= 50", total)) return end
      if score == 0 then finish(false, "score 0 after qualifying") return end
      if rec ~= total then finish(false, string.format("record %d, total %d", rec, total)) return end
      finish(true, string.format("Pop Drop: GUM GAMES row + Right x3 starts it; HUD lit, %d pops, total %d, score %d, record saved", pops, total, score))
    elseif n - t0 > 1500 then finish(false, "result never led to game over") end
  end
end)
