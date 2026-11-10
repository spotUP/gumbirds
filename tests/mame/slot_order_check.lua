-- Sprite draw-order proof (make test-slots, plan 2026-11-10-neo-geo-graphics-max.md G1). Runs the real game to
-- PLAYING, takes the head sprite of a live object pool run (src/sprite_slots.h POOL_SPRITE_BASE..) from a Lua VRAM
-- shadow and forges a copy of it with an all-magenta palette (palette 250, colours 1..15) at the same position:
--   behind copy: slot BG_NEAR_SPRITE, a background plane slot below the pool. The pool sprite covers it, so
--                the screen must show 0 magenta pixels.
--   front copy:  slot FG_RAIN_SPRITE, above the hero (not the hazard strip: its two bank heads swap hide and show every few frames, which wipes a forged head). It covers the pool sprite, so the screen must show N > 0
--                magenta pixels (the copy's opaque pixels) and the pool sprite's own words stay unchanged.
-- Both slots are reserved and unused by the game, so the copies are the only writers. Env: BRAWL_FLOW_ADDR,
-- BRAWL_HIT_LAYOUT, BRAWL_RESULT, BRAWL_SLOT_LAYOUT (tests/mame/slot_probe.c output).
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result    = os.getenv("BRAWL_RESULT")
local lay = {}
for v in (os.getenv("BRAWL_HIT_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local O_STATE = lay[1]
local slots = {}
for v in (os.getenv("BRAWL_SLOT_LAYOUT") or ""):gmatch("%d+") do slots[#slots + 1] = tonumber(v) end
local POOL_FIRST, POOL_END, BEHIND, FRONT = slots[1], slots[2], slots[3], slots[4]
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
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "slotvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then vram[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
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
local src, words, behind_n, front_n, found_at
local function snap(s) return { vram[SCB3 + s], vram[SCB4 + s], vram[SCB2 + s], vram[SCB1 + s * 64 + 1] } end
local function same(a, b) for i = 1, 4 do if a[i] ~= b[i] then return false end end return true end

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
    -- not drawn); look each frame after PLAYING frame 60 until a platform or flier shows, for at most 600 frames.
    if since_start < 60 then return end
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
    if not same(words, snap(src)) then finish(false, "pool sprite changed during the check"); return end
    vwrite(SCB3 + BEHIND, { 0 })
    forge(FRONT, src)
  elseif since_start == found_at + 8 then
    front_n = magenta()
    local ok = behind_n == 0 and front_n > 0 and same(words, snap(src))
    finish(ok, string.format("pool sprite %d, magenta pixels: copy in slot %d (behind pool) %d, copy in slot %d (above hero) %d",
      src, BEHIND, behind_n, FRONT, front_n))
  end
end)
