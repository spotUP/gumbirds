-- Gum Games Pop Drop check (make test-gum-pop-drop): UniBIOS 4.0, one coin, Down to the PARTY event list, Right three times picks Pop Drop, Start:
--   P1. the game is PLAYING in GAME_MODE_GUM with Pop Drop running (gg_pop 1) and the HUD row (fix row 7) is lit;
--   P2. the bird falls (depth grows); a platform is parked on the bird each frame, so three hits follow (one per stun) and the third is the crash;
--   P0. the GET SET / GO! countdown runs (cd_t counts up from 0) and its first glyph column (slot 309, ARC_ELEM_SPRITE) is on screen while it does;
--   P4. the summer sky is up: sky head (slot 1) 14 rows, cloud head (slot 21) 1 row and its SCB3 word changes as the platforms scroll, plane slot 72 hidden;
--   P5. sprites per line (shared counter, tests/mame/sprite_line_count.lua, every frame of the run with sky, clouds, platforms and birds) stay <= 96;
--       flush time g_last_us (play, and the 14 frames after Pop Drop ends = the 8 restore frames) is printed and stays <= 1800 us (GFX_FLUSH_BUDGET_US);
--   P6. after Pop Drop ends (attract), SCB3 words 1..110 equal the arena snapshot taken before the run: plane slots shown again, sky and cloud words gone.
--   P7. the burst gum skin (rag, slot 349 PD_RAG_SLOT in src/main.c) is on screen while the bird falls: SCB3 height 2 tiles (rag_seen);
--   P3. the run ends: the result shows, A leaves it, the flow reaches GAME_OVER, the record equals the fall score.
-- Env: BRAWL_LASTUS_ADDR (hex, g_last_us), BRAWL_FLOW_ADDR (hex), BRAWL_BLOW_LAYOUT (gum_pop_drop_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local lastus_addr = tonumber(os.getenv("BRAWL_LASTUS_ADDR"), 16)
local line_count = dofile("tests/mame/sprite_line_count.lua")
local SB_LIMIT, FLUSH_LIMIT, RESTORE_FRAMES = 96, 1800, 14
local L = {}
for v in (os.getenv("BRAWL_BLOW_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local POOL = os.getenv("BRAWL_POOL") == "1" -- make test-gum-pop-drop-pool: no platform is parked; the run is moved to the pool (P8)
-- start the fall near the pool: dist = (bird y 72 + PD_POOL_DEPTH * 8 - 200) * 16, in 1/16 px (probe slot 31)
local POOL_DIST = (72 + L[31] * 8 - 200) * 16
local O = { state = L[1], mode = L[2], pop = L[3], phase = L[4], hits = L[5], pscore = L[6], depth = L[7], record = L[8],
            hx = L[9], plat = L[10], res = L[11], cdt = L[16], score = L[17], dist = L[25], pool_y = L[26], landed = L[27], card0 = L[28] }
local K = { playing = L[12], gum = L[13], over = L[14], fall = L[15], pool = L[29], result = L[30] }
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
local fsamp = dofile("tests/mame/flush_sample.lua")(mem)
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
  print(fsamp.report("popdrop")) f = io.open(result, "a"); f:write(fsamp.report("popdrop") .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and up and abtn and cbtn and pick) then finish(false, "missing ports") end

local n, phase, t0, hud, cd_shown, maxhits = 0, "boot", 0, false, 0, 0
local pip_heart, pip_last, pip_t, pip_ok, pip_fall = 0, -1, 0, 0, 0
local cd_pop, cd_pop_n = {}, 0
local saved_msg
local sky_ok, cloud_vals, cloud_n = false, {}, 0
local peak, peak_line, us_play, us_restore, snap, left_n = 0, 0, 0, 0, nil, nil
local function scb3_diff()
  local bad, first = 0, nil
  for s = 1, 110 do if (fix[0x8200 + s] or 0) ~= snap[s] then bad = bad + 1; first = first or s end end
  return bad, first
end
local CD_SLOT = 309 -- ARC_ELEM_SPRITE (src/sprite_slots.h)
-- P7: count fall frames with the rag column up (owner report 2026-11-20: the broken gum never showed)
local RAG_SLOT, rag_n = 349, 0 -- PD_RAG_SLOT (src/main.c)
-- P8: the pool finish slots (src/main.c PD_BACK = POOL_SPRITE_BASE 161): water column 193 + 8 is 14 rows, flop 189, splash 214, card of fan 0 slot 173
local WATER_SLOT, FLOP_SLOT, SPLASH_SLOT, CARD_SLOT = 161 + 32 + 8, 161 + 28, 161 + 53, 161 + 10 + 2
local pool_n, flop_n, splash_n, card_n, pool_peak = 0, 0, 0, 0, 0
local function h(s) return (fix[0x8200 + s] or 0) & 0x3f end
local function pool_seen(cnt)
  if b(O.landed) == 1 then
    for y = 0, 223 do if cnt[y] > pool_peak then pool_peak = cnt[y] end end
    if h(FLOP_SLOT) == 2 then flop_n = flop_n + 1 end
    if h(SPLASH_SLOT) > 0 then splash_n = splash_n + 1 end
    if h(CARD_SLOT) == 2 then card_n = card_n + 1 end
  end
  if h(WATER_SLOT) == 14 then pool_n = pool_n + 1 end
end
local function rag_seen(falling)
  if falling and ((fix[0x8200 + RAG_SLOT] or 0) & 0x3f) == 2 then rag_n = rag_n + 1 end
end
emu.register_frame_done(function()
  n = n + 1
  if n > 17000 then finish(false, string.format("watchdog in phase %s: phase %d hits %d maxhits %d state %d", phase, b(O.phase), b(O.hits), maxhits, b(O.state))) return end
  local playing = b(O.state) == K.playing
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    -- the shared sequence presses Down at +70..+78 (the PARTY event list); Right taps at +80..+83, +88..+91 and +96..+99 reach Pop Drop (fourth event) before Start
    local k = n - t0
    if (n - t0) == 50 then snap = {}; for s = 1, 110 do snap[s] = fix[0x8200 + s] or 0 end end   -- arena planes before the run (menu behind the list)
    if ss.step(n, playing, 1) then phase = "pop"; t0 = n; pick:set_value(0) end
    ss.menu(n - t0, 7, abtn, pick)
  elseif phase == "pop" then
    fsamp.frame()
    if b(O.mode) ~= K.gum or b(O.pop) ~= 1 then finish(false, string.format("mode %d pop %d, want GAME_MODE_GUM %d and pop 1", b(O.mode), b(O.pop), K.gum)) return end
    if lit(7) >= 8 then hud = true end
    local cnt = line_count.count(fix, 1, 381)
    for y = 0, 223 do if cnt[y] > peak then peak, peak_line = cnt[y], y end end
    local us = mem:read_u16(lastus_addr)
    if us > us_play then us_play = us end
    if ((fix[0x8201] or 0) & 0x3f) == 14 and ((fix[0x8200 + 21] or 0) & 0x3f) == 1 and (fix[0x8200 + 72] or 1) == 0 then
      sky_ok = true
      local w = fix[0x8200 + 21]
      if not cloud_vals[w] then cloud_vals[w] = true; cloud_n = cloud_n + 1 end
    end
    local cd = mem:read_u16(flow_addr + O.cdt)   -- uint16_t; the word shows for cd_t 1..90 (gg_countdown.h): SCB3 height > 0, full size SCB2
    if cd >= 1 and cd <= 90 and ((fix[0x8200 + CD_SLOT] or 0) & 0x3f) > 0 and (fix[0x8000 + CD_SLOT] or 0) == 0x0fff then cd_shown = cd_shown + 1 end
    if cd >= 1 and cd <= 30 then   -- pop-in (draft anim_A2_go): the first glyph column's SCB2 shrink and SCB3 y change over the first frames
      local k = string.format("%x/%x", fix[0x8000 + CD_SLOT] or 0, fix[0x8200 + CD_SLOT] or 0)
      if not cd_pop[k] then cd_pop[k] = true; cd_pop_n = cd_pop_n + 1 end
    end
    if b(O.res) == 1 or b(O.state) == K.over then phase = "result"; t0 = n; cbtn:set_value(0) return end
    if POOL then pool_seen(cnt) end
    if POOL and b(O.phase) == K.fall then   -- no platform in the way; start the fall 150 px above the pool
      for k = 0, 3 do mem:write_u8(flow_addr + O.plat + k * 8 + 6, 0) end
      if mem:read_u32(flow_addr + O.dist) < POOL_DIST then mem:write_u32(flow_addr + O.dist, POOL_DIST) end
    elseif b(O.phase) == K.fall then   -- park a platform (rock, 3 tiles wide) on the bird each frame: one hit per stun, three hits crash
      local bx = mem:read_u32(flow_addr + O.hx) >> 16
      mem:write_u16(flow_addr + O.plat, (bx - 24) & 0xffff); mem:write_u16(flow_addr + O.plat + 2, 72)
      mem:write_u8(flow_addr + O.plat + 5, 1); mem:write_u8(flow_addr + O.plat + 6, 1); mem:write_u8(flow_addr + O.plat + 7, 0)
    end
    rag_seen(b(O.phase) == K.fall)
    -- Life pips (fix row 7, columns 1..3): pip k is a heart while k < 3 - hits, blank after; checked 24 frames after each hit, once the flash is over.
    if b(O.phase) == K.fall then
      local hh = b(O.hits)
      if hh ~= pip_last then pip_last, pip_t = hh, n end
      if hh > 0 and hh < 3 and n - pip_t == 24 then
        pip_heart = cell(1, 7)   -- pip 0 is alive until the third hit
        if pip_heart == cell(0, 27) then finish(false, string.format("life pip 0 blank after %d hits", hh)) return end
        for k = 0, 2 do
          local want = k < 3 - hh and pip_heart or cell(0, 27)
          if cell(1 + k, 7) ~= want then finish(false, string.format("life pip %d after %d hits is %x, want %x", k, hh, cell(1 + k, 7), want)) return end
        end
        pip_ok = pip_ok + 1
      end
    end
    if b(O.hits) > maxhits then maxhits = b(O.hits) end
    if n - t0 > 6000 then finish(false, "run never reached the result") end
  elseif phase == "result" then
    abtn:set_value(((n - t0) % 4) == 0 and 1 or 0)
    if b(O.state) == K.over then
      local depth, pscore, rec = mem:read_u16(flow_addr + O.depth), mem:read_u16(flow_addr + O.pscore), mem:read_u32(flow_addr + O.record)
      if peak > SB_LIMIT then finish(false, string.format("sprites per line %d on line %d, limit %d", peak, peak_line, SB_LIMIT)) return end
      if us_play > FLUSH_LIMIT then finish(false, string.format("flush %d us in play, limit %d", us_play, FLUSH_LIMIT)) return end
      if cd_shown < 60 then finish(false, string.format("countdown word on screen %d frames, want >= 60", cd_shown)) return end
      if cd_pop_n < 6 then finish(false, string.format("countdown pop-in: first column SCB2/SCB3 took %d values over cd_t 1..30, want >= 6", cd_pop_n)) return end
      if not hud then finish(false, "HUD row never lit") return end
      if not sky_ok then finish(false, "Pop Drop sky never up (slot 1 14 rows, slot 21 1 row, slot 72 hidden)") return end
      if cloud_n < 20 then finish(false, string.format("cloud head SCB3 took %d values, want >= 20 (clouds must scroll)", cloud_n)) return end
      if POOL then
        if pool_n < 60 then finish(false, string.format("water column (slot %d, 14 rows) up %d frames, want >= 60", WATER_SLOT, pool_n)) return end
        if flop_n < 30 then finish(false, string.format("flop bird (slot %d) up %d frames, want >= 30", FLOP_SLOT, flop_n)) return end
        if splash_n < 10 then finish(false, string.format("splash (slot %d) up %d frames, want >= 10", SPLASH_SLOT, splash_n)) return end
        if card_n < 30 then finish(false, string.format("score card (slot %d) up %d frames, want >= 30", CARD_SLOT, card_n)) return end
      elseif rag_n < 30 then finish(false, string.format("rag (slot %d) up %d fall frames, want >= 30", RAG_SLOT, rag_n)) return end
      if not POOL and pip_ok ~= 2 then finish(false, string.format("life pips checked after %d of 2 hits", pip_ok)) return end
      if not POOL and maxhits ~= 3 then finish(false, string.format("hits %d, want 3 (the crash)", maxhits)) return end
      if depth == 0 or pscore < depth then finish(false, string.format("depth %d score %d", depth, pscore)) return end
      if rec ~= pscore then finish(false, string.format("record %d, fall score %d", rec, pscore)) return end
      phase = "restore"; t0 = n; abtn:set_value(0)
      saved_msg = string.format("Pop Drop: PARTY event list + Right x3 starts it; countdown shown, HUD lit, 3 hits crash, depth %d, score %d, record saved; pool worst %d; worst %d sprites on line %d (limit %d), flush play %d us", depth, pscore, pool_peak, peak, peak_line, SB_LIMIT, us_play)
    elseif n - t0 > 1500 then finish(false, "result never led to game over") end
  elseif phase == "restore" then
    -- the sky stays through GAME_OVER; the restore starts when the flow leaves it. RESTORE_FRAMES frames from there cover the 8 restore frames plus the final SCB3 send.
    if not left_n and b(O.state) ~= K.over then left_n = n end
    if left_n then
      local us = mem:read_u16(lastus_addr)
      if us > us_restore then us_restore = us end
      local bad, first = scb3_diff()
      if bad == 0 then
        if us_restore > FLUSH_LIMIT then finish(false, string.format("flush %d us in the restore, limit %d", us_restore, FLUSH_LIMIT)) return end
        finish(true, saved_msg .. string.format(", flush restore %d us (limit %d), arena SCB3 slots 1..110 back after %d frames (state %d)", us_restore, FLUSH_LIMIT, n - left_n, b(O.state)))
      elseif n - left_n > 600 then finish(false, string.format("restore: %d of 110 SCB3 words still differ 600 frames after GAME_OVER (first slot %d: %04x, was %04x), flush %d us, state %d", bad, first, fix[0x8200 + first] or 0, snap[first], us_restore, b(O.state))) end
    elseif n - t0 > 2400 then finish(false, "flow never left GAME_OVER") end
  end
end)
