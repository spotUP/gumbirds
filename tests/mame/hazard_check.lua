-- Hazard strip proof (make test-hazard, plan 2026-11-10-neo-geo-graphics-max.md G3). Runs the real game, starts the
-- first match (hazard 0 = spikes) and watches the strip over a window of frames:
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
-- Env: BRAWL_FLOW_ADDR, BRAWL_HIT_LAYOUT, BRAWL_HAZARD_LAYOUT (hazard_probe.c), BRAWL_HAZARD_STEPS (frames per step of
-- each hazard), BRAWL_KIND_ADDR, BRAWL_SPEED_ADDR, BRAWL_SWAPS_ADDR, BRAWL_MATCHES_ADDR, BRAWL_PALMAX_ADDR, BRAWL_RESULT.
local result = os.getenv("BRAWL_RESULT")
local function nums(name) local t = {} for v in (os.getenv(name) or ""):gmatch("%d+") do t[#t + 1] = tonumber(v) end return t end
local lay, steps_tab, hit = nums("BRAWL_HAZARD_LAYOUT"), nums("BRAWL_HAZARD_STEPS"), nums("BRAWL_HIT_LAYOUT")
local HS, COLS, PAL0, NPAL, ROWS, STRIP_Y = lay[1], lay[2], lay[3], lay[4], lay[5], lay[6]
local O_STATE, STATE_PLAYING = hit[1], 3
local function addr(n) return tonumber(os.getenv(n), 16) end
local flow_addr, kind_addr, speed_addr, swaps_addr, matches_addr, palmax_addr =
  addr("BRAWL_FLOW_ADDR"), addr("BRAWL_KIND_ADDR"), addr("BRAWL_SPEED_ADDR"), addr("BRAWL_SWAPS_ADDR"), addr("BRAWL_MATCHES_ADDR"), addr("BRAWL_PALMAX_ADDR")
local X_OFF, Y_OFF = 28, 16 -- screen:pixel origin of the visible area (as in autoanim_check.lua)
local STRIP_W = 320
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
local function finish(ok, msg)
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

local SETTLE = 40
local n, watching = 0, false
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
    for x = X_OFF, X_OFF + STRIP_W - 1, 3 do
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
    for x = X_OFF, X_OFF + STRIP_W - 1, 4 do s = (s * 31 + (screen:pixel(x, y + Y_OFF) & 0xffffff)) % 4294967291 end
    t[y] = s
  end
  return t
end

local phase, phase_at, START_AT, WINDOW, SPEED, KIND = "boot", 0, nil, nil, nil, nil
local hashes, prev_band, rows_changed, prev_c, ctr_steps, swaps0 = {}, nil, {}, nil, 0, 0
emu.register_frame_done(function()
  n = n + 1
  if not START_AT then
    if mem:read_u8(flow_addr + O_STATE) == STATE_PLAYING then
      start:set_value(0); START_AT = n + 30
    else
      if n > 300 and phase == "boot" then phase = "coin"; phase_at = n; coin:set_value(1) end
      if phase == "coin" and n == phase_at + 15 then coin:set_value(0) end
      if phase == "coin" and n >= phase_at + 40 then phase = "start"; phase_at = n; start:set_value(1) end
      if phase == "start" and n == phase_at + 15 then start:set_value(0) end
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
    local distinct, set = 0, {}
    for _, r in ipairs(runs) do if not set[r.h] then set[r.h] = true; distinct = distinct + 1 end end
    local bad_runs, periodic = 0, true
    for i = 2, #runs - 1 do if runs[i].len ~= SPEED then bad_runs = bad_runs + 1 end end
    for i = 1, #runs - 16 do if runs[i].h ~= runs[i + 16].h then periodic = false end end
    local rmin, rmax = 999, -1
    for y in pairs(rows_changed) do if y < rmin then rmin = y end if y > rmax then rmax = y end end
    -- shown head word: y and height
    local w0, w1 = vram[H0] or 0, vram[H1] or 0
    local shown = (w0 ~= 0) and w0 or w1
    local sy, sh = (496 - (shown >> 7)) & 0x1ff, shown & 0x3f
    local expected_speed = steps_tab[KIND + 1]
    local pal_ok = PAL0 + NPAL <= 256
    for p = 0, NPAL - 1 do
      local nz = 0
      for i = 1, 15 do if mem:read_u16(0x400000 + ((PAL0 + p) * 16 + i) * 2) ~= 0 then nz = nz + 1 end end
      if nz < 8 then pal_ok = false end
    end
    local palmax = mem:read_u16(palmax_addr)
    local ok = KIND == 0 and mem:read_u16(matches_addr) == 1 and SPEED == expected_speed
      and scb1_w == 0 and scb24_w == 0 and other_w == 0 and scb3_w == 2 * swaps and swaps >= WINDOW // (8 * SPEED) - 1
      and bad_vram == 0 and total > 0
      and distinct == 16 and bad_runs == 0 and periodic
      and sy == STRIP_Y and sh == ROWS and rmin >= STRIP_Y and rmax <= STRIP_Y + 16 * ROWS - 1
      and math.abs(ctr_steps - WINDOW // SPEED) <= 1 and pal_ok and palmax <= PAL_MAX
    finish(ok, string.format("kind %d speed %d (table %d), window %d frames, strip y %d height %d, changing lines %d..%d (want %d..%d), distinct frames %d (want 16), runs %d with %d off length (want 0) periodic %s, counter steps %d (want %d +-1), swaps %d, CPU writes: SCB1 %d SCB2/4 %d other SCB3 %d (want 0) head SCB3 %d (want %d), writes outside vblank %d of %d (want 0), palette ok %s, palette words per flush max %d (limit %d)",
      KIND, SPEED, expected_speed or -1, WINDOW, sy, sh, rmin, rmax, STRIP_Y, STRIP_Y + 16 * ROWS - 1, distinct, #runs, bad_runs, tostring(periodic), ctr_steps, WINDOW // SPEED, swaps, scb1_w, scb24_w, other_w, scb3_w, 2 * swaps, bad_vram, total, tostring(pal_ok), palmax, PAL_MAX))
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
