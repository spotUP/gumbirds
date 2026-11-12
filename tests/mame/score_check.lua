-- Score tables per mode (make test-score). 
-- Drives the real ROM from boot. Two MAME boots share one nvram dir (BRAWL_PHASE=1 or 2), like hiscore_reach.lua.
--   Phase 1 asserts:
--     (a) fresh defaults: trip table rows 3000 down to 300 step 300, name "GUMTRIP "; arena table is whatever the
--         core defaults (checked only for rows descending and non-empty names; values are in src/core/score_table.c).
--     (b) title shows no table and keeps mode select on fix rows 14/15; the attract table screen shows the arena caption
--         then the trip caption, and g_table_mode_draws[0] and [1] both move.
--     (c) a Gum Trip run (input death, Trip.bonus written: exemption in play_run) ends in the trip table only; the arena table is unchanged;
--         a later arena run lands in the arena table only; each save bumps g_hiscore_saves by 1.
--     (d) fix layer: no caption on name entry rows 13/14; save reminder keeps row 13 text and shows the caption on row 14 (the highlighted table is drawn below it); the title after it shows the caption on row 14 too (highlight kept).
--     (e) the 250-byte backup RAM image: 'ROOF', version 2, arena table at 6, trip table at 126, FNV-1a at 246.
--   Phase 2 (fresh boot, same nvram): image and flow tables hold both entries at the same rows, g_hiscore_saves is 0.
-- Env (hex addresses from nm): BRAWL_FLOW_ADDR, BRAWL_FRAME_ADDR, BRAWL_HISCORE_ADDR, BRAWL_SAVES_ADDR,
--   BRAWL_TABLEDRAWS_ADDR (g_table_mode_draws, u32[2]); BRAWL_SCORE_LAYOUT (score_probe.c output);
--   BRAWL_FIXFONT_H (build/gen/fix_font.h, fixfont_map); BRAWL_RESULT, BRAWL_EXPECT (files).
local phase_no   = tonumber(os.getenv("BRAWL_PHASE"))
local flow_addr  = tonumber(os.getenv("BRAWL_FLOW_ADDR") or "", 16)
local frame_addr = tonumber(os.getenv("BRAWL_FRAME_ADDR") or "", 16)
local hs_addr    = tonumber(os.getenv("BRAWL_HISCORE_ADDR") or "", 16)
local saves_addr = tonumber(os.getenv("BRAWL_SAVES_ADDR") or "", 16)
local draws_addr = tonumber(os.getenv("BRAWL_TABLEDRAWS_ADDR") or "", 16)
local font_h     = os.getenv("BRAWL_FIXFONT_H") or "build/gen/fix_font.h"
local result     = os.getenv("BRAWL_RESULT")
local expect     = os.getenv("BRAWL_EXPECT")
local lay = {}
for v in (os.getenv("BRAWL_SCORE_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local O_STATE, O_LAST, O_LMODE, O_MODE, O_TIMER, O_TNAME, O_TSCORE, TABLE_SIZE = table.unpack(lay, 1, 8)
local O_ENAME, O_ESYM, O_EPOS, O_EDONE, O_EIDLE = table.unpack(lay, 9, 13)
local O_GMODE, O_GSCORE, O_GOVER, O_BONUS, O_HSTATE = table.unpack(lay, 14, 18)
local NAME_TIMEOUT, IMAGE_SIZE, DROWNED, MODE_TRIP = table.unpack(lay, 19, 22)
local S_PLAYING, S_OVER, S_NAME, S_REMIND, S_TABLE, S_TITLE = table.unpack(lay, 23, 28)
local rl = {}   -- BRAWL_REACH_LAYOUT (reach_probe.c): arena slice and stomp-teleport offsets, same indexes as hiscore_reach.lua
for v in (os.getenv("BRAWL_REACH_LAYOUT") or ""):gmatch("%d+") do rl[#rl + 1] = tonumber(v) end
local O_FX, O_FVX, O_FGROUND, O_SCORE = table.unpack(rl, 9, 12)
local O_FY, O_FVY, O_CX, O_CY, O_CSTATE, O_CBALL = table.unpack(rl, 13, 18)
local flay = {}   -- BRAWL_FLIER_LAYOUT (flier_probe.c) for tests/mame/flier_drive.lua
for v in (os.getenv("BRAWL_FLIER_LAYOUT") or ""):gmatch("%d+") do flay[#flay + 1] = tonumber(v) end
local mem   = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local HOLD, GAP, WATCHDOG = 3, 4, 40000
local TRIP_FORCE = 5000   -- Trip.bonus written during a trip run (exemption: a 300 point trip row is 2400 px, beyond what the idle hero lives to)
local ARENA_MIN = 1200   -- arena table last row is 1000 (hiscore_reach.lua TABLE_MIN): play until the score passes it

local function field(tag, nm)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname == nm then return f end end
end
local coin  = field(":AUDIO_COIN", "Coin 1")
local start = field(":edge:joy:START", "1 Player Start")
local abtn  = field(":edge:joy:JOY1", "P1 A")
local ubtn  = field(":edge:joy:JOY1", "P1 Up")
local dbtn  = field(":edge:joy:JOY1", "P1 Down")
local lbtn  = field(":edge:joy:JOY1", "P1 Left")
local rbtn  = field(":edge:joy:JOY1", "P1 Right")

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
local function fail(msg) finish(false, msg) error("score_check abort: " .. msg, 0) end
local function check(c, msg) if not c then fail(msg) end end

local function g8(o) return mem:read_u8(flow_addr + o) end
local function g16(o) return mem:read_u16(flow_addr + o) end
local function g32(o) return mem:read_u32(flow_addr + o) end
local function str(a, n)
  local t = {}
  for i = 0, n - 1 do t[#t + 1] = string.char(mem:read_u8(a + i)) end
  return table.concat(t)
end
local function tname(mode, row) return str(flow_addr + O_TNAME + mode * TABLE_SIZE + row * 8, 8) end
local function tscore(mode, row) return g32(O_TSCORE + mode * TABLE_SIZE + row * 4) end
local function table_dump(mode)
  local t = {}
  for r = 0, 9 do t[#t + 1] = tname(mode, r) .. ":" .. tscore(mode, r) end
  return table.concat(t, ",")
end

-- fix layer: shadow of VRAM from the write tap (same as trip_check.lua)
local vram, vaddr, vmod = {}, 0, 0
fixw, fixlast = 0, 0
-- keep the handle: a discarded tap is garbage collected and silently stops after a few frames (every other check script keeps its tap in a global)
tap_vram = mem:install_write_tap(0x3c0000, 0x3c000f, "score_vram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 4 then vmod = data
  elseif r == 2 then vram[vaddr] = data; if vaddr >= 0x7000 and vaddr < 0x7500 then fixw = fixw + 1; fixlast = data end; vaddr = (vaddr + vmod) & 0xffff end
end)
-- fixfont_map comes from the generated header (no ELF symbol; static const)
local fmap = {}
do
  local fh = io.open(font_h, "r")
  if fh then
    local txt = fh:read("*a"); fh:close()
    local body = txt:match("fixfont_map%s*%[[^%]]*%]%s*=%s*{(.-)}")
    if body then for tok in body:gmatch("[%w]+") do fmap[#fmap + 1] = tonumber(tok) end end
  end
end
local function cell(x, y) return (vram[0x7000 + x * 32 + y] or -1) & 0x0fff end
local function text_at(x, y, s)
  for i = 1, #s do
    if cell(x + i - 1, y) ~= fmap[s:byte(i) + 1] then return false end
  end
  return true
end
local rev = {}
for ch = 255, 0, -1 do if fmap[ch + 1] and fmap[ch + 1] ~= 255 then rev[fmap[ch + 1]] = ch end end
local function dump_row(y)
  local t = {}
  for x = 0, 39 do local c = rev[cell(x, y)]; t[#t + 1] = (c and c >= 32 and c < 127) and string.char(c) or "." end
  return table.concat(t)
end
local CAP_ARENA, CAP_TRIP = "ARENA SCORES   ", "GUM TRIP SCORES"
local function caption_at(y)
  if text_at(12, y, CAP_ARENA) then return 0 end
  if text_at(12, y, CAP_TRIP) then return 1 end
  return nil
end

-- frame-driven coroutine: wait(n) and until_(cond, max, why) yield to the next frame
local function wait(n) for _ = 1, n do coroutine.yield() end end
local function until_(cond, max, why)
  for _ = 1, max do
    if cond() then return end
    coroutine.yield()
  end
  fail("timeout waiting for " .. (type(why) == "function" and why() or why) .. " (state " .. g8(O_STATE) .. ")")
end
local function press(f) f:set_value(1); wait(HOLD); f:set_value(0); wait(GAP) end

local function fnv(a, n)
  local h = 2166136261
  for i = 0, n - 1 do h = ((h ~ mem:read_u8(a + i)) * 16777619) & 0xffffffff end
  return h
end
local IMG = { arena = 6, trip = 126 }
local function image_row(mode, row)
  local base = hs_addr + (mode == 0 and IMG.arena or IMG.trip) + row * 12
  return str(base, 8), mem:read_u32(base + 8)
end
local function image_checks(tag)
  check(str(hs_addr, 4) == "ROOF", tag .. ": image magic is " .. str(hs_addr, 4))
  check(mem:read_u16(hs_addr + 4) == 2, tag .. ": image version " .. mem:read_u16(hs_addr + 4))
  check(IMAGE_SIZE == 250, tag .. ": SCORE_IMAGE_SIZE " .. IMAGE_SIZE)
  check(mem:read_u32(hs_addr + IMAGE_SIZE - 4) == fnv(hs_addr, IMAGE_SIZE - 4), tag .. ": image checksum mismatch")
  for m = 0, 1 do
    for r = 0, 9 do
      local n, s = image_row(m, r)
      check(n == tname(m, r) and s == tscore(m, r), string.format("%s: image mode %d row %d (%s %d) differs from flow table (%s %d)", tag, m, r, n, s, tname(m, r), tscore(m, r)))
    end
  end
end
local function find_row(mode, name, score)
  for r = 0, 9 do if tname(mode, r) == name and tscore(mode, r) == score then return r end end
end

local function coin_start()
  coin:set_value(1); wait(15); coin:set_value(0); wait(15) -- one coin: the first Start press opens the title mode select (no credit), the second begins play (BG4)
  until_(function() press(start); return g8(O_STATE) == S_PLAYING end, 60, "PLAYING after Start")
end
-- play a run to GAME_OVER through input only; return when NAME_ENTRY is up.
--   Arena: the hiscore_reach.lua manoeuvre: put the hero's feet on a computer balloon (test input, the game's own stomp code scores),
--   then walk off the island and drown (tests/mame/flier_drive.lua). Game.score is never written.
--   Gum Trip: the hero idles into the kill strip (input only). EXEMPTION: Trip.bonus is written to TRIP_FORCE every frame because
--   the idle hero only lives a few hundred px, below the lowest default trip row (300 points = 2400 px). The score still enters the
--   table through the game's own game over, name entry and insert path.
local function play_run(mode)
  wait(30)
  check(g8(O_GMODE) == mode, "game mode " .. g8(O_GMODE) .. " expected " .. mode)
  local drive = dofile("tests/mame/flier_drive.lua")(mem, flow_addr, flay, abtn, lbtn, rbtn)
  local driving = false
  until_(function()
    if mode == MODE_TRIP then
      mem:write_u32(flow_addr + O_BONUS, TRIP_FORCE)
    elseif g8(O_STATE) == S_PLAYING then
      if not driving and g32(O_SCORE) > ARENA_MIN then driving = true end
      if driving then drive()
      else
        abtn:set_value(0); rbtn:set_value(0); lbtn:set_value(0)
        -- Stomp the first computer flier that still has a balloon (cpu[0], then cpu[1], ...): a balloonless one stays ALIVE on the island and
        -- body contact with it would kill the (balloonless) hero first, so the hero never lingers on a flier that has no balloon left.
        local cpu_stride = flay[20] - flay[17]   -- sizeof(Flier): cpu[1].x - cpu[0].x from flier_probe.c
        for k = 0, mem:read_u8(flow_addr + flay[13]) - 1 do
          local b = flow_addr + k * cpu_stride
          if mem:read_u8(b + O_CSTATE) <= 1 and mem:read_u8(b + O_CBALL) > 0 then
            mem:write_u32(flow_addr + O_FX, mem:read_u32(b + O_CX))
            mem:write_u32(flow_addr + O_FY, mem:read_u32(b + O_CY) - 26 * 65536)
            mem:write_u32(flow_addr + O_FVX, 0)
            mem:write_u32(flow_addr + O_FVY, 0)
            break
          end
        end
      end
    end
    return g8(O_STATE) == S_OVER
  end, 6000, "GAME_OVER")
  abtn:set_value(0); rbtn:set_value(0); lbtn:set_value(0)
  check(mode ~= MODE_TRIP or g32(O_LAST) >= TRIP_FORCE, "last_score " .. g32(O_LAST) .. " below forced " .. TRIP_FORCE)
  check(mode == MODE_TRIP or g32(O_LAST) > ARENA_MIN, "last_score " .. g32(O_LAST) .. " not above " .. ARENA_MIN)
  check(g8(O_LMODE) == mode, "last_mode " .. g8(O_LMODE) .. " expected " .. mode)
  until_(function() return g8(O_STATE) == S_NAME end, 400, "NAME_ENTRY")
end
local function enter_name()
  -- (d) caption must not be drawn on the name entry rows while typing
  wait(5)
  check(caption_at(14) == nil and caption_at(13) == nil, "caption drawn on name entry rows 13/14")
  -- the game draws confirmed letters [0, pos) from entry.name and the symbol under the cursor for the rest ('_' for END); it never shows raw entry.name
  local function symchar(sy) if sy < 26 then return string.char(65 + sy) elseif sy < 36 then return string.char(48 + sy - 26) elseif sy == 36 then return " " elseif sy == 37 then return "." end return "_" end
  local pos, shown = g8(O_EPOS), {}
  for k = 0, 7 do shown[#shown + 1] = k < pos and string.char(mem:read_u8(flow_addr + O_ENAME + k)) or symchar(g8(O_ESYM + k)) end
  check(text_at(16, 13, table.concat(shown)), "name entry row 13 does not show the confirmed letters and cursor symbols [" .. table.concat(shown) .. "]")
  until_(function() press(abtn); return g8(O_EDONE) == 1 end, 40, "name entry done")
  local nm = str(flow_addr + O_ENAME, 8)
  until_(function() return g8(O_STATE) == S_REMIND end, 120, "SAVE_REMINDER")
  return nm
end

local function phase1()
  local expect_t = {}
  -- (a) defaults
  for r = 0, 9 do
    check(tname(1, r) == "GUMTRIP " and tscore(1, r) == 3000 - r * 300, string.format("trip default row %d is %s %d", r, tname(1, r), tscore(1, r)))
  end
  for r = 0, 8 do check(tscore(0, r) > tscore(0, r + 1) and tname(0, r) ~= string.rep(" ", 8), "arena default row " .. r) end
  check(#fmap == 256, "fixfont_map parsed " .. #fmap .. " entries from " .. font_h)
  local saves0 = mem:read_u32(saves_addr)
  -- (d) title: mode select rows 14/15, no caption, PRESS START row 13
  check(g8(O_STATE) == S_TITLE, "boot did not reach the title (state " .. g8(O_STATE) .. ")")
  -- state 0 is also the pre-boot value: wait until the title draw has reached the fix layer (the UniBIOS screens come first)
  until_(function() return text_at(17, 14, "ARENA") end, 900, function() return "title mode select drawn (fix writes " .. fixw .. ", last 0x" .. string.format("%x", fixlast) .. ") rows 12..16 [" .. dump_row(12) .. "|" .. dump_row(13) .. "|" .. dump_row(14) .. "|" .. dump_row(15) .. "|" .. dump_row(16) .. "]" end)
  check(text_at(17, 14, "ARENA") and text_at(17, 15, "GUM TRIP"), string.format("title mode select not on fix rows 14/15 at x 17 (cells row 14 x17..19: 0x%x 0x%x 0x%x, row 15 x17: 0x%x; want A=0x%x G=0x%x)",
    cell(17, 14), cell(18, 14), cell(19, 14), cell(17, 15), fmap[66] or -1, fmap[72] or -1))
  check(caption_at(14) == nil, "caption drawn on title row 14")
  press(dbtn)
  until_(function() return g8(O_MODE) == 1 end, 30, "Down selects Gum Trip")
  -- (b) let the title time out into the attract table; both captions and both draw counters must show up
  local d0, d1 = mem:read_u32(draws_addr), mem:read_u32(draws_addr + 4)
  local seen_a, seen_t = false, false
  until_(function() return g8(O_STATE) == S_TABLE end, 900, "attract table screen")
  for _ = 1, 520 do
    local c = caption_at(6)
    if c == 0 then seen_a = true elseif c == 1 then seen_t = true end
    if c ~= nil then
      local m, nm = c, tname(c, 0)
      check(text_at(14, 8, nm), "table row 8 name does not match mode " .. m .. " row 0 (" .. nm .. ")")
    end
    coroutine.yield()
  end
  check(seen_a and seen_t, "attract table captions seen: arena " .. tostring(seen_a) .. " trip " .. tostring(seen_t))
  check(mem:read_u32(draws_addr) > d0 and mem:read_u32(draws_addr + 4) > d1, "g_table_mode_draws did not move for both modes")
  -- (c) Gum Trip run
  until_(function() return g8(O_STATE) == S_TITLE end, 900, "title again")
  local arena_before = table_dump(0)
  coin_start()
  play_run(MODE_TRIP)
  local tscore_run = g32(O_LAST)
  local nm = enter_name()
  local row = find_row(1, nm, tscore_run)
  check(row ~= nil, "trip table has no row " .. nm .. " " .. tscore_run)
  check(table_dump(0) == arena_before, "arena table changed by a trip run")
  check(mem:read_u32(saves_addr) == saves0 + 1, "g_hiscore_saves " .. mem:read_u32(saves_addr) .. " expected " .. (saves0 + 1))
  image_checks("after trip save")
  -- (d) reminder: row 13 text kept, caption on row 14 is the trip one (draw() still draws the highlighted table under the reminder text; the screen fills in about 20 frames after the state change)
  until_(function() return text_at(9, 13, "OPEN THE MENU TO SAVE") end, 60, "save reminder row 13 text")
  check(caption_at(14) == 1, "save reminder row 14 caption is not GUM TRIP SCORES")
  check(g8(O_LMODE) == 1, "last_mode not 1 after trip run")
  expect_t.trip = { nm, tscore_run, row }
  until_(function() return g8(O_STATE) == S_TITLE end, 2000, "title after trip run")
  wait(30)
  check(caption_at(14) == 1, "title after the save reminder row 14 caption is not GUM TRIP SCORES")
  -- arena run: highlight Arena again
  local trip_before = table_dump(1)
  press(ubtn)
  until_(function() return g8(O_MODE) == 0 end, 30, "Up selects Arena")
  coin_start()
  play_run(0)
  local ascore = g32(O_LAST)
  local anm = enter_name()
  local arow = find_row(0, anm, ascore)
  check(arow ~= nil, "arena table has no row " .. anm .. " " .. ascore)
  check(table_dump(1) == trip_before, "trip table changed by an arena run")
  check(mem:read_u32(saves_addr) == saves0 + 2, "g_hiscore_saves after arena run " .. mem:read_u32(saves_addr))
  image_checks("after arena save")
  until_(function() return text_at(9, 13, "OPEN THE MENU TO SAVE") end, 60, "save reminder row 13 text (arena run)")
  check(caption_at(14) == 0, "save reminder row 14 caption is not ARENA SCORES")
  expect_t.arena = { anm, ascore, arow }
  until_(function() return g8(O_STATE) == S_TITLE end, 2000, "title after arena run (caption)")
  wait(30)
  check(caption_at(14) == 0, "title after the save reminder row 14 caption is not ARENA SCORES")
  -- the BIOS copies the work RAM block into backup RAM only when the game returns to it (main.c game_loop, g_bram_unsaved), which happens
  -- once attract resumes after the reminder; ending the boot earlier loses the arena row (the trip row survived because a title wait followed it)
  until_(function() return g8(O_STATE) == S_TITLE end, 2000, "title after arena run (backup RAM save)")
  wait(120)
  local f = io.open(expect, "w")
  f:write(string.format("%s|%d|%d|%s|%d|%d\n", expect_t.trip[1], expect_t.trip[2], expect_t.trip[3], expect_t.arena[1], expect_t.arena[2], expect_t.arena[3]))
  f:close()
  finish(true, string.format("score tables: trip %s %d row %d, arena %s %d row %d, saves %d", expect_t.trip[1], expect_t.trip[2], expect_t.trip[3], expect_t.arena[1], expect_t.arena[2], expect_t.arena[3], mem:read_u32(saves_addr)))
end

local function phase2()
  local f = io.open(expect, "r")
  check(f, "no expect file from phase 1")
  local line = f:read("*l"); f:close()
  local tn, ts, tr, an, as, ar = line:match("^(.-)|(%d+)|(%d+)|(.-)|(%d+)|(%d+)$")
  check(tn, "bad expect file: " .. tostring(line))
  wait(30)
  image_checks("second boot")
  check(tname(1, tonumber(tr)) == tn and tscore(1, tonumber(tr)) == tonumber(ts), "trip row not restored after reboot")
  check(tname(0, tonumber(ar)) == an and tscore(0, tonumber(ar)) == tonumber(as), "arena row not restored after reboot: want row " .. ar .. " " .. an .. " " .. as .. ", arena table now " .. table_dump(0))
  check(mem:read_u32(saves_addr) == 0, "g_hiscore_saves " .. mem:read_u32(saves_addr) .. " after load (expected 0, not re-saved)")
  finish(true, "second boot holds both tables and image, no resave")
end

local co
local n = 0
emu.register_frame_done(function()
  if done then return end
  n = n + 1
  if n > WATCHDOG then finish(false, "watchdog at frame " .. n) return end
  if not (coin and start and abtn and ubtn and dbtn) then finish(false, "missing input field") return end
  if not (phase_no and frame_addr and hs_addr and saves_addr and draws_addr and O_STATE and result and expect) then
    finish(false, "missing env (phase/addresses/layout/files)") return
  end
  if not co then
    if mem:read_u32(frame_addr) == 0 then return end
    co = coroutine.create(function()
      wait(30)
      if phase_no == 1 then phase1() else phase2() end
    end)
  end
  if coroutine.status(co) == "suspended" then
    local ok, err = coroutine.resume(co)
    if not ok and not done then finish(false, tostring(err)) end
  end
end)
