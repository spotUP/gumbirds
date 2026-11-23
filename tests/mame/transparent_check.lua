-- Text and overlays keep a transparent background over the scene (make test-transparent): UniBIOS 4.0, one coin, PARTY event list, Gum Fling, Start.
-- Owner 2026-11-23: "texts and overlay gfx lack transparent backgrounds" (rules card, GET SET / GO, HUD over the stadium).
--   T1. on the rules card, through GET SET / GO and in the first run-up, no fix cell on screen shows a tile that is a filled box in the S-ROM
--       (a font atlas tile with fewer than 8 of its 64 pixels colour 0): no plate fill, no backed glyph, no panel edge;
--   T2. no sprite column above the world slots (1..160) is a filled box in the C-ROM (every shown tile has all 256 pixels set).
-- The tile pixels are read from the cartridge regions MAME loaded, the cells from a Lua shadow of LSPC VRAM.
-- TRANSPARENT_LOG=file also writes every offending tile per screen (the measurement behind the fix).
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_BLOW_LAYOUT (gum_fling_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_BLOW_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { state = L[1], fling = L[3], phase = L[4] }
local K = { playing = L[10], windup = L[15], card = L[16] }
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, match)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname:find(match, 1, true) then return f end end
end
local coin, start1, up = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start"), field(":edge:joy:JOY1", "P1 Up")
local abtn, bbtn, pick = field(":edge:joy:JOY1", "P1 A"), field(":edge:joy:JOY1", "P1 B"), field(":edge:joy:JOY1", "P1 Down")
local ss = dofile("tests/mame/start_seq.lua")(coin, start1, up)
local function b(o) return mem:read_u8(flow_addr + o) end
local vram, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "transparentvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then vram[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
  elseif r == 4 then vmod = data end
end)
local srom, crom
for tag, r in pairs(manager.machine.memory.regions) do
  if tag:find("cslot1:fixed$") then srom = r elseif tag:find("cslot1:sprites$") then crom = r end
end
local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and up and abtn and bbtn and pick) then finish(false, "missing ports") end
if not (srom and crom) then finish(false, "cartridge fixed / sprites region not found") end

local fix_box, spr_box = {}, {}   -- tile -> is it a filled box (cached)
local function fix_is_box(t)
  if t < 0x300 or t > 0x3bf then return false end   -- the font atlas only (16 x 12 tiles from FIXFONT_GAME_BASE): button faces and bar cells behind it are drawn art, filled by design
  if fix_box[t] == nil then
    local clear = 0
    for i = 0, 31 do
      local v = srom:read_u8(t * 32 + i)
      if v & 0x0f == 0 then clear = clear + 1 end
      if v & 0xf0 == 0 then clear = clear + 1 end
    end
    fix_box[t] = clear < 8
  end
  return fix_box[t]
end
local function spr_is_box(t)
  if spr_box[t] == nil then
    local full = true
    for i = 0, 127, 4 do   -- one 8-pixel run: four bitplane bytes, a pixel is colour 0 when its bit is clear in all four
      if (crom:read_u8(t * 128 + i) | crom:read_u8(t * 128 + i + 1) | crom:read_u8(t * 128 + i + 2) | crom:read_u8(t * 128 + i + 3)) ~= 0xff then full = false; break end
    end
    spr_box[t] = full
  end
  return spr_box[t]
end
local bad, bad_n, seen = {}, {}, {}   -- per screen: first offender text, offending frames; seen = "screen what" set for the log
local logf = os.getenv("TRANSPARENT_LOG")
local function note(screen, what)
  bad[screen] = bad[screen] or what
  if logf and not seen[screen .. what] then
    seen[screen .. what] = true
    local f = io.open(logf, "a"); f:write(screen .. " " .. what .. "\n"); f:close()
  end
end
local function scan(screen)
  local hit = false
  for col = 0, 39 do
    for row = 2, 29 do   -- visible fix rows
      local c = vram[0x7000 + col * 32 + row] or 0
      if fix_is_box(c & 0xfff) then hit = true; note(screen, string.format("fix tile 0x%03x palette %d at col %d row %d", c & 0xfff, c >> 12, col, row)) end
    end
  end
  for s = 161, 380 do
    local w3 = vram[0x8200 + s] or 0
    local h = w3 & 0x3f
    if h > 0 and (w3 & 0x40) == 0 and (((496 - (w3 >> 7)) & 0x1ff) < 224) then
      local box = true
      for r = 0, (h > 32 and 32 or h) - 1 do
        local t = (vram[s * 64 + 2 * r] or 0) | ((((vram[s * 64 + 2 * r + 1] or 0) >> 4) & 0xf) << 16)
        if not spr_is_box(t) then box = false; break end
      end
      if box then hit = true; note(screen, string.format("sprite slot %d (%d tiles) at x %d", s, h, (vram[0x8400 + s] or 0) >> 7)) end
    end
  end
  if hit then bad_n[screen] = (bad_n[screen] or 0) + 1 end
end

local n, phase, t0, cardn, playn, frames = 0, "boot", 0, 0, 0, {}
emu.register_frame_done(function()
  n = n + 1
  if n > 6000 then finish(false, "watchdog in phase " .. phase) return end
  local playing = b(O.state) == K.playing
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    if ss.step(n, playing, 1) then phase = "fling"; t0 = n; pick:set_value(0) end
    ss.menu(n - t0, 9, abtn, pick)
  elseif phase == "fling" then
    if not playing or b(O.fling) ~= 1 then finish(false, "Gum Fling not running") return end
    local screen
    if b(K.card) == 1 then   -- rules card: A is ignored for its first 30 frames, then one press dismisses it
      cardn = cardn + 1
      abtn:set_value((cardn >= 40 and cardn < 44) and 1 or 0)
      screen = cardn > 2 and "card" or nil
    else
      playn = playn + 1   -- GET SET holds the first run-up for 60 frames, GO! follows; then the HUD and the meter while A and B are mashed
      abtn:set_value((playn > 70 and playn % 8 < 2) and 1 or 0); bbtn:set_value((playn > 70 and playn % 8 >= 4 and playn % 8 < 6) and 1 or 0)
      screen = playn > 2 and (playn <= 100 and "countdown" or "play") or nil
      if b(O.phase) ~= K.windup or playn > 160 then phase = "check" end
    end
    if screen then frames[screen] = (frames[screen] or 0) + 1; scan(screen) end
  elseif phase == "check" then
    local t = {}
    for _, s in ipairs({ "card", "countdown", "play" }) do
      if (frames[s] or 0) < 20 then finish(false, string.format("screen %s seen only %d frames", s, frames[s] or 0)) return end
      if bad[s] then t[#t + 1] = string.format("%s: %s (%d of %d frames)", s, bad[s], bad_n[s], frames[s]) end
    end
    if #t > 0 then finish(false, "filled box behind text or overlay: " .. table.concat(t, "; ")) return end
    finish(true, string.format("Gum Fling rules card %d, GET SET / GO %d and run-up %d frames: no filled fix cell, no filled sprite column above the world", frames.card, frames.countdown, frames.play))
  end
end)
