-- Round clear banner sentinels (make test-banner). Sentinels g_banner_calls / g_banner_cells (src/main.c draw()):
--   1. attract (title, table, then one whole demo phase): g_banner_calls stays 0 (the demo shows no banner, user decision);
--      whether the demo itself reached round_end == RE_HOLD is reported (a demo that never does leaves the check weaker).
--   2. real game (coin, two Starts via start_seq.lua): a round won by RAM poke (round_skip.lua) enters RE_HOLD; during
--      the hold calls and cells rise above 0; after the hold both counters stop rising within BANNER_SETTLE frames.
-- Env: BRAWL_FLOW_ADDR, BRAWL_FRAME_ADDR, BRAWL_CALLS_ADDR, BRAWL_CELLS_ADDR, BRAWL_RE_ADDR, BRAWL_FLIER_LAYOUT, BRAWL_RESULT.
local function hex(name) return tonumber(os.getenv(name) or "", 16) end
local flow_addr, frame_addr, calls_addr, cells_addr = hex("BRAWL_FLOW_ADDR"), hex("BRAWL_FRAME_ADDR"), hex("BRAWL_CALLS_ADDR"), hex("BRAWL_CELLS_ADDR")
local re_addr, result = hex("BRAWL_RE_ADDR"), os.getenv("BRAWL_RESULT")
local flay = {}
for v in (os.getenv("BRAWL_FLIER_LAYOUT") or ""):gmatch("%d+") do flay[#flay + 1] = tonumber(v) end
local S_TITLE, S_TABLE, S_DEMO, S_PLAYING = 0, 1, 2, 3
local RE_HOLD = 1
local BANNER_SETTLE = 5      -- frames after the hold ends until the counters must be still
local DEMO_CAP = 2400        -- attract is 420 + 480 + 900 frames; give up on a demo that never ends (40 s emulated)

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

local rs = (#flay >= 23 and re_addr) and dofile("tests/mame/round_skip.lua")(mem, flow_addr, flay) or nil
local n, phase, fc0, t = 0, "boot", nil, 0
local seen, demo_frames, demo_done, demo_hold = {}, 0, false, false
local end_calls, end_cells = nil, nil
emu.register_frame_done(function() local ok_, err_ = pcall(function()
  if done then return end
  n = n + 1
  if n > 12000 then finish(false, "watchdog in phase " .. phase) return end
  if not (coin and start and frame_addr and calls_addr and cells_addr and rs) then finish(false, "missing input field, address or probe layout") return end
  local state = mem:read_u8(flow_addr + flay[1])
  local fc = mem:read_u32(frame_addr)
  local calls, cells = mem:read_u16(calls_addr), mem:read_u16(cells_addr)
  local re = mem:read_u16(re_addr)

  if phase == "boot" then
    if fc ~= 0 then fc0 = fc0 or fc end
    if fc0 and fc - fc0 >= 30 then phase = "attract"; t = 0 end
    return
  elseif phase == "attract" then
    t = t + 1
    if calls ~= 0 then finish(false, string.format("attract (flow state %d, frame %d): g_banner_calls %d, want 0 (no banner in attract)", state, t, calls)) return end
    seen[state] = true
    if state == S_DEMO then
      demo_frames = demo_frames + 1
      if re == RE_HOLD then demo_hold = true end
    elseif seen[S_DEMO] then demo_done = true end
    if demo_done or demo_frames >= DEMO_CAP then
      if not (seen[S_TITLE] and seen[S_DEMO]) then finish(false, string.format("attract did not show title and demo (title %s, table %s, demo frames %d)", tostring(seen[S_TITLE]), tostring(seen[S_TABLE]), demo_frames)) return end
      phase = "coin"; t = 0; ss.begin(n)
    end
    return
  elseif phase == "coin" then
    if ss.step(n, state == S_PLAYING) then phase = "live"; t = 0 end
    return
  end
  if state ~= S_PLAYING then finish(false, "left PLAYING in phase " .. phase) return end
  if phase == "live" then
    if not rs.live() then t = 0 return end -- round start text still running
    t = t + 1
    if t < 5 then return end
    if calls ~= 0 then finish(false, "g_banner_calls " .. calls .. " in play before any round end, want 0") return end
    rs.win(); phase = "wait_hold"; t = 0
  elseif phase == "wait_hold" then
    t = t + 1
    if re == RE_HOLD then phase = "hold"; t = 0
    elseif t > 120 then finish(false, "round won by poke but round_end never reached RE_HOLD in 120 frames") end
  elseif phase == "hold" then
    t = t + 1
    if re == RE_HOLD then
      if t > 3000 then finish(false, "RE_HOLD never ended") end
      return
    end
    if calls <= 0 then finish(false, "g_banner_calls " .. calls .. " after a whole RE_HOLD, want > 0") return end
    if cells <= 0 then finish(false, "g_banner_cells " .. cells .. " after a whole RE_HOLD, want > 0") return end
    phase = "settle"; t = 0
  elseif phase == "settle" then
    t = t + 1
    if t == BANNER_SETTLE then end_calls, end_cells = calls, cells end
    if t > BANNER_SETTLE then
      if calls ~= end_calls or cells ~= end_cells then finish(false, string.format("banner counters still rising %d frames after the hold: calls %d -> %d, cells %d -> %d", t, end_calls, calls, end_cells, cells)) return end
      if t >= BANNER_SETTLE + 30 then
        finish(true, string.format("banner: attract calls 0 over title/table/demo (%d demo frames, demo reached RE_HOLD: %s); hold drew calls %d cells %d; still after %d frames",
          demo_frames, tostring(demo_hold), calls, cells, t))
      end
    end
  end
end) if not ok_ then print("BRAWL_TEST ERROR " .. tostring(err_)); finish(false, "Lua error: " .. tostring(err_)) end end)
