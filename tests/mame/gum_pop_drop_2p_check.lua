-- Gum Games Pop Drop 2P check (make test-gum-pop-drop-2p): UniBIOS 4.0, one coin, the GUM GAMES row, Right three times picks Pop Drop, Start;
-- then a second coin and P2 Start in the GET SET countdown (the real join path, game_can_join_p2):
--   Q1. Game.players 2 and pop.seq.players 2 after the join;
--   Q2. both birds fall at once: 60 fall frames with neither crashed, the P2 bird (slot 350, PD_BIRD2_SLOT in src/main.c) and its rag
--       (slot 356, PD_RAG2_SLOT) on screen, the birds at different x;
--   Q3. a platform parked on P1 only crashes it (3 hits); the fall goes on (phase PD_FALL) for 60 frames with P2 alive, the P1 ghost drawn
--       (slot 323 up) and its hit count frozen at 3 (a ghost touches nothing);
--   sprites per line (tests/mame/sprite_line_count.lua) stay <= 96 and flush time g_last_us <= 1800 us; the flush sampler counts are printed.
-- Env: BRAWL_LASTUS_ADDR (hex, g_last_us), BRAWL_FLOW_ADDR (hex), BRAWL_BLOW_LAYOUT (gum_pop_drop_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local lastus_addr = tonumber(os.getenv("BRAWL_LASTUS_ADDR"), 16)
local line_count = dofile("tests/mame/sprite_line_count.lua")
local SB_LIMIT, FLUSH_LIMIT = 96, 1800
local L = {}
for v in (os.getenv("BRAWL_BLOW_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { state = L[1], mode = L[2], pop = L[3], phase = L[4], hits = L[5], hx = L[9], plat = L[10],
            players = L[18], splayers = L[19], crash0 = L[20], crash1 = L[21], hits1 = L[22], hx1 = L[23] }
local K = { playing = L[12], gum = L[13], over = L[14], fall = L[15] }
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, match)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname:find(match, 1, true) then return f end end
end
local coin, start1, up = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start"), field(":edge:joy:JOY1", "P1 Up")
local start2 = field(":edge:joy:START", "2 Players Start") or field(":edge:joy:START", "2 Player")
local abtn, pick = field(":edge:joy:JOY1", "P1 A"), field(":edge:joy:JOY1", "P1 Down")
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
local function up_rows(slot) return (fix[0x8200 + slot] or 0) & 0x3f end
local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  print(fsamp.report("popdrop2p")) f = io.open(result, "a"); f:write(fsamp.report("popdrop2p") .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and start2 and up and abtn and pick) then finish(false, "missing ports") end

local P1_BIRD, P2_BIRD, P2_RAG = 323, 350, 356   -- PD_BIRD_SLOT, PD_BIRD2_SLOT, PD_RAG2_SLOT (src/main.c)
local n, phase, t0, both_n, p2_up, rag2_up, apart, ghost_n, ghost_up = 0, "boot", 0, 0, 0, 0, 0, 0, 0
local peak, peak_line, us_play = 0, 0, 0
local function measure()
  fsamp.frame()
  local cnt = line_count.count(fix, 1, 381)
  for y = 0, 223 do if cnt[y] > peak then peak, peak_line = cnt[y], y end end
  local us = mem:read_u16(lastus_addr)
  if us > us_play then us_play = us end
end
emu.register_frame_done(function()
  n = n + 1
  if n > 12000 then finish(false, string.format("watchdog in phase %s: phase %d crash %d/%d players %d", phase, b(O.phase), b(O.crash0), b(O.crash1), b(O.players))) return end
  local playing = b(O.state) == K.playing
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    local k = n - t0
    pick:set_value(((k >= 86 and k < 90) or (k >= 92 and k < 96) or (k >= 98 and k < 102)) and 1 or 0); abtn:set_value((k >= 80 and k < 84) and 1 or 0)
    if ss.step(n, playing, 1) then phase = "join"; t0 = n; pick:set_value(0) end
  elseif phase == "join" then
    local k = n - t0
    if b(O.mode) ~= K.gum or b(O.pop) ~= 1 then finish(false, "not in Pop Drop after Start") return end
    coin:set_value((k >= 2 and k < 10) and 1 or 0)
    start2:set_value((k >= 30 and k < 38) and 1 or 0)
    if k == 60 then
      if b(O.players) ~= 2 or b(O.splayers) ~= 2 then finish(false, string.format("after P2 Start: Game.players %d pop.seq.players %d, want 2 and 2", b(O.players), b(O.splayers))) return end
      phase = "both"; t0 = n
    end
  elseif phase == "both" then
    measure()
    if b(O.phase) == K.fall and mem:read_u16(flow_addr + L[16]) > 90 then
      if b(O.crash0) ~= 0 or b(O.crash1) ~= 0 then finish(false, string.format("a bird crashed with no platform parked (crash %d/%d)", b(O.crash0), b(O.crash1))) return end
      both_n = both_n + 1
      if up_rows(P2_BIRD) > 0 then p2_up = p2_up + 1 end
      if up_rows(P2_RAG) == 2 then rag2_up = rag2_up + 1 end
      if (mem:read_u32(flow_addr + O.hx) >> 16) ~= (mem:read_u32(flow_addr + O.hx1) >> 16) then apart = apart + 1 end
      if both_n >= 60 then
        if p2_up < 60 or rag2_up < 30 or apart < 60 then finish(false, string.format("2P fall: P2 bird up %d, P2 rag up %d, birds apart %d of 60 frames", p2_up, rag2_up, apart)) return end
        phase = "crash1"; t0 = n
      end
    elseif n - t0 > 600 then finish(false, "fall never started after the join") end
  elseif phase == "crash1" then
    measure()
    if b(O.crash0) == 1 then phase = "ghost"; t0 = n return end
    if b(O.phase) ~= K.fall then finish(false, string.format("fall left PD_FALL (phase %d) before P1 crashed", b(O.phase))) return end
    local bx = mem:read_u32(flow_addr + O.hx) >> 16   -- park a rock on P1 only (P2 starts 48 px away)
    mem:write_u16(flow_addr + O.plat, (bx - 24) & 0xffff); mem:write_u16(flow_addr + O.plat + 2, 72)
    mem:write_u8(flow_addr + O.plat + 5, 1); mem:write_u8(flow_addr + O.plat + 6, 1); mem:write_u8(flow_addr + O.plat + 7, 0)
    if n - t0 > 600 then finish(false, "P1 never crashed under the parked platform") end
  elseif phase == "ghost" then
    measure()
    local k = n - t0
    if b(O.crash1) ~= 0 then finish(false, "P2 crashed during the ghost window (random platforms): rerun") return end
    if b(O.phase) ~= K.fall then finish(false, string.format("phase %d with P2 alive, want PD_FALL (the fall must go on)", b(O.phase))) return end
    if b(O.hits) ~= 3 then finish(false, string.format("ghost hits %d, want frozen at 3", b(O.hits))) return end
    local bx = mem:read_u32(flow_addr + O.hx) >> 16   -- keep a rock on the ghost: no hit may count
    mem:write_u16(flow_addr + O.plat, (bx - 24) & 0xffff); mem:write_u16(flow_addr + O.plat + 2, 72)
    mem:write_u8(flow_addr + O.plat + 5, 1); mem:write_u8(flow_addr + O.plat + 6, 1); mem:write_u8(flow_addr + O.plat + 7, 0)
    if up_rows(P1_BIRD) > 0 then ghost_up = ghost_up + 1 end
    if k >= 60 then
      if ghost_up < 50 then finish(false, string.format("P1 ghost (slot %d) up %d of 60 frames", P1_BIRD, ghost_up)) return end
      if peak > SB_LIMIT then finish(false, string.format("sprites per line %d on line %d, limit %d", peak, peak_line, SB_LIMIT)) return end
      if us_play > FLUSH_LIMIT then finish(false, string.format("flush %d us, limit %d", us_play, FLUSH_LIMIT)) return end
      finish(true, string.format("Pop Drop 2P: P2 joins in the countdown (players 2); both birds fall 60 frames (P2 bird and rag up); P1 crashes under a parked rock, its ghost floats on 60 frames with hits frozen at 3 and P2 alive; worst %d sprites on line %d (limit %d), flush %d us (limit %d)", peak, peak_line, SB_LIMIT, us_play, FLUSH_LIMIT))
    end
  end
end)
