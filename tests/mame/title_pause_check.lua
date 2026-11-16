-- Title pause after a run (make test-title-pause, UniBIOS 4.0): frames from the end of the run (PLAYING -> GAME_OVER) to the live title.
-- BRAWL_MODE=trip (Down on the title picks Gum Trip) or arcade. No rank (last score poked to 0). Reports:
--   over->title   frames from the run end to the first frame in state TITLE (0)
--   held          game frames in state TITLE with the flow timer still 0 (the entry hold / mood rewrite pause); asserted <= BRAWL_MAX_PAUSE (30).
--                The BIOS return after a run (SYSTEM_RETURN, no game frames, same for arcade) is reported apart
--   over->colour  frames from the run end to the first title frame showing more than 2 colours
--   over->live    run end to a title that draws and runs
local function addr(k) return tonumber(os.getenv(k), 16) end
local flow_addr, frame_addr = addr("BRAWL_FLOW_ADDR"), addr("BRAWL_FRAME_ADDR")
local out, mode = os.getenv("BRAWL_RESULT"), os.getenv("BRAWL_MODE") or "trip"
local max_pause = tonumber(os.getenv("BRAWL_MAX_PAUSE") or "30")
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local screen = manager.machine.screens[":screen"]
local ports = manager.machine.ioport.ports
local function field(tag, name) for f, v in pairs(ports[tag].fields) do if f == name then return v end end end
local coin, start = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start")
local down, abtn = field(":edge:joy:JOY1", "P1 Down"), field(":edge:joy:JOY1", "P1 A")
local log = io.open(out, "w")
local function W(s) log:write(s .. "\n"); log:flush() end
local function colours()
  local px, seen, k = screen:pixels(), {}, 0
  for i = 1, #px - 3, 4 * 37 do
    local c = px:sub(i, i + 2)
    if not seen[c] then seen[c] = true; k = k + 1; if k > 2 then return k end end
  end
  return k
end
local function press(f, on) f:set_value(on and 1 or 0) end
local function finish(ok, msg) W((ok and "PASS " or "FAIL ") .. msg); log:close(); manager.machine:exit() end
local n, phase, t0, fc0 = 0, "boot", 0, nil
local t_over, t_title, t_live, t_col, fc_title, fc_prev, held = nil, nil, nil, nil, nil, nil, 0
emu.register_frame_done(function()
  n = n + 1
  local st, timer = mem:read_u8(flow_addr), mem:read_u16(flow_addr + 2)
  local fc = mem:read_u32(frame_addr); fc0 = fc0 or fc
  local k = n - t0
  local fc_was = fc_prev; fc_prev = fc
  if phase == "boot" then
    if fc ~= fc0 and n > 120 then phase = "coin"; t0 = n end
  elseif phase == "coin" then
    press(coin, (k % 30) < 10 and k < 60)
    if k >= 90 then phase = "menu"; t0 = n end
  elseif phase == "menu" then
    press(down, mode == "trip" and k >= 40 and k < 49)
    press(start, k >= 70 and ((k - 70) % 60) < 16)
    if st == 3 then press(start, false); press(down, false); phase = "play"; t0 = n end
    if k > 1500 then finish(false, "never started") end
  elseif phase == "play" then
    press(abtn, k < 1500 and (k % 18) < 4)
    if st == 4 then phase = "over"; t0 = n; t_over = n end
    if k > 9000 then finish(false, "run never ended") end
  elseif phase == "over" then
    if st == 4 then mem:write_u32(flow_addr + 22, 0) end
    if st == 5 then finish(false, "ranked: score poke missed") end
    if st == 0 and not t_title then t_title = n; fc_title = fc end
    if t_title then
      if timer == 0 and fc ~= fc_was then held = held + 1 end  -- a game frame that left the title timer at 0: the hold
      if not t_col and colours() > 2 then t_col = n end
      if not t_live and timer > 0 and n > t_title then t_live = n end
      if t_live and t_col then
        local t2l = held
        finish(t2l <= max_pause, string.format("%s: over->title %d, held game frames %d (max %d, BIOS return frames %d), over->colour %d, over->live %d",
          mode, t_title - t_over, t2l, max_pause, (t_live - t_title) - (fc - fc_title) + 0, t_col - t_over, math.max(t_live, t_col) - t_over))
      end
    end
    if k > 3000 then finish(false, string.format("%s: title never live (state %d)", mode, st)) end
  end
end)
