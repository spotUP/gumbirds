-- Headless arcade mode check (make test-arcade). Real ROM, real entry: coin, Down twice on the title select (ARCADE), Start.
--   A1. Game.mode is ARCADE, flow PLAYING, stage 1, arcade state PLAY;
--   A2. forcing every rival GONE (RAM poke, the way rs.win does) clears the stage: arcade state CLEAR for ARC_CLEAR_FRAMES frames,
--       then stage 2 and PLAY;
--   A3. stage 2 draws other islands than stage 1: a Lua shadow of the LSPC VRAM (as scroll_check.lua) is hashed over the island
--       sprites ISLAND_SPRITE.. (SCB1 tiles, SCB3 y) 90 frames after each stage starts; the two hashes differ;
--   A4. forced flier deaths (player state GONE) take the lives down one by one; the last one opens the continue state
--       (lives 0, countdown ARC_CONTINUE_FRAMES counting down, flow still PLAYING, not GAME_OVER);
--   A5. A pressed in the continue state restores ARC_LIVES_START lives, score 0, state PLAY, same stage.
-- A6: logic end stays under 224 on EVERY playing frame (steady and spike frames alike; 999 = past vblank end); steady = frames >3 after a stage/state change. ARCADE_WALK=1 (make test-arcade-walk): walks stages 1..12 instead of A2..A5.
-- Also reports the max frame logic end (raster lines after vblank end) in arcade play. Env: BRAWL_FLOW_ADDR, BRAWL_FRAME_ADDR (hex),
-- BRAWL_ARCADE_LAYOUT (arcade_probe.c output), BRAWL_RESULT.
local flow_addr  = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local frame_addr = tonumber(os.getenv("BRAWL_FRAME_ADDR"), 16)
local result     = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_ARCADE_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O_FLOW, O_MODE, O_STAGE, O_ASTATE, O_LIVES, O_LSTATE, O_COUNT, O_NCPU, O_C0STATE, SZ_FLIER, O_PSTATE, O_SCORE, O_OVER, O_LSCORE =
  L[1], L[2], L[3], L[4], L[5], L[6], L[7], L[8], L[9], L[10], L[11], L[12], L[13], L[14]
local K = { playing = L[15], arcade = L[16], play = L[17], clear = L[18], life_play = L[19], life_cont = L[20], lives = L[21],
  clear_frames = L[22], cont_frames = L[23], gone = L[24], isl = L[25], isl_n = L[26], game_over = L[27], life_end = L[28],
  isl_tile = L[29], isl_tiles = L[30], isl_pal = L[31], bonus = L[33] }
local O_NLIVE, O_BTIMER, BONUS_LIVE_MAX = L[32], L[34], L[35]
local mem    = manager.machine.devices[":maincpu"].spaces["program"]
local screen = manager.machine.screens[":screen"]
local ports  = manager.machine.ioport.ports
local function field(tag, name)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname == name then return f end end
end
local coin  = field(":AUDIO_COIN", "Coin 1")
local start = field(":edge:joy:START", "1 Player Start")
local down  = field(":edge:joy:JOY1", "P1 Down")
local abtn  = field(":edge:joy:JOY1", "P1 A")
local rgt   = field(":edge:joy:JOY1", "P1 Right")
local lft   = field(":edge:joy:JOY1", "P1 Left")
local ss = dofile("tests/mame/start_seq.lua")(coin, start, down)
local function u32(o) return mem:read_u32(flow_addr + o) end
local function s32(v) return v >= 0x80000000 and v - 0x100000000 or v end
local function g(o) return s32(u32(o)) end
local function b(o) return mem:read_u8(flow_addr + o) end   -- uint8_t fields (target is big endian: a u32 read of a byte is wrong)

local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

-- VRAM shadow (as scroll_check.lua) and the island hash
local vram, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "arcvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then vram[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
  elseif r == 4 then vmod = data end
end)
local function island_hash()
  local h = 0
  for s = K.isl, K.isl + K.isl_n - 1 do
    for w = 0, 63 do h = (h * 31 + (vram[s * 64 + w] or 0)) & 0x7fffffff end   -- SCB1 tiles and attributes
    h = (h * 31 + (vram[0x8200 + s] or 0)) & 0x7fffffff                        -- SCB3 y and height
  end
  return h
end

