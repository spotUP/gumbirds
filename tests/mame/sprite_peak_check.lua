-- Gameplay sprites per scanline (make test-sprite-peak, plan 2026-11-10-neo-geo-graphics-max.md G1). Measures the real
-- worst case of the gameplay slot range (object pool + hero, src/sprite_slots.h POOL_SPRITE_BASE .. HERO_SPRITE +
-- HERO_SPRITE_COUNT - 1) against SB_GAMEPLAY_PER_LINE. Each frame it reads the SCB3/SCB4 shadow (Lua write tap on
-- the VRAM port, as slot_order_check.lua), resolves sticky chains (a sticky sprite takes y and height of its head, x =
-- head x + 16 per column), and counts per screen line 0..223 the visible sprites covering it (height > 0, on screen in x).
-- The match is forced to the maximum computer flier count (matches_won = 4 -> CPU_MAX 3 at match start, 4 fliers with
-- the player). On some frames every flier is pinned to one height (feet 124, lines 92..123) so they overlap the widest
-- island (112 px, 7 sprites, lines 104..119). The island range is counted the same way and added per line to the gameplay
-- count: the sum is reported and must not exceed SB_GAMEPLAY_PER_LINE + the island row's per_line (the budget the host test sums).
-- Records the maximum per line for natural play and for pinned frames, and the frame.
-- Env: BRAWL_PEAK_LAYOUT (tests/mame/peak_probe.c output), BRAWL_FLOW_ADDR, BRAWL_RESULT, BRAWL_PEAK_FRAMES (playing frames).
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result    = os.getenv("BRAWL_RESULT")
local TOTAL     = tonumber(os.getenv("BRAWL_PEAK_FRAMES") or "6000")
local ISL_LINE  = 7    -- island row per_line (src/core/sprite_budget.c; duplicated like LIMIT)
local LIMIT     = 18   -- SB_GAMEPLAY_PER_LINE (src/core/sprite_budget.h; duplicated, no shared generated value)
local lay = {}
for v in (os.getenv("BRAWL_PEAK_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local S_FIRST, S_END, O_STATE, O_CPUN, O_WON, O_PX, O_PY, O_C0X, O_C0Y, FSIZE, O_ALIVE, O_PBAL, O_PSTATE, O_FRAME, I_FIRST, I_END =
  table.unpack(lay)
local STATE_PLAYING = 3
local SCB3, SCB4 = 0x8200, 0x8400
local PIN_FEET = 124

local mem   = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, name)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname == name then return f end end
end
local coin  = field(":AUDIO_COIN", "Coin 1")
local start = field(":edge:joy:START", "1 Player Start")

local vram, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "peakvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then vram[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
  elseif r == 4 then vmod = data end
end)

local function finish(ok, msg)
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

