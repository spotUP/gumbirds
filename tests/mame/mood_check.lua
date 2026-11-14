-- Background mood in a real match (make test-mood, DUSK-1). Sentinels in src/bg.c: g_bg_mood (mood drawn), g_bg_mood_busy
-- (column strips still being rewritten), g_bg_mood_changes (count of bg_set_mood switches).
--   1. coin and one Start (start_seq.lua); in play, after the round start text, record mood A and backdrop entry 4095.
--   2. win rounds by RAM poke (round_skip.lua) until match_start picks the other mood and the strip rewrite ends; record B.
--   3. PASS when both moods were seen (moon 0, dusk 1), the backdrop words differ, and palette RAM from the dusk first
--      entry equals the generated dusk_palettes words read from ROM (both palette sets stay resident).
-- Env: BRAWL_FLOW_ADDR, BRAWL_FRAME_ADDR, BRAWL_RE_ADDR, BRAWL_FLIER_LAYOUT, BRAWL_MOOD_ADDR, BRAWL_BUSY_ADDR,
--      BRAWL_CHANGES_ADDR, BRAWL_FIRST_ADDR (const u16 g_bg_dusk_pal_first_entry), BRAWL_PAL_ADDR, BRAWL_PAL_SIZE (dusk_palettes), BRAWL_RESULT.
local function hex(name) return tonumber(os.getenv(name) or "", 16) end
local flow_addr, frame_addr, re_addr = hex("BRAWL_FLOW_ADDR"), hex("BRAWL_FRAME_ADDR"), hex("BRAWL_RE_ADDR")
local mood_addr, busy_addr, changes_addr = hex("BRAWL_MOOD_ADDR"), hex("BRAWL_BUSY_ADDR"), hex("BRAWL_CHANGES_ADDR")
local first_addr, pal_addr, pal_size = hex("BRAWL_FIRST_ADDR"), hex("BRAWL_PAL_ADDR"), hex("BRAWL_PAL_SIZE")
local result = os.getenv("BRAWL_RESULT")
local flay = {}
for v in (os.getenv("BRAWL_FLIER_LAYOUT") or ""):gmatch("%d+") do flay[#flay + 1] = tonumber(v) end
local S_PLAYING = 3
local PALRAM, BACKDROP = 0x400000, 0x400000 + 4095 * 2
local MAX_WINS = 6

local mem   = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, name)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname == name then return f end end
end
local coin, start = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start")
local ss = dofile("tests/mame/start_seq.lua")(coin, start)

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

-- First palette word that differs from the ROM table, or nil when all match.
local function pal_mismatch()
  local first = mem:read_u16(first_addr)
  for i = 0, pal_size // 2 - 1 do
    local want, got = mem:read_u16(pal_addr + i * 2), mem:read_u16(PALRAM + (first + i) * 2)
    if want ~= got then return string.format("entry %d: palette RAM %04x, dusk_palettes %04x", first + i, got, want) end
  end
end

local rs = (#flay >= 23 and re_addr) and dofile("tests/mame/round_skip.lua")(mem, flow_addr, flay) or nil
local n, phase, fc0, t, wins = 0, "boot", nil, 0, 0
local mood_a, back_a, seen = nil, nil, {}
emu.register_frame_done(function() local ok_, err_ = pcall(function()
  if done then return end
  n = n + 1
  if n > 20000 then finish(false, "watchdog in phase " .. phase) return end
  if not (coin and start and frame_addr and mood_addr and busy_addr and changes_addr and first_addr and pal_addr and pal_size and rs) then
    finish(false, "missing input field, address or probe layout") return end
  local state = mem:read_u8(flow_addr + flay[1])
  local fc = mem:read_u32(frame_addr)
  local mood, busy = mem:read_u8(mood_addr), mem:read_u8(busy_addr)
  if mood > 1 then finish(false, "g_bg_mood " .. mood .. ", want 0 or 1") return end
  seen[mood] = true

  if phase == "boot" then
    if fc ~= 0 then fc0 = fc0 or fc end
    if fc0 and fc - fc0 >= 30 then phase = "coin"; ss.begin(n) end
    return
  elseif phase == "coin" then
    if ss.step(n, state == S_PLAYING) then phase = "live"; t = 0 end
    return
  end
  if state ~= S_PLAYING then finish(false, "left PLAYING in phase " .. phase) return end
  if not rs.live() or busy ~= 0 then t = 0 return end
  t = t + 1
  if t < 5 then return end
  if phase == "live" then
    mood_a, back_a = mood, mem:read_u16(BACKDROP)
    local bad = pal_mismatch()
    if bad then finish(false, "dusk palette not resident in mood " .. mood .. ": " .. bad) return end
    rs.win(); wins = 1; phase = "next"; t = 0
  elseif phase == "next" then
    if mood == mood_a then
      if wins >= MAX_WINS then finish(false, "mood stayed " .. mood .. " after " .. wins .. " won rounds") return end
      rs.win(); wins = wins + 1; t = 0
      return
    end
    local back_b = mem:read_u16(BACKDROP)
    if back_b == back_a then finish(false, string.format("backdrop 4095 %04x in both moods", back_a)) return end
    local bad = pal_mismatch()
    if bad then finish(false, "dusk palette not resident in mood " .. mood .. ": " .. bad) return end
    if not (seen[0] and seen[1]) then finish(false, "not both moods seen") return end
    finish(true, string.format("mood: %d -> %d after %d won rounds (changes %d), backdrop %04x -> %04x, dusk palette %d words resident from entry %d",
      mood_a, mood, wins, mem:read_u16(changes_addr), back_a, back_b, pal_size // 2, mem:read_u16(first_addr)))
  end
end) if not ok_ then print("BRAWL_TEST ERROR " .. tostring(err_)); finish(false, "Lua error: " .. tostring(err_)) end end)
