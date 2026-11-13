-- Headless check under UniBIOS 4.0 (make test-unibios): video state survives the BIOS
-- re-entry on coin. A real BIOS (UniBIOS, and the SNK MVS BIOS on the cabinet) clears
-- palette RAM before it sends USER command 3 (title) when a coin is inserted. nullbios
-- does not, so make test cannot see this. The resume path in src/main.c must reload the
-- palettes; before that fix the screen went black after the coin while the game ran on.
-- Asserts: palette words read before the coin (fix text palette 0 colour 1, hero palette
-- slot 2 colour 1) are back 60 frames after the coin, and g_frame_counter never goes back.
-- City palettes (CITY_PALETTE_COUNT slots x 16 words from g_bg_pal_first_entry) and the backdrop (last palette RAM entry)
-- are checked the same way: a checksum of all of them must be unchanged and nonzero.
-- Second phase (game over with a credit left): a second coin gives two credits, start, idle until
-- the hero dies with a non-ranking score. With a credit left the BIOS must keep calling the
-- VBlank callback: g_frame_counter advances on >= 90% of the 600 frames after death with no
-- 60-frame stall, flow reaches an attract state, and a start press then begins a second game
-- (FLOW_PLAYING, credit used) whose counter still advances. Regression for BIOS_USER_MODE 1
-- being set on entering GAME_OVER: UniBIOS stopped the callback and game_loop spun forever.
-- Fix layer (FX1): 120 frames after the coin the title is back and no fix cell holds tile 0x20 (the BIOS ASCII
-- space it fills the layer with; the cart blanks with tile 255), and the title text cells hold the backed font tiles.
-- COIN1: from the coin on, no frame may show BIOS space cells (tile 0x20, rows 2..29) while palette entry 0x400002 (fix palette 0
-- colour 1, the visible text colour) is non-zero. video_init commits the fix clear first, while palette 0 is still the BIOS zero.
-- Limit 0 cells: the cart never writes tile 0x20, so any such cell on a lit frame is the BIOS fill showing (unfixed ROM: see
-- thoughts/spot/2026-11-12-coin1-ne1.md for the measured frames).
-- Env: BRAWL_FRAME_ADDR, BRAWL_BG_PAL_ADDR, BRAWL_BG_PAL_BYTES (hex, nm -S size of city_palettes), BRAWL_FLOW_ADDR (hex, nm on the ELF),
-- BRAWL_REACH_LAYOUT (flow state offset first), BRAWL_RESULT (file).
local frame_addr = tonumber(os.getenv("BRAWL_FRAME_ADDR"), 16)
local bgpal_addr = tonumber(os.getenv("BRAWL_BG_PAL_ADDR"), 16)
local bgpal_words = tonumber(os.getenv("BRAWL_BG_PAL_BYTES"), 16) // 2  -- size of city_palettes (CITY_PALETTE_COUNT x 16 words)
local flow_addr  = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local lay = {}
for v in os.getenv("BRAWL_REACH_LAYOUT"):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local O_STATE = lay[1]
local O_FX, O_FVX, O_FGROUND = lay[9], lay[10], lay[11]   -- arena slice flier x, vx (16.16), on_ground (reach_probe.c)
local result     = os.getenv("BRAWL_RESULT")
local FLOW_ATTRACT_TITLE, FLOW_ATTRACT_DEMO, FLOW_PLAYING, FLOW_GAME_OVER = 0, 2, 3, 4
local AFTER_DEATH, DEATH_TIMEOUT, STALL_LIMIT = 600, 2400, 60
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local USER_REQUEST = 0x10fdae
local soot_addr = tonumber(os.getenv("BRAWL_SOOT_ADDR"), 16)  -- g_soot_range: {first tile, tile count, palette slot, ...}
-- Fix palettes 0..FIXFONT_PAL_COUNT-1 (FIX_PAL_COUNT in src/vram_layout.h; the count is read from the generated fix_font.h,
-- BRAWL_FIXFONT_H), colour 1 of each, packed into one hex string; 0 when any of them is unset.
local FIX_PAL_COUNT = tonumber(io.open(os.getenv("BRAWL_FIXFONT_H")):read("a"):match("#define FIXFONT_PAL_COUNT%s+(%d+)"))
assert(FIX_PAL_COUNT and FIX_PAL_COUNT > 0, "FIXFONT_PAL_COUNT not found in BRAWL_FIXFONT_H")
local function fix_pal_c1()
  local sig = ""
  for slot = 0, FIX_PAL_COUNT - 1 do
    local w = mem:read_u16(0x400000 + slot * 32 + 2)
    if w == 0 then return 0 end
    sig = sig .. string.format("%04x", w)
  end
  return sig
