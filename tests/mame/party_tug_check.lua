-- PARTY Tug Gum check (target test-party-tug): UniBIOS 4.0, Arena 1P Start, the script sets the flow to Party mode with rule TUG and joins P2
-- (the join restarts the match into Tug Gum), then player 1 mashes A and player 2 never pulls:
--   G1. Tug Gum is running (mode GUM, gg_tug set) and the P2 Start press seated a second human (Tug.humans 2);
--   G2. the strand is drawn (first strand sprite has a height) and its knot (main.c g_tug_knot_x) follows Tug.knot;
--   G3. a snap happens and the left team wins two rounds (RESULT, wins 2 - 0);
--   G4. the winner line is on the fix layer: its first letter is the P tile that PULL showed in the play prompt;
--   G6. all four birds are drawn: the hero sprite, the P2 body (pool object P2_OBJ_BODY) and the two computer partners' pool
--       objects (main.c g_cpu_obj) each have a sprite height on most play frames (owner bug 2026-11-21: one computer bird missing in 2P);
--   G5. sprites per line (tests/mame/sprite_line_count.lua) stay <= 96 and flush time g_last_us <= 1800 us.
-- BRAWL_SNAP=<dir> writes tug_play.png, tug_snap.png and tug_result.png.
-- Env: BRAWL_FLOW_ADDR, BRAWL_LASTUS_ADDR, BRAWL_TUGKNOT_ADDR, BRAWL_CPUOBJ_ADDR (hex), BRAWL_TUG_LAYOUT (party_tug_probe.c output), BRAWL_RESULT, BRAWL_SNAP.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local lastus_addr = tonumber(os.getenv("BRAWL_LASTUS_ADDR") or "", 16)
local knot_addr = tonumber(os.getenv("BRAWL_TUGKNOT_ADDR") or "", 16)
local cpuobj_addr = tonumber(os.getenv("BRAWL_CPUOBJ_ADDR") or "", 16)
local result = os.getenv("BRAWL_RESULT")
local mid = os.getenv("BRAWL_TUG_MID") == "1"   -- variant: Party + Tug is set on the title, Tug starts 1P, P2 Start joins INSIDE the match
local snap = (os.getenv("BRAWL_SNAP") or "") ~= ""
local line_count = dofile("tests/mame/sprite_line_count.lua")
local SB_LIMIT, FLUSH_LIMIT = 96, 1800
local HERO_SPRITE, POOL_BASE, P2_OBJ = 257, 161, 30   -- HERO_SPRITE, POOL_SPRITE_BASE (src/sprite_slots.h), P2_OBJ_BODY = POOL_MAX - 2
local STRAND_SLOT, TEXT_COL, TEXT_ROW = 142, 5, 9   -- TUG_STRAND_SPRITE, (40 - BLOW_TEXT_W) / 2, BLOW_TEXT_ROW + 4 (src/main.c)
local L = {}
for v in (os.getenv("BRAWL_TUG_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { flow = L[1], mode = L[2], on = L[3], phase = L[4], humans = L[5], wins = L[6], knot = L[7], fmode = L[13], frule = L[14], ccount = L[17], cst = { L[18], L[19], L[20] }, p2st = L[21] }
local K = { playing = L[8], gum = L[9], play = L[10], snap = L[11], result = L[12], party = L[15], tug = L[16] }
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local screen = manager.machine.screens[":screen"]
local ports = manager.machine.ioport.ports
local function field(tag, match)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname:find(match, 1, true) then return f end end
end
local coin, start1 = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start")
local start2 = field(":edge:joy:START", "2 Players Start") or field(":edge:joy:START", "2 Player")
local abtn = field(":edge:joy:JOY1", "P1 A")
local ss = dofile("tests/mame/start_seq.lua")(coin, start1, nil)
local fsamp = dofile("tests/mame/flush_sample.lua")(mem)
local function b(o) return mem:read_u8(flow_addr + o) end
local fix, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "tugvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then fix[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
  elseif r == 4 then vmod = data end
end)
local function cell(col, row) return (fix[0x7000 + col * 32 + row] or 0) & 0xfff end
local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n" .. fsamp.report("tug") .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and start2 and abtn) then finish(false, "missing ports") end
if not (lastus_addr and knot_addr and cpuobj_addr and K.tug and O.p2st) then finish(false, "missing g_last_us / g_tug_knot_x / g_cpu_obj / PARTY_TUG / probe layout") end

local n, phase, t0 = 0, "boot", 0
local peak, peak_line, us_play, knot_ok, seen_snap, play_p, res_n, snaps = 0, 0, 0, 0, false, 0, 0, {}
local drawn, play_n = { 0, 0, 0, 0 }, 0   -- frames with a sprite height: hero, P2 body, computer 0, computer 1
local function tall(s) return ((fix[0x8200 + s] or 0) & 0x3f) > 0 end
local where = ""
local function at(s) return string.format("s%d y%d x%d t%x", s, (fix[0x8200 + s] or 0) >> 7, (fix[0x8400 + s] or 0) >> 7, fix[s * 64] or 0) end
local function bodies()
  play_n = play_n + 1
  local o0, o1 = mem:read_u8(cpuobj_addr), mem:read_u8(cpuobj_addr + 1)
  where = at(HERO_SPRITE) .. " / " .. at(POOL_BASE + 3 * P2_OBJ) .. " / " .. at(POOL_BASE + 3 * o0) .. " / " .. at(POOL_BASE + 3 * o1)
  if tall(HERO_SPRITE) then drawn[1] = drawn[1] + 1 end
  if tall(POOL_BASE + 3 * P2_OBJ) then drawn[2] = drawn[2] + 1 end
  for i = 0, 1 do
    local o = mem:read_u8(cpuobj_addr + i)
    if o ~= 0xff and tall(POOL_BASE + 3 * o) then drawn[3 + i] = drawn[3 + i] + 1 end
  end
end
local function birds_msg()
  return string.format("birds drawn hero %d p2 %d cpu0 %d cpu1 %d of %d play frames; cpu_count %d, cpu states %d %d %d, p2 state %d, cpu objs %d %d %d; %s",
    drawn[1], drawn[2], drawn[3], drawn[4], play_n, b(O.ccount), b(O.cst[1]), b(O.cst[2]), b(O.cst[3]), b(O.p2st),
    mem:read_u8(cpuobj_addr), mem:read_u8(cpuobj_addr + 1), mem:read_u8(cpuobj_addr + 2), where)
end
local function press(f, k, from) f:set_value((k >= from and (k - from) < 15) and 1 or 0) end
local function shot(name) if snap and not snaps[name] then screen:snapshot(name .. ".png"); snaps[name] = true end end
emu.register_frame_done(function()
  if done then return end
  n = n + 1
  if n > 30000 then finish(false, "watchdog in phase " .. phase .. " snap " .. tostring(seen_snap) .. " wins " .. b(O.wins) .. "-" .. b(O.wins + 1)) return end
  local k = n - t0
  if phase == "boot" then
    if mid and n == 590 then mem:write_u8(flow_addr + O.fmode, K.party); mem:write_u8(flow_addr + O.frule, K.tug) end
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    if ss.step(n, b(O.flow) == K.playing, nil) then phase = "join"; t0 = n end
  elseif phase == "join" then
    if k == 5 then coin:set_value(1) end
    if k == 20 then coin:set_value(0) end
    if k == 100 and not mid then mem:write_u8(flow_addr + O.fmode, K.party); mem:write_u8(flow_addr + O.frule, K.tug) end
    if k >= 110 then press(start2, k, 110) end
    if mid and k == 100 and (b(O.mode) ~= K.gum or b(O.on) ~= 1 or b(O.humans) ~= 1) then finish(false, "mid-join variant: Tug did not start 1P: mode " .. b(O.mode) .. " gg_tug " .. b(O.on) .. " humans " .. b(O.humans)) return end
    if k > 130 and b(O.flow) == K.playing and b(O.mode) == K.gum and b(O.on) == 1 then
      if b(O.humans) ~= 2 then finish(false, "P2 start did not add a second human: humans " .. b(O.humans)) return end
      phase = "watch"; t0 = n
    end
    if k > 3000 then finish(false, "Tug Gum never started: flow " .. b(O.flow) .. " mode " .. b(O.mode) .. " gg_tug " .. b(O.on)) return end
  elseif phase == "watch" then
    fsamp.frame()
    local cnt = line_count.count(fix, 1, 381)
    for y = 0, 223 do if cnt[y] > peak then peak, peak_line = cnt[y], y end end
    local us = mem:read_u16(lastus_addr)
    if us > us_play then us_play = us end
    abtn:set_value(k % 8 < 4 and 1 or 0)
    local ph, knot, kx = b(O.phase), mem:read_i16(flow_addr + O.knot), mem:read_i16(knot_addr)
    -- the view may lag the logic by a frame, so the drawn knot only has to be on the same side and within a pull of Tug.knot / 4
    if ph == K.play and knot < -8 and kx ~= 0 and kx < 160 and math.abs(kx - 160 - knot / 4) <= 6 and ((fix[0x8200 + STRAND_SLOT] or 0) & 0x3f) > 0 then
      knot_ok = knot_ok + 1
    end
    if ph == K.play then bodies() end
    if ph == K.play and cell(TEXT_COL + 10, TEXT_ROW) ~= 0 then play_p = cell(TEXT_COL + 10, TEXT_ROW) end
    if ph == K.play and knot < -60 then shot("tug_play") end
    if ph == K.snap then seen_snap = true; shot("tug_snap") end
    if ph == K.result then
      if b(O.wins) >= 2 or b(O.wins + 1) >= 2 then res_n = res_n + 1 end   -- the result of the last round only
      if res_n == 40 then
        res_n = 41
        shot("tug_result")
        local w0, w1 = b(O.wins), b(O.wins + 1)
        if not seen_snap then finish(false, "result without a snap") return end
        for j = 1, 4 do if drawn[j] * 2 < play_n then finish(false, birds_msg()) return end end
        if w0 ~= 2 or w1 ~= 0 then finish(false, "rounds " .. w0 .. " - " .. w1 .. ", want 2 - 0 for the mashing left team") return end
        if knot_ok < 20 then finish(false, "strand knot followed Tug.knot on " .. knot_ok .. " frames only") return end
        if play_p == 0 or cell(TEXT_COL, TEXT_ROW) ~= play_p then finish(false, "winner line not shown: tile " .. cell(TEXT_COL, TEXT_ROW) .. ", P is " .. play_p) return end
        if peak > SB_LIMIT then finish(false, string.format("%d sprites on line %d, limit %d", peak, peak_line, SB_LIMIT)) return end
        if us_play > FLUSH_LIMIT then finish(false, string.format("flush %d us, limit %d", us_play, FLUSH_LIMIT)) return end
        finish(true, string.format("Tug Gum: 2 humans, player 1 mashes, snap seen, rounds 2 - 0, winner line shown, knot drawn on %d frames; %s; worst %d sprites on line %d (limit %d); flush max %d us (limit %d); %d frames",
          knot_ok, birds_msg(), peak, peak_line, SB_LIMIT, us_play, FLUSH_LIMIT, n - t0))
      end
    end
  end
end)
