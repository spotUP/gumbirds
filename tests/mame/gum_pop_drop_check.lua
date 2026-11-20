-- Gum Games Pop Drop check (make test-gum-pop-drop): UniBIOS 4.0, one coin, Down to the GUM GAMES row, Right three times picks Pop Drop, Start:
--   P1. the game is PLAYING in GAME_MODE_GUM with Pop Drop running (gg_pop 1) and the HUD row (fix row 7) is lit;
--   P2. the bird falls (depth grows); a platform is parked on the bird each frame, so three hits follow (one per stun) and the third is the crash;
--   P0. the GET SET / GO! countdown runs (cd_t counts up from 0) and its first glyph column (slot 309, ARC_ELEM_SPRITE) is on screen while it does;
--   P4. the summer sky is up: sky head (slot 1) 14 rows, cloud head (slot 21) 1 row and its SCB3 word changes as the platforms scroll, plane slot 72 hidden;
--   P3. the run ends: the result shows, A leaves it, the flow reaches GAME_OVER, the record equals the fall score.
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_BLOW_LAYOUT (gum_pop_drop_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_BLOW_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { state = L[1], mode = L[2], pop = L[3], phase = L[4], hits = L[5], pscore = L[6], depth = L[7], record = L[8],
            hx = L[9], plat = L[10], res = L[11], cdt = L[16], score = L[17] }
local K = { playing = L[12], gum = L[13], over = L[14], fall = L[15] }
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

local n, phase, t0, hud, cd_shown, maxhits = 0, "boot", 0, false, 0, 0
local sky_ok, cloud_vals, cloud_n = false, {}, 0
local CD_SLOT = 309 -- ARC_ELEM_SPRITE (src/sprite_slots.h)
emu.register_frame_done(function()
  n = n + 1
  if n > 17000 then finish(false, string.format("watchdog in phase %s: phase %d hits %d maxhits %d state %d", phase, b(O.phase), b(O.hits), maxhits, b(O.state))) return end
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
    if ((fix[0x8201] or 0) & 0x3f) == 14 and ((fix[0x8200 + 21] or 0) & 0x3f) == 1 and (fix[0x8200 + 72] or 1) == 0 then
      sky_ok = true
      local w = fix[0x8200 + 21]
      if not cloud_vals[w] then cloud_vals[w] = true; cloud_n = cloud_n + 1 end
    end
    local cd = mem:read_u16(flow_addr + O.cdt)   -- uint16_t; the word shows for cd_t 1..90 (gg_countdown.h): SCB3 height > 0, full size SCB2
    if cd >= 1 and cd <= 90 and ((fix[0x8200 + CD_SLOT] or 0) & 0x3f) > 0 and (fix[0x8000 + CD_SLOT] or 0) == 0x0fff then cd_shown = cd_shown + 1 end
    if b(O.res) == 1 or b(O.state) == K.over then phase = "result"; t0 = n; cbtn:set_value(0) return end
    if b(O.phase) == K.fall then   -- park a platform (rock, 3 tiles wide) on the bird each frame: one hit per stun, three hits crash
      local bx = mem:read_u32(flow_addr + O.hx) >> 16
      mem:write_u16(flow_addr + O.plat, (bx - 24) & 0xffff); mem:write_u16(flow_addr + O.plat + 2, 72)
      mem:write_u8(flow_addr + O.plat + 5, 1); mem:write_u8(flow_addr + O.plat + 6, 1); mem:write_u8(flow_addr + O.plat + 7, 0)
    end
    if b(O.hits) > maxhits then maxhits = b(O.hits) end
    if n - t0 > 6000 then finish(false, "run never reached the result") end
  elseif phase == "result" then
    abtn:set_value(((n - t0) % 4) == 0 and 1 or 0)
    if b(O.state) == K.over then
      local depth, pscore, rec = mem:read_u16(flow_addr + O.depth), mem:read_u16(flow_addr + O.pscore), mem:read_u32(flow_addr + O.record)
      if cd_shown < 60 then finish(false, string.format("countdown word on screen %d frames, want >= 60", cd_shown)) return end
      if not hud then finish(false, "HUD row never lit") return end
      if not sky_ok then finish(false, "Pop Drop sky never up (slot 1 14 rows, slot 21 1 row, slot 72 hidden)") return end
      if cloud_n < 20 then finish(false, string.format("cloud head SCB3 took %d values, want >= 20 (clouds must scroll)", cloud_n)) return end
      if maxhits ~= 3 then finish(false, string.format("hits %d, want 3 (the crash)", maxhits)) return end
      if depth == 0 or pscore < depth then finish(false, string.format("depth %d score %d", depth, pscore)) return end
      if rec ~= pscore then finish(false, string.format("record %d, fall score %d", rec, pscore)) return end
      finish(true, string.format("Pop Drop: GUM GAMES row + Right x3 starts it; countdown shown, HUD lit, 3 hits crash, depth %d, score %d, record saved", depth, pscore))
    elseif n - t0 > 1500 then finish(false, "result never led to game over") end
  end
end)
