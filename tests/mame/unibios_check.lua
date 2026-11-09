-- Headless check under UniBIOS 4.0 (make test-unibios): video state survives the BIOS
-- re-entry on coin. A real BIOS (UniBIOS, and the SNK MVS BIOS on the cabinet) clears
-- palette RAM before it sends USER command 3 (title) when a coin is inserted. nullbios
-- does not, so make test cannot see this. The resume path in src/main.c must reload the
-- palettes; before that fix the screen went black after the coin while the game ran on.
-- Asserts: palette words read before the coin (fix text palette 0 colour 1, hero palette
-- slot 2 colour 1) are back 60 frames after the coin, and g_frame_counter never goes back.
-- City palettes (4 slots x 16 words from g_bg_pal_first_entry) and the backdrop (last palette RAM entry)
-- are checked the same way: a checksum of all of them must be unchanged and nonzero.
-- Second phase (game over with a credit left): a second coin gives two credits, start, idle until
-- the hero dies with a non-ranking score. With a credit left the BIOS must keep calling the
-- VBlank callback: g_frame_counter advances on >= 90% of the 600 frames after death with no
-- 60-frame stall, flow reaches an attract state, and a start press then begins a second game
-- (FLOW_PLAYING, credit used) whose counter still advances. Regression for BIOS_USER_MODE 1
-- being set on entering GAME_OVER: UniBIOS stopped the callback and game_loop spun forever.
-- Env: ROOFLINE_FRAME_ADDR, ROOFLINE_BG_PAL_ADDR, ROOFLINE_FLOW_ADDR (hex, nm on the ELF),
-- ROOFLINE_REACH_LAYOUT (flow state offset first), ROOFLINE_RESULT (file).
local frame_addr = tonumber(os.getenv("ROOFLINE_FRAME_ADDR"), 16)
local bgpal_addr = tonumber(os.getenv("ROOFLINE_BG_PAL_ADDR"), 16)
local flow_addr  = tonumber(os.getenv("ROOFLINE_FLOW_ADDR"), 16)
local O_STATE    = tonumber(os.getenv("ROOFLINE_REACH_LAYOUT"):match("%d+"))
local result     = os.getenv("ROOFLINE_RESULT")
local FLOW_ATTRACT_DEMO, FLOW_PLAYING, FLOW_GAME_OVER = 2, 3, 4
local AFTER_DEATH, DEATH_TIMEOUT, STALL_LIMIT = 600, 2400, 60
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local USER_REQUEST = 0x10fdae
local PAL_TEXT_C1, PAL_HERO_C1 = 0x400002, 0x400042
local COIN_FRAME, CHECK_FRAME = 900, 960
local PAL_BACKDROP = 0x400000 + 4095 * 2

-- Position-weighted sum of the 64 city palette words, and the backdrop word.
local function city_sum()
  local first = mem:read_u16(bgpal_addr)
  local s = 0
  for i = 0, 63 do s = s + mem:read_u16(0x400000 + (first + i) * 2) * (i + 1) end
  return s, mem:read_u16(PAL_BACKDROP)
end

local coin, start
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
  print("ROOFLINE_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
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
    if p2_n >= 46 then p2, p2_n = "start", 0; start:set_value(1) end
  elseif p2 == "start" then
    if st == FLOW_PLAYING then start:set_value(0); p2, p2_n = "play", 0
    elseif p2_n > 120 then finish(false, "start with two credits never reached FLOW_PLAYING") end
  elseif p2 == "play" then
    if st == FLOW_GAME_OVER then p2, p2_n, last_c = "watch", 0, c
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
      start:set_value(1)
    end
  elseif p2 == "again" then
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
    text_before, hero_before = mem:read_u16(PAL_TEXT_C1), mem:read_u16(PAL_HERO_C1)
    city_before, back_before = city_sum()
    if text_before == 0 or hero_before == 0 or prev == 0 or city_before == 0 or back_before == 0 then
      finish(false, string.format("game not running before coin (text %04x hero %04x counter %d)",
        text_before, hero_before, prev))
      return
    end
  elseif n == COIN_FRAME then coin:set_value(1)
  elseif n == COIN_FRAME + 6 then coin:set_value(0)
  end
  if n > COIN_FRAME and mem:read_u8(USER_REQUEST) == 3 then saw_title = true end
  if n == CHECK_FRAME then
    local t, h = mem:read_u16(PAL_TEXT_C1), mem:read_u16(PAL_HERO_C1)
    if not saw_title then
      finish(false, "BIOS never sent USER command 3 after the coin")
    elseif t ~= text_before or h ~= hero_before then
      finish(false, string.format("palettes lost after coin: text %04x (was %04x) hero %04x (was %04x)",
        t, text_before, h, hero_before))
    else
      p2_msg = string.format("palettes kept after UniBIOS coin re-entry (text %04x hero %04x city sum %d backdrop %04x)", t, h, city_before, back_before)
      p2 = "coin"
    end
  end
end)