-- sprites of the gameplay range covering each line this frame (shared counter, tests/mame/sprite_line_count.lua)
local line_count = dofile(((debug and debug.getinfo and debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")) or "tests/mame") .. "/sprite_line_count.lua")
local function count_lines(first, last) return line_count.count(vram, first, last) end   -- (all sprites with height > 0, on screen only)

local function ranges(arr, v)
  local out, a = {}, nil
  for y = 0, 224 do
    local hit = y < 224 and arr[y] == v
    if hit and not a then a = y end
    if not hit and a then out[#out + 1] = (a == y - 1) and tostring(a) or (a .. "-" .. (y - 1)); a = nil end
  end
  return table.concat(out, ",")
end

local since_nonplay, played, last_frame = 0, 0, 1e9
local poked = false
local peak = { nat = { v = 0, frame = 0 }, pin = { v = 0, frame = 0 } }
local per_line = { nat = {}, pin = {} }
for y = 0, 223 do per_line.nat[y] = 0; per_line.pin[y] = 0 end
local cpu6_frames, pin_frames, resets = 0, 0, 0
local scr_max = 0   -- printed only: the earlier on-screen-x-only figure for the gameplay range
local both_max, isl_max = { v = 0, y = 0 }, 0 -- island + gameplay sprites on one line (max, its line), most island sprites on one line

emu.register_frame_done(function() local ok_, err_ = pcall(function()
  local state = mem:read_u8(flow_addr + O_STATE)
  if state ~= STATE_PLAYING then
    since_nonplay = since_nonplay + 1
    local k = since_nonplay % 200
    if since_nonplay > 300 then
      coin:set_value((k >= 60 and k < 75) and 1 or 0)
      start:set_value((k >= 100 and k < 115) and 1 or 0)
    end
    poked = false
    return
  end
  since_nonplay = 0
  coin:set_value(0); start:set_value(0)
  played = played + 1
  local gframe = mem:read_u32(flow_addr + O_FRAME)
  if gframe < last_frame then poked = false; resets = resets + 1 end
  last_frame = gframe
  local cpun = mem:read_u8(flow_addr + O_CPUN)
  if not poked and cpun > 0 and cpun < 3 then
    -- restart the match with the maximum computer flier count (game.c match_start reads matches_won when cpu_count is 0)
    mem:write_u8(flow_addr + O_WON, 4)
    mem:write_u8(flow_addr + O_CPUN, 0)
    poked = true
  end
  local pinned = (played % 1000) >= 600 and (played % 1000) < 800
  if pinned then
    local cy = (PIN_FEET - 6) * 65536
    mem:write_u32(flow_addr + O_PY, cy)
    for i = 0, 2 do mem:write_u32(flow_addr + O_C0Y + i * FSIZE, cy) end
    pin_frames = pin_frames + 1
  end
  if cpun == 3 then cpu6_frames = cpu6_frames + 1 end
  local cnt, cnt_scr = count_lines(S_FIRST, S_END)
  local icnt = count_lines(I_FIRST, I_END)
  local key = pinned and "pin" or "nat"
  local pk = peak[key]
  for y = 0, 223 do
    if cnt[y] + icnt[y] > both_max.v then both_max.v = cnt[y] + icnt[y]; both_max.y = y end
    if icnt[y] > isl_max then isl_max = icnt[y] end
    if cnt[y] > per_line[key][y] then per_line[key][y] = cnt[y] end
    if cnt_scr[y] > scr_max then scr_max = cnt_scr[y] end
    if cnt[y] > pk.v then pk.v = cnt[y]; pk.frame = played; pk.cpun = cpun; pk.alive = mem:read_u8(flow_addr + O_ALIVE); pk.pstate = mem:read_u8(flow_addr + O_PSTATE) end
  end
  if played >= TOTAL then
    local both = {}
    for y = 0, 223 do both[y] = math.max(per_line.nat[y], per_line.pin[y]) end
    local prof, last, start_y = {}, -1, 0
    for y = 0, 224 do
      local v = y < 224 and both[y] or -2
      if v ~= last then
        if last >= 0 then prof[#prof + 1] = string.format("%d-%d:%d", start_y, y - 1, last) end
        last, start_y = v, y
      end
    end
    print("BRAWL_PROFILE " .. table.concat(prof, " "))
    local msg = string.format(
      "natural peak %d at playing frame %d (cpu %s, alive %s, player state %s) lines %s; pinned peak %d at playing frame %d lines %s; frames with 3 computer fliers %d of %d, pinned frames %d, game restarts %d; island max %d, island + gameplay max %d at line %d (limit %d); gameplay peak counting only sprites on screen in x (printed, not asserted) %d",
      peak.nat.v, peak.nat.frame, tostring(peak.nat.cpun), tostring(peak.nat.alive), tostring(peak.nat.pstate), ranges(per_line.nat, peak.nat.v),
      peak.pin.v, peak.pin.frame, ranges(per_line.pin, peak.pin.v), cpu6_frames, played, pin_frames, resets, isl_max, both_max.v, both_max.y, LIMIT + ISL_LINE, scr_max)
    finish(math.max(peak.nat.v, peak.pin.v) <= LIMIT and both_max.v <= LIMIT + ISL_LINE and isl_max <= ISL_LINE, msg)
  end
end) if not ok_ then print("LUAERR " .. tostring(err_)); finish(false, "lua error: " .. tostring(err_)) end end)
