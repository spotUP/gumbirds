-- BLACK-SCREEN regression (make test-black-screen, UniBIOS 4.0): Gum Trip runs back to back with the inputs a player gives between
-- runs, and no run ranks (last score poked to 0 at Game Over, the owner's "died, no high score"). Paths, one per run:
--   run 1 two coins at boot, Start            between 1-2: Start mashed through Game Over and the title (a credit left: a game)
--   run 2 coin at Game Over                   between 2-3: A mashed the same way (a credit left)
--   between 3-4: coin on the title, Start     between 4-5: credits out, title -> table -> demo, coin in the demo, A starts
-- In play A flaps on a rhythm so the run lasts, then stops so the bird falls. Black = the screen bitmap shows at most 2 colours
-- (sampled every 10 frames) for 90+ frames in a row, or the entry hold (g_bg_held) lasts 300+ frames. FAIL names run, path and state.
local function addr(k) return tonumber(os.getenv(k), 16) end
local flow_addr, frame_addr, held_addr, busy_addr, mood_addr = addr("BRAWL_FLOW_ADDR"), addr("BRAWL_FRAME_ADDR"),
  addr("BRAWL_BGHELD_ADDR"), addr("BRAWL_BUSY_ADDR"), addr("BRAWL_MOOD_ADDR")
local out = os.getenv("BRAWL_RESULT")
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local screen = manager.machine.screens[":screen"]
local ports = manager.machine.ioport.ports
local function field(tag, name) for f, v in pairs(ports[tag].fields) do if f == name then return v end end end
local coin = field(":AUDIO_COIN", "Coin 1")
local start = field(":edge:joy:START", "1 Player Start")
local down = field(":edge:joy:JOY1", "P1 Down")
local abtn = field(":edge:joy:JOY1", "P1 A")
local CREDIT = 0x10fe00
local RUNS = 5
local log = io.open(out, "w")
local n, fc0, last = 0, nil, -1
local run, phase, t0 = 0, "boot", 0          -- phase: boot, coin, menu, play, over, between
local coins_left_demo, cr_drop
local cr_prev = 0
local coins_left, black_run, held_run, fail = 0, 0, 0, nil
local function W(s) log:write(s .. "\n"); log:flush() end
local function colours()
  local px = screen:pixels()
  local seen, k = {}, 0
  for i = 1, #px - 3, 4 * 37 do
    local c = px:sub(i, i + 2)
    if not seen[c] then seen[c] = true; k = k + 1; if k > 2 then return k end end
  end
  return k
end
local function finish(ok, msg)
  W((ok and "PASS " or "FAIL ") .. msg); log:close(); manager.machine:exit()
end
local function press(f, on) f:set_value(on and 1 or 0) end
emu.register_frame_done(function()
  if fail then return end
  n = n + 1
  local st = mem:read_u8(flow_addr)
  local fc = mem:read_u32(frame_addr); fc0 = fc0 or fc
  if st ~= last then W(string.format("frame %d run %d phase %s state %d -> %d credit %02x", n, run, phase, last, st, mem:read_u8(CREDIT))); last = st end
  -- black detectors, every phase after boot
  if phase ~= "boot" then
    if n % 10 == 0 then
      if colours() <= 2 then black_run = black_run + 10 else black_run = 0 end
      -- 90, not 60: every game-end SYSTEM_RETURN with a credit shows ~52 frames of one colour (UniBIOS clears palette RAM at
      -- PC C1871A, then video_init blocks while the fix clear and palettes flush, BLACK-SCREEN-3); a stuck screen is far longer
      if black_run >= 90 then
        fail = true
        finish(false, string.format("black screen run %d phase %s state %d frame %d: held %d busy %d mood %d credit %02x",
          run, phase, st, n, mem:read_u8(held_addr), mem:read_u8(busy_addr), mem:read_u8(mood_addr), mem:read_u8(CREDIT)))
        return
      end
    end
    if mem:read_u8(held_addr) ~= 0 then held_run = held_run + 1 else held_run = 0 end
    if held_run >= 300 then
      fail = true
      finish(false, string.format("entry hold stuck run %d state %d frame %d: busy %d mood %d", run, st, n, mem:read_u8(busy_addr), mem:read_u8(mood_addr)))
      return
    end
  end
  local cr_now = mem:read_u8(CREDIT)
  if phase ~= "boot" and cr_now < cr_prev and st ~= 3 then cr_drop = cr_drop or n end
  cr_prev = cr_now
  if st == 3 then cr_drop = nil end
  if cr_drop and n - cr_drop > 120 then
    fail = true
    finish(false, string.format("credit taken, no game: run %d phase %s state %d frame %d (taken at %d): busy %d mood %d",
      run, phase, st, n, cr_drop, mem:read_u8(busy_addr), mem:read_u8(mood_addr)))
    return
  end
  local k = n - t0
  if phase == "boot" then
    if fc ~= fc0 and n > 120 then phase = "coin"; t0 = n; coins_left = 2; run = 1 end
  elseif phase == "coin" then          -- coins_left coins, 30 frames apart
    press(coin, coins_left > 0 and (k % 30) < 10)
    if k % 30 == 29 then coins_left = coins_left - 1 end
    if coins_left <= 0 and k % 30 == 29 then phase = "menu"; t0 = n end
  elseif phase == "menu" then          -- Down once (Gum Trip), Start until playing
    press(down, k >= 40 and k < 49)
    press(run == 5 and abtn or start, k >= 70 and ((k - 70) % 60) < 16) -- run 5 starts with A (a second Start)
    if st == 3 then press(start, false); press(abtn, false); press(down, false); phase = "play"; t0 = n end
    if k > 1500 then fail = true; finish(false, string.format("run %d never started (state %d credit %02x)", run, st, mem:read_u8(CREDIT))) return end
  elseif phase == "play" then
    press(abtn, k < 1500 and (k % 18) < 4)
    if st == 4 then phase = "over"; t0 = n end
    if k > 9000 then fail = true; finish(false, string.format("run %d never ended (state %d)", run, st)) return end
  elseif phase == "over" then          -- Game Over: no rank; path 2 coins here
    if st == 4 then mem:write_u32(flow_addr + 22, 0) end
    if run == 2 then press(coin, k >= 20 and k < 30) end
    press(start, run == 1 and (k % 18) < 4)                           -- run 1: Start mashed through Game Over into the title
    press(abtn, run == 2 and (k % 18) < 4)                            -- run 2: A mashed the same way
    if st ~= 4 and st ~= 3 then press(coin, false); phase = "between"; t0 = n end
    if st == 5 then fail = true; finish(false, string.format("run %d ranked (name entry): score poke missed", run)) return end
  elseif phase == "between" then
    local cr = mem:read_u8(CREDIT)
    if st == 3 then                    -- a mashed Start or A spent the credit left: that game is the next run
      press(start, false); press(abtn, false); press(coin, false); run = run + 1; phase = "play"; t0 = n; return
    end
    press(start, run == 1 and k < 300 and (k % 18) < 4)
    press(abtn, run == 2 and k < 300 and (k % 18) < 4)
    if run == RUNS then if k > 600 then finish(true, string.format("%d runs, no black screen, last state %d credit %02x", RUNS, st, cr)) end return end
    if run == 3 then press(coin, k >= 200 and k < 210) end          -- coin on the title
    if run == 4 and cr == 0 then                                      -- credits out: wait for the demo, coin there
      if st == 2 and not coins_left_demo then coins_left_demo = n end
      if coins_left_demo then press(coin, n - coins_left_demo >= 60 and n - coins_left_demo < 70) end
      if k > 6000 then fail = true; finish(false, "run 4: no demo reached") return end
      return
    end
    if k >= 400 and st == 0 then press(coin, false); coins_left_demo = nil; run = run + 1; phase = "menu"; t0 = n end
  end
  if n > 80000 then fail = true; finish(false, string.format("watchdog run %d phase %s state %d", run, phase, st)) end
end)
