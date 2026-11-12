-- Headless check (make test-soft-reset): a soft reset in the middle of play really reboots the game and it comes back sane.
-- Plan: thoughts/spot/2026-11-10-soft-reset-test-plan.md (SR1..SR8). No game source change.
-- Scope: this settles path A only (a stale g_boot_magic in work RAM making rom_game/rom_title take resume_game_loop after a
-- reset, src/main.c). It does NOT close the "random restart" report (path B: magic lost, or the save-return path).
-- Drive: coin + start until FLOW_PLAYING, idle PLAY_FRAMES, record counter and magic, manager.machine:soft_reset().
-- Sentinel that the reset and the boot path ran: g_frame_counter drops below its pre-reset value (the crt0 .bss clear ran) and
-- g_boot_magic reads 0x424F4F54 again only after that drop (main() set it). Pre-reset the magic must be armed.
-- Sane state RESET_WAIT frames after the reset: flow state is attract (0..2), Game score 0, counter advances >= 55 of 60 frames.
-- High score table: valid (first score nonzero, sorted highest first), not compared with the pre-reset table.
-- Credits: observed only. The ngdevkit headers have no credit counter address, so the observation is whether start without a
-- coin begins a play after the reset; then a coin + start must reach FLOW_PLAYING with the counter running (a new play).
-- Env: BRAWL_FLOW_ADDR, BRAWL_FRAME_ADDR, BRAWL_MAGIC_ADDR (hex, nm on the ELF), BRAWL_REACH_LAYOUT (reach_probe.c numbers),
-- BRAWL_RESULT (file), BRAWL_LABEL (text for the result line, e.g. the BIOS).
local frame_addr = tonumber(os.getenv("BRAWL_FRAME_ADDR"), 16)
local flow_addr  = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local magic_addr = tonumber(os.getenv("BRAWL_MAGIC_ADDR"), 16)
local result     = os.getenv("BRAWL_RESULT")
local label      = os.getenv("BRAWL_LABEL") or "nullbios"
local lay = {}
for v in os.getenv("BRAWL_REACH_LAYOUT"):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local O_STATE, O_TSCORE, O_SCORE = lay[1], lay[4], lay[12]   -- flow state, table.score, game.score (reach_probe.c order)
local BOOT_MAGIC = 0x424F4F54
local FLOW_ATTRACT_DEMO, FLOW_PLAYING = 2, 3
local PLAY_FRAMES, RESET_TIMEOUT, ALIVE_FRAMES = 120, 3000, 60   -- the real BIOS needs about 1000 frames to reach the game again
-- nullbios (the MAME stub BIOS) does not clear work RAM at reset: the stale g_boot_magic is then meant to take the resume path
-- (src/main.c:555-557), so that leg asserts the resume (counter keeps counting, state stays PLAYING, BIOS user mode reset to 1).
local EXPECT_RESUME = label == "nullbios"
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports

local function field(tag, name)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname == name then return f end end
end
local coin  = field(":AUDIO_COIN", "Coin 1")
local start = field(":edge:joy:START", "1 Player Start")

local function finish(ok, msg)
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

local function counter() return mem:read_u32(frame_addr) end
local function magic() return mem:read_u32(magic_addr) end
local function state() return mem:read_u8(flow_addr + O_STATE) end

-- Phase machine, one step per frame; p_n counts frames in the phase.
local n, phase, p_n = 0, "title", 0
local c_before, magic_before, n_reset, dropped_at, rearmed_at, c_low
local saw_mode1, c_sane
local magic_log, c_alive0, credit_note, start_noc_state, play_c0 = {}, nil, nil, nil, nil
local MAGIC_LOG_AT = { [1] = true, [60] = true, [200] = true }

local function press(f, on) if f then f:set_value(on and 1 or 0) end end

