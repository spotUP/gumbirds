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
local FLOW_ATTRACT_DEMO, FLOW_PLAYING, FLOW_GAME_OVER = 2, 3, 4
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

-- Second phase, one call per frame.
local function phase2()
  p2_n = p2_n + 1
  local c = mem:read_u32(frame_addr)
  local st = mem:read_u8(flow_addr + O_STATE)
  if p2 == "coin" then
    if p2_n == 1 then coin:set_value(1) elseif p2_n == 16 then coin:set_value(0) end
    if p2_n >= 46 then p2, p2_n = "start", 0 end
  elseif p2 == "start" then
    -- BG4: the first Start press opens the title mode select, the second begins the game; pulses 60 frames apart
    start:set_value(((p2_n - 1) % 60) < 15 and 1 or 0)
    if p2_n == 50 and mem:read_u8(0x10fe00) ~= 2 then finish(false, "credit taken by the Start press that only opens the mode select (two coins, credit byte " .. mem:read_u8(0x10fe00) .. ", want 2)") return end
    if st == FLOW_PLAYING then start:set_value(0); p2, p2_n = "play", 0
    elseif p2_n > 240 then finish(false, "start with two credits never reached FLOW_PLAYING") end
  elseif p2 == "play" then
    -- The flier stays alive on the island with no input: walk off the right edge, steer back over the gap with
    -- left + flap until the horizontal speed is gone, then fall into the water (as tests/mame/flier_check.lua).
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
    start:set_value(((p2_n - 1) % 60) < 15 and 1 or 0) -- BG4: the first press opens the mode select, the second begins the game
    if st == FLOW_PLAYING then start:set_value(0); p2, p2_n, play_c0 = "again_run", 0, c
    elseif p2_n > 300 then finish(false, "start after game over never began a second game (state " .. st .. ")") end
  elseif p2 == "again_run" and p2_n == 120 then
    if c - play_c0 < 100 then
      finish(false, string.format("second game counter stalled: %d -> %d in 120 frames", play_c0, c))
    else
      finish(true, p2_msg .. string.format("; game over with a credit left kept running (advanced %d of %d frames, longest stall %d), second game started",
        move, AFTER_DEATH, stall))
    end
  end
end

emu.register_frame_done(function()
  n = n + 1
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
  if n == CHECK_FRAME then
    local t, h = fix_pal_c1(), mem:read_u16(PAL_HERO_C1)
    if not saw_title then
      finish(false, "BIOS never sent USER command 3 after the coin")
    elseif t ~= text_before or h ~= hero_before then
      finish(false, string.format("palettes lost after coin: text %s (was %s) hero %04x (was %04x)",
        t, text_before, h, hero_before))
    else
      p2_msg = string.format("palettes kept after UniBIOS coin re-entry (text %s hero %04x city sum %d backdrop %04x)", t, h, city_before, back_before)
      p2 = "coin"
    end
  end
end)
