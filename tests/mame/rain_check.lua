-- Storm rain (test-rain target, src/core/rain.c). Real match via start_seq.lua, then the mood is forced by poking Game mood (as mood_check.lua):
--   1. calm mood: for NOSTORM_FRAMES frames no fix cell uses palette slot RAIN_SLOT (VRAM 0x7000..0x74ff, word >> 12).
--   2. storm: for STORM_FRAMES frames (past the first lightning gap) rain cells appear (peak >= MIN_CELLS), the worst sprites per screen line stay
--      <= SB_LIMIT 90, the worst flush time (g_last_us, sampled by flush_sample.lua) stays <= FLUSH_LIMIT 1800 us. Prints worst line and flush us.
-- Env: BRAWL_FLOW_ADDR, BRAWL_FRAME_ADDR, BRAWL_MOOD_ADDR, BRAWL_BUSY_ADDR, BRAWL_FLIER_LAYOUT, BRAWL_LASTUS_ADDR, BRAWL_DEFER_ADDR,
--      BRAWL_FLUSHN_ADDR, BRAWL_RAIN_SLOT (decimal), BRAWL_RESULT.
local function hex(name) return tonumber(os.getenv(name) or "", 16) end
local flow_addr, frame_addr, mood_addr, busy_addr = hex("BRAWL_FLOW_ADDR"), hex("BRAWL_FRAME_ADDR"), hex("BRAWL_MOOD_ADDR"), hex("BRAWL_BUSY_ADDR")
local rain_slot, result = tonumber(os.getenv("BRAWL_RAIN_SLOT") or ""), os.getenv("BRAWL_RESULT")
local flay = {}
for v in (os.getenv("BRAWL_FLIER_LAYOUT") or ""):gmatch("%d+") do flay[#flay + 1] = tonumber(v) end
local S_PLAYING, GAME_MOOD_STORM = 3, 2
local NOSTORM_FRAMES, STORM_FRAMES, SB_LIMIT, FLUSH_LIMIT, MIN_CELLS = 120, 900, 90, 1800, 20

local mem   = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, name)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname == name then return f end end
end
local coin, start = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start")
local ss = dofile("tests/mame/start_seq.lua")(coin, start)
local line_count = dofile("tests/mame/sprite_line_count.lua")
local fs = dofile("tests/mame/flush_sample.lua")(mem)

local vram, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "rainvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then vram[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
  elseif r == 4 then vmod = data end
end)
local function rain_cells()
  local c = 0
  for a = 0x7000, 0x74ff do if ((vram[a] or 0) >> 12) == rain_slot then c = c + 1 end end
  return c
end

local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

local rs = (#flay >= 23) and dofile("tests/mame/round_skip.lua")(mem, flow_addr, flay) or nil
local n, phase, fc0, t = 0, "boot", nil, 0
local calm_cells, calm_frames, peak_cells, sframes, worst, worst_line = 0, 0, 0, 0, 0, 0
emu.register_frame_done(function() local ok_, err_ = pcall(function()
  if done then return end
  n = n + 1
  if n > 20000 then finish(false, "watchdog in phase " .. phase) return end
  if not (coin and start and frame_addr and mood_addr and busy_addr and rain_slot and flay[28] and rs) then finish(false, "missing input field, address or probe layout") return end
  local state, fc = mem:read_u8(flow_addr + flay[1]), mem:read_u32(frame_addr)
  local mood, busy = mem:read_u8(mood_addr), mem:read_u8(busy_addr)
  if phase == "boot" then
    if fc ~= 0 then fc0 = fc0 or fc end
    if fc0 and fc - fc0 >= 30 then phase = "coin"; ss.begin(n) end
    return
  elseif phase == "coin" then
    if ss.step(n, state == S_PLAYING) then phase = "calm_poke"; t = 0 end
    return
  end
  if state ~= S_PLAYING then finish(false, "left PLAYING in phase " .. phase) return end
  if not rs.live() or busy ~= 0 then t = 0 return end
  t = t + 1
  if t < 5 then return end
  if phase == "calm_poke" then
    mem:write_u8(flow_addr + flay[28], 0); phase = "calm"; t = 0
  elseif phase == "calm" then
    if mood == GAME_MOOD_STORM then if t > 300 then finish(false, "mood stayed storm after the calm poke") end return end
    calm_frames = calm_frames + 1
    calm_cells = math.max(calm_cells, rain_cells())
    if calm_frames < NOSTORM_FRAMES then return end
    if calm_cells > 0 then finish(false, string.format("%d rain cells in mood %d (not storm)", calm_cells, mood)) return end
    mem:write_u8(flow_addr + flay[28], GAME_MOOD_STORM); phase = "storm"; t = 0
  elseif phase == "storm" then
    if mood ~= GAME_MOOD_STORM then if t > 300 then finish(false, "mood " .. mood .. " 300 frames after the storm poke") end return end
    local cnt = line_count.count(vram, 1, 381)
    for y = 0, 223 do if cnt[y] > worst then worst, worst_line = cnt[y], y end end
    peak_cells = math.max(peak_cells, rain_cells())
    fs.frame()
    sframes = sframes + 1
    if sframes < STORM_FRAMES then return end
    local msg = string.format("rain: calm cells %d, storm peak %d cells, worst line %d sprites at line %d (limit %d), flush max %d us (limit %d), flushes %d, deferred %d",
      calm_cells, peak_cells, worst, worst_line, SB_LIMIT, fs.us_max, FLUSH_LIMIT, fs.flushes, fs.sat)
    if peak_cells < MIN_CELLS then finish(false, "no rain in storm: " .. msg) return end
    if worst > SB_LIMIT or fs.us_max > FLUSH_LIMIT then finish(false, msg) return end
    finish(true, msg)
  end
end) if not ok_ then print("BRAWL_TEST ERROR " .. tostring(err_)); finish(false, "Lua error: " .. tostring(err_)) end end)
