-- Headless check: frame counter sentinel advances; flow leaves ATTRACT after coin + start.
-- Also guards the one-boot-init rule: the BIOS issues USER commands again on coin/start
-- (command 3 title, 2 game); main() must not be re-run, so g_frame_counter must never go
-- backwards across the coin + start window, and the hiscore image in backup RAM must be
-- unchanged across it.
-- Also: BIOS_USER_MODE is 2 while PLAYING (set by main.c), a second coin during play keeps the
-- counter monotonic, the mode at 2 and the state PLAYING, and screen snapshots are written
-- (pre_start.png before start, playing.png during play) for tests/mame/check_hero_pixels.py.
-- Also: the fix layer prints with the Gumdrop font (build/gen/fix_font.h): during play the VRAM words of "SCORE" (2,5) and
-- "Balloons" (2,6, lowercase maps to capitals) equal palette 0 | fixfont_map[char], differ from the old ASCII tile numbers,
-- and the debug header cell (2,2) is the blank tile (header is off in the normal build).
-- Env: BRAWL_FIXFONT_H (path of build/gen/fix_font.h), BRAWL_FRAME_ADDR, BRAWL_FLOW_ADDR, BRAWL_HISCORE_ADDR (hex, from nm on the
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
local ss = dofile("tests/mame/start_seq.lua")(coin, start)   -- one coin, one Start begins play
local play_n = nil   -- frame at which the flow state first read PLAYING

local function image()
  local t = {}
  for i = 0, hs_size - 1 do t[#t + 1] = string.format("%02x", mem:read_u8(hs_addr + i)) end
  return table.concat(t)
end

local screen = manager.machine.screens[":screen"]

-- Fix-layer proof: shadow every VRAM word written through the LSPC (address 0x3c0000, data 0x3c0002, modulo 0x3c0004).
local fixfont_map = {}
do
  local src = io.open(os.getenv("BRAWL_FIXFONT_H")):read("a")
  local body = src:match("fixfont_map%[256%] = {(.-)}")
  for v in body:gmatch("%d+") do fixfont_map[#fixfont_map + 1] = tonumber(v) end
end
assert(#fixfont_map == 256, "fixfont_map has " .. #fixfont_map .. " entries")
local FIX_BASE, FIX_ROWS = 0x7000, 32
local vram, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c000f, "fixshadow", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 4 then vmod = data
  elseif r == 2 then vram[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff end
end)
local function fix_cell(x, y) return vram[FIX_BASE + x * FIX_ROWS + y] end
local function fix_text_ok(x, y, s)
  for i = 1, #s do
    local want = fixfont_map[s:upper():byte(i) + 1]
    if fix_cell(x + i - 1, y) ~= want or want == s:byte(i) then return false end
  end
  return true
end
local fix_msg, fix_ok = "fix font unchecked", false
local mode_play, mode_after_coin2, st_play, st_after_coin2 = nil, nil, nil, nil

local n, st_early, st_late = 0, nil, nil
local c_end
local c_first, c_last, prev = nil, nil, nil
local reset_msg = nil
local img_before, img_after = nil, nil

-- Background proof for tests/mame/check_bg_pixels.py: two snapshots BG_GAP frames apart during play plus
-- the five plane x values (g_bg_plane_x) and the plane write counter (g_bg_x_writes) the game exported at the same frame.
local BG_A, BG_B = 100, 130   -- frames after PLAYING begins: past the ROUND nn / GO! hold (90 frames), where the arena is drawn
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
  if n >= 290 and n <= 760 then
    local c = mem:read_u32(frame_addr)
    if n == 290 then c_first = c end
    if prev and c < prev and not reset_msg then
      reset_msg = string.format("counter not monotonic at frame %d: %d -> %d (user_request=%d user_mode=%d)",
        n, prev, c, mem:read_u8(USER_REQUEST), mem:read_u8(USER_MODE))
    end
    prev = c
    if n == 420 then c_last = c end
    if n == 760 then c_end = c end
  end
  if n == 320 and coin then ss.begin(n) end
  if n >= 320 and not play_n and ss.step(n, mem:read_u8(flow_addr) == 3) then play_n = n end
  if n == 300 then
    st_early = mem:read_u8(flow_addr)
    img_before = image()
  elseif n == 350 then screen:snapshot("pre_start.png")
  elseif play_n and n == play_n + BG_A then
    screen:snapshot("bg_a.png")
    bg_record("a")
  elseif play_n and n == play_n + BG_B then
    screen:snapshot("playing.png")
    bg_record("b")
    local bf = io.open(result .. ".bg", "w")
    bf:write(table.concat(bg_lines, "\n") .. "\n")
    bf:close()
    fix_ok = fix_text_ok(2, 5, "SCORE") and fix_text_ok(2, 6, "Balloons") and fix_cell(2, 2) == 255
    fix_msg = string.format("fix font %s (SCORE cell %s, header cell %s)", fix_ok and "in use" or "NOT in use",
      tostring(fix_cell(2, 5)), tostring(fix_cell(2, 2)))
    mode_play = mem:read_u8(USER_MODE)
    st_play = mem:read_u8(flow_addr)
  elseif play_n and n == play_n + 180 and coin then coin:set_value(1)
  elseif play_n and n == play_n + 195 and coin then coin:set_value(0)
  elseif play_n and n == play_n + 240 then
    mode_after_coin2 = mem:read_u8(USER_MODE)
    st_after_coin2 = mem:read_u8(flow_addr)
  elseif n == 760 then
    st_late = mem:read_u8(flow_addr)
    img_after = image()
    local img_ok = img_before == img_after
    local msg = string.format("counter %d -> %d over frames 290..420 (-> %d at 760), state %d -> %d, image %s, coin=%s start=%s, user_mode %s playing, %s after 2nd coin, state %s/%s",
      c_first, c_last, c_end, st_early, st_late, img_ok and "unchanged" or "CHANGED",
      tostring(coin ~= nil), tostring(start ~= nil), tostring(mode_play), tostring(mode_after_coin2),
      tostring(st_play), tostring(st_after_coin2))
    local play_ok = mode_play == 2 and mode_after_coin2 == 2 and st_play == 3 and st_after_coin2 == 3
    msg = msg .. "; " .. fix_msg
    if reset_msg then msg = reset_msg .. "; " .. msg end
    -- FlowState: 0..2 attract, 3 playing
    finish(reset_msg == nil and c_last > c_first and c_end > c_last and img_ok and play_ok
           and st_early <= 2 and st_late >= 3 and fix_ok, msg)
  end
end)