emu.register_frame_done(function()
  n, p_n = n + 1, p_n + 1
  local st, c = state(), counter()
  if phase == "title" then
    -- Wait for a running game (counter) and the attract title; the UniBIOS needs more frames than nullbios.
    if c >= 300 and st <= FLOW_ATTRACT_DEMO then phase, p_n = "coin", 0 end
    if n > 3000 then finish(false, "game never reached attract (counter " .. c .. " state " .. st .. ")") end
  elseif phase == "coin" then
    if p_n == 1 then press(coin, true) elseif p_n == 16 then press(coin, false) elseif p_n == 46 then press(start, true)
    elseif p_n == 61 then press(start, false) end
    if st == FLOW_PLAYING then press(start, false); phase, p_n = "play", 0
    elseif p_n > 600 then finish(false, "coin + start never reached FLOW_PLAYING (state " .. st .. ")") end
  elseif phase == "play" then
    if p_n == PLAY_FRAMES then
      c_before, magic_before = c, magic()
      if magic_before ~= BOOT_MAGIC then
        finish(false, string.format("boot magic not armed before the reset: %08x (main() never set g_boot_magic)", magic_before))
        return
      end
      if st ~= FLOW_PLAYING then finish(false, "left PLAYING before the reset (state " .. st .. ")") return end
      n_reset = n
      manager.machine:soft_reset()
      phase, p_n = "reset", 0
    end
  elseif phase == "reset" then
    if MAGIC_LOG_AT[p_n] then magic_log[#magic_log + 1] = string.format("+%d=%08x", p_n, magic()) end
    if not dropped_at and c < c_before then dropped_at, c_low = p_n, c end
    if dropped_at and not rearmed_at and magic() == BOOT_MAGIC then rearmed_at = p_n end
    if p_n <= 3 and mem:read_u8(0x10fdaf) == 1 then saw_mode1 = true end
    if EXPECT_RESUME then
      if p_n == 200 then
        if not saw_mode1 then finish(false, "no BIOS reset seen (user mode never 1 after soft_reset): n_reset " .. n_reset) return end
        if c < c_before or st ~= FLOW_PLAYING or magic() ~= BOOT_MAGIC then
          finish(false, string.format("nullbios resume expected but counter %d (before %d) state %d magic %08x", c, c_before, st, magic())) return
        end
        finish(true, string.format("[%s] soft reset at frame %d: BIOS reset ran (user mode 1), work RAM kept, resume path taken as documented (counter %d -> %d, state %d, magic kept)", label, n_reset, c_before, c, st))
      end
    elseif (dropped_at and rearmed_at and c >= 300) or p_n == RESET_TIMEOUT then
      local detail = string.format("n_reset %d, counter before %d, last counter %d, magic %s", n_reset, c_before, c, table.concat(magic_log, " "))
      if not dropped_at then
        finish(false, "counter never dropped after the soft reset (stale magic, resume path taken?): " .. detail)
        return
      end
      if not rearmed_at then finish(false, "magic never re-armed after the counter drop: " .. detail) return end
      local score = mem:read_u32(flow_addr + O_SCORE)
      local t1, t2 = mem:read_u32(flow_addr + O_TSCORE), mem:read_u32(flow_addr + O_TSCORE + 4)
      if st > FLOW_ATTRACT_DEMO then finish(false, "not in attract after the reset (flow state " .. st .. "): " .. detail) return end
      if score ~= 0 then finish(false, "game score " .. score .. " carried over the reset: " .. detail) return end
      if t1 == 0 or t1 < t2 then finish(false, string.format("high score table invalid after reset (%d, %d): %s", t1, t2, detail)) return end
      sane = string.format("counter dropped to %d at +%d, magic re-armed at +%d (%s), state %d, score 0, table top %d", c_low, dropped_at, rearmed_at, table.concat(magic_log, " "), st, t1)
      phase, p_n, c_alive0, c_sane = "alive", 0, nil, c
    end
  elseif phase == "alive" then
    -- The loop sits still for about 30 frames while the real BIOS finishes its boot: time the window once the counter has moved 10 past the sane check.
    if not c_alive0 then if c >= c_sane + 10 then c_alive0, p_n = c, 0 end return end
    if p_n == ALIVE_FRAMES then
      if c - c_alive0 < 55 then finish(false, string.format("game loop stalled after the reset: counter %d -> %d in %d frames", c_alive0, c, ALIVE_FRAMES)) return end
      alive = c - c_alive0
      phase, p_n = "start_noc", 0   -- credit observation: start without a coin
    end
  elseif phase == "start_noc" and st == FLOW_PLAYING and p_n == 1 then
    credit_note = "a play began by itself after the reset (a credit survived the BIOS reset and its compulsion timer started it)"
    phase, p_n, play_c0 = "newplay_run", 0, c
  elseif phase == "start_noc" then
    if p_n == 1 then press(start, true) elseif p_n == 16 then press(start, false) end
    if p_n == 90 then
      start_noc_state = st
      credit_note = st == FLOW_PLAYING and "start without coin began a play (free play or a credit survived)" or "start without coin did not begin a play (no credit after reset)"
      if st == FLOW_PLAYING then phase, p_n, play_c0 = "newplay_run", 0, c else phase, p_n = "newcoin", 0 end
    end
  elseif phase == "newcoin" then
    if p_n == 1 then press(coin, true) elseif p_n == 16 then press(coin, false) elseif p_n == 46 then press(start, true)
    elseif p_n == 61 then press(start, false) end
    if st == FLOW_PLAYING then phase, p_n, play_c0 = "newplay_run", 0, c
    elseif p_n > 300 then finish(false, "coin + start after the reset never began a play (state " .. st .. "): " .. sane) end
  elseif phase == "newplay_run" and p_n == 120 then
    if st ~= FLOW_PLAYING or c - play_c0 < 100 then
      finish(false, string.format("new play stalled: state %d, counter %d -> %d in 120 frames", st, play_c0, c))
    else
      finish(true, string.format("[%s] soft reset at frame %d from counter %d: %s; loop alive (%d of %d frames); credits observed: %s; new play running (counter %d -> %d)",
        label, n_reset, c_before, sane, alive, ALIVE_FRAMES, credit_note, play_c0, c))
    end
  end
end)