-- A7: every drawn island column uses the tiles and palette of the look the stage should have (look = level modulo 3: stage 1 roof, 2 garden).
-- Returns nil when all fit, else a message. A column is drawn when its SCB1 tile word is not 0 (parked sprites keep 0).
local function island_look_bad(look)
  local lo, n = K.isl_tile + look * K.isl_tiles, 0
  for s = K.isl, K.isl + K.isl_n - 1 do
    local t, a = vram[s * 64] or 0, vram[s * 64 + 1] or 0
    if t ~= 0 then
      n = n + 1
      if t < lo or t >= lo + K.isl_tiles then return string.format("sprite %d tile %d outside look %d range %d..%d", s, t, look, lo, lo + K.isl_tiles - 1) end
      if (a >> 8) ~= K.isl_pal + look then return string.format("sprite %d palette %d, want %d", s, a >> 8, K.isl_pal + look) end
    end
  end
  if n == 0 then return "no island column drawn" end
end

-- logic end (report only): g_frame_counter write, raster lines after vblank end
local LINE_S = screen.scan_period
local logic_max, fc_line = 0, -1
tap_fc = mem:install_write_tap(frame_addr, frame_addr + 3, "arcfc", function(offset, data, mask)
  local to_end, to_start = screen:time_until_vblank_end():as_double(), screen:time_until_vblank_start():as_double()
  if to_end < to_start then fc_line = 999 else fc_line = 224 - to_start / LINE_S end
end)

