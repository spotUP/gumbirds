-- Sprite draw-order proof (make test-slots, plan 2026-11-10-neo-geo-graphics-max.md G1). Runs the real game to
-- PLAYING, takes the head sprite of a live object pool run (src/sprite_slots.h POOL_SPRITE_BASE..) from a Lua VRAM
-- shadow and forges a copy of it with an all-magenta palette (palette 250, colours 1..15) at the same position:
--   behind copy: slot BG_NEAR_SPRITE, a background plane slot below the pool. The pool sprite covers it, so
--                the screen must show 0 magenta pixels.
--   front copy:  slot FG_RAIN_SPRITE, above the hero (not the hazard strip: its two bank heads swap hide and show every few frames, which wipes a forged head). It covers the pool sprite, so the screen must show N > 0
--                magenta pixels (the copy's opaque pixels) and the pool sprite's own words stay unchanged.
-- Both slots are reserved and unused by the game, so the copies are the only writers.
-- The same run is the reachability test of the floating islands (plan 2026-11-10-islands-build-plan.md I11): after PLAYING
-- frame 60 it reads the 41 island sprites from the VRAM shadow and checks the 8 chains (head height, head top, column counts,
-- palette, auto-animation bit on the caps only), that g_island_draws advanced once per PLAYING frame (island_step ran), that the
-- CPU wrote no island SCB1 word in a 60 frame window (the auto-animation does the work), and, with the island palettes painted
-- magenta, that the first drawn row of a middle column is the stage y of its platform (the drawn line is the collision floor).
-- Env: BRAWL_FLOW_ADDR, BRAWL_HIT_LAYOUT, BRAWL_RESULT, BRAWL_SLOT_LAYOUT (tests/mame/slot_probe.c output),
-- BRAWL_ISLAND_DRAWS_ADDR (g_island_draws), BRAWL_STAGE_PLATFORMS (x y w of each platform, from src/core/stage.c).
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result    = os.getenv("BRAWL_RESULT")
local lay = {}
for v in (os.getenv("BRAWL_HIT_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local O_STATE = lay[1]
local slots = {}
for v in (os.getenv("BRAWL_SLOT_LAYOUT") or ""):gmatch("%d+") do slots[#slots + 1] = tonumber(v) end
local POOL_FIRST, POOL_END, BEHIND, FRONT = slots[1], slots[2], slots[3], slots[4]
local ISL_FIRST, ISL_END, ISL_PAL, ISL_PAL_N = slots[1], slots[2], slots[5], slots[6]
local draws_addr = tonumber(os.getenv("BRAWL_ISLAND_DRAWS_ADDR"), 16)
local plats = {}
do
  local v = {}
  for d in (os.getenv("BRAWL_STAGE_PLATFORMS") or ""):gmatch("%d+") do v[#v + 1] = tonumber(d) end
  for i = 1, #v - 2, 3 do plats[#plats + 1] = { x = v[i], y = v[i + 1], w = v[i + 2] } end
end
local STATE_PLAYING, PAL = 3, 250
local SCB1, SCB2, SCB3, SCB4 = 0, 0x8000, 0x8200, 0x8400

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
local isl_writes, isl_watch = 0, false   -- CPU writes to island SCB1 words while watched
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "slotvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then
    if isl_watch and vaddr < SCB2 and (vaddr >> 6) >= ISL_FIRST and (vaddr >> 6) < ISL_END then isl_writes = isl_writes + 1 end
    vram[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
  elseif r == 4 then vmod = data end
end)

-- write words at a VRAM address (modulo 1); the address and modulo seen by the game are restored afterwards
local function vwrite(addr, words)
  local sa, sm = vaddr, vmod
  mem:write_u16(0x3c0004, 1)
  mem:write_u16(0x3c0000, addr)
  for _, w in ipairs(words) do mem:write_u16(0x3c0002, w) end
  mem:write_u16(0x3c0004, sm)
  mem:write_u16(0x3c0000, sa)
end

-- ---- islands (I11) ----
local X_OFF, Y_OFF = 28, 16 -- screen:pixel origin of the visible area (as in hazard_check.lua)
local isl_cols = {}      -- columns of each island: width / 16
local isl_head = {}      -- first sprite of each island
do
  local s = ISL_FIRST
  for i, p in ipairs(plats) do isl_head[i] = s; isl_cols[i] = p.w // 16; s = s + p.w // 16 end
end
local isl_before, isl_tiles, isl_saved
local function isl_fail(msg) finish(false, "islands: " .. msg) end

local function isl_structure()
  if #plats == 0 then isl_fail("no platforms in BRAWL_STAGE_PLATFORMS") end
  local total = 0
  for i, p in ipairs(plats) do
    local cols, h = isl_cols[i], isl_head[i]
    total = total + cols
    local top = p.y - 4
    local want = (((496 - top) & 0x1ff) << 7) | 1
    if vram[SCB3 + h] ~= want then isl_fail(string.format("island %d head SCB3 %04x, want %04x (height 1, top %d)", i, vram[SCB3 + h] or -1, want, top)) end
    for c = 1, cols - 1 do
      if ((vram[SCB3 + h + c] or 0) & 0x40) == 0 then isl_fail(string.format("island %d column %d is not sticky", i, c)) end
    end
    if h + cols < ISL_END and ((vram[SCB3 + h + cols] or 0) & 0x40) ~= 0 then isl_fail(string.format("island %d chain runs into the next island", i)) end
    for c = 0, cols - 1 do
      local attr = vram[SCB1 + (h + c) * 64 + 1] or 0
      local pal = attr >> 8
      if pal < ISL_PAL or pal >= ISL_PAL + ISL_PAL_N then isl_fail(string.format("island %d column %d palette %d outside %d..%d", i, c, pal, ISL_PAL, ISL_PAL + ISL_PAL_N - 1)) end
      local cap = (c == 0 or c == cols - 1)
      if cap ~= ((attr & 0x08) ~= 0) then isl_fail(string.format("island %d column %d auto-animation bit %s, caps are columns 0 and %d", i, c, tostring((attr & 0x08) ~= 0), cols - 1)) end
    end
  end
  if total ~= ISL_END - ISL_FIRST then isl_fail(string.format("%d columns in the stage table, %d island sprites", total, ISL_END - ISL_FIRST)) end
end

local function isl_tile_words()
  local t = {}
  for s = ISL_FIRST, ISL_END - 1 do t[#t + 1] = vram[SCB1 + s * 64] or 0; t[#t + 1] = vram[SCB1 + s * 64 + 1] or 0 end
  return t
end

-- Paint every island palette magenta (colours 1..15), remembering the words; restored by isl_restore.
local function isl_paint()
  isl_saved = {}
  for p = ISL_PAL, ISL_PAL + ISL_PAL_N - 1 do
    for i = 0, 15 do
      local a = 0x400000 + p * 32 + i * 2
      isl_saved[a] = mem:read_u16(a)
      if i > 0 then mem:write_u16(a, 0x0f0f) end
    end
  end
end
local function isl_restore() for a, w in pairs(isl_saved) do mem:write_u16(a, w) end end

-- First magenta row in a middle column of every island fully inside the view; sheet row 4 is the first opaque row of a middle
-- piece (ISLAND_LINE_ROW), so it must be at stage y.
local function isl_pixels()
  local matched, bad, detail = 0, 0, {}
  for i, p in ipairs(plats) do
    local h = isl_head[i]
    local sx = ((vram[SCB4 + h] or 0) >> 7) & 0x1ff
    if sx + p.w <= 320 then
      local x = X_OFF + sx + 32 + 8
      local first
      for y = p.y + Y_OFF - 12, p.y + Y_OFF + 12 do
        local px = screen:pixel(x, y)
        if ((px >> 16) & 0xff) > 200 and ((px >> 8) & 0xff) < 80 and (px & 0xff) > 200 then first = y; break end
      end
      if first == p.y + Y_OFF then matched = matched + 1
      elseif first and first < p.y + Y_OFF then bad = bad + 1; detail[#detail + 1] = string.format("island %d first row %d want %d", i, first, p.y + Y_OFF)
      else detail[#detail + 1] = string.format("island %d first row %s (covered?)", i, tostring(first)) end
    end
  end
  return matched, bad, table.concat(detail, "; ")
end

local isl_msg = ""

-- The pool now holds only fliers, which move (the islands that stood still left it): a source that moved during the
-- 8 frame window is dropped with its copies hidden and a still one is searched for, until the 600 frame limit.
local src, behind_n, front_n, found_at, words
local function retry()
  vwrite(SCB3 + BEHIND, { 0 })
  vwrite(SCB3 + FRONT, { 0 })
  src = nil
end

local function forge(slot, src)
  local h = vram[SCB3 + src] & 0x3f
  local strip = {}
  for i = 0, h * 2 - 1 do
    local w = vram[SCB1 + src * 64 + i] or 0
    if i % 2 == 1 then w = (w & 0x00ff) | (PAL << 8) end
    strip[#strip + 1] = w
  end
  vwrite(SCB1 + slot * 64, strip)
  vwrite(SCB2 + slot, { vram[SCB2 + src] })
  vwrite(SCB3 + slot, { vram[SCB3 + src] & 0xffbf })   -- head: not sticky
  vwrite(SCB4 + slot, { vram[SCB4 + src] })
end

local function magenta()
  local w, h, n = screen.width, screen.height, 0
  for y = 0, h - 1 do
    for x = 0, w - 1 do
      local p = screen:pixel(x, y)
      local r, g, b = (p >> 16) & 0xff, (p >> 8) & 0xff, p & 0xff
      if r > 200 and g < 80 and b > 200 then n = n + 1 end
    end
  end
  return n
end

local n, phase, phase_at, since_start = 0, "boot", 0, 0
-- All words that shape the sprite on screen: SCB2..4 and every tile and attribute word of its strip (a flier changes tiles
-- while flapping; a copy forged from an older tile would not match the pool sprite's pixels).
local function snap(s)
  local t = { vram[SCB3 + s], vram[SCB4 + s], vram[SCB2 + s] }
  for i = 0, 31 do t[#t + 1] = vram[SCB1 + s * 64 + i] end
  return t
end
local function same(a, b) for i = 1, #a do if a[i] ~= b[i] then return false end end return true end

emu.register_frame_done(function()
  n = n + 1
  local state = mem:read_u8(flow_addr + O_STATE)
  if state ~= STATE_PLAYING then
    since_start = 0
    if n > 300 and phase == "boot" then phase = "coin"; phase_at = n; coin:set_value(1) end
    if phase == "coin" and n == phase_at + 15 then coin:set_value(0) end
    if phase == "coin" and n >= phase_at + 40 then phase = "start"; phase_at = n; start:set_value(1) end
    if phase == "start" and n == phase_at + 15 then start:set_value(0) end
    return
  end
  if phase == "start" then start:set_value(0); phase = "play" end
  since_start = since_start + 1
  if not src then
    -- A pool head sprite fully inside the 320 px view (the arena is wider than the view and a sprite at the right edge is
    -- not drawn); look each frame after PLAYING frame 60 until an island sprite (still, unlike the pool fliers) shows, for at most 600 frames.
    if since_start == 60 then
      -- reads of the island shadow need the first PLAYING frames written: frame 60 is well past the match start
      isl_before = mem:read_u16(draws_addr)
      isl_structure()
      isl_tiles = isl_tile_words()
      isl_writes = 0; isl_watch = true
      isl_paint()
      return
    elseif since_start == 64 then
      local matched, bad, detail = isl_pixels()
      isl_restore()
      if bad > 0 or matched < 1 then isl_fail(string.format("%d islands matched the stage line, %d drawn above it; %s", matched, bad, detail)) end
      isl_msg = string.format("%d islands: drawn line == stage y in %d visible; ", #plats, matched)
      return
    elseif since_start == 120 then
      isl_watch = false
      local delta = (mem:read_u16(draws_addr) - isl_before) & 0xffff
      local after = isl_tile_words()
      if isl_writes ~= 0 then isl_fail(string.format("the CPU wrote %d island SCB1 words in 60 frames", isl_writes)) end
      if not same(isl_tiles, after) then isl_fail("island SCB1 words changed after frame 60") end
      if delta ~= 60 or isl_before == 0 then isl_fail(string.format("g_island_draws %d at frame 60 and +%d in 60 PLAYING frames, want >0 and +60", isl_before, delta)) end
      isl_msg = isl_msg .. string.format("g_island_draws %d at frame 60, +%d in 60 frames, 0 CPU SCB1 writes; ", isl_before, delta)
      return
    end
    if since_start < 125 then return end
    for s = POOL_FIRST, POOL_END - 1 do
      local v = vram[SCB3 + s] or 0
      local sx = ((vram[SCB4 + s] or 0) >> 7) & 0x1ff
      local sy = (496 - (v >> 7)) & 0x1ff
      if (v & 0x3f) > 0 and (v & 0x40) == 0 and sx < 288 and sy < 180 then src = s; break end
    end
    if not src then
      if since_start > 600 then finish(false, "no live on-screen pool head sprite in 600 PLAYING frames") end
      return
    end
    found_at = since_start
    words = snap(src)
    for i = 1, 15 do mem:write_u16(0x400000 + PAL * 32 + i * 2, 0x0f0f) end
    mem:write_u16(0x400000 + PAL * 32, 0)
    forge(BEHIND, src)
  elseif since_start == found_at + 4 then
    behind_n = magenta()
    if not same(words, snap(src)) then retry(); return end
    vwrite(SCB3 + BEHIND, { 0 })
    forge(FRONT, src)
  elseif since_start == found_at + 8 then
    front_n = magenta()
    if not same(words, snap(src)) then retry(); return end
    local ok = behind_n == 0 and front_n > 0
    finish(ok, isl_msg .. string.format("pool sprite %d, magenta pixels: copy in slot %d (behind pool) %d, copy in slot %d (above hero) %d",
      src, BEHIND, behind_n, FRONT, front_n))
  end
end)
