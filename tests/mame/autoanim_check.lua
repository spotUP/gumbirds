-- Hardware auto-animation proof (make test-autoanim, plan 2026-11-10-neo-geo-graphics-max.md G2). Runs the real game
-- and watches the 16 star sprites (slots 0..15, src/sprite_slots.h BG_STAR_SPRITE) over a window of frames:
--   1. VRAM shadow (taps on REG_VRAMADDR/VRAMRW/VRAMMOD): the CPU writes ZERO words into the SCB1 area of the star
--      slots during the window, so any change on screen comes from the LSPC, not from software.
--   2. SCB1 attribute word of every star keeps bit 3 (8-frame auto-animation) and one of the two group bases is used.
--   3. REG_LSPCMODE (0x3c0006) read: the 3-bit auto-animation counter (bits 2..0) takes all 8 values in the window
--      and steps once per BG_STAR_STEP_FRAMES frames (speed field bits 15..8 = frames per step - 1).
--   4. The pixels around star 0 and star 1 (even group, odd group) change at least STEPS_MIN times, and the two
--      stars show different signature sequences (out of phase).
-- Env: BRAWL_FLOW_ADDR, BRAWL_HIT_LAYOUT, BRAWL_RESULT, BRAWL_AUTOANIM_LAYOUT (tests/mame/autoanim_probe.c: star x/y of stars 0 and 1, step frames).
local result = os.getenv("BRAWL_RESULT")
local lay = {}
for v in (os.getenv("BRAWL_AUTOANIM_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local STEP = lay[1] -- compile time star speed; the live speed is read at the window start (a match raises it to the hazard's)
local speed_addr = tonumber(os.getenv("BRAWL_SPEED_ADDR"), 16)
local STAR = { { lay[2], lay[3] }, { lay[4], lay[5] } }
local STARS_FIRST, STARS_END = 0, 16
local X_OFF, Y_OFF = 28, 16 -- screen:pixel origin of the visible area (measured: first backdrop pixel of a row is x 28; the header text starts at y 16)
local WINDOW
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local hit = {}
for v in (os.getenv("BRAWL_HIT_LAYOUT") or ""):gmatch("%d+") do hit[#hit + 1] = tonumber(v) end
local O_STATE, STATE_PLAYING = hit[1], 3

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

local vram, vaddr, vmod = {}, 0, 1
local watching, star_writes = false, 0
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "aavram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then
    vram[vaddr] = data
    if watching and vaddr < STARS_END * 64 then star_writes = star_writes + 1 end
    vaddr = (vaddr + vmod) & 0xffff
  elseif r == 4 then vmod = data end
end)

-- signature of the 11x11 pixel box centred on a star pixel, searched over a small offset range (screen origin)
local function sig(cx, cy)
  local s = 0
  for y = cy + Y_OFF - 5, cy + Y_OFF + 5 do
    for x = cx + X_OFF - 5, cx + X_OFF + 5 do
      local p = screen:pixel(x, y) & 0xffffff
      s = (s * 31 + p) % 4294967291
    end
  end
  return s
end

local n, phase, phase_at, START_AT = 0, "boot", 0, nil
local prev_c, steps = nil, 0
local seq, last, changes, counters = { {}, {} }, { nil, nil }, { 0, 0 }, {}
emu.register_frame_done(function()
  n = n + 1
  if not START_AT then
    if mem:read_u8(flow_addr + O_STATE) == STATE_PLAYING then
      start:set_value(0); START_AT = n + 30
    else -- coin, start (same input sequence as tests/mame/slot_order_check.lua)
      if n > 300 and phase == "boot" then phase = "coin"; phase_at = n; coin:set_value(1) end
      if phase == "coin" and n == phase_at + 15 then coin:set_value(0) end
      if phase == "coin" and n >= phase_at + 40 then phase = "start"; phase_at = n; start:set_value(1) end
      if phase == "start" and n == phase_at + 15 then start:set_value(0) end
    end
    return
  end
  if n < START_AT then return end
  if n == START_AT then
    STEP = mem:read_u8(speed_addr) -- g_autoanim_frames: the active hazard's frames per step while a match runs (src/hazard.c)
    WINDOW = STEP * 8 * 2 + 4
    watching = true
  end
  if n > START_AT + WINDOW then
    watching = false
    local ncount = 0
    for _ in pairs(counters) do ncount = ncount + 1 end
    local differ = false
    for i = 1, #seq[1] do if seq[1][i] ~= seq[2][i] then differ = true end end
    -- group bases: attribute word, bit 3 set, sprites alternate between two tile base words
    local bit3 = true
    local tiles = {}
    for s = STARS_FIRST, STARS_END - 1 do
      local t, a = vram[s * 64], vram[s * 64 + 1] or 0
      if a & 0x08 == 0 then bit3 = false end
      tiles[s] = t
    end
    local alt = tiles[0] ~= tiles[1]
    local ok = star_writes == 0 and bit3 and alt and ncount == 8 and math.abs(steps - WINDOW // STEP) <= 1 and changes[1] >= 8 and changes[2] >= 8 and differ
    finish(ok, string.format("window %d frames, CPU writes to star SCB1 %d (want 0), attr bit3 on all stars %s, groups differ %s, counter values seen %d (want 8), counter steps %d (want %d +-1), pixel changes star0 %d star1 %d (want >= 8), phases differ %s",
      WINDOW, star_writes, tostring(bit3), tostring(alt), ncount, steps, WINDOW // STEP, changes[1], changes[2], tostring(differ)))
    return
  end
  local c = mem:read_u16(0x3c0006) & 7
  counters[c] = true
  if prev_c and c ~= prev_c then steps = steps + 1 end
  prev_c = c
  for i = 1, 2 do
    local s = sig(STAR[i][1], STAR[i][2])
    seq[i][#seq[i] + 1] = s
    if last[i] ~= nil and s ~= last[i] then changes[i] = changes[i] + 1 end
    last[i] = s
  end
end)
