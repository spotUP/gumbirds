-- Hazard kill line reachability (make test-hazard-kill, build plan P6-4 and P6-5). Runs the real game for four plays in
-- a row (match N shows hazard N % 4: spikes, fire, water, lava; the same rotation test-hazard walks). Per play:
--   0. kill_y equals the spec on the FIRST PLAYING frame seen (before the 5 frame sync wait);
--   1. sentinel: the strip is shown (g_hazard_kind, set by hazard.c start) and the game knows it: Game.hazard_kind equals
--      g_hazard_kind (proves game_set_hazard ran with the drawn kind), and the player's Flier.kill_y equals the spec line;
--   2. the built kill line of that kind (probe, from hazard_kind.h) equals the spec line;
--   3. the flier is put (RAM poke of y, vy 0, full balloons) with its feet 1 px above the line: it stays ALIVE for 3 frames;
--   4. P6-5, while it sits there: the hero slot numbers are lower than the hazard slot numbers (lower draws behind on Neo
--      Geo) and, where the sprite reaches into the strip (every kind but spikes, tip at the top line), the hero SCB3 and a
--      hazard bank SCB3 are both live, so the hero is drawn behind the strip;
--   5. the feet are put on the line: state DROWNED within 2 frames.
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
local P_KINDS, P_SPIKES, P_FIRE, P_WATER, P_LAVA, P_TOP, HALF_H16, O_KILLY, O_GKIND, HERO, HERO_N, HAZ, COLS = table.unpack(klay)
local SPEC_TOP = 192
local SPEC = { [0] = 192, [1] = 214, [2] = 208, [3] = 206 }
local NAMES = { [0] = "spikes", [1] = "fire", [2] = "water", [3] = "lava" }
local FLOW_PLAYING, FL_ALIVE, FL_DROWNED = 3, 0, 3

local mem   = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, name)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname == name then return f end end
end
local coin  = field(":AUDIO_COIN", "Coin 1")
local start = field(":edge:joy:START", "1 Player Start")

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

local function g32(o) return mem:read_u32(flow_addr + o) end
local function put_feet(feet_px) mem:write_u32(flow_addr + O_Y, (feet_px * 65536 - HALF_H16) & 0xffffffff) end

local n, phase, phase_at, n_wait, fc0 = 0, "boot", 0, 0, nil
local covered, lines, plays, tick, kind, line = {}, {}, 0, 0, nil, nil
local overlap_kinds, overlap_verdict, first_frames = 0, 0, 0

emu.register_frame_done(function() local ok_, err_ = pcall(function()
  if done then return end
  n = n + 1
  if n > 12000 then finish(false, "watchdog in phase " .. phase .. ", plays " .. plays) return end
  if not (coin and start and frame_addr and kind_addr and #klay == 13 and O_GROUND) then
    finish(false, "missing input field, address or probe layout") return
  end
  local state = mem:read_u8(flow_addr + flay[1])
  local fc = mem:read_u32(frame_addr)
  local hk = mem:read_u8(kind_addr)

  if phase == "boot" then
    if fc ~= 0 then fc0 = fc0 or fc end
    if fc0 and fc - fc0 >= 30 and n > n_wait + 30 then phase = "coin"; phase_at = n; coin:set_value(1) end
    return
  elseif phase == "coin" then
    if n == phase_at + 15 then coin:set_value(0) end
    if n >= phase_at + 40 then phase = "start"; phase_at = n; start:set_value(1) end
    return
  elseif phase == "start" then
    local k = (n - phase_at) % 60   -- pulse start until the play begins (a name entry screen would eat one press)
    if k == 15 then start:set_value(0) elseif k == 0 then start:set_value(1) end
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

  if state ~= FLOW_PLAYING and phase ~= "die" then finish(false, "left PLAYING in phase " .. phase .. " (flier died early?)") return end

  if phase == "sync" then
    tick = tick + 1
    if tick < 5 then return end
    kind = hk
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
    if tick < 3 or (kind ~= 0 and not haz_live and tick < 600) then
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
      local c = 0
      for _ in pairs(covered) do c = c + 1 end
      if c == P_KINDS then
        if overlap_kinds < P_KINDS - 1 then finish(false, "hero over strip checked for " .. overlap_kinds .. " kinds, want " .. (P_KINDS - 1)) return end
        finish(true, "kill lines in the real ROM: " .. table.concat(lines, "; ") .. "; hero slots " .. HERO .. ".." .. (HERO + HERO_N - 1) .. " draw behind hazard slot " .. HAZ .. ", overlap seen for " .. overlap_kinds .. " kinds, kill_y right on the first PLAYING frame for " .. first_frames .. " plays")
        return
      end
      if plays >= 8 then finish(false, "kinds covered " .. c .. " of " .. P_KINDS .. " after " .. plays .. " plays") return end
      phase = "wait_end"
      return
    end
    if tick > 2 then finish(false, string.format("%s: feet put on the line %d but the flier state is %d after 2 frames (want DROWNED)", NAMES[kind], line, fs)) return end
  end
end) if not ok_ then print("BRAWL_TEST ERROR " .. tostring(err_)); finish(false, "Lua error: " .. tostring(err_)) end end)
