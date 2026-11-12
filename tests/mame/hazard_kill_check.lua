-- Hazard kill line reachability (make test-hazard-kill, build plan P6-4 and P6-5). Runs the real game for four plays in
-- a row (play N is checked in round N % 4 of its game, reached by winning rounds with a RAM poke: water, spikes, lava, fire). Per play:
--   0. kill_y equals the spec on the FIRST PLAYING frame seen (before the 5 frame sync wait);
--   1. sentinel: the strip is shown (g_hazard_kind, set by hazard.c start) and the game knows it: Game.hazard_kind equals
--      g_hazard_kind (proves game_set_hazard ran with the drawn kind), and the player's Flier.kill_y equals the spec line;
--   2. the built kill line of that kind (probe, from hazard_kind.h) equals the spec line;
--   3. the flier is put (RAM poke of y, vy 0, full balloons) with its feet 1 px above the line: it stays ALIVE for 3 frames;
--   4. P6-5, while it sits there: the hero slot numbers are lower than the hazard slot numbers (lower draws behind on Neo
--      Geo) and, where the sprite reaches into the strip (every kind but spikes, tip at the top line), the hero SCB3 and a
--      hazard bank SCB3 are both live, so the hero is drawn behind the strip;
--   5. the feet are put on the line: state DROWNED within 2 frames.
--   6. dead fall (phase "fall", from the DROWNED frame until the state is GONE): the body is never GONE while its sprite
--      is still on screen (GONE only once feet bottom >= FLIER_REMOVE_FEET_Y, i.e. feet - FLIER_ART_H >= SCREEN_H), and it is
--      still DROWNED well below the hazard surface line; liquids: the body slot (hero slots) is live, below the hazard slots
--      and the dead-body slots are empty, vy never goes negative; spikes: the dead-body slots (above every other range) are
--      live and the hero slot is empty from the first dead frame, vy changes sign exactly once (up at the tips, then down for
--      good) and the hop stays above the tips.
-- Spec numbers are written out here (not read from the build) so a changed knob fails: strip top 192, kill lines
-- spikes 192, fire 214, water 208, lava 206 (thoughts/spot/2026-11-10-hazard-surface-rows.md plus the 4 px dip).
-- Env: BRAWL_FLOW_ADDR, BRAWL_FRAME_ADDR, BRAWL_KIND_ADDR (g_hazard_kind), BRAWL_FLIER_LAYOUT (flier_probe.c),
-- BRAWL_KILL_LAYOUT (hazard_kill_probe.c), BRAWL_RESULT.
local flow_addr  = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local frame_addr = tonumber(os.getenv("BRAWL_FRAME_ADDR"), 16)
local kind_addr  = tonumber(os.getenv("BRAWL_KIND_ADDR"), 16)
local result     = os.getenv("BRAWL_RESULT")
local function nums(name) local t = {} for v in (os.getenv(name) or ""):gmatch("%d+") do t[#t + 1] = tonumber(v) end return t end
local flay, klay = nums("BRAWL_FLIER_LAYOUT"), nums("BRAWL_KILL_LAYOUT")
local O_STATE, O_Y, O_VY, O_FSTATE, O_BAL, O_GROUND = flay[1], flay[7], flay[9], flay[10], flay[11], flay[12]
local P_KINDS, P_SPIKES, P_FIRE, P_WATER, P_LAVA, P_TOP, HALF_H16, O_KILLY, O_GKIND, HERO, HERO_N, HAZ, COLS,
      HALF_NOBAL, REMOVE_FEET, ART_H, SCREEN_H, HAZ_N, DEAD, DEAD_N = table.unpack(klay)
local SPEC_TOP = 192
local SPEC = { [0] = 192, [1] = 214, [2] = 208, [3] = 206 }
local NAMES = { [0] = "spikes", [1] = "fire", [2] = "water", [3] = "lava" }
local ORDER = { 2, 0, 3, 1 } -- spec of the round order in one game (water, spikes, lava, fire); play N is checked in round N % 4
local FLOW_PLAYING, FL_ALIVE, FL_DROWNED, FL_GONE = 3, 0, 3, 4

local mem   = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, name)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname == name then return f end end
end
local coin  = field(":AUDIO_COIN", "Coin 1")
local start = field(":edge:joy:START", "1 Player Start")
local ss = dofile("tests/mame/start_seq.lua")(coin, start)

-- VRAM shadow through a write tap on the video port, as small_sootling_check.lua
local vram, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "hzkillvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then vram[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
  elseif r == 4 then vmod = data end
end)

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

local rs = dofile("tests/mame/round_skip.lua")(mem, flow_addr, flay) -- rs.win(): win the round by poke; rs.live(): no round end or round start text
local adv_from = nil
local function g32(o) return mem:read_u32(flow_addr + o) end
local function put_feet(feet_px) mem:write_u32(flow_addr + O_Y, (feet_px * 65536 - HALF_H16) & 0xffffffff) end

