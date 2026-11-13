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
local O_X = flay[6]
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
-- ROT1: the arena layout rotates per round (src/core/stage.c layouts). stage_platforms is a RAM copy of the current layout: four int16 x, y, w, h each.
local stage_addr = tonumber(os.getenv("BRAWL_STAGE_ADDR") or "", 16)
local HOME = "0,164,80,12 280,148,80,12" -- every layout of src/core/stage.c starts with the two home islands
local function layout_now()
  local t = {}
  for i = 0, 7 do t[#t + 1] = string.format("%d,%d,%d,%d", mem:read_i16(stage_addr + i * 8), mem:read_i16(stage_addr + i * 8 + 2), mem:read_i16(stage_addr + i * 8 + 4), mem:read_i16(stage_addr + i * 8 + 6)) end
  local text = table.concat(t, " ")
  if text:sub(1, #HOME) ~= HOME then return nil, text end
  return text
end
local lay_prev, lay_seen, lay_cur = nil, {}, nil
local st_fc, st_run, st_chg, st_chg_max, st_changes, st_lay = nil, 0, false, 0, 0, nil
local function g32(o) return mem:read_u32(flow_addr + o) end
local function put_feet(feet_px) mem:write_u32(flow_addr + O_Y, (feet_px * 65536 - HALF_H16) & 0xffffffff) end

local n, phase, phase_at, n_wait, fc0 = 0, "boot", 0, 0, nil
local covered, lines, plays, tick, kind, line = {}, {}, 0, 0, nil, nil
-- Death sound: the 68k sentinels g_sound_sent / g_sound_last (one command per frame) over the death of each kind. Fire sends sizzle and never hit; the other kinds never send sizzle.
local snd_ids = dofile("tests/mame/snd_ids.lua")
local A_SENT, A_LAST = tonumber(os.getenv("BRAWL_SENT_ADDR"), 16), tonumber(os.getenv("BRAWL_LAST_ADDR"), 16)
local snd_prev, snd_seen = nil, {}
local function snd_watch()
  local s = mem:read_u16(A_SENT)
  if snd_prev and s ~= snd_prev then local c = mem:read_u8(A_LAST); snd_seen[c] = (snd_seen[c] or 0) + 1 end
  snd_prev = s
end
local function snd_check()
  local sz, hit = snd_seen[snd_ids.SND_SFX_SIZZLE] or 0, snd_seen[snd_ids.SND_SFX_HIT] or 0
  if kind == 1 and (sz < 1 or hit > 0) then return string.format("fire death sent sizzle %d times, hit %d times (want sizzle >= 1, hit 0)", sz, hit) end
  if kind ~= 1 and sz > 0 then return string.format("%s death sent sizzle %d times (want 0)", NAMES[kind], sz) end
end
local overlap_kinds, overlap_verdict, first_frames = 0, 0, 0
local popped, popped_n, pf_splash, pf_checked = {}, 0, 0, false
local fall = nil   -- per play dead fall record, see phase "fall"
local fall_kinds, front_kinds, sign_kinds = 0, 0, 0
-- Splash sprites (src/sprite_slots.h SPLASH_SPRITE / SPLASH_COUNT, written out like the other spec numbers): live during a
-- liquid death, empty again once the animation (12 frames x 3 water / 4 lava ticks, +6 slack) has run, below the hazard slots.
local SPLASH_S, SPLASH_N, SPLASH_DONE = 113, 3, 54
local function s32(v) if v >= 0x80000000 then return v - 0x100000000 end return v end
local function scb3_h(slot) return (vram[0x8200 + slot] or 0) & 0x3f end
local function splash_live() for s_ = SPLASH_S, SPLASH_S + SPLASH_N - 1 do if scb3_h(s_) ~= 0 then return true end end return false end

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
  -- Relayout stall: Lua frames in a row where the main loop did not finish an iteration (g_frame_counter unchanged), for the runs that contain a layout change.
  if stage_addr then
    local lt = layout_now()
    if lt and st_lay and lt ~= st_lay then st_chg = true; st_changes = st_changes + 1 end
    if lt then st_lay = lt end
  end
  if fc == st_fc then st_run = st_run + 1
  else
    if st_chg then if st_run > st_chg_max then st_chg_max = st_run end; st_chg = false end
    st_run = 0
  end
  st_fc = fc

  if phase == "boot" then
    if fc ~= 0 then fc0 = fc0 or fc end
    if fc0 and fc - fc0 >= 30 and n > n_wait + 30 then phase = "coin"; phase_at = n; ss.begin(n) end
    return
  elseif phase == "coin" then
    -- one coin; one Start press begins the game (BG4; tests/mame/start_seq.lua)
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

  if state ~= FLOW_PLAYING and phase ~= "die" and phase ~= "fall" and phase ~= "popfall" then finish(false, "left PLAYING in phase " .. phase .. " (flier died early?) state " .. state .. " plays " .. plays .. " kind " .. tostring(kind) .. " fstate " .. mem:read_u8(flow_addr + O_FSTATE) .. string.format(" x %d y %d hk %d re %d,%d,%d", mem:read_u32(flow_addr + O_X) >> 16, mem:read_u32(flow_addr + O_Y) >> 16, hk, mem:read_u16(tonumber(os.getenv("BRAWL_RE_ADDR"), 16)), mem:read_u16(tonumber(os.getenv("BRAWL_RE_ADDR"), 16) + 2), mem:read_u16(tonumber(os.getenv("BRAWL_RE_ADDR"), 16) + 4))) return end

  if phase == "advance" then -- a poke won the round: wait for the next round's strip
    if hk ~= adv_from and hk < P_KINDS then phase = "sync"; tick = 0 end
    return
  end
  if phase == "sync" then
    if mem:read_u8(flow_addr + flay[13]) == 0 then tick = 0 return end -- match_start has not run: a new game's island reload can hold the main loop for frames
    if not rs.live() then tick = 0 return end -- play is frozen during the banner hold, the camera slide and ROUND nn / GO!
    tick = tick + 1
    if tick < 5 then return end
    if not stage_addr then finish(false, "missing BRAWL_STAGE_ADDR") return end
    do
      local k, text = layout_now()
      if not k then finish(false, "stage_platforms in RAM do not start with the home islands: " .. text) return end
      if lay_prev and k == lay_prev then finish(false, "layout " .. k .. " did not change after a won round") return end
      lay_prev = nil; lay_seen[k] = true; lay_cur = k
    end
    kind = hk
    if kind < P_KINDS and kind ~= ORDER[plays % 4 + 1] then lay_prev = lay_cur; rs.win(); adv_from = kind; phase = "advance"; return end
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
    -- x 184 is under no stage platform (islands span x 0..80 and 280..360 at the sides, the shelf is at y 108..120): the gum column above the feet must not overlap a solid, or the solids push the flier out of the kill line
    mem:write_u32(flow_addr + O_X, 184 * 65536)
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
    if kind >= 2 and not popped[kind] then
      -- a real popped fall: the last balloon gone, FALLING (2) from 40 px above the surface; the body must splash on crossing it (no DROWNED poke)
      popped[kind] = true
      mem:write_u8(flow_addr + O_BAL, 0); mem:write_u8(flow_addr + O_FSTATE, 2)
      put_feet(line - 40); mem:write_u32(flow_addr + O_VY, 0)
      phase = "popfall"; tick = 0; pf_splash = 0
      return
    end
    phase = "die"; tick = 0; snd_seen = {}
    put_feet(line); mem:write_u32(flow_addr + O_VY, 0)
    return
  elseif phase == "popfall" then
    tick = tick + 1
    if splash_live() then pf_splash = pf_splash + 1 end
    local fs = mem:read_u8(flow_addr + O_FSTATE)
    if tick == 2 and fs == FL_ALIVE then finish(false, NAMES[kind] .. ": popped FALLING poke did not stick (flier ALIVE again)") return end
    if tick > 900 then finish(false, NAMES[kind] .. ": flier never came back after the popped fall") return end
    if tick > 5 and fs == FL_GONE and not pf_checked then
      pf_checked = true
      if pf_splash < 8 then finish(false, string.format("%s: popped flier fell through the surface, splash live in only %d frames (want >= 8)", NAMES[kind], pf_splash)) return end
      popped_n = popped_n + 1
    end
    if pf_checked and state ~= FLOW_PLAYING then pf_checked = false; phase = "wait_end"; n_wait = n return end
    if pf_checked and fs == FL_ALIVE then pf_checked = false; phase = "sync"; tick = 0 end
    return
  elseif phase == "die" then
    tick = tick + 1; snd_watch()
    local fs = mem:read_u8(flow_addr + O_FSTATE)
    if fs == FL_DROWNED or fs > FL_DROWNED then
      covered[kind] = true; plays = plays + 1
      lines[#lines + 1] = string.format("%s line %d (alive at %d, dead at %d)", NAMES[kind], line, line - 1, line)
      phase = "fall"; tick = 0
      fall = { frames = 0, last_vy = nil, flips = 0, max_feet = 0, below = 0, behind = 0, front = 0, splash = 0, prev_feet = nil, prev_state = nil }
      return
    end
    if tick > 2 then finish(false, string.format("%s: feet put on the line %d but the flier state is %d after 2 frames (want DROWNED)", NAMES[kind], line, fs)) return end
  elseif phase == "fall" then
    tick = tick + 1; snd_watch()
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
        if kind >= 2 and fall.splash < 8 then finish(false, string.format("%s: splash sprites live in only %d frames of the death", NAMES[kind], fall.splash)) return end
        if fall.behind < 3 then finish(false, string.format("%s: only %d samples with the body in a hero slot below the hazard slots", NAMES[kind], fall.behind)) return end
      end
      do local bad = snd_check() if bad then finish(false, bad) return end end
      fall_kinds = fall_kinds + 1
      fall = nil
      local c = 0
      for _ in pairs(covered) do c = c + 1 end
      if c == P_KINDS then
        if overlap_kinds < P_KINDS - 1 then finish(false, "hero over strip checked for " .. overlap_kinds .. " kinds, want " .. (P_KINDS - 1)) return end
        if popped_n < 2 then finish(false, "popped fall splash checked for " .. popped_n .. " liquid kinds, want 2") return end
        local seen_n = 0
        for _ in pairs(lay_seen) do seen_n = seen_n + 1 end
        if seen_n < 2 then finish(false, "the rounds showed only one layout of the table") return end
        finish(true, "popped flier splashes in " .. popped_n .. " liquid kinds; layouts rotate (" .. seen_n .. " layouts seen, each won round changes it; " .. st_changes .. " layout changes, the main loop lost at most " .. st_chg_max .. " frames to one); kill lines in the real ROM: " .. table.concat(lines, "; ") .. "; hero slots " .. HERO .. ".." .. (HERO + HERO_N - 1) .. " draw behind hazard slot " .. HAZ .. ", overlap seen for " .. overlap_kinds .. " kinds, kill_y right on the first PLAYING frame for " .. first_frames .. " plays; dead fall for " .. fall_kinds .. " kinds: GONE only at feet " .. REMOVE_FEET .. " (sprite off screen), liquid bodies in hero slots below hazard slots " .. HAZ .. ".." .. (HAZ + HAZ_N - 1) .. ", spike body in dead-body slots " .. DEAD .. ".." .. (DEAD + DEAD_N - 1) .. " after " .. sign_kinds .. " bounce with one vy sign change")
        return
      end
      if plays >= 8 then finish(false, "kinds covered " .. c .. " of " .. P_KINDS .. " after " .. plays .. " plays") return end
      phase = "wait_end"
      return
    end
    -- DROWNED: the sprite is still being drawn, so it must be on screen
    if fall.prev_state == FL_DROWNED and feet - ART_H >= SCREEN_H then finish(false, string.format("%s: body still DROWNED with the sprite fully below the screen (feet %.1f)", NAMES[kind], feet)) return end
    fall.frames = fall.frames + 1
    if kind < 2 then
      if splash_live() then finish(false, NAMES[kind] .. ": a splash sprite is live for a non-liquid death") return end
    else
      if SPLASH_S + SPLASH_N > HAZ then finish(false, string.format("splash slots %d..%d not below hazard slot %d", SPLASH_S, SPLASH_S + SPLASH_N - 1, HAZ)) return end
      if splash_live() then fall.splash = fall.splash + 1 end
      if fall.frames > SPLASH_DONE and splash_live() then finish(false, string.format("%s: splash still live %d frames after the death", NAMES[kind], fall.frames)) return end
    end
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