end
local PAL_HERO_C1 = 0x400000 + mem:read_u16(soot_addr + 4) * 32 + 2   -- Sootling player palette, colour 1
local COIN_FRAME, CHECK_FRAME = 900, 960
local backed = {}
for v in io.open(os.getenv("BRAWL_FIXFONT_H")):read("a"):match("fixfont_map_backed%[256%] = {(.-)}"):gmatch("%d+") do backed[#backed + 1] = tonumber(v) end
assert(#backed == 256, "fixfont_map_backed has " .. #backed .. " entries")
local FIX_BASE, FIX_ROWS, BIOS_SPACE = 0x7000, 32, 0x20
local vram, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c000f, "fixshadow", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 4 then vmod = data
  elseif r == 2 then vram[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff end
end)
-- Returns nil when the title fix layer is right, else the reason.
local function fix_title_problem()
  local stale = 0
  for x = 0, 39 do for y = 2, 29 do if ((vram[FIX_BASE + x * FIX_ROWS + y] or 0) & 0xfff) == BIOS_SPACE then stale = stale + 1 end end end
  if stale > 0 then return stale .. " fix cells still hold BIOS space tile 0x20" end
  local s = "HIGH SCORE"
  for i = 1, #s do
    local c = s:byte(i)
    local got = (vram[FIX_BASE + (11 + i - 1) * FIX_ROWS + 3] or 0) & 0xfff
    if c ~= 32 and got ~= backed[c + 1] then return string.format("title cell %d holds %03x, want %03x", 11 + i - 1, got, backed[c + 1]) end
  end
end
local function bios_space_cells()
  local stale = 0
  for x = 0, 39 do for y = 2, 29 do if ((vram[FIX_BASE + x * FIX_ROWS + y] or 0) & 0xfff) == BIOS_SPACE then stale = stale + 1 end end end
  return stale
end
local blank_lit_frames, blank_worst, blank_first = 0, 0, nil
local PAL_BACKDROP = 0x400000 + 4095 * 2

-- Position-weighted sum of the city palette words, and the backdrop word.
local function city_sum()
  local first = mem:read_u16(bgpal_addr)
  local s = 0
  for i = 0, bgpal_words - 1 do s = s + mem:read_u16(0x400000 + (first + i) * 2) * (i + 1) end
  return s, mem:read_u16(PAL_BACKDROP)
end

local coin, start
local rbtn, lbtn, abtn
for name, f in pairs(manager.machine.ioport.ports[":edge:joy:JOY1"].fields) do
  if name == "P1 Right" then rbtn = f elseif name == "P1 Left" then lbtn = f elseif name == "P1 A" then abtn = f end
end
local steering, steer_tick = false, 0
local function s32(v) return v >= 0x80000000 and v - 0x100000000 or v end
for name, f in pairs(manager.machine.ioport.ports[":AUDIO_COIN"].fields) do
  if name == "Coin 1" then coin = f end
end
-- Coin sentinel (g_coin_calls, raised by the BIOS coin vector, drained by game_loop): count button presses and sentinel rises.
local coin_addr = tonumber(os.getenv("BRAWL_COINCALLS_ADDR"), 16)
local coins_in, coin_rises, coin_last, coin_btn, coin_stray = 0, 0, 0, 0, false
local real_coin = coin
coin = {set_value = function(_, v) if v == 1 and coin_btn == 0 then coins_in = coins_in + 1 end coin_btn = v real_coin:set_value(v) end}
tap_coin = mem:install_write_tap(coin_addr & ~1, coin_addr | 1, "coincalls", function(offset, data, mask)
  local sh = (coin_addr & 1 == 0) and 8 or 0
  if (mask >> sh) & 0xff ~= 0xff then return end
  local v = (data >> sh) & 0xff
  if v == ((coin_last + 1) & 0xff) then coin_rises = coin_rises + 1; if coin_rises > coins_in then coin_stray = true end end
  coin_last = v
end)
for name, f in pairs(manager.machine.ioport.ports[":edge:joy:START"].fields) do
  if name == "1 Player Start" then start = f end
end

local function finish(ok, msg)
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

local n, prev, text_before, hero_before, saw_title = 0, nil, nil, nil, false
local city_before, back_before
local p2, p2_n, p2_msg = nil, 0, nil   -- second phase state, frames in it, first phase PASS text
local move, stall, run, last_c, saw_attract, play_c0 = 0, 0, 0, nil, false, nil

-- One frame of "stay alive on the island, then fall into the water" (see the play phase).
local function steer(st)
  if st == FLOW_PLAYING then
    local fx = s32(mem:read_u32(flow_addr + O_FX)) / 65536
    local vx = s32(mem:read_u32(flow_addr + O_FVX)) / 65536
    local ground = mem:read_u8(flow_addr + O_FGROUND)
    -- A computer flier can bump the player back onto the island (body-contact reflect): walk off again.
    if steering and ground == 1 then steering = false end
    if not steering and (ground == 1 or fx < 212) then
      rbtn:set_value(1)
    else
      steering = true
      rbtn:set_value(0)
      if vx > 0 then
        lbtn:set_value(1); abtn:set_value((steer_tick % 6) < 2 and 1 or 0); steer_tick = steer_tick + 1
      else
        lbtn:set_value(0); abtn:set_value(0)
      end
    end
  end
end

-- COIN-ITEM2 phases (after the second game): verdicts a..e, COIN2 measurement. Every verdict is recorded; none stops the run.
local verdicts, die_next, last_cr, last_st, coin_next, settle_games = {}, nil, nil, nil, "b", 0
local function cr() return mem:read_u8(0x10fe00) end
local function verdict(name, ok, ev)
  verdicts[#verdicts + 1] = (ok and "[PASS] " or "[FAIL] ") .. name .. ": " .. ev
  print("BRAWL_VERDICT " .. verdicts[#verdicts])
end
local function press(btn, n0, len, n) btn:set_value((n >= n0 and n < n0 + len) and 1 or 0) end
local trace, first_change, first_play = {}, nil, nil
local coin2 = {black = 0, notitle = 0, first_black = nil, last_black = nil, users = {}}

local function phase2()
  p2_n = p2_n + 1
  local c = mem:read_u32(frame_addr)
  local st = mem:read_u8(flow_addr + O_STATE)
  if p2 == "coin" then
    if p2_n == 1 then coin:set_value(1) elseif p2_n == 16 then coin:set_value(0) end
    if p2_n >= 46 then p2, p2_n = "start", 0 end
  elseif p2 == "start" then
    -- one Start press takes exactly one credit and begins the highlighted mode (START-EATS-CREDIT)
    start:set_value(((p2_n - 1) % 60) < 15 and 1 or 0)
    if p2_n == 50 and st ~= FLOW_PLAYING then finish(false, "START-EATS-CREDIT: 50 frames after Start the game has not begun (flow state " .. st .. ", credit byte " .. mem:read_u8(0x10fe00) .. ")") return end
    if p2_n == 50 and mem:read_u8(0x10fe00) ~= 1 then finish(false, "the first Start did not take exactly one credit (two coins, credit byte " .. mem:read_u8(0x10fe00) .. ", want 1)") return end
    if st == FLOW_PLAYING then start:set_value(0); p2, p2_n = "play", 0
    elseif p2_n > 240 then finish(false, "start with two credits never reached FLOW_PLAYING") end
  elseif p2 == "play" then
    -- The flier stays alive on the island with no input: walk off the right edge, steer back over the gap with
    -- left + flap until the horizontal speed is gone, then fall into the water (as tests/mame/flier_check.lua).
    steer(st)
    if st == FLOW_GAME_OVER then rbtn:set_value(0); lbtn:set_value(0); abtn:set_value(0); p2, p2_n, last_c = "watch", 0, c
    elseif p2_n > DEATH_TIMEOUT then finish(false, "hero never died (flow state " .. st .. ")") end
  elseif p2 == "watch" then
    if c ~= last_c then move, run = move + 1, 0 else run = run + 1; if run > stall then stall = run end end
    last_c = c
    if st <= FLOW_ATTRACT_DEMO then saw_attract = true end
    if p2_n >= AFTER_DEATH then
      if move < AFTER_DEATH * 0.9 or stall >= STALL_LIMIT then
        finish(false, string.format("frame counter froze after game over with a credit left (advanced %d of %d frames, longest stall %d, flow state %d)",
          move, AFTER_DEATH, stall, st))
      elseif not saw_attract then
        finish(false, "flow never reached an attract state after game over (state " .. st .. ")")
      end
      p2, p2_n = "again", 0
    end
  elseif p2 == "again" then
    start:set_value(((p2_n - 1) % 60) < 15 and 1 or 0) -- one press begins the game
    if st == FLOW_PLAYING then start:set_value(0); p2, p2_n, play_c0 = "again_run", 0, c
    elseif p2_n > 300 then finish(false, "start after game over never began a second game (state " .. st .. ")") end
  elseif p2 == "again_run" and p2_n == 120 then
    if c - play_c0 < 100 then
      finish(false, string.format("second game counter stalled: %d -> %d in 120 frames", play_c0, c))
    else
      p2_msg = p2_msg .. string.format("; game over with a credit left kept running (advanced %d of %d frames, longest stall %d), second game started", move, AFTER_DEATH, stall)
      steering = false; p2, p2_n, die_next = "die", 0, "e"
    end
  elseif p2 == "die" then
    if p2_n == 1 or cr() ~= last_cr then print(string.format("BRAWL_LOG die(%s) +%d credit %02x state %d", die_next, p2_n, cr(), st)) end
    last_cr = cr()
    steer(st)
    if st == FLOW_GAME_OVER then rbtn:set_value(0); lbtn:set_value(0); abtn:set_value(0); p2, p2_n = "die_wait", 0
    elseif p2_n > DEATH_TIMEOUT then finish(false, "hero never died in phase " .. die_next .. " (state " .. st .. ")") end
  elseif p2 == "die_wait" then
    if cr() ~= last_cr or st ~= last_st or p2_n % 120 == 0 then print(string.format("BRAWL_LOG die_wait(%s) +%d credit %02x state %d", die_next, p2_n, cr(), st)) end
    last_cr, last_st = cr(), st
    if st <= FLOW_ATTRACT_DEMO and p2_n > 30 then p2, p2_n = die_next, 0
    elseif p2_n > 1200 then finish(false, "no attract after game over before phase " .. die_next .. " (state " .. st .. ")") end
  elseif p2 == "e" then -- Start with 0 credits changes nothing
    press(start, 1, 15, p2_n)
    if p2_n == 90 then
      verdict("e Start with 0 credits", cr() == 0 and st ~= FLOW_PLAYING, string.format("credit byte %02x, flow state %d", cr(), st))
      p2, p2_n = "a_wait", 0
    end
  elseif p2 == "a_wait" then -- need a non-title attract screen for the coin
    if st == FLOW_ATTRACT_DEMO then p2, p2_n = "a", 0   -- the demo, so the coin also has to clear the how-to-play overlay
    elseif p2_n > 7500 then verdict("a coin during attract", false, "no demo in 7500 frames"); p2, p2_n = "b_coin", 0 end
  elseif p2 == "a" then
    press(coin, 1, 6, p2_n)
    local bd, fp = mem:read_u16(PAL_BACKDROP), fix_pal_c1()
    if p2_n >= 2 and p2_n <= 70 then
      local blk = (bd == 0 or fp == 0)
      if blk then coin2.black = coin2.black + 1; coin2.first_black = coin2.first_black or p2_n; coin2.last_black = p2_n end
      if fix_title_problem() then coin2.notitle = coin2.notitle + 1 end
      local u = mem:read_u8(USER_REQUEST)
      if blk then coin2.users[#coin2.users + 1] = string.format("%d:u%d", p2_n, u) end
    end
    if p2_n == 8 then
      coin2.title8 = st
      for x = 1, 13 do for y = 21, 26 do   -- overlay icon tiles are 0x400..0x43A (src/vram_layout.h ATTRACT_FIX_BASE, 59 tiles)
        local t = (vram[FIX_BASE + x * FIX_ROWS + y] or 0) & 0xfff
        if t >= 0x400 and t <= 0x43A then coin2.overlay = (coin2.overlay or 0) + 1 end
      end end
    end
    if p2_n == 70 then
      verdict("a coin during attract", coin2.title8 == FLOW_ATTRACT_TITLE and cr() == 1, string.format("8 frames after coin flow state %d (want 0), credit byte %02x (want 01)", coin2.title8, cr()))
      verdict("COIN2 measurement", true, string.format("black frames (backdrop 4095 == 0 or fix palette colour 1 == 0) %d, first +%d last +%d; frames without clean title fix layer %d; USER_REQUEST on black frames [%s]",
        coin2.black, coin2.first_black or -1, coin2.last_black or -1, coin2.notitle, table.concat(coin2.users, " ")))
      verdict("a coin clears the overlay", (coin2.overlay or 0) == 0, string.format("%d overlay icon cells left 8 frames after the coin", coin2.overlay or 0))
      p2, p2_n = "b_coin", 0
    end
  elseif p2 == "settle" then
    -- Game over with a credit left: the BIOS starts the next game at once (measured below), so play on until credit 0 in attract.
    if st == FLOW_PLAYING then settle_games = settle_games + 1; p2, p2_n = "die", 0
    elseif cr() == 0 and p2_n > 10 then p2, p2_n, coin_next = "b_coin", 0, "c"
    elseif p2_n > 300 then finish(false, "settle: credit byte " .. cr() .. " but no game and no credit loss for 300 frames (state " .. st .. ")") end
  elseif p2 == "b_coin" then -- second credit
    press(coin, 1, 6, p2_n)
    if p2_n == 40 then p2, p2_n, trace = coin_next, 0, {} end
  elseif p2 == "b" then
    local c0 = 2
    if p2_n == 1 then trace.before = cr() end
    press(start, 1, 15, p2_n)
    trace[#trace + 1] = string.format("%02x", cr())
    if p2_n == 150 then
      verdict("b one Start with 2 credits", trace.before == 2 and cr() == 1 and st == FLOW_PLAYING, string.format("credit before %02x after %02x (want 02 -> 01), flow state %d (want 3); trace every frame: %s", trace.before, cr(), st, table.concat(trace, ",", 1, 150):gsub("(%x%x,)%1+", "%1*")))
      steering = false; p2, p2_n, die_next = "die", 0, "settle"
    end
  elseif p2 == "c" then -- A only, one credit banked
    if p2_n == 1 then trace = {before = cr()} end
    press(abtn, 1, 5, p2_n)
    trace[#trace + 1] = string.format("%02x", cr())
    if st == FLOW_PLAYING and not first_play then first_play = p2_n end
    if p2_n == 180 then
      local steady, p = true, first_play or 1
      for i = p + 5, 180 do if trace[i] ~= trace[180] then steady = false end end
      verdict("c one A press with a credit", trace.before == 1 and cr() == 0 and first_play ~= nil and steady, string.format("[settle: BIOS started %d extra game(s) after b's game over with a credit left] credit before %02x after %02x (want 01 -> 00), PLAYING at +%s, byte steady from +%d on: %s; trace: %s",
        settle_games, trace.before, cr(), tostring(first_play), p + 5, tostring(steady), table.concat(trace, ",", 1, 180):gsub("(%x%x,)%1+", "%1*")))
      abtn:set_value(0)
      steering = false; p2, p2_n, die_next = "die", 0, "d_coin"
    end
  elseif p2 == "d_coin" then
    press(coin, 1, 6, p2_n)
    if p2_n == 60 then
      if cr() ~= 1 then verdict("d precondition", false, "credit byte " .. string.format("%02x", cr()) .. " after coin, want 01") end
      p2, p2_n, trace, first_change = "d", 0, {}, nil
    end
  elseif p2 == "d" then -- one credit, no press: measure the BIOS title timeout
    if not first_change and (cr() ~= 1 or st == FLOW_PLAYING) then first_change = p2_n; trace.st, trace.cr = st, cr() end
    if p2_n == 3300 or first_change then
      -- The BIOS title timer (about 30 s) forces a start through player_start; the cart cannot refuse that without losing the
      -- credit. So d asserts the invariant (credit gone only together with a running game) and reports the measured timeout.
      verdict("d credit, no press (BIOS title timeout)", not first_change or (trace.cr == 0 and trace.st == FLOW_PLAYING), first_change and string.format("after %d frames (%.1f s) credit byte %02x, flow state %d: the BIOS forced a start, credit and game together (Require Start is not possible against the BIOS timer)", first_change, first_change / 60, trace.cr, trace.st)
        or string.format("%d frames (%.1f s) with a credit and no press: credit byte stayed 01, flow never reached PLAYING", p2_n, p2_n / 60))
      verdict("f coin sentinel", coin_rises == coins_in and not coin_stray, string.format("%d coins inserted, g_coin_calls rose %d times, a rise without a coin: %s", coins_in, coin_rises, tostring(coin_stray)))
      local bad = false
      for _, v in ipairs(verdicts) do if v:sub(1, 6) == "[FAIL]" then bad = true end end
      finish(not bad, p2_msg .. "\n" .. table.concat(verdicts, "\n"))
    end
  end
end

-- U3b: the BIOS eyecatcher draws its text with fix palette 15 (U3 report: blocks A and B, F334-F617); the observable is block A, fix tiles 0x200-0x25F in palette 15 before the game's first frame
-- (g_frame_counter still 0). With the cartridge header eyecatcher mode set to "none" no fix cell may hold those tiles in palette 15 in that window.
local eye_cells, eye_first = 0, nil
local function eyecatcher_cells()
  local k = 0
  for x = 0, 39 do for y = 0, 31 do local w = vram[FIX_BASE + x * FIX_ROWS + y] or 0
    if (w >> 12) == 15 and (w & 0xfff) >= 0x200 and (w & 0xfff) < 0x260 then k = k + 1 end end end
  return k
end

emu.register_frame_done(function()
  n = n + 1
  if n < COIN_FRAME - 20 and mem:read_u32(frame_addr) == 0 then
    local k = eyecatcher_cells()
    if k > eye_cells then eye_cells = k end
    if k > 0 then eye_first = eye_first or n end
  end
  if n == COIN_FRAME - 1 and eye_cells > 0 then
    finish(false, string.format("U3b: BIOS eyecatcher drew up to %d eyecatcher fix cells before the game's first frame (first at frame %d)", eye_cells, eye_first))
    return
  end
  if p2 then phase2() return end
  if n >= COIN_FRAME - 20 then
    local c = mem:read_u32(frame_addr)
    if prev and c < prev then
      finish(false, string.format("counter not monotonic at frame %d: %d -> %d", n, prev, c))
      return
    end
    prev = c
  end
  if n == COIN_FRAME - 1 then
    text_before, hero_before = fix_pal_c1(), mem:read_u16(PAL_HERO_C1)
    city_before, back_before = city_sum()
    if text_before == 0 or hero_before == 0 or prev == 0 or city_before == 0 or back_before == 0 then
      finish(false, string.format("game not running before coin (text %s hero %04x counter %d)",
        text_before, hero_before, prev))
      return
    end
  elseif n == COIN_FRAME then coin:set_value(1)
  elseif n == COIN_FRAME + 6 then coin:set_value(0)
  end
  if n > COIN_FRAME and mem:read_u8(USER_REQUEST) == 3 then saw_title = true end
  if n > COIN_FRAME and n <= COIN_FRAME + 120 and mem:read_u16(0x400002) ~= 0 then
    local st = bios_space_cells()
    if st > 0 then
      blank_lit_frames = blank_lit_frames + 1
      if st > blank_worst then blank_worst = st end
      blank_first = blank_first or n
    end
  end
  if n == CHECK_FRAME then
    local t, h = fix_pal_c1(), mem:read_u16(PAL_HERO_C1)
    if not saw_title then
      finish(false, "BIOS never sent USER command 3 after the coin")
    elseif t ~= text_before or h ~= hero_before then
      finish(false, string.format("palettes lost after coin: text %s (was %s) hero %04x (was %04x)",
        t, text_before, h, hero_before))
    else
      p2_msg = string.format("palettes kept after UniBIOS coin re-entry (text %s hero %04x city sum %d backdrop %04x)", t, h, city_before, back_before)
    end
  end
  if n == COIN_FRAME + 120 then
    if blank_lit_frames > 0 then
      finish(false, string.format("COIN1: BIOS space tiles visible on %d lit frames after the coin (first at frame +%d, worst %d cells)", blank_lit_frames, blank_first - COIN_FRAME, blank_worst))
      return
    end
    local why = fix_title_problem()
    if why then finish(false, "fix layer after UniBIOS coin: " .. why) return end
    p2_msg = p2_msg .. "; fix layer clean (no BIOS space tiles, title text on the cart font)"
    p2 = "coin"
  end
end)