local n, phase, phase_at, n_wait, fc0 = 0, "boot", 0, 0, nil
local covered, lines, plays, tick, kind, line = {}, {}, 0, 0, nil, nil
local overlap_kinds, overlap_verdict, first_frames = 0, 0, 0
local fall = nil   -- per play dead fall record, see phase "fall"
local fall_kinds, front_kinds, sign_kinds = 0, 0, 0
local function s32(v) if v >= 0x80000000 then return v - 0x100000000 end return v end
local function scb3_h(slot) return (vram[0x8200 + slot] or 0) & 0x3f end

emu.register_frame_done(function() local ok_, err_ = pcall(function()
  if done then return end
  n = n + 1
  if n > 24000 then finish(false, "watchdog in phase " .. phase .. ", plays " .. plays) return end
  if not (coin and start and frame_addr and kind_addr and #klay == 20 and O_GROUND) then
    finish(false, "missing input field, address or probe layout") return
  end
  local state = mem:read_u8(flow_addr + flay[1])
  local fc = mem:read_u32(frame_addr)
  local hk = mem:read_u8(kind_addr)

  if phase == "boot" then
    if fc ~= 0 then fc0 = fc0 or fc end
    if fc0 and fc - fc0 >= 30 and n > n_wait + 30 then phase = "coin"; phase_at = n; ss.begin(n) end
    return
  elseif phase == "coin" then
    -- one coin; first Start press opens the title mode select, the second begins the game (BG4; tests/mame/start_seq.lua)
    ss.step(n, false)
    if state == FLOW_PLAYING and hk ~= 0xFF then
      -- First frame of PLAYING seen (the strip is already shown): the line must be right NOW, not after a sync wait.
      start:set_value(0); phase = "sync"; tick = 0
      local k0 = hk
      if k0 < P_KINDS then
        local ky0 = g32(O_KILLY) >> 16
        if ky0 ~= SPEC[k0] then finish(false, string.format("%s flier kill_y is %d on the FIRST PLAYING frame, spec %d", NAMES[k0], ky0, SPEC[k0])) return end
        first_frames = first_frames + 1
      end
    end
    return
  elseif phase == "wait_end" then
    if hk == 0xFF and state ~= FLOW_PLAYING then phase = "boot"; n_wait = n end
    return
  end

  if state ~= FLOW_PLAYING and phase ~= "die" and phase ~= "fall" then finish(false, "left PLAYING in phase " .. phase .. " (flier died early?)") return end

  if phase == "advance" then -- a poke won the round: wait for the next round's strip
    if hk ~= adv_from and hk < P_KINDS then phase = "sync"; tick = 0 end
    return
  end
  if phase == "sync" then
    if not rs.live() then tick = 0 return end -- play is frozen during the banner hold, the camera slide and ROUND nn / GO!
    tick = tick + 1
    if tick < 5 then return end
    kind = hk
    if kind < P_KINDS and kind ~= ORDER[plays % 4 + 1] then rs.win(); adv_from = kind; phase = "advance"; return end
    if kind >= P_KINDS then finish(false, "g_hazard_kind " .. kind .. " is not a kind") return end
    local gk = mem:read_u8(flow_addr + O_GKIND)
    if gk ~= kind then finish(false, string.format("Game.hazard_kind %d but the strip shows kind %d (%s): game_set_hazard not wired", gk, kind, NAMES[kind])) return end
    line = SPEC[kind]
    local built = ({ [0] = P_SPIKES, P_FIRE, P_WATER, P_LAVA })[kind]
    if P_TOP ~= SPEC_TOP then finish(false, string.format("built strip top %d, spec %d", P_TOP, SPEC_TOP)) return end
    if built ~= line then finish(false, string.format("%s kill line built as %d, spec %d", NAMES[kind], built, line)) return end
    local ky = g32(O_KILLY) >> 16
    if ky ~= line then finish(false, string.format("%s flier kill_y is %d in the running game, spec %d", NAMES[kind], ky, line)) return end
    if (HERO + HERO_N - 1) >= HAZ then finish(false, string.format("hero slots %d..%d are not below hazard slot %d: hero would draw in front of the strip", HERO, HERO + HERO_N - 1, HAZ)) return end
    mem:write_u8(flow_addr + O_BAL, mem:read_u8(flow_addr + O_BAL) < 2 and 2 or mem:read_u8(flow_addr + O_BAL))
    phase = "hold"; tick = 0
    put_feet(line - 1); mem:write_u32(flow_addr + O_VY, 0); mem:write_u8(flow_addr + O_GROUND, 0)
    return
  elseif phase == "hold" then
    tick = tick + 1
    local fy = (g32(O_Y) + HALF_H16) / 65536
    if mem:read_u8(flow_addr + O_FSTATE) ~= FL_ALIVE then finish(false, string.format("%s: flier not ALIVE with feet at %.2f, 1 px above the line %d", NAMES[kind], fy, line)) return end
    if fy >= line or fy < line - 1.5 then finish(false, string.format("%s: feet at %.2f, want within [%.1f, %d)", NAMES[kind], fy, line - 1.5, line)) return end
    -- slot order against the live sprites (P6-5). The strip's head SCB3 word is written by the bank swap (hazard.c arms it
    -- at the play start, the first swap comes at the next step boundary), so hold the flier until a bank is live.
    local w3 = vram[0x8200 + HERO] or 0
    local h = w3 & 0x3f
    local haz_live = ((vram[0x8200 + HAZ] or 0) & 0x3f) ~= 0 or ((vram[0x8200 + HAZ + COLS] or 0) & 0x3f) ~= 0
    -- A flier under spawn protection blinks (flier_view_visible), so the hero slot can be empty on one frame: keep holding until it is drawn; still a failure if it never is within 600 ticks.
    if tick < 3 or (kind ~= 0 and (not haz_live or h == 0) and tick < 600) then
      put_feet(line - 1); mem:write_u32(flow_addr + O_VY, 0)
      return
    end
    local bottom = ((496 - (w3 >> 7)) & 0x1ff) + 16 * h
    if kind ~= 0 then
      if h == 0 then finish(false, string.format("%s: hero SCB3 height 0 (not drawn) with the feet at the strip", NAMES[kind])) return end
      if not haz_live then finish(false, string.format("%s: no hazard bank SCB3 live", NAMES[kind])) return end
      if bottom <= SPEC_TOP then finish(false, string.format("%s: hero sprite bottom %d does not reach the strip top %d (overlap check vacuous)", NAMES[kind], bottom, SPEC_TOP)) return end
      overlap_kinds = overlap_kinds + 1
    end
    phase = "die"; tick = 0
    put_feet(line); mem:write_u32(flow_addr + O_VY, 0)
    return
  elseif phase == "die" then
    tick = tick + 1
    local fs = mem:read_u8(flow_addr + O_FSTATE)
    if fs == FL_DROWNED or fs > FL_DROWNED then
      covered[kind] = true; plays = plays + 1
      lines[#lines + 1] = string.format("%s line %d (alive at %d, dead at %d)", NAMES[kind], line, line - 1, line)
      phase = "fall"; tick = 0
      fall = { frames = 0, last_vy = nil, flips = 0, max_feet = 0, below = 0, behind = 0, front = 0, prev_feet = nil, prev_state = nil }
      return
    end
    if tick > 2 then finish(false, string.format("%s: feet put on the line %d but the flier state is %d after 2 frames (want DROWNED)", NAMES[kind], line, fs)) return end
  elseif phase == "fall" then
    tick = tick + 1
    local fs = mem:read_u8(flow_addr + O_FSTATE)
    local feet = (g32(O_Y) + HALF_NOBAL) / 65536
    local vy = s32(g32(O_VY))
    local solid = kind == 0
    if tick > 400 then finish(false, string.format("%s: dead body never GONE after 400 frames (feet %.1f, state %d)", NAMES[kind], feet, fs)) return end
    if fs ~= FL_DROWNED and fs ~= FL_GONE then finish(false, string.format("%s: dead fall left DROWNED for state %d at feet %.1f", NAMES[kind], fs, feet)) return end
    if fs == FL_GONE then
      -- GONE only when the whole sprite is below the screen: the frame before it was still on screen and this step took the feet to REMOVE_FEET
      if feet < REMOVE_FEET or feet - ART_H < SCREEN_H then finish(false, string.format("%s: GONE with feet %.1f, sprite top %.1f still above screen bottom %d (feet must reach %d)", NAMES[kind], feet, feet - ART_H, SCREEN_H, REMOVE_FEET)) return end
      if not fall.prev_feet or fall.prev_feet >= REMOVE_FEET then finish(false, string.format("%s: GONE one frame after feet %s, which is already past %d (vanished late or never seen on screen)", NAMES[kind], tostring(fall.prev_feet), REMOVE_FEET)) return end
      if fall.max_feet <= line + 8 then finish(false, string.format("%s: body gone before its feet passed the surface line %d by 8 px (max feet %.1f)", NAMES[kind], line, fall.max_feet)) return end
      if fall.below < 3 then finish(false, string.format("%s: only %d slot samples below the surface line", NAMES[kind], fall.below)) return end
      if solid then
        if fall.flips ~= 1 then finish(false, string.format("spikes: vy changed sign %d times, want exactly 1 (bounce at the tips, then fall on)", fall.flips)) return end
        if fall.front < 3 then finish(false, string.format("spikes: only %d samples with the body in the dead-body slots %d..%d", fall.front, DEAD, DEAD + DEAD_N - 1)) return end
        sign_kinds = sign_kinds + 1; front_kinds = front_kinds + 1
      else
        if fall.flips ~= 0 then finish(false, string.format("%s: vy changed sign %d times, a liquid body only falls", NAMES[kind], fall.flips)) return end
        if fall.behind < 3 then finish(false, string.format("%s: only %d samples with the body in a hero slot below the hazard slots", NAMES[kind], fall.behind)) return end
      end
      fall_kinds = fall_kinds + 1
      fall = nil
      local c = 0
      for _ in pairs(covered) do c = c + 1 end
      if c == P_KINDS then
        if overlap_kinds < P_KINDS - 1 then finish(false, "hero over strip checked for " .. overlap_kinds .. " kinds, want " .. (P_KINDS - 1)) return end
        finish(true, "kill lines in the real ROM: " .. table.concat(lines, "; ") .. "; hero slots " .. HERO .. ".." .. (HERO + HERO_N - 1) .. " draw behind hazard slot " .. HAZ .. ", overlap seen for " .. overlap_kinds .. " kinds, kill_y right on the first PLAYING frame for " .. first_frames .. " plays; dead fall for " .. fall_kinds .. " kinds: GONE only at feet " .. REMOVE_FEET .. " (sprite off screen), liquid bodies in hero slots below hazard slots " .. HAZ .. ".." .. (HAZ + HAZ_N - 1) .. ", spike body in dead-body slots " .. DEAD .. ".." .. (DEAD + DEAD_N - 1) .. " after " .. sign_kinds .. " bounce with one vy sign change")
        return
      end
      if plays >= 8 then finish(false, "kinds covered " .. c .. " of " .. P_KINDS .. " after " .. plays .. " plays") return end
      phase = "wait_end"
      return
    end
    -- DROWNED: the sprite is still being drawn, so it must be on screen
    if fall.prev_state == FL_DROWNED and feet - ART_H >= SCREEN_H then finish(false, string.format("%s: body still DROWNED with the sprite fully below the screen (feet %.1f)", NAMES[kind], feet)) return end
    fall.frames = fall.frames + 1
    fall.prev_feet, fall.prev_state = feet, fs
    if feet > fall.max_feet then fall.max_feet = feet end
    if vy ~= 0 then
      if fall.last_vy and ((vy < 0) ~= (fall.last_vy < 0)) then fall.flips = fall.flips + 1 end
      fall.last_vy = vy
    end
    if solid then
      if fall.frames == 1 and vy >= 0 then finish(false, string.format("spikes: first dead frame vy %d, want upward (the bounce at the tips)", vy)) return end
      if vy < 0 and feet > line + 0.01 then finish(false, string.format("spikes: moving up with feet %.2f below the tips %d", feet, line)) return end
    elseif vy < 0 then finish(false, string.format("%s: dead body moves up (vy %d)", NAMES[kind], vy)) return end
    -- slot samples (2 frames after the death for the draw to catch up), body on screen and below the surface line
    if fall.frames > 2 and feet > line + 3 and feet - ART_H < SCREEN_H - 2 then
      fall.below = fall.below + 1
      local hero_h, dead_h = scb3_h(HERO), 0
      for s_ = DEAD, DEAD + DEAD_N - 1 do if scb3_h(s_) ~= 0 then dead_h = dead_h + 1 end end
      if solid then
        if hero_h ~= 0 then finish(false, string.format("spikes: after the bounce the hero slot %d is still drawn (it draws behind the spikes), want the dead-body slots", HERO)) return end
        if dead_h == 0 then finish(false, string.format("spikes: after the bounce no dead-body slot %d..%d is live (body would be behind the spike art)", DEAD, DEAD + DEAD_N - 1)) return end
        if DEAD < HAZ + HAZ_N then finish(false, string.format("dead-body slot %d is not above the hazard slots %d..%d", DEAD, HAZ, HAZ + HAZ_N - 1)) return end
        fall.front = fall.front + 1
      else
        if hero_h == 0 then finish(false, string.format("%s: body below the surface (feet %.1f) but the hero slot %d is empty: vanished early", NAMES[kind], feet, HERO)) return end
        if dead_h ~= 0 then finish(false, string.format("%s: a dead-body slot is live for a liquid death (it would draw in front of the liquid)", NAMES[kind])) return end
        if HERO + HERO_N - 1 >= HAZ then finish(false, string.format("hero slots %d..%d not below hazard slot %d", HERO, HERO + HERO_N - 1, HAZ)) return end
        fall.behind = fall.behind + 1
      end
    end
  end
end) if not ok_ then print("BRAWL_TEST ERROR " .. tostring(err_)); finish(false, "Lua error: " .. tostring(err_)) end end)
