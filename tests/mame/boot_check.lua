-- Headless check: frame counter sentinel advances; flow leaves ATTRACT after coin + start.
-- Also guards the one-boot-init rule: the BIOS issues USER commands again on coin/start
-- (command 3 title, 2 game); main() must not be re-run, so g_frame_counter must never go
-- backwards across the coin + start window, and the hiscore image in backup RAM must be
-- unchanged across it.
-- Also: BIOS_USER_MODE is 2 while PLAYING (set by main.c), a second coin during play keeps the
-- counter monotonic, the mode at 2 and the state PLAYING, and screen snapshots are written
-- (pre_start.png before start, playing.png during play) for tests/mame/check_hero_pixels.py.
-- Env: BRAWL_FRAME_ADDR, BRAWL_FLOW_ADDR, BRAWL_HISCORE_ADDR (hex, from nm on the
-- ELF), BRAWL_HISCORE_SIZE (hex, nm -S), BRAWL_RESULT (file).
local frame_addr = tonumber(os.getenv("BRAWL_FRAME_ADDR"), 16)
local flow_addr  = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local hs_addr    = tonumber(os.getenv("BRAWL_HISCORE_ADDR"), 16)
local hs_size    = tonumber(os.getenv("BRAWL_HISCORE_SIZE"), 16)
local result     = os.getenv("BRAWL_RESULT")
local bg_x_addr = tonumber(os.getenv("BRAWL_BG_X_ADDR"), 16)            -- g_bg_plane_x[5] (s16 each)
local bg_writes_addr = tonumber(os.getenv("BRAWL_BG_WRITES_ADDR"), 16)  -- g_bg_x_writes
local mem  = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports

-- BIOS RAM (ngdevkit bios-ram.h): BIOS_USER_REQUEST, BIOS_USER_MODE
local USER_REQUEST, USER_MODE = 0x10fdae, 0x10fdaf

local function field(tag, name)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do
    if fname == name then return f end
  end
end
local coin  = field(":AUDIO_COIN", "Coin 1")
local start = field(":edge:joy:START", "1 Player Start")

local function image()
  local t = {}
  for i = 0, hs_size - 1 do t[#t + 1] = string.format("%02x", mem:read_u8(hs_addr + i)) end
  return table.concat(t)
end

local screen = manager.machine.screens[":screen"]
local mode_play, mode_after_coin2, st_play, st_after_coin2 = nil, nil, nil, nil

local n, st_early, st_late = 0, nil, nil
local c_end
local c_first, c_last, prev = nil, nil, nil
local reset_msg = nil
local img_before, img_after = nil, nil

-- Background proof for tests/mame/check_bg_pixels.py: two snapshots BG_GAP frames apart during play plus
-- the five plane x values (g_bg_plane_x) and the plane write counter (g_bg_x_writes) the game exported at the same frame.
local BG_A, BG_B = 420, 450
local bg_lines = {}
local function bg_record(tag)
  local xs = {}
  for p = 0, 4 do xs[#xs + 1] = mem:read_i16(bg_x_addr + 2 * p) end
  bg_lines[#bg_lines + 1] = string.format("%s %s %d", tag, table.concat(xs, " "), mem:read_u32(bg_writes_addr))
end

local function finish(ok, msg)
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

emu.register_frame_done(function()
  n = n + 1
  if n >= 290 and n <= 700 then
    local c = mem:read_u32(frame_addr)
    if n == 290 then c_first = c end
    if prev and c < prev and not reset_msg then
      reset_msg = string.format("counter not monotonic at frame %d: %d -> %d (user_request=%d user_mode=%d)",
        n, prev, c, mem:read_u8(USER_REQUEST), mem:read_u8(USER_MODE))
    end
    prev = c
    if n == 420 then c_last = c end
    if n == 700 then c_end = c end
  end
  if n == 300 then
    st_early = mem:read_u8(flow_addr)
    img_before = image()
  elseif n == 320 and coin then coin:set_value(1)
  elseif n == 335 and coin then coin:set_value(0)
  elseif n == 360 and start then start:set_value(1)
  elseif n == 375 and start then start:set_value(0)
  elseif n == 350 then screen:snapshot("pre_start.png")
  elseif n == BG_A then
    screen:snapshot("bg_a.png")
    bg_record("a")
  elseif n == BG_B then
    screen:snapshot("playing.png")
    bg_record("b")
    local bf = io.open(result .. ".bg", "w")
    bf:write(table.concat(bg_lines, "\n") .. "\n")
    bf:close()
    mode_play = mem:read_u8(USER_MODE)
    st_play = mem:read_u8(flow_addr)
  elseif n == 500 and coin then coin:set_value(1)
  elseif n == 515 and coin then coin:set_value(0)
  elseif n == 560 then
    mode_after_coin2 = mem:read_u8(USER_MODE)
    st_after_coin2 = mem:read_u8(flow_addr)
  elseif n == 700 then
    st_late = mem:read_u8(flow_addr)
    img_after = image()
    local img_ok = img_before == img_after
    local msg = string.format("counter %d -> %d over frames 290..420 (-> %d at 700), state %d -> %d, image %s, coin=%s start=%s, user_mode %s playing, %s after 2nd coin, state %s/%s",
      c_first, c_last, c_end, st_early, st_late, img_ok and "unchanged" or "CHANGED",
      tostring(coin ~= nil), tostring(start ~= nil), tostring(mode_play), tostring(mode_after_coin2),
      tostring(st_play), tostring(st_after_coin2))
    local play_ok = mode_play == 2 and mode_after_coin2 == 2 and st_play == 3 and st_after_coin2 == 3
    if reset_msg then msg = reset_msg .. "; " .. msg end
    -- FlowState: 0..2 attract, 3 playing
    finish(reset_msg == nil and c_last > c_first and c_end > c_last and img_ok and play_ok
           and st_early <= 2 and st_late >= 3, msg)
  end
end)
