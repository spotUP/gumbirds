-- Headless flier reachability check (make test-flier). Sentinel-driven timeline, no fixed frame numbers:
--   1. coin once the main loop runs (g_frame_counter advanced), hold start until the flow state is PLAYING;
--   2. settle: no input, the flier stands on its start island 0 (on_ground);
--   3. flap: press A eight times (edge each time); flier y must rise above the standing y;
--   4. drown: walk right off the island, steer back over the gap between islands with left+flap until vx <= 0, then
--      no input: the flier falls to the hazard kill line of the strip shown (Flier.kill_y, read from the ROM: 192..214), state DROWNED, and the flow leaves PLAYING for GAME_OVER;
--   5. sentinel: Game.flier_steps (counts flier_step calls) must track the game loop frames spent in PLAYING.
-- The frame cap is only a hang watchdog. Env: BRAWL_FLOW_ADDR, BRAWL_FRAME_ADDR (hex), BRAWL_FLIER_LAYOUT
-- (flier_probe.c output), BRAWL_RESULT (file).
local flow_addr  = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local frame_addr = tonumber(os.getenv("BRAWL_FRAME_ADDR") or "", 16)
local result     = os.getenv("BRAWL_RESULT")
local soot_addr  = tonumber(os.getenv("BRAWL_SOOT_ADDR") or "", 16)   -- g_soot_range (main.c): range, then sentinels
local view_addr  = tonumber(os.getenv("BRAWL_SOOTVIEW_ADDR") or "", 16)   -- g_soot_view (main.c): player clip, sheet frame, ticks
local pair_addr  = tonumber(os.getenv("BRAWL_PAIR_ADDR") or "", 16)   -- g_flier_pair_calls (flier.c): flier_pair call counter
local blocked_addr = tonumber(os.getenv("BRAWL_BLOCKED_ADDR") or "", 16)   -- g_flier_pair_blocked (flier.c): platform-block predicate hits
local ceil_addr = tonumber(os.getenv("BRAWL_CEIL_ADDR") or "", 16)   -- g_flier_ceiling_hits (flier.c): ceiling bounces in flier_step
local ceilrival_addr = tonumber(os.getenv("BRAWL_CEILRIVAL_ADDR") or "", 16)   -- of those, on the lowered computer flier line
local lay = {}
for v in (os.getenv("BRAWL_FLIER_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local O_STATE, O_FRAME, O_STEPS, O_OVER, O_SCORE, O_X, O_Y, O_VX, O_VY, O_FSTATE, O_BAL, O_GROUND =
  lay[1], lay[2], lay[3], lay[4], lay[5], lay[6], lay[7], lay[8], lay[9], lay[10], lay[11], lay[12]
local O_CPUN, O_CPUALIVE, O_STOMPS, O_WON, O_C0X, O_C0Y, O_THINKS, O_C1X =
  lay[13], lay[14], lay[15], lay[16], lay[17], lay[18], lay[19], lay[20]
local K_POP, K_DEFEAT, O_C0STATE, O_C0BAL, O_KILLY = lay[21], lay[22], lay[23], lay[24], lay[25]
local O_SPAWN, O_INV = lay[26], lay[27]   -- player's spawn_inv (uint16) and invincible (uint8)   -- knob values and cpu[0] state, balloons
local mem    = manager.machine.devices[":maincpu"].spaces["program"]
local rs     = dofile("tests/mame/round_skip.lua")(mem, flow_addr, lay) -- rs.live(): no round end or round start text running
local ports  = manager.machine.ioport.ports

local FLOW_PLAYING, FLOW_GAME_OVER = 3, 4
local FL_DROWNED = 3
local WATCHDOG = 6000
local diag_f = os.getenv("BRAWL_FLIER_LOG") and io.open(os.getenv("BRAWL_FLIER_LOG"), "w") or nil
if diag_f then diag_f:setvbuf("line") end
local diag_re = tonumber(os.getenv("BRAWL_RE_ADDR") or "", 16)
local diag_kind = tonumber(os.getenv("BRAWL_HKIND_ADDR") or "", 16)
local diag_m = tonumber(os.getenv("BRAWL_HMATCH_ADDR") or "", 16)

local function field(tag, pred)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if pred(fname) then return f end end
end
local coin  = field(":AUDIO_COIN", function(nm) return nm == "Coin 1" end)
local start = field(":edge:joy:START", function(nm) return nm == "1 Player Start" end)
local ss = dofile("tests/mame/start_seq.lua")(coin, start)
local abtn  = field(":edge:joy:JOY1", function(nm) return nm == "P1 A" end)
local rbtn  = field(":edge:joy:JOY1", function(nm) return nm == "P1 Right" end)
local lbtn  = field(":edge:joy:JOY1", function(nm) return nm == "P1 Left" end)

local function s32(v) return v >= 0x80000000 and v - 0x100000000 or v end
local function g32(o) return mem:read_u32(flow_addr + o) end
local function s32_to_u(px) return math.floor(px * 65536 + 0.5) & 0xffffffff end
local function gs32(o) return s32(g32(o)) end

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

local n, phase, fc0, coin_at = 0, "boot", nil, nil
local frozen = 0
local play_fc0, steps0 = nil, nil
local stand_x, stand_y, flaps, tick, min_y = nil, nil, 0, 0, nil
local settle_at = nil
local ceil_min_y, ceil0
local si_start, si_before = 0, 0
local cpu_n, cpu_x0, cpu_y0, cpu_x1, thinks0, cpu_report

local function release() abtn:set_value(0); rbtn:set_value(0); lbtn:set_value(0) end
local drive = dofile("tests/mame/flier_drive.lua")(mem, flow_addr, lay, abtn, lbtn, rbtn)   -- walk off the island and drown

-- Sootling clip numbers and sheet frames (assets/flier/sootling_sheet.json; build/gen/sootling_tables.h)
local CLIP_FLAP2, CLIP_WALK2, CLIP_BREATHE2 = 0, 10, 12
local WALK2_FIRST, WALK2_LAST = 77, 84     -- sheet frames of the 8 WALK2 frames
local FLAP_REST = 0                        -- sheet frame the flap clip rests on (first frame of FLAP2)
local FLAP_FRAMES, FLAP_HOLD = 8, 2        -- frames in a flap play and ticks each (FLIER_FLAP_HOLD, src/core/tuning.h)
local FLAP_COOLDOWN = 9                    -- FLIER_FLAP_COOLDOWN (src/core/tuning.h)
local WV_SETTLE, WV_WALK_FRAMES, WV_STOP_FRAMES = 60, 16, 90   -- settle: the put-back lands the player, let the landing clip finish
local wv_frames, wv_tiles, wv_seen
local fv_stage, fv_t, fv_rec = 0, 0, {}

-- Flap animation seen in the ROM. Stage 1: no input, airborne, every shown frame is the rest frame. Stage 2: one
-- two-frame press: rest, then the remaining frames of one play each held FLAP_HOLD, then rest again for good. Stage 3:
-- two presses FLAP_COOLDOWN frames apart: the second restarts the play, so the rest frame shows 9 frames after the first press.
-- Returns true when finished. The player is put high above the island before each stage so it stays airborne.
local function flapview_step()
  if not view_addr then finish(false, "missing BRAWL_SOOTVIEW_ADDR") return false end
  local function lift()
    mem:write_u32(flow_addr + O_Y, s32_to_u(40)); mem:write_u32(flow_addr + O_VY, 0); mem:write_u32(flow_addr + O_VX, 0)
    fv_t, fv_rec = 0, {}
  end
  local function shown() return mem:read_u16(view_addr + 2) end
  local function airborne_or_fail()
    if mem:read_u8(flow_addr + O_GROUND) == 1 then finish(false, string.format("flap view stage %d: the player landed after %d frames, lifted too low", fv_stage, fv_t)) return false end
    return true
  end
  if fv_stage == 0 then
    mem:write_u8(flow_addr + O_BAL, 2)   -- a computer flier may have popped one: the rest frame checked below is the two-balloon flap clip
    lift(); fv_stage = 1; return false
  end
  -- hold the player high up every frame so it never lands (flap and gravity still run; only y and vy are pinned)
  mem:write_u32(flow_addr + O_Y, s32_to_u(40)); mem:write_u32(flow_addr + O_VY, 0); mem:write_u32(flow_addr + O_VX, 0)
  if fv_stage == 1 then
    fv_t = fv_t + 1
    if fv_t > 70 then   -- skip the first frames: restoring the second balloon plays the inflate clip
      if not airborne_or_fail() then return false end
      fv_rec[#fv_rec + 1] = shown()
    end
    if fv_t >= 110 then
      for i, v in ipairs(fv_rec) do
        if v ~= FLAP_REST then finish(false, string.format("flap view: released for %d frames, sheet frame %d at sample %d, want the rest frame %d every frame", fv_t, v, i, FLAP_REST)) return false end
      end
      cpu_report = cpu_report .. string.format("; flap rest frame held %d samples", #fv_rec)
      lift(); fv_stage = 2
    end
    return false
  end
  local function runs(rec)
    local r = {}
    for _, v in ipairs(rec) do
      if #r > 0 and r[#r][1] == v then r[#r][2] = r[#r][2] + 1 else r[#r + 1] = { v, 1 } end
    end
    return r
  end
  if fv_stage == 2 then
    fv_t = fv_t + 1
    -- rest for 20 frames, press at t = 21 and 22, then record FLAP_FRAMES * FLAP_HOLD + 30 frames
    abtn:set_value((fv_t == 21 or fv_t == 22) and 1 or 0)
    if fv_t > 20 then
      if not airborne_or_fail() then return false end
      fv_rec[#fv_rec + 1] = shown()
    end
    if fv_t >= 20 + FLAP_FRAMES * FLAP_HOLD + 30 then
      abtn:set_value(0)
      local r = runs(fv_rec)
      -- runs: rest (merged with play frame 0), FLAP_FRAMES - 1 increasing frames held FLAP_HOLD, rest to the end
      local msg = ""
      for _, x in ipairs(r) do msg = msg .. string.format(" %d x%d", x[1], x[2]) end
      if #r ~= FLAP_FRAMES + 1 then finish(false, string.format("flap view: %d runs, want %d (rest, %d frames, rest); runs:%s", #r, FLAP_FRAMES + 1, FLAP_FRAMES - 1, msg)) return false end
      if r[1][1] ~= FLAP_REST or r[#r][1] ~= FLAP_REST then finish(false, "flap view: the play does not start and end on the rest frame; runs:" .. msg) return false end
      for i = 2, FLAP_FRAMES do
        if r[i][1] <= r[i - 1][1] or r[i][2] ~= FLAP_HOLD then finish(false, string.format("flap view: play frame run %d is %d x%d, want increasing frames held %d; runs:%s", i, r[i][1], r[i][2], FLAP_HOLD, msg)) return false end
      end
      if r[#r][2] < 10 then finish(false, "flap view: the rest frame did not stay after the play; runs:" .. msg) return false end
      cpu_report = cpu_report .. "; flap play:" .. msg
      lift(); fv_stage = 3
    end
    return false
  end
  fv_t = fv_t + 1
  -- two presses FLAP_COOLDOWN frames apart (press 1 at t = 21, press 2 at t = 21 + FLAP_COOLDOWN)
  local p2 = 21 + FLAP_COOLDOWN
  abtn:set_value((fv_t == 21 or fv_t == 22 or fv_t == p2 or fv_t == p2 + 1) and 1 or 0)
  if fv_t > 20 then
    if not airborne_or_fail() then return false end
    fv_rec[#fv_rec + 1] = shown()
  end
  if fv_t >= p2 + FLAP_FRAMES * FLAP_HOLD + 10 then
    abtn:set_value(0)
    -- fv_rec[k] is the sample at t = 20 + k. The play after press 1 is on its fifth frame by p2 - 1 (not rest);
    -- the restart by press 2 shows the rest frame within two samples of p2.
    local before, after = fv_rec[p2 - 1 - 20], math.min(fv_rec[p2 - 20] or -1, fv_rec[p2 + 1 - 20] or -1)
    if before == FLAP_REST then finish(false, "flap view: the first play was already back at rest before the second press") return false end
    if after ~= FLAP_REST then finish(false, string.format("flap view: the second press %d frames after the first did not restart the play (frames %s)", FLAP_COOLDOWN, table.concat(fv_rec, ","))) return false end
    cpu_report = cpu_report .. string.format("; second press %d frames after the first restarted the play", FLAP_COOLDOWN)
    return true
  end
  return false
end

emu.register_frame_done(function() local ok_, err_ = pcall(function()
  if done then return end
  n = n + 1
  if n > WATCHDOG then
    finish(false, string.format("watchdog: phase %s (steps %d, flier state %d, y %.1f)", phase,
      O_STEPS and g32(O_STEPS) or -1, O_FSTATE and mem:read_u8(flow_addr + O_FSTATE) or -1,
      O_Y and gs32(O_Y) / 65536 or -1))
    return
  end
  if not (coin and start and abtn and rbtn and lbtn) then finish(false, "missing input field") return end
  if not frame_addr or not O_GROUND then finish(false, "missing BRAWL_FRAME_ADDR or probe layout") return end
  local state = mem:read_u8(flow_addr + O_STATE)
  local fc = mem:read_u32(frame_addr)
  if diag_f then -- diagnostic only (BRAWL_FLIER_LOG): per-frame state, no assert
    diag_f:write(string.format("%d %s fc %d st %d re %d,%d,%d,%d kind %d m %d x %.2f y %.2f vx %.2f fs %d gnd %d alive %d won %d\n",
      n, phase, fc, state, mem:read_u16(diag_re), mem:read_u16(diag_re + 2), mem:read_u16(diag_re + 4), mem:read_u16(diag_re + 6),
      diag_kind and mem:read_u8(diag_kind) or -1, diag_m and mem:read_u16(diag_m) or -1, gs32(O_X) / 65536, gs32(O_Y) / 65536,
      gs32(O_VX) / 65536, mem:read_u8(flow_addr + O_FSTATE), mem:read_u8(flow_addr + O_GROUND), mem:read_u8(flow_addr + O_CPUALIVE),
      mem:read_u8(flow_addr + O_WON)))
  end
  if play_fc0 and state == FLOW_PLAYING and not rs.live() then frozen = frozen + 1 end -- banner hold, camera slide, ROUND nn, GO!: no flier steps

  if phase == "boot" then
    if fc ~= 0 then fc0 = fc0 or fc end
    if fc0 and fc - fc0 >= 30 then phase = "coin"; coin_at = n; ss.begin(n) end
    return
  elseif phase == "coin" then
    -- one coin; the first Start press opens the title mode select, the second begins the game (BG4; tests/mame/start_seq.lua)
    if ss.step(n, state == FLOW_PLAYING) then phase = "start" end
    return
  elseif phase == "start" then
    if state ~= FLOW_PLAYING then return end
    play_fc0, steps0 = fc, g32(O_STEPS)
    si_start = mem:read_u16(flow_addr + O_SPAWN)
    if si_start == 0 then finish(false, "spawn_inv is 0 at the start of play, want the spawn protection running") return end
    phase = "settle"; settle_at = n
    return
  end

  local on_ground = mem:read_u8(flow_addr + O_GROUND)
  local fy = gs32(O_Y) / 65536
  local fx = gs32(O_X) / 65536
  local vx = gs32(O_VX) / 65536

  if phase == "flap" and state ~= FLOW_PLAYING then
    finish(false, string.format("flow left PLAYING during %s (state %d, flier state %d, cpu_alive %d, stomps %d)", phase, state,
      mem:read_u8(flow_addr + O_FSTATE), mem:read_u8(flow_addr + O_CPUALIVE), mem:read_u8(flow_addr + O_STOMPS))) return
  end
  if phase == "settle" then
    if state ~= FLOW_PLAYING then finish(false, "left PLAYING while settling") return end
    if on_ground == 1 then stand_y, stand_x = fy, fx; phase = "cpu"; tick = 0 end
    if n > settle_at + 600 then finish(false, "flier never landed on the island") end
    return
  elseif phase == "cpu" then
    -- computer fliers run through the real loop: present, moving, and thinking (no input from the player)
    if state ~= FLOW_PLAYING then finish(false, "left PLAYING while watching the computer fliers") return end
    if tick == 0 then
      cpu_n = mem:read_u8(flow_addr + O_CPUN)
      if cpu_n < 2 or mem:read_u8(flow_addr + O_CPUALIVE) ~= cpu_n then
        finish(false, "computer fliers missing after start: count " .. cpu_n) return
      end
      cpu_x0, cpu_y0, cpu_x1 = g32(O_C0X), g32(O_C0Y), g32(O_C1X)
      thinks0 = g32(O_THINKS)
    end
    tick = tick + 1
    if tick >= 150 then
      local moved = g32(O_C0X) ~= cpu_x0 or g32(O_C0Y) ~= cpu_y0 or g32(O_C1X) ~= cpu_x1
      local thinks = g32(O_THINKS) - thinks0
      if not moved then finish(false, "computer fliers did not move in 150 frames") return end
      if thinks < 3 then finish(false, "AI think counter advanced only " .. thinks .. " in 150 frames") return end
      -- Sentinel: the Sootling frame-select path ran for the player and a computer flier (main.c hero_show,
      -- pool_show_hero): the tile numbers last written to the sprite registers lie in the Sootling tile range.
      local sbase, scount = mem:read_u16(soot_addr), mem:read_u16(soot_addr + 2)
      local ptile, ctile, cdraws = mem:read_u16(soot_addr + 6), mem:read_u16(soot_addr + 8), mem:read_u16(soot_addr + 10)
      if ptile < sbase or ptile >= sbase + scount then finish(false, string.format("player sprite tile %d outside Sootling range %d+%d", ptile, sbase, scount)) return end
      if ctile < sbase or ctile >= sbase + scount or cdraws < 100 then finish(false, string.format("computer flier tile %d (draws %d) outside Sootling range %d+%d", ctile, cdraws, sbase, scount)) return end
      cpu_report = string.format("Sootling tiles drawn (player %d, computer %d, range %d+%d, %d computer draws); ", ptile, ctile, sbase, scount, cdraws) .. string.format("%d computer fliers moved, %d thinks in 150 frames", cpu_n, thinks)
      si_before = mem:read_u16(flow_addr + O_SPAWN)
      -- SI: spawn protection counted down while the player gave no input (read at start and now, 150+ frames apart)
      if si_start == 0 or si_before >= si_start then finish(false, string.format("spawn_inv did not count down with no input: %d at start, %d after %d frames", si_start, si_before, tick)) return end
      cpu_report = cpu_report .. string.format("; spawn_inv %d -> %d with no input", si_start, si_before)
      phase = "si"; tick = 0
    end
    return
  elseif phase == "si" then
    -- SI: the first input cancels the protection. Press A for two frames; one frame after, spawn_inv must be 0.
    if state ~= FLOW_PLAYING then finish(false, "left PLAYING during the spawn protection phase") return end
    if tick < 2 then abtn:set_value(1) else abtn:set_value(0) end
    tick = tick + 1
    if tick == 4 then
      local si = mem:read_u16(flow_addr + O_SPAWN)
      if si ~= 0 then finish(false, "spawn_inv " .. si .. " after the first flap input, want 0") return end
      cpu_report = cpu_report .. "; first flap input cleared spawn_inv"
      phase = "stomp"; tick = 0
    end
    return
  elseif phase == "stomp" then
    -- Real stomp through game_step_arena: the player's feet are put in the box of computer flier 0 (test input,
    -- same placement as tests/host/stomp_assist.h). Sentinels: g_stomps rises (a computer-on-computer stomp can add to it too) and the score rises by the knob value.
    if state ~= FLOW_PLAYING then finish(false, "left PLAYING during the stomp phase") return end
    local c0state, c0bal = mem:read_u8(flow_addr + O_C0STATE), mem:read_u8(flow_addr + O_C0BAL)
    if stomp_stomps0 and g32(O_SCORE) ~= stomp_score0 then
      local delta = g32(O_SCORE) - stomp_score0
      -- defeat bonus only when the last balloon popped in the air: a grounded computer flier keeps standing with 0 balloons
      -- (flier_lose_balloon) and is defeated later by body contact, so read the state after the pop
      local want = K_POP + ((stomp_bal0 == 1 and c0state > 1) and K_DEFEAT or 0)
      if g32(O_STOMPS) < stomp_stomps0 + 1 or delta ~= want then
        finish(false, string.format("stomp: stomps %d -> %d, score delta %d, want at least +1 stomp and %d (pop %d, balloons before %d)",
          stomp_stomps0, g32(O_STOMPS), delta, want, K_POP, stomp_bal0)) return
      end
      cpu_report = cpu_report .. string.format("; stomp popped a computer balloon, score +%d", delta)
      phase = "side"; tick = 0; side_step = 1; side_n0 = n
      return
    end
    -- score unchanged here: cpu0 lost a balloon under the player's feet since last frame, so the score add is missing
    -- (g_stomps alone is not used: a computer-on-computer stomp also raises it and scores nothing)
    if stomp_stomps0 and c0bal < stomp_bal0 then
      finish(false, string.format("stomp landed (stomps %d -> %d, cpu0 balloons %d -> %d) but the score never rose",
        stomp_stomps0, g32(O_STOMPS), stomp_bal0, c0bal)) return
    end
    if c0state > 1 or c0bal == 0 then finish(false, "computer flier 0 gone before the stomp test") return end
    if not stomp_stomps0 and c0bal < 2 then
      -- test setup: the computer flier may have lost a balloon already; two are needed, one for the stomp and one for the side phase
      mem:write_u8(flow_addr + O_C0BAL, 2)
      c0bal = 2
    end
    stomp_stomps0, stomp_score0, stomp_bal0 = g32(O_STOMPS), g32(O_SCORE), c0bal
    mem:write_u32(flow_addr + O_X, g32(O_C0X))
    mem:write_u32(flow_addr + O_Y, g32(O_C0Y) - 26 * 65536)
    mem:write_u32(flow_addr + O_VX, 0)
    mem:write_u32(flow_addr + O_VY, 65536)   -- falling 1 px per frame: a pop needs the pair to close
    mem:write_u8(flow_addr + O_GROUND, 0)   -- teleported into the air
    tick = tick + 1
    if tick > 300 then finish(false, string.format("no scoring stomp in 300 frames: player (%.1f,%.1f) cpu0 (%.1f,%.1f) state %d balloons %d", gs32(O_X) / 65536, gs32(O_Y) / 65536, gs32(O_C0X) / 65536, gs32(O_C0Y) / 65536, c0state, c0bal)) end
    return
  elseif phase == "side" then
    -- Gum contact through the real game_step_arena (flier_pair), two cases against computer flier 0:
    --   step 1 level: the player is put 10 px beside it at the same height, moving toward it at 3 px per frame (faster than any computer flier drifts away, so the pair closes). Gum meets gum, so both
    --          bounce: player vx turns positive, no balloon is lost, the score does not move.
    --   step 2 wait until the invincible window left by the stomp is over.
    --   step 3 side: the player is put 11 px beside it and 16 px higher, falling 1 px per frame (a pop needs the pair to close). The lower flier's gum pops: cpu0 loses one
    --          balloon and the score rises by the pop knob (plus the defeat knob for a last balloon in the air).
    -- Both cases need g_flier_pair_calls to rise, so a compiled-out contact cannot pass.
    if state ~= FLOW_PLAYING then finish(false, "left PLAYING during the side phase") return end
    if not pair_addr then finish(false, "missing BRAWL_PAIR_ADDR") return end
    local c0state, c0bal = mem:read_u8(flow_addr + O_C0STATE), mem:read_u8(flow_addr + O_C0BAL)
    local calls = mem:read_u32(pair_addr)
    local function put(dx, dy, vx, vy)
      mem:write_u32(flow_addr + O_X, (g32(O_C0X) + dx * 65536) & 0xffffffff)
      mem:write_u32(flow_addr + O_Y, (g32(O_C0Y) + dy * 65536) & 0xffffffff)
      mem:write_u32(flow_addr + O_VX, vx % 0x100000000)
      mem:write_u32(flow_addr + O_VY, (vy or 0) % 0x100000000)
      mem:write_u8(flow_addr + O_GROUND, 0)
    end
    tick = tick + 1
    if side_step >= 2 then
      -- other computer fliers pop the free player while the wait runs and the side pop is set up; a player at zero balloons is FALLING (dead) and flier_pair ignores it,
      -- so restoring the balloon count afterwards cannot revive it. Keep the player immune; the pop under test lands on computer flier 0, whose own window is not touched.
      mem:write_u8(flow_addr + O_INV, 200)
    end
    if side_step == 1 then
      if side_armed and calls > side_calls0 then
        local pbal = mem:read_u8(flow_addr + O_BAL)
        if c0bal ~= side_bal0 or pbal ~= side_pbal0 or g32(O_SCORE) ~= side_score0 then
          finish(false, string.format("side level: balloons cpu0 %d -> %d, player %d -> %d, score %d -> %d; a level bounce changes none",
            side_bal0, c0bal, side_pbal0, pbal, side_score0, g32(O_SCORE))) return
        end
        if gs32(O_VX) <= 0 then finish(false, string.format("side level: player vx %d did not turn positive after the bounce", gs32(O_VX))) return end
        cpu_report = cpu_report .. string.format("; level gum contact bounced the player (vx %d, pair calls +%d), nothing lost", gs32(O_VX), calls - side_calls0)
        side_step = 2; side_armed = false
        return
      end
      if c0state > 1 or c0bal == 0 then finish(false, string.format("computer flier 0 gone before the side test: state %d balloons %d (before the stomp %s)", c0state, c0bal, tostring(stomp_bal0))) return end
      side_calls0, side_bal0, side_score0 = calls, c0bal, g32(O_SCORE)
      side_pbal0 = mem:read_u8(flow_addr + O_BAL)
      put(10, 0, -196608)
      side_armed = true
      if tick > 300 then finish(false, "no level contact in 300 frames: flier_pair never ran") end
      return
    elseif side_step == 2 then
      if n - side_n0 >= 80 then
        -- the free player may have been popped by a computer flier during the wait: restore the balloon here so the inflate clip is over before the walk view
        mem:write_u8(flow_addr + O_BAL, 2)
        side_step = 3; tick = 0
      end
      return
    end
    if side_armed and g32(O_SCORE) ~= side_score0 then
      local delta = g32(O_SCORE) - side_score0
      local want = K_POP + ((side_bal0 == 1 and c0state > 1) and K_DEFEAT or 0)
      if calls <= side_calls0 or c0bal ~= side_bal0 - 1 or delta ~= want then
        finish(false, string.format("side pop: pair calls %d -> %d, cpu0 balloons %d -> %d, score delta %d, want %d",
          side_calls0, calls, side_bal0, c0bal, delta, want)) return
      end
      cpu_report = cpu_report .. string.format("; side contact popped the lower gum, score +%d (pair calls +%d)", delta, calls - side_calls0)
      -- put the player back where it stood: the rest of the check walks off the middle island
      mem:write_u32(flow_addr + O_X, s32_to_u(stand_x))
      mem:write_u32(flow_addr + O_Y, s32_to_u(stand_y))
      mem:write_u32(flow_addr + O_VX, 0)
      mem:write_u32(flow_addr + O_VY, 0)
      phase = "walkview"; tick = 0
      return
    end
    if side_armed and c0bal < side_bal0 then finish(false, "side pop: cpu0 lost a balloon but the score never rose") return end
    if c0state > 1 or c0bal == 0 then finish(false, "computer flier 0 gone before the side pop") return end
    side_calls0, side_bal0, side_score0 = calls, c0bal, g32(O_SCORE)
    -- 11 px: flier_pair pops a one-balloon gum from above only while |dx| < FLIER_BODY_HALF_W + FLIER_GUM_HALF_W1
    -- (7 + 5 = 12 px, edge exclusive); cpu0 has one balloon left after the stomp, so 12 px is outside the box and bounces.
    put(11, -16, 0, 65536)
    side_armed = true
    if tick > 300 then finish(false, "no side pop in 300 frames") end
    return
  elseif phase == "walkview" then
    -- Walk cycle through the real ROM: hold right on the island, the player clip must be WALK2 with sheet frames
    -- 77..84 and more than one distinct tile written to the sprite registers; after letting go it must settle in BREATHE2.
    if state ~= FLOW_PLAYING then finish(false, "left PLAYING during the walk view check") return end
    if not view_addr then finish(false, "missing BRAWL_SOOTVIEW_ADDR") return end
    if tick == 0 then wv_frames, wv_tiles, wv_seen = {}, {}, 0 end
    tick = tick + 1
    mem:write_u8(flow_addr + O_INV, 200)   -- computer fliers roam the arena: a pop here would swap the walk and breathing clips under test for pop clips
    local clip, frame = mem:read_u16(view_addr), mem:read_u16(view_addr + 2)
    if tick > WV_SETTLE and tick <= WV_SETTLE + WV_WALK_FRAMES then
      rbtn:set_value(1)
      if clip == CLIP_WALK2 then
        wv_seen = wv_seen + 1
        if frame < WALK2_FIRST or frame > WALK2_LAST then finish(false, string.format("walk: sheet frame %d outside the WALK2 frames %d..%d", frame, WALK2_FIRST, WALK2_LAST)) return end
        wv_frames[frame] = true
        wv_tiles[mem:read_u16(soot_addr + 6)] = true
      end
    else
      rbtn:set_value(0)
    end
    if tick == WV_SETTLE + WV_WALK_FRAMES then
      local nf, nt = 0, 0
      for _ in pairs(wv_frames) do nf = nf + 1 end
      for t in pairs(wv_tiles) do nt = nt + 1 end
      local sbase, scount = mem:read_u16(soot_addr), mem:read_u16(soot_addr + 2)
      if wv_seen < 4 then finish(false, string.format("walk: clip WALK2 (%d) seen on only %d of %d frames of holding right (last clip %d)", CLIP_WALK2, wv_seen, WV_WALK_FRAMES, clip)) return end
      if nf < 2 or nt < 2 then finish(false, string.format("walk: %d distinct sheet frames and %d distinct tiles while walking, want at least 2 each", nf, nt)) return end
      for t in pairs(wv_tiles) do
        if t < sbase or t >= sbase + scount then finish(false, string.format("walk: tile %d outside Sootling range %d+%d", t, sbase, scount)) return end
      end
      cpu_report = cpu_report .. string.format("; walk: clip WALK2 on %d frames, %d sheet frames, %d tiles", wv_seen, nf, nt)
    end
    if tick == WV_SETTLE + WV_WALK_FRAMES + WV_STOP_FRAMES then
      -- a computer flier may pop a balloon meanwhile: the breathing clip follows the balloon count then
      local bal = mem:read_u8(flow_addr + O_BAL)
      local want = ({ [0] = 9, [1] = 15, [2] = CLIP_BREATHE2 })[bal]
      if clip ~= want then finish(false, string.format("walk: after stopping the clip is %d with %d balloons, want %s", clip, bal, tostring(want))) return end
      cpu_report = cpu_report .. string.format("; stopped into breathing clip %d (%d balloons)", clip, bal)
      phase = "flap"; tick = 0
    end
    return
  elseif phase == "flap" then
    -- press for 2 frames, release for 4: eight edges
    local k = tick % 6
    abtn:set_value(k < 2 and 1 or 0)
    if k == 0 then flaps = flaps + 1 end
    tick = tick + 1
    min_y = math.min(min_y or fy, fy)
    if flaps > 8 and k == 5 then
      release()
      if min_y >= stand_y - 4 then
        finish(false, string.format("flier did not rise after flaps: stand y %.1f, min y %.1f", stand_y, min_y))
        return
      end
      phase = "ceiling"; tick = 0; ceil_min_y = nil; ceil0 = ceil_addr and mem:read_u32(ceil_addr) or nil
    end
    return
  elseif phase == "ceiling" then
    -- Top edge: flap up until the player meets the ceiling. The player's feet line is FLIER_CEILING_FEET_Y = 31
    -- (src/core/tuning.h), so with gum (half height 5.5) the centre stops at y 25.5 and the gum top at screen row 0.
    -- g_flier_ceiling_hits (flier_step bounce counter) must rise, so a compiled-out or unreachable path fails.
    if state ~= FLOW_PLAYING then phase = "ended" release() return end
    if not ceil_addr or not ceilrival_addr then finish(false, "missing BRAWL_CEIL_ADDR or BRAWL_CEILRIVAL_ADDR") return end
    if tick == 0 then
      -- flapping alone only holds an equilibrium near y 88: start the climb 15 px under the line, moving up 3 px per frame
      mem:write_u32(flow_addr + O_Y, 40 * 65536)
      mem:write_u32(flow_addr + O_VY, s32_to_u(-3 * 65536))
    end
    abtn:set_value(tick % 2 == 0 and 1 or 0)
    tick = tick + 1
    if mem:read_u8(flow_addr + O_BAL) > 0 then ceil_min_y = math.min(ceil_min_y or fy, fy) end
    if tick >= 60 then
      release()
      local hits = mem:read_u32(ceil_addr) - ceil0
      if not ceil_min_y then finish(false, "ceiling: player lost its gum before the ceiling was reached") return end
      if ceil_min_y < 25.5 - 0.01 then finish(false, string.format("ceiling: player y %.2f is above the ceiling line 25.5", ceil_min_y)) return end
      if ceil_min_y > 25.5 + 2 then finish(false, string.format("ceiling: player never reached the ceiling in %d frames: min y %.2f, want 25.5", tick, ceil_min_y)) return end
      if hits < 1 then finish(false, string.format("ceiling: g_flier_ceiling_hits did not rise (%d -> %d): the bounce path never ran", ceil0, ceil0 + hits)) return end
      cpu_report = cpu_report .. string.format("; ceiling: player min y %.2f (line 25.5), %d ceiling bounces in ROM, %d on the lowered computer line in total", ceil_min_y, hits, mem:read_u32(ceilrival_addr))
      phase = "flapview"; tick = 0
    end
    return
  elseif phase == "flapview" then
    if state ~= FLOW_PLAYING then phase = "ended" release() return end
    if not flapview_step() then return end
    -- test setup: the flap and ceiling phases leave the player over island 0 or the gap; the drive walks off the
    -- start island (0, R01) and falls into the water. Put back on island 0 at rest it cannot loop on another island (earlier layout: from island 5 it landed on island 2 and looped until the
    -- watchdog (thoughts/spot/2026-11-12-test-flier-hazard-regression.md). Put it back where it stood, at rest.
    mem:write_u32(flow_addr + O_X, s32_to_u(stand_x))
    mem:write_u32(flow_addr + O_Y, s32_to_u(stand_y))
    mem:write_u32(flow_addr + O_VX, 0)
    mem:write_u32(flow_addr + O_VY, 0)
    phase = "walk"; tick = 0
    return
  elseif phase == "walk" then
    -- a computer flier may pop the player on the way; the run then ends here and the end checks below still apply
    if state ~= FLOW_PLAYING then phase = "ended" release() return end
    -- off the middle island and back over the gap (shared driver, island edge read from the ROM stage table)
    drive()
    return
  end
  if phase == "ended" then
    release()
    local fstate = mem:read_u8(flow_addr + O_FSTATE)
    local steps = g32(O_STEPS) - steps0
    local frames = fc - play_fc0 - frozen -- PLAYING frames that step the flier (frozen round end and round start frames excluded)
    local over = mem:read_u8(flow_addr + O_OVER)
    if state ~= FLOW_GAME_OVER then finish(false, "flow state after play is " .. state .. ", want GAME_OVER (4)") return end
    if fstate < FL_DROWNED then finish(false, "flier state " .. fstate .. ", want DROWNED (3) or GONE (4)") return end
    local kill_y = g32(O_KILLY) / 65536   -- the line the game set for the strip shown; values pinned by hazard_kill_check.lua
    if fstate == FL_DROWNED and fy + 6 < kill_y then finish(false, string.format("flier y %.1f is not at the kill line %.1f", fy, kill_y)) return end
    if over ~= 1 then finish(false, "game.over not set") return end
    if steps < 100 or math.abs(frames - steps) > 3 then
      finish(false, string.format("sentinel: flier_steps %d vs game loop frames %d in PLAYING", steps, frames)) return
    end
    local blocked = blocked_addr and mem:read_u32(blocked_addr) or -1
    cpu_report = cpu_report .. string.format("; g_flier_pair_blocked %d (platform block, pop window and computer-never-pops are proven by host tests only, not in ROM)", blocked)
    finish(true, cpu_report .. "; " .. string.format("flier rose %.1f px after %d flaps, drowned at y %.1f, flow GAME_OVER, flier_steps %d of %d frames, score %d",
      stand_y - min_y, flaps - 1, fy, steps, frames, g32(O_SCORE)))
  end
end) if not ok_ then print('LUAERR ' .. tostring(err_)); finish(false, 'lua error: ' .. tostring(err_)) end end)