local n, phase, t0, fc0 = 0, "boot", nil, nil
local clear_frames, hash1, hash2, wait = 0, nil, nil, 0
local died, expect_lives, cd0, press = 0, nil, nil, 0
-- per-frame logic end bookkeeping: steady = more than 3 frames after any stage/flow/arcade-state change, arcade state PLAY, lives state PLAY
local walk = os.getenv("ARCADE_WALK") == "1"
local bonus_run = os.getenv("ARCADE_BONUS") == "1" -- make test-arcade-bonus: clear stages 1..3 and measure the bonus stage (up to 10 bubbles alive)
local bon_by = {}
local bon_over, bon_over_note, bon_prev, bon_prev_cur = 0, nil, nil, nil
local bon_logic, bon_frames, bon_nlive_max, bon_busy, bon_wait = 0, 0, 0, 0, 0
local last_sig, since_change = nil, 0
local steady_max, spike_max, spike_note, top = {}, {}, {}, {}
local steady_n, steady_over, steady_hi, steady_fit = {}, {}, {}, {}   -- per stage: steady frames, frames at or past 224 (overrun), frames over 215, max of the frames under 224
local function note_frame(stage, astate, lstate, line)
  local sig = b(O_FLOW) * 1000000 + stage * 10000 + astate * 100 + lstate
  if sig ~= last_sig then last_sig = sig; since_change = 0 else since_change = since_change + 1 end
  local steady = since_change > 3 and astate == K.play and lstate == K.life_play
  local tab = steady and steady_max or spike_max
  if steady then
    steady_n[stage] = (steady_n[stage] or 0) + 1
    if line >= 224 then steady_over[stage] = (steady_over[stage] or 0) + 1 else steady_fit[stage] = math.max(steady_fit[stage] or 0, line) end
    if line > 215 then steady_hi[stage] = (steady_hi[stage] or 0) + 1 end
  end
  if line > (tab[stage] or 0) then
    tab[stage] = line
    if not steady then spike_note[stage] = string.format("frame %d astate %d lstate %d, %d since change", n, astate, lstate, since_change) end
  end
  top[#top + 1] = { line = line, n = n, stage = stage, astate = astate, lstate = lstate, since = since_change }
  table.sort(top, function(a, c) return a.line > c.line end)
  top[6] = nil
end
local function report()
  for i, t in ipairs(top) do print(string.format("ARC_TOP%d line %.1f frame %d stage %d astate %d lstate %d since_change %d", i, t.line, t.n, t.stage, t.astate, t.lstate, t.since)) end
  for st = 1, 12 do
    if steady_max[st] or spike_max[st] then print(string.format("ARC_STAGE %d steady %.1f (fit %.1f, %d of %d frames over 215, %d overrun) spike %.1f %s", st, steady_max[st] or 0, steady_fit[st] or 0, steady_hi[st] or 0, steady_n[st] or 0, steady_over[st] or 0, spike_max[st] or 0, spike_note[st] or "")) end
  end
  for st, v in pairs(steady_max) do if v >= 224 then return false, "steady logic end " .. v .. " at stage " .. st end end
  for st, v in pairs(spike_max) do if v >= 224 then return false, "spike logic end " .. v .. " at stage " .. st .. " (" .. (spike_note[st] or "") .. ")" end end
  return true
end
local walk_wait = 0
local function state() return string.format("flow=%d mode=%d stage=%d arc=%d lives=%d lstate=%d", b(O_FLOW), b(O_MODE), g(O_STAGE), g(O_ASTATE), g(O_LIVES), g(O_LSTATE)) end

emu.register_frame_done(function()
  n = n + 1
  if n > (walk and 40000 or 9000) then finish(false, "watchdog in phase " .. phase .. ": " .. state()) return end
  local playing = b(O_FLOW) == K.playing
  if playing and fc_line > logic_max then logic_max = fc_line end
  if playing and phase ~= "boot" and phase ~= "start" then note_frame(g(O_STAGE), g(O_ASTATE), g(O_LSTATE), fc_line) end
  if (walk or bonus_run) and phase ~= "boot" and phase ~= "start" and phase ~= "stage1" and phase ~= "walk_clear" then mem:write_u32(flow_addr + O_LIVES, K.lives) end
  if phase == "boot" then
    local fc = mem:read_u32(frame_addr)
    fc0 = fc0 or fc
    if fc ~= fc0 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    if ss.step(n, playing, 2) then phase = "stage1" ; wait = 0 end
    if n - t0 > 1500 then finish(false, "A1 never reached PLAYING: " .. state()) end
  elseif phase == "stage1" then
    if b(O_MODE) ~= K.arcade then finish(false, "A1 mode is not ARCADE (ARCADE entry missing from the title select): " .. state()) return end
    if b(O_NCPU) > 0 then wait = wait + 1 end
    if g(O_STAGE) ~= 1 or g(O_ASTATE) ~= K.play then finish(false, "A1 not stage 1 PLAY: " .. state()) return end
    if wait >= 90 then
      local bad = island_look_bad(0)
      if bad then finish(false, "A7 stage 1 should draw the roof look: " .. bad) return end
      hash1 = island_hash(); phase = walk and "walk" or (bonus_run and "bonus_go" or "force_clear"); walk_wait = 0 end
  elseif phase == "walk" then
    -- ARCADE_WALK=1: play ~300 frames per stage with every rival alive (lives poked up), then force the clear
    walk_wait = walk_wait + 1
    if (g(O_STAGE) >= 12 and walk_wait >= 300) or not playing then
      local ok, why = report()
      finish(ok, ok and "walk stages 1..12 done" or why)
    elseif walk_wait >= 300 then phase = "walk_clear" end
  elseif phase == "walk_clear" then
    local st = g(O_STAGE)
    for i = 0, b(O_NCPU) - 1 do mem:write_u8(flow_addr + O_C0STATE + i * SZ_FLIER, K.gone) end
    if g(O_ASTATE) == K.clear then phase = "walk_wait_next"; clear_frames = 0 end
  elseif phase == "walk_wait_next" then
    if g(O_ASTATE) == K.play then phase = "walk"; walk_wait = 0; print(string.format("ARC_PROG stage %d at frame %d", g(O_STAGE), n)) end
  elseif phase == "bonus_go" then
    -- every stage's rivals forced GONE until the arcade state is BONUS; then every frame of the bonus stage is measured until it ends
    bon_wait = bon_wait + 1
    if g(O_ASTATE) == K.bonus then
      if playing then
        local nl = g(O_NLIVE)
        -- stress: the reference pace (spawn gap 40..103, about 300 frames per rise) rarely has more than 7 alive, so force the spawn
        -- timer due while the pool has room: the pool fills to ARC_BONUS_LIVE_MAX and the logic end is measured at the real worst case
        if nl < BONUS_LIVE_MAX then mem:write_u16(flow_addr + O_BTIMER, 1) end
        bon_frames = bon_frames + 1
        if nl > bon_nlive_max then bon_nlive_max = nl end
        if nl >= 8 then bon_busy = bon_busy + 1; if fc_line >= 224 then bon_over = bon_over + 1; if not bon_over_note then bon_over_note = string.format('frame %d nlive %d bonus frame %d', n, nl, bon_frames) end elseif fc_line > bon_logic then bon_logic = fc_line end end
        bon_prev = nl
        -- fly left and right with flaps so the camera scrolls (the floor and nozzles must be placed again)
        rgt:set_value((bon_frames % 240) < 120 and 1 or 0); lft:set_value((bon_frames % 240) >= 120 and 1 or 0); abtn:set_value((bon_frames % 14) < 3 and 1 or 0)
        do local t = bon_by[nl] or {0, 0, 0}; t[1] = t[1] + 1; t[2] = t[2] + (fc_line >= 224 and 1 or 0); if fc_line < 224 and fc_line > t[3] then t[3] = fc_line end; bon_by[nl] = t end
      end
      bon_wait = 0
    elseif bon_frames > 0 then
      local why
      for k = 0, 10 do local t = bon_by[k]; if t then print(string.format('BON_NL %d frames %d over %d max %.1f', k, t[1], t[2], t[3])) end end
      if bon_nlive_max < BONUS_LIVE_MAX then why = "bonus never had " .. BONUS_LIVE_MAX .. " bubbles alive (max " .. bon_nlive_max .. ")"
      elseif bon_over > 0 then why = "bonus logic end past 224 on " .. bon_over .. " of " .. bon_busy .. " busy frames, first " .. bon_over_note
      elseif bon_busy < 50 then why = "only " .. bon_busy .. " frames with 8+ bubbles" end
      finish(why == nil, why or string.format("bonus stage: %d frames, max %d bubbles alive, %d frames with 8+ alive, max logic end %.1f of 224 (%d over)", bon_frames, bon_nlive_max, bon_busy, bon_logic, bon_over))
      return
    elseif bon_wait > 12000 then finish(false, "bonus stage never reached: " .. state()) return
    else for i = 0, b(O_NCPU) - 1 do mem:write_u8(flow_addr + O_C0STATE + i * SZ_FLIER, K.gone) end end
  elseif phase == "force_clear" then
    for i = 0, b(O_NCPU) - 1 do mem:write_u8(flow_addr + O_C0STATE + i * SZ_FLIER, K.gone) end
    if g(O_ASTATE) == K.clear then phase = "clear"; clear_frames = 0 end
  elseif phase == "clear" then
    if g(O_ASTATE) == K.clear then clear_frames = clear_frames + 1
    else
      if clear_frames < K.clear_frames - 2 or clear_frames > K.clear_frames + 2 then finish(false, "A2 CLEAR lasted " .. clear_frames .. " frames, want " .. K.clear_frames) return end
      if g(O_STAGE) ~= 2 or g(O_ASTATE) ~= K.play then finish(false, "A2 after CLEAR not stage 2 PLAY: " .. state()) return end
      phase = "stage2"; wait = 0
    end
  elseif phase == "stage2" then
    wait = wait + 1
    if wait >= 150 then
      local bad = island_look_bad(1)
      if bad then finish(false, "A7 stage 2 should draw the garden look: " .. bad) return end
      hash2 = island_hash()
      if hash1 == hash2 then finish(false, "A3 island VRAM words unchanged between stage 1 and 2 (hash " .. hash1 .. ")") return end
      phase = "die"; expect_lives = g(O_LIVES)
      if expect_lives ~= K.lives then finish(false, "A4 lives at stage 2 are " .. expect_lives .. ", want " .. K.lives) return end
    end
  elseif phase == "die" then
    if g(O_LIVES) < expect_lives or g(O_LSTATE) ~= K.life_play then
      died = died + 1; expect_lives = g(O_LIVES)
      if g(O_LSTATE) == K.life_cont then phase = "continue"; cd0 = nil; wait = 0 end
    elseif g(O_PSTATE) ~= K.gone and b(O_NCPU) > 0 then
      mem:write_u8(flow_addr + O_PSTATE, K.gone)
    end
  elseif phase == "continue" then
    wait = wait + 1
    if wait <= 40 and (b(O_FLOW) ~= K.playing or g(O_LIVES) ~= 0 or g(O_LSTATE) ~= K.life_cont) then finish(false, "A4 continue state lost: " .. state()) return end
    local c = g(O_COUNT)
    if wait == 1 and c > K.cont_frames then finish(false, "A4 countdown " .. c .. " above " .. K.cont_frames) return end
    cd0 = cd0 or c
    if wait == 40 then
      if not (c < cd0) then finish(false, "A4 continue countdown does not run: " .. cd0 .. " -> " .. c) return end
      abtn:set_value(1)
    elseif wait == 46 then abtn:set_value(0)
    elseif wait > 46 then
      finish(false, "A5 A did not continue: " .. state())
    end
    if wait >= 41 and wait <= 46 and g(O_LSTATE) == K.life_play then
      abtn:set_value(0)
      if g(O_LIVES) ~= K.lives or g(O_SCORE) ~= 0 or g(O_STAGE) ~= 2 then finish(false, "A5 continue state wrong: " .. state() .. " score=" .. g(O_SCORE)) return end
      local ok, why = report()
      if not ok then finish(false, "A6 " .. why) return end
      finish(true, string.format("arcade entry, stage 1 -> CLEAR (%d frames) -> stage 2, islands differ, %d deaths -> continue -> resumed; max logic end %.1f of 224", clear_frames, died, logic_max))
    end
  end
end)
