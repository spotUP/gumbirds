-- Headless title check under UniBIOS 4.0 (make test-logo; coins need a real BIOS). Asserts:
--   L1. title: g_logo_draws advances and every logo strip sprite (LOGO_STRIP_COUNT from LOGO_SPRITE) has a non-zero SCB3 height, its tiles lie in the
--       logo tile block;
--   L2. 0 credits: the "PRESS START" cell at fix col 14 row 22 (tile of 'P') is never written; the "INSERT COIN" cell ('I') is;
--   L3. the BIOS credit byte 0x10FE00 reads 0 before and 1 after one coin; after the coin "PRESS START" is written;
--   L4. kill strips (slots shared with the logo, 323..354): in each of two Gum Trips (title, play, title, play) every visible sprite of
--       TRIP_STRIP_SPRITE..+COUNT carries a tripstrip tile and none a logo tile; back on the title the logo is visible again.
-- Fix cells and sprite words come from a tap on the VRAM ports (what the game wrote), not from game variables.
-- Env: BRAWL_FLOW_ADDR, BRAWL_LOGODRAWS_ADDR, BRAWL_FIXFONT_H, BRAWL_LOGO_LAYOUT (logo_probe.c), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local draws_addr = tonumber(os.getenv("BRAWL_LOGODRAWS_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local lay = {}
for v in os.getenv("BRAWL_LOGO_LAYOUT"):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local O_STATE, O_OPEN, O_PAID, O_MODE = lay[1], lay[2], lay[3], lay[4]
local TS_BASE, TS_COUNT, LG_BASE, LG_COUNT, LG_SPR, LG_N, TS_SPR, TS_N, SOOT_SPR, SOOT_N, MODE_TRIP, PLAYING, LG_STRIPS = table.unpack(lay, 5, 17)
local CREDIT = 0x10fe00
-- fix tile of 'P' and 'I' in the backed map (same table gfx_text_backed uses), parsed from the generated header
local hdr = io.open(os.getenv("BRAWL_FIXFONT_H")):read("a")
local body = hdr:match("fixfont_map_backed%[256%]%s*=%s*{(.-)}")
local map = {}
for v in body:gmatch("%d+") do map[#map + 1] = tonumber(v) end
assert(#map == 256, "fixfont_map_backed not parsed")
local TILE_P, TILE_I = map[string.byte("P") + 1], map[string.byte("I") + 1]
local PRESS_ADDR = 0x7000 + 14 * 32 + 22   -- fix cell col 14, row 22 (TITLE_PLATE_ROW in src/main.c)
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, name)
  for fname, f in pairs(ports[tag].fields) do if fname == name then return f end end
end
local coin = field(":AUDIO_COIN", "Coin 1")
local start = field(":edge:joy:START", "1 Player Start")
local down = field(":edge:joy:JOY1", "P1 Down")
local ss = dofile("tests/mame/start_seq.lua")(coin, start, down)
local function finish(ok, msg)
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

local vram, vaddr, vmod = {}, 0, 1
local seen_p, seen_i = 0, 0
tap_vram = mem:install_write_tap(0x3c0000, 0x3c000f, "logovram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 4 then vmod = data
  elseif r == 2 then
    if vaddr == PRESS_ADDR then
      local t = data & 0xfff
      if t == TILE_P then seen_p = seen_p + 1 elseif t == TILE_I then seen_i = seen_i + 1 end
    end
    vram[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
  end
end)

-- visible sprites of slots first..first+count-1 as {slot, tile} lists (SCB3 height, sticky chains inherit; tiles from SCB1)
local function tiles_of(first, count)
  local out, h = {}, 0
  for s = first, first + count - 1 do
    local c = vram[0x8200 + s] or 0
    if (c & 0x40) == 0 then h = c & 0x3f end
    for i = 0, h - 1 do
      local lo, at = vram[s * 64 + i * 2], vram[s * 64 + i * 2 + 1]
      if lo then out[#out + 1] = { s, lo | (((at or 0) >> 4) & 0xf) << 16 } end
    end
  end
  return out
end
local function in_range(t, base, n) return t >= base and t < base + n end
local function logo_visible()   -- the strips are always shown; the pieces after them come and go per frame
  for s = LG_SPR, LG_SPR + LG_STRIPS - 1 do if ((vram[0x8200 + s] or 0) & 0x3f) == 0 then return false, s end end
  return true
end

local n, phase, t0, base_draws, bad = 0, "boot", 0, 0, nil
local trips_done, strip_checked, last_title_n, over_n = 0, 0, 0, 0
local c_before, c_after
local L1_ok, L1_msg = false, nil
local function fail(m) if not bad then bad = m end end
local function state() return mem:read_u8(flow_addr + O_STATE) end

emu.register_frame_done(function()
  n = n + 1
  if bad then finish(false, bad) return end
  if phase == "boot" then
    if state() == 0 and mem:read_u16(draws_addr) > 0 and n > 240 then   -- FLOW_ATTRACT_TITLE with the game running (BIOS boot takes a while)
      phase = "title0"; t0 = n; base_draws = mem:read_u16(draws_addr); seen_p, seen_i = 0, 0
      c_before = mem:read_u8(CREDIT)
    end
  elseif phase == "title0" then   -- 0 credits: INSERT COIN only
    if n - t0 == 120 then
      if mem:read_u16(draws_addr) <= base_draws then fail("L1 g_logo_draws did not advance on the title") return end
      local ok, s = logo_visible()
      if not ok then fail("L1 logo sprite " .. s .. " hidden on the title") return end
      for _, e in ipairs(tiles_of(LG_SPR, LG_N)) do
        if not in_range(e[2], LG_BASE, LG_COUNT) then fail(string.format("L1 logo sprite %d tile %d outside the logo block", e[1], e[2])) return end
      end
      if seen_p ~= 0 then fail("L2 PRESS START written at 0 credits") return end
      if seen_i == 0 then fail("L2 INSERT COIN never written at 0 credits") return end
      if c_before ~= 0 then fail("L3 credit byte before the coin is " .. c_before) return end
      L1_ok = true
      phase = "coin"; t0 = n; ss.begin(n); ss.watch(mem)
    end
  elseif phase == "coin" then   -- one coin, then watch (no Start press yet): PRESS START appears
    local k = n - t0
    if k >= 15 then coin:set_value(0) end
    if k == 60 then
      c_after = mem:read_u8(CREDIT)
      if c_after ~= 1 then fail("L3 credit byte after one coin is " .. tostring(c_after) .. ", want 1") return end
      if seen_p == 0 then fail("L3 PRESS START never written after the coin") return end
      phase = "trip"; t0 = n; ss.begin(n)
      coin:set_value(0)   -- the coin above is already banked: a second one would leave a credit, and the BIOS starts a new game from it as soon as the title returns
    end
  elseif phase == "trip" then   -- Down (Gum Trip) then one Start: play; the coin phase above already gave the credit, ss gives a second
    if ss.step(n, state() == PLAYING and mem:read_u8(flow_addr + O_MODE) == MODE_TRIP, trips_done == 0) then   -- the title remembers Gum Trip: a Down in trip 2 would switch back to the Arena
      phase = "play"; t0 = n; strip_checked = 0
    elseif n - t0 > 900 then fail("L4 trip " .. (trips_done + 1) .. " not reached") return end
  elseif phase == "play" then
    if n - t0 > 90 and n - t0 <= 330 and state() == PLAYING then   -- the idle flier dies after a varying time: only count frames while still playing
      for _, e in ipairs(tiles_of(LG_SPR, LG_N + TS_N)) do
        if e[1] <= 354 and in_range(e[2], LG_BASE, LG_COUNT) then fail(string.format("L4 trip %d: slot %d holds logo tile %d", trips_done + 1, e[1], e[2])) return end
      end
      for _, e in ipairs(tiles_of(LG_SPR, 44)) do
        strip_checked = strip_checked + 1
        if not in_range(e[2], TS_BASE, TS_COUNT) then fail(string.format("L4 trip %d: slot %d tile %d is not a tripstrip tile", trips_done + 1, e[1], e[2])) return end
      end
    elseif n - t0 > 330 or (n - t0 > 90 and state() ~= PLAYING) then
      if strip_checked == 0 then fail("L4 trip " .. (trips_done + 1) .. ": no visible kill strip sprites seen") return end
      trips_done = trips_done + 1
      phase = "wait"; t0 = n   -- no poke: the idle flier dies, Game Over runs out and the game itself returns to the title
    end
  elseif phase == "wait" then
    if state() == 4 then   -- U2: FLOW_GAME_OVER keeps the Gum Trip scene; the kill strip must stay drawn until the title takes the slots
      over_n = over_n + 1
      if over_n > 2 and #tiles_of(LG_SPR, 44) == 0 then fail(string.format("U2 trip %d: kill strip hidden %d frames into Game Over", trips_done, over_n)) return end
    end
    if state() == 0 then
      if over_n < 30 then fail(string.format("U2 trip %d: only %d Game Over frames seen (want >= 30)", trips_done, over_n)) return end
      over_n = 0; phase = "back"; t0 = n
    elseif n - t0 > 4000 then fail("L4 the game did not return to the title after trip " .. trips_done .. " (flow state " .. state() .. ")") return
    end
  elseif phase == "back" then
    if n - t0 == 1 and (state() ~= 0 or mem:read_u8(CREDIT) ~= 0) then fail(string.format("L4 title after trip %d: flow state %d, credit byte %02x (a banked credit starts a game at once)", trips_done, state(), mem:read_u8(CREDIT))) return end
    if n - t0 == 40 then   -- early: a paid title starts the next game by itself when its timer runs out
      local ok, s = logo_visible()
      if not ok then fail("L4 logo sprite " .. s .. " hidden when back on the title after trip " .. trips_done .. " (flow state " .. state() .. ", scb3 " .. string.format("%x", vram[0x8200 + s] or 0) .. ")") return end
      for _, e in ipairs(tiles_of(LG_SPR, LG_N)) do
        if not in_range(e[2], LG_BASE, LG_COUNT) then fail(string.format("L4 back on the title: slot %d tile %d is not a logo tile", e[1], e[2])) return end
      end
      if trips_done >= 2 then
        finish(true, string.format("logo draws %d, PRESS cell P/I writes %d/%d, credit %d->%d, kill-strip tiles checked %d, trips %d",
          mem:read_u16(draws_addr) - base_draws, seen_p, seen_i, c_before, c_after, strip_checked, trips_done))
        return
      end
      phase = "trip"; t0 = n; ss.begin(n)
      coin:set_value(1)
    end
  end
end)
