-- Hazard strip proof (make test-hazard, plan 2026-11-10-neo-geo-graphics-max.md G3). Runs the real game and plays four matches in a row (hazards 0..3: spikes, fire, water, lava), each checked with the same rules. Per match: starts the
-- match and watches the strip over a window of frames:
--   1. Strip lines: the SCB3 head word of the shown bank decodes to y 192, height 2 tiles; the pixels of the strip
--      lines change, and every changing pixel in the band around them lies on screen lines 192..223.
--   2. Animation: the hash of the strip pixels takes 16 distinct values (bank 0 steps 0..7, bank 1 steps 8..15), in a
--      repeating period-16 order, each held exactly frames-per-step frames (a bank swap glitch would be a short run).
--   3. Speed: the live g_autoanim_frames equals the active hazard's entry in HAZARD_TABLE_STEP_FRAMES and the LSPC
--      counter (REG_LSPCMODE bits 2..0) steps once per that many frames.
--   4. Writes: during the window the CPU writes ZERO SCB1 words of the hazard slots and no SCB2/SCB4 word; SCB3 is
--      written only by the bank swap (2 words per swap, swaps counted by g_swap_count). No VRAM or palette register
--      write at all lands outside vblank (all frames after the settle frame).
--   5. Palette: the hazard palettes sit in palette RAM below slot 256 and g_pal_words_frame_max <= PAL_MAX.
--   6. Idle speed: after each match (hazard kind back to 0xFF) g_autoanim_frames equals ISLAND_STEP_FRAMES (BRAWL_ISLAND_STEP), the island baseline.
-- Env: BRAWL_ISLAND_STEP, BRAWL_FLOW_ADDR, BRAWL_HIT_LAYOUT, BRAWL_HAZARD_LAYOUT (hazard_probe.c), BRAWL_FLIER_LAYOUT (flier_probe.c, to end a match), BRAWL_HAZARD_STEPS (frames per step of
-- each hazard), BRAWL_KIND_ADDR, BRAWL_SPEED_ADDR, BRAWL_SWAPS_ADDR, BRAWL_MATCHES_ADDR, BRAWL_PALMAX_ADDR, BRAWL_RESULT.
local result = os.getenv("BRAWL_RESULT")
local function nums(name) local t = {} for v in (os.getenv(name) or ""):gmatch("%d+") do t[#t + 1] = tonumber(v) end return t end
local lay, steps_tab, hit = nums("BRAWL_HAZARD_LAYOUT"), nums("BRAWL_HAZARD_STEPS"), nums("BRAWL_HIT_LAYOUT")
local var_tab = nums("BRAWL_HAZARD_VARIANTS") -- tile variants per kind (fire: A B C)
local HS, COLS, PAL0, NPAL, ROWS, STRIP_Y = lay[1], lay[2], lay[3], lay[4], lay[5], lay[6]
local O_STATE, STATE_PLAYING = hit[1], 3
local function addr(n) return tonumber(os.getenv(n), 16) end
local flow_addr, kind_addr, speed_addr, swaps_addr, matches_addr, palmax_addr =
  addr("BRAWL_FLOW_ADDR"), addr("BRAWL_KIND_ADDR"), addr("BRAWL_SPEED_ADDR"), addr("BRAWL_SWAPS_ADDR"), addr("BRAWL_MATCHES_ADDR"), addr("BRAWL_PALMAX_ADDR")
local X_OFF, Y_OFF = 28, 16 -- screen:pixel origin of the visible area (as in autoanim_check.lua)
local STRIP_W = 384 -- the strip is the arena wide (24 sprite columns) and scrolls with the world
local VIEW_W = 320 -- pixels the screen shows; the pixel hashes cover these
local PAL_MAX = 112 -- palette words per flush: init loads fix, city, soot, obstacle and the 4 hazard palettes; measured 111 (see notes)
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
local rbtn  = field(":edge:joy:JOY1", "P1 Right")
local lbtn  = field(":edge:joy:JOY1", "P1 Left")
local abtn  = field(":edge:joy:JOY1", "P1 A")
local flay  = nums("BRAWL_FLIER_LAYOUT")
local new_drive = function() return dofile("tests/mame/flier_drive.lua")(mem, flow_addr, flay, abtn, lbtn, rbtn) end
local drive = new_drive() -- walks the flier off the island and drowns it, which ends a match (tests/mame/flier_drive.lua)
local function finish(ok, msg)
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

local SETTLE = 40
local n, watching, n_wait = 0, false, 0
local vram, vaddr, vmod = {}, 0, 1
local scb1_w, scb24_w, scb3_w, other_w, bad_vram, total = 0, 0, 0, 0, 0, 0
local to_end_in_vblank = function()
  return screen:time_until_vblank_end():as_double() < screen:time_until_vblank_start():as_double()
end
local H0, H1 = 0x8200 + HS, 0x8200 + HS + COLS
tap_vram = mem:install_write_tap(0x3c0000, 0x3c000f, "hz", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 4 then vmod = data
  elseif r == 2 or r == 6 and false then
    vram[vaddr] = data
    if n > SETTLE and not to_end_in_vblank() then bad_vram = bad_vram + 1 end
    if n > SETTLE then total = total + 1 end
    if watching then
      if vaddr < 0x7000 and (vaddr >> 6) >= HS and (vaddr >> 6) < HS + 2 * COLS then scb1_w = scb1_w + 1
      elseif vaddr == H0 or vaddr == H1 then scb3_w = scb3_w + 1
      elseif (vaddr >= 0x8000 + HS and vaddr < 0x8000 + HS + 2 * COLS) or (vaddr >= 0x8400 + HS and vaddr < 0x8400 + HS + 2 * COLS) then scb24_w = scb24_w + 1
      elseif vaddr >= 0x8200 + HS and vaddr < 0x8200 + HS + 2 * COLS then other_w = other_w + 1 end
    end
    vaddr = (vaddr + vmod) & 0xffff
  end
end)
tap_pal = mem:install_write_tap(0x400000, 0x401fff, "hzp", function(offset, data, mask)
  if n > SETTLE and not to_end_in_vblank() then bad_vram = bad_vram + 1 end
end)

local function strip_hash()
  local s = 0
  for y = STRIP_Y + Y_OFF, STRIP_Y + 16 * ROWS - 1 + Y_OFF, 2 do
    for x = X_OFF, X_OFF + VIEW_W - 1, 3 do
      s = (s * 31 + (screen:pixel(x, y) & 0xffffff)) % 4294967291
    end
  end
  return s
end
-- all pixels of the band, lines 176..239 (rows by y), to find which lines change
local function band()
  local t = {}
  for y = 176, 239 do
    local s = 0
    for x = X_OFF, X_OFF + VIEW_W - 1, 4 do s = (s * 31 + (screen:pixel(x, y + Y_OFF) & 0xffffff)) % 4294967291 end
    t[y] = s
  end
  return t
end

local ISLAND_STEP = tonumber(os.getenv("BRAWL_ISLAND_STEP")) -- ISLAND_STEP_FRAMES: the counter speed whenever no hazard runs (plan I8)
local idle_checks, idle_bad = 0, 0 -- samples of g_autoanim_frames while no hazard runs, and how many differ from ISLAND_STEP
local KINDS = 4 -- spikes 0, fire 1, water 2, lava 3: match N shows hazard N % 4, so four matches in a row walk all of them
local phase, phase_at, START_AT, WINDOW, SPEED, KIND = "boot", 0, nil, nil, nil, nil
local hashes, prev_band, rows_changed, prev_c, ctr_steps, swaps0 = {}, nil, {}, nil, 0, 0
local want, lines, failed = 0, {}, false -- the kind this match must show; one verdict line per kind
-- every counter of one kind's window starts at zero; the write counters start here too so each kind also covers the
-- transition into its match (title, coin, start) with the same "no write outside vblank" rule
local function reset_kind()
  hashes, prev_band, rows_changed, prev_c, ctr_steps, swaps0 = {}, nil, {}, nil, 0, 0
  scb1_w, scb24_w, scb3_w, other_w, bad_vram, total = 0, 0, 0, 0, 0, 0
  START_AT, phase = nil, "wait_end"
  drive = new_drive()
end
emu.register_frame_done(function()
  n = n + 1
  if not START_AT then
    if phase == "wait_end" then -- the previous match must be over (strip hidden) before the next coin and start
      if mem:read_u8(kind_addr) == 0xFF then
        idle_checks = idle_checks + 1
        if mem:read_u8(speed_addr) ~= ISLAND_STEP then idle_bad = idle_bad + 1 end
        phase = "boot"; n_wait = n
        abtn:set_value(0); rbtn:set_value(0); lbtn:set_value(0)
      elseif mem:read_u8(flow_addr + O_STATE) == STATE_PLAYING then drive() end
      return
    end
    if mem:read_u8(flow_addr + O_STATE) == STATE_PLAYING then
      start:set_value(0); START_AT = n + 30
    else
      if n > math.max(300, n_wait + 30) and phase == "boot" then phase = "coin"; phase_at = n; coin:set_value(1) end
      if phase == "coin" and n == phase_at + 15 then coin:set_value(0) end
      if phase == "coin" and n >= phase_at + 40 then phase = "start"; phase_at = n; start:set_value(1) end
      -- A ranked score of the previous match opens the name entry and the BIOS-less attract loop takes a while to come back:
      -- pulse start every 60 frames until the match begins (the press that ends name entry is not the one that starts a match).
      if phase == "start" then
        local k = (n - phase_at) % 60
        if k == 15 then start:set_value(0) elseif k == 0 then start:set_value(1) end
      end
    end
    return
  end
  if n < START_AT then return end
  if n == START_AT then
    SPEED, KIND = mem:read_u8(speed_addr), mem:read_u8(kind_addr)
    WINDOW = 16 * SPEED * 2 + 8
    swaps0 = mem:read_u16(swaps_addr)
    watching = true
  end
  if n > START_AT + WINDOW then
    watching = false
    local swaps = mem:read_u16(swaps_addr) - swaps0
    -- runs of equal hashes
    local runs = {}
    for i, h in ipairs(hashes) do
      if #runs > 0 and runs[#runs].h == h then runs[#runs].len = runs[#runs].len + 1 else runs[#runs + 1] = { h = h, len = 1 } end
    end
    -- the first run is the counter finishing the step length it had before the strip took it over: not counted
    local distinct, set = 0, {}
    for ri, r in ipairs(runs) do if ri > 1 and not set[r.h] then set[r.h] = true; distinct = distinct + 1 end end
    local bad_runs, periodic = 0, true
    for i = 2, #runs - 1 do if runs[i].len ~= SPEED then bad_runs = bad_runs + 1 end end
    for i = 2, #runs - 16 do if runs[i].h ~= runs[i + 16].h then periodic = false end end
    local rmin, rmax = 999, -1
    for y in pairs(rows_changed) do if y < rmin then rmin = y end if y > rmax then rmax = y end end
    -- shown head word: y and height
    local w0, w1 = vram[H0] or 0, vram[H1] or 0
    local shown = (w0 ~= 0) and w0 or w1
    local sy, sh = (496 - (shown >> 7)) & 0x1ff, shown & 0x3f
    local expected_speed = steps_tab[KIND + 1]
    -- reachability of the variants: SCB1 of bank 0 (written once at the match start) holds one tile list per group of 4
    -- sprite columns; the strip cycles through variant groups, so the number of distinct lists is the kind's variant
    -- count (fire: 3, so tile C is referenced), and group g repeats group g % nv (fire A B C A B C, lava A B A B A B: the pattern repeats with a period that divides 384 px, so the wrap seam is a tile boundary)
    local nv, sigs, nsig, seen = var_tab[KIND + 1], {}, 0, {}
    for g = 0, STRIP_W // 64 - 1 do
      local t = {}
      for c = 0, 3 do for r = 0, ROWS - 1 do
        local a = ((HS + g * 4 + c) << 6) + 2 * r
        t[#t + 1] = (vram[a] or 0) .. ":" .. ((vram[a + 1] or 0) >> 4)
      end end
      sigs[g] = table.concat(t, ",")
      if not seen[sigs[g]] then seen[sigs[g]] = true; nsig = nsig + 1 end
    end
    local var_ok = nsig == nv
    for g = 0, STRIP_W // 64 - 1 do if sigs[g] ~= sigs[g % nv] then var_ok = false end end
    local pal_ok = PAL0 + NPAL <= 256
    for p = 0, NPAL - 1 do
      local nz = 0
      for i = 1, 15 do if mem:read_u16(0x400000 + ((PAL0 + p) * 16 + i) * 2) ~= 0 then nz = nz + 1 end end
      if nz < 8 then pal_ok = false end
    end
    local palmax = mem:read_u16(palmax_addr)
    local ok = KIND == want and mem:read_u16(matches_addr) == want + 1 and SPEED == expected_speed
      and scb1_w == 0 and scb24_w == 0 and other_w == 0 and scb3_w == 2 * swaps and swaps >= WINDOW // (8 * SPEED) - 1
      and bad_vram == 0 and total > 0 and var_ok
      and distinct == 16 and bad_runs == 0 and periodic
      and sy == STRIP_Y and sh == ROWS and rmin >= STRIP_Y and rmax <= STRIP_Y + 16 * ROWS - 1
      and math.abs(ctr_steps - WINDOW // SPEED) <= 1 and pal_ok and palmax <= PAL_MAX
    local line = string.format("kind %d speed %d (table %d), window %d frames, strip y %d height %d, changing lines %d..%d (want %d..%d), distinct frames %d (want 16), runs %d with %d off length (want 0) periodic %s, counter steps %d (want %d +-1), swaps %d, CPU writes: SCB1 %d SCB2/4 %d other SCB3 %d (want 0) head SCB3 %d (want %d), writes outside vblank %d of %d (want 0), palette ok %s, palette words per flush max %d (limit %d), tile variants in SCB1 %d (table %d)",
      KIND, SPEED, expected_speed or -1, WINDOW, sy, sh, rmin, rmax, STRIP_Y, STRIP_Y + 16 * ROWS - 1, distinct, #runs, bad_runs, tostring(periodic), ctr_steps, WINDOW // SPEED, swaps, scb1_w, scb24_w, other_w, scb3_w, 2 * swaps, bad_vram, total, tostring(pal_ok), palmax, PAL_MAX, nsig, nv or -1)
    lines[#lines + 1] = (ok and "[kind " or "[kind ") .. want .. (ok and " PASS] " or " FAIL] ") .. line
    if not ok then failed = true end
    want = want + 1
    if idle_bad > 0 or (want > 1 and idle_checks == 0) then
      failed = true
      lines[#lines + 1] = string.format("FAIL idle speed: %d of %d idle samples differ from ISLAND_STEP_FRAMES %d", idle_bad, idle_checks, ISLAND_STEP)
    end
    if failed or want == KINDS then
      finish(not failed, string.format("%d of %d hazard kinds driven\n%s", want, KINDS, table.concat(lines, "\n")))
    else
      reset_kind()
    end
    return
  end
  local c = mem:read_u16(0x3c0006) & 7
  if prev_c and c ~= prev_c then ctr_steps = ctr_steps + 1 end
  prev_c = c
  hashes[#hashes + 1] = strip_hash()
  local b = band()
  if prev_band then for y = 176, 239 do if b[y] ~= prev_band[y] then rows_changed[y] = true end end end
  prev_band = b
end)
