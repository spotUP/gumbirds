-- Headless check: frame counter sentinel advances; flow leaves ATTRACT after coin + start.
-- Also guards the one-boot-init rule: the BIOS issues USER commands again on coin/start
-- (command 3 title, 2 game); main() must not be re-run, so g_frame_counter must never go
-- backwards across the coin + start window, and the hiscore image in backup RAM must be
-- unchanged across it.
-- Also: BIOS_USER_MODE is 2 while PLAYING (set by main.c), a second coin during play keeps the
-- counter monotonic, the mode at 2 and the state PLAYING, and screen snapshots are written
-- (pre_start.png before start, playing.png during play) for tests/mame/check_hero_pixels.py.
-- Env: ROOFLINE_FRAME_ADDR, ROOFLINE_FLOW_ADDR, ROOFLINE_HISCORE_ADDR (hex, from nm on the
-- ELF), ROOFLINE_HISCORE_SIZE (hex, nm -S), ROOFLINE_RESULT (file).
local frame_addr = tonumber(os.getenv("ROOFLINE_FRAME_ADDR"), 16)
local flow_addr  = tonumber(os.getenv("ROOFLINE_FLOW_ADDR"), 16)
local hs_addr    = tonumber(os.getenv("ROOFLINE_HISCORE_ADDR"), 16)
local hs_size    = tonumber(os.getenv("ROOFLINE_HISCORE_SIZE"), 16)
local result     = os.getenv("ROOFLINE_RESULT")
local bg_scroll_addr = tonumber(os.getenv("ROOFLINE_BG_SCROLL_ADDR"), 16)  -- g_bg_scroll_px[3]
local bg_writes_addr = tonumber(os.getenv("ROOFLINE_BG_WRITES_ADDR"), 16)  -- g_bg_column_writes
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

-- Active obstacles (type x y w h, pixels) from RAM, for check_obstacle_pixels.py. Offsets come from
-- tests/mame/layout_probe.c compiled for the 68000: first_offset size count x y w h type active.
local lay = {}
for v in (os.getenv("ROOFLINE_OBS_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local function active_obstacles()
  local t = {}
  for i = 0, lay[3] - 1 do
    local a = flow_addr + lay[1] + i * lay[2]
    if mem:read_u8(a + lay[9]) ~= 0 then
      local function s16(o) local v = mem:read_u16(a + o); return v >= 0x8000 and v - 0x10000 or v end
      t[#t + 1] = {mem:read_u8(a + lay[8]), mem:read_u32(a + lay[4]) // 256, s16(lay[5]), s16(lay[6]), s16(lay[7])}
    end
  end
  return t
end
-- First frame (after play started, state PLAYING) with an obstacle fully on screen: snapshot it and
-- write the boxes. Checked every frame, because the first spawn time depends on the seed.
local obs_done = false
local function snapshot_obstacles()
  if obs_done or n < 380 or mem:read_u8(flow_addr) ~= 3 then return end
  local list = active_obstacles()
  local ok = #list > 0
  for _, o in ipairs(list) do if o[2] < 60 or o[2] + o[4] > 300 then ok = false end end
  if not ok then return end
  obs_done = true
  screen:snapshot("obstacles.png")
  local f = io.open(result .. ".obs", "w")
  for _, o in ipairs(list) do f:write(string.format("%d %d %d %d %d\n", o[1], o[2], o[3], o[4], o[5])) end
  f:close()
end

-- Background proof for tests/mame/check_bg_pixels.py: two snapshots BG_GAP frames apart during play plus
-- the scroll values and the column write counter the game exported at the same frame.
local BG_A, BG_B = 420, 450
local bg_lines = {}
local function bg_record(tag)
  bg_lines[#bg_lines + 1] = string.format("%s %d %d %d %d", tag, mem:read_u32(bg_scroll_addr),
    mem:read_u32(bg_scroll_addr + 4), mem:read_u32(bg_scroll_addr + 8), mem:read_u32(bg_writes_addr))
end

local function finish(ok, msg)
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("ROOFLINE_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

emu.register_frame_done(function()
  n = n + 1
  snapshot_obstacles()
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
