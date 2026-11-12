-- High score reachability (make test-reach, plan P5.1). Two MAME boots share one nvram dir; the Makefile
-- passes BRAWL_PHASE=1 or 2. Sentinel-driven, no fixed frame numbers (the cap is only a hang guard).
--   Phase 1: coin, start, autoplay (as flier_check.lua) until the score passes the table minimum, then idle
--            until the hero dies; GAME_OVER -> NAME_ENTRY; type BRAWL_NAME with the joystick (up cycles,
--            A confirms) by reading the cursor position and symbol from RAM; wait for the save reminder, then the title screen.
--            Asserts: score > 0 and ranks, g_hiscore_saves went 0 -> 1, backup RAM image holds name and
--            score at the row computed from the pre-insert table. Writes name/score/row to BRAWL_EXPECT.
--            Then keeps running 1500 frames past the BIOS title timeout: the game loop must not stall and the
--            text palette must stay set (PLAYER_START regression: blink, only the sky, after the save).
--   Phase 2: fresh boot, same nvram: backup RAM image and the flow table hold that name and score at that
--            row, g_hiscore_saves is 0 (loaded, not re-saved).
-- Env (hex addresses from nm): BRAWL_FLOW_ADDR, BRAWL_FRAME_ADDR, BRAWL_HISCORE_ADDR,
--   BRAWL_SAVES_ADDR; BRAWL_REACH_LAYOUT (reach_probe.c output); BRAWL_RESULT, BRAWL_EXPECT (files).
local phase_no   = tonumber(os.getenv("BRAWL_PHASE"))
local flow_addr  = tonumber(os.getenv("BRAWL_FLOW_ADDR") or "", 16)
local frame_addr = tonumber(os.getenv("BRAWL_FRAME_ADDR") or "", 16)
local hs_addr    = tonumber(os.getenv("BRAWL_HISCORE_ADDR") or "", 16)
local saves_addr = tonumber(os.getenv("BRAWL_SAVES_ADDR") or "", 16)
local namesec_addr = tonumber(os.getenv("BRAWL_NAMESEC_ADDR") or "", 16)   -- g_name_seconds_shown (countdown sentinel)
local result     = os.getenv("BRAWL_RESULT")
local expect     = os.getenv("BRAWL_EXPECT")
local NAME       = "REACHTST"
local lay = {}
for v in (os.getenv("BRAWL_REACH_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local O_STATE, O_LAST, O_TNAME, O_TSCORE, O_ENAME, O_ESYM, O_EPOS, O_EDONE = table.unpack(lay, 1, 8)
local O_FX, O_FVX, O_FGROUND, O_SCORE = table.unpack(lay, 9, 12)
local O_FY, O_FVY, O_CX, O_CY, O_CSTATE, O_CBALL = table.unpack(lay, 13, 18)
local O_EIDLE, NAME_TIMEOUT = table.unpack(lay, 19, 20)   -- entry.idle offset; NAME_TIMEOUT_FRAMES value
local cd_frames, cd_bad, cd_max, cd_note = 0, 0, 0, ""      -- name entry countdown: frames checked, mismatches, max shown   -- stomp teleport: flier y, vy; cpu[0] x, y, state, balloons   -- arena slice: flier x, vx (16.16), on_ground; game score
local mem    = manager.machine.devices[":maincpu"].spaces["program"]
local ports  = manager.machine.ioport.ports

local FLOW_ATTRACT_TITLE, FLOW_PLAYING, FLOW_GAME_OVER, FLOW_NAME_ENTRY, FLOW_SAVE_REMINDER = 0, 3, 4, 5, 6
local TABLE_MIN = 1000             -- factory table last place; a score must beat it (ties rank below)
local HOLD, GAP = 3, 4
local WATCHDOG = 40000             -- MAME frames; hang guard only

local function field(tag, pred)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if pred(fname) then return f end end
end
local function named(tag, nm) return field(tag, function(x) return x == nm end) end
local coin  = named(":AUDIO_COIN", "Coin 1")
local start = named(":edge:joy:START", "1 Player Start")
local ss = dofile("tests/mame/start_seq.lua")(coin, start)
ss.watch(manager.machine.devices[":maincpu"].spaces["program"])
local abtn, bbtn, cbtn = named(":edge:joy:JOY1", "P1 A"), named(":edge:joy:JOY1", "P1 B"), named(":edge:joy:JOY1", "P1 C")
local ubtn = named(":edge:joy:JOY1", "P1 Up")
local rbtn = named(":edge:joy:JOY1", "P1 Right")
local lbtn = named(":edge:joy:JOY1", "P1 Left")
local steering, steer_tick = false, 0
local function s32(v) return v >= 0x80000000 and v - 0x100000000 or v end

local function s16(v) return v >= 0x8000 and v - 0x10000 or v end
local function g32(o) return mem:read_u32(flow_addr + o) end
local function str(a, n)
  local t = {}
  for i = 0, n - 1 do t[#t + 1] = string.char(mem:read_u8(a + i)) end
  return table.concat(t)
end

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

-- Backup RAM image: 6 header bytes, then 10 x (8 name bytes + u32 score), big endian.
local function image_row(i)
  local a = hs_addr + 6 + i * 12
  return str(a, 8), mem:read_u32(a + 8)
end

local function release_all()
  abtn:set_value(0); bbtn:set_value(0); cbtn:set_value(0); ubtn:set_value(0); rbtn:set_value(0); lbtn:set_value(0)
end

local n, phase, coin_at = 0, "boot", nil
local fc0
local b_prev = 0
local idle_play = false
local entry_gap = 0
local exp_row, exp_score, saves0
local saved_msg, after_n, after_fc, last_fc, stall, pal_zero
local AFTER_FRAMES, STALL_MAX, PAL_ZERO_MAX = 1500, 60, 60  -- past the BIOS title timeout (bug looped from ~frame 660)
local PAL_TEXT_C1 = 0x400002                                 -- fix text palette 0 colour 1 (as unibios_check.lua)

emu.register_frame_done(function()
  if done then return end
  n = n + 1
  if n > WATCHDOG then
    finish(false, string.format("watchdog: phase %s state %d at frame %d", phase, mem:read_u8(flow_addr + O_STATE), n))
    return
  end
  if not (coin and start and abtn and bbtn and cbtn and ubtn) then finish(false, "missing input field") return end
  if not (phase_no and frame_addr and hs_addr and saves_addr and O_SCORE and result and expect) then
    finish(false, "missing env (phase/addresses/layout/files)") return
  end
  local state = mem:read_u8(flow_addr + O_STATE)

  if phase == "boot" then
    local fc = mem:read_u32(frame_addr)
    if fc ~= 0 then fc0 = fc0 or fc end
    if fc0 and fc - fc0 >= 30 then
      if phase_no == 2 then phase = "verify" else phase = "coin"; coin_at = n; ss.begin(n) end
    end
    return
  end

  if phase == "verify" then
    local f = io.open(expect, "r")
    if not f then finish(false, "no expectation file from boot 1") return end
    local name, score, row = f:read("*l"):match("^(%S.-)|(%d+)|(%d+)$")
    f:close()
    score, row = tonumber(score), tonumber(row)
    local iname, iscore = image_row(row)
    if iname ~= name or iscore ~= score then
      finish(false, string.format("boot 2 backup RAM row %d is '%s' %d, expected '%s' %d", row, iname, iscore, name, score))
      return
    end
    local tname, tscore = str(flow_addr + O_TNAME + row * 8, 8), g32(O_TSCORE + row * 4)
    if tname ~= name or tscore ~= score then
      finish(false, string.format("boot 2 flow table row %d is '%s' %d, expected '%s' %d", row, tname, tscore, name, score))
      return
    end
    if mem:read_u32(saves_addr) ~= 0 then finish(false, "boot 2 wrote the table again") return end
    finish(true, string.format("boot 2 table row %d = '%s' %d", row, name, score))
    return
  end

  if phase == "coin" then
    -- one coin; the first Start press opens the title mode select, the second begins the game (BG4; tests/mame/start_seq.lua)
    if ss.step(n, state == FLOW_PLAYING) then
      -- BG4 regression: one coin, the first Start only opens the select (credit still 1), the second begins play (credit 0)
      local bad = ss.verdict(1, 1, 0)
      if bad then finish(false, bad) return end
      phase = "play"
    end
    return
  end

  if phase == "play" then
    if state == FLOW_PLAYING then
      if not idle_play and g32(O_SCORE) > TABLE_MIN + 200 then idle_play = true end
      -- Arena slice autoplay: stomp a computer balloon, then stand on the island (no input after the stomp teleport) until the score
      -- passes the table minimum, then walk off the right edge, steer back over the gap with left + flap until the
      -- horizontal speed is gone, and fall into the water (same manoeuvre as tests/mame/flier_check.lua).
      if not idle_play then
        release_all()
        -- Test input instead of a rule change: put the player's feet on the first computer balloon (same
        -- placement as tests/host/stomp_assist.h) so the game's own stomp code scores; state <= 1 is alive/parachute.
        if mem:read_u8(flow_addr + O_CSTATE) <= 1 and mem:read_u8(flow_addr + O_CBALL) > 0 then
          mem:write_u32(flow_addr + O_FX, g32(O_CX))
          mem:write_u32(flow_addr + O_FY, g32(O_CY) - 26 * 65536)
          mem:write_u32(flow_addr + O_FVX, 0)
          mem:write_u32(flow_addr + O_FVY, 0)
        end
      else
        local fx = s32(g32(O_FX)) / 65536
        local vx = s32(g32(O_FVX)) / 65536
        local ground = mem:read_u8(flow_addr + O_FGROUND)
        -- A computer flier can bump the player back onto the island (body-contact reflect): walk off again.
        if steering and ground == 1 then steering = false end
        if not steering and (ground == 1 or fx < 212) then
          rbtn:set_value(1)
        else
          steering = true
          rbtn:set_value(0)
          if vx > 0 then
            lbtn:set_value(1)
            abtn:set_value((steer_tick % 6) < 2 and 1 or 0)
            steer_tick = steer_tick + 1
          else
            lbtn:set_value(0); abtn:set_value(0)
          end
        end
      end
    elseif state == FLOW_GAME_OVER then
      release_all()
      saves0 = mem:read_u32(saves_addr)
      phase = "over"
    else
      finish(false, string.format("left PLAYING for state %d", state))
    end
    return
  end

  if phase == "over" then
    if state == FLOW_GAME_OVER then return end
    local score = g32(O_LAST)
    if state ~= FLOW_NAME_ENTRY then
      finish(false, string.format("game over with score %d did not reach name entry (state %d)", score, state))
      return
    end
    if score <= 0 then finish(false, "score is 0") return end
    -- Expected row from the pre-insert table: number of rows with score >= ours (ties rank below).
    exp_row, exp_score = 0, score
    for i = 0, 9 do if g32(O_TSCORE + i * 4) >= score then exp_row = exp_row + 1 end end
    if exp_row > 9 then finish(false, string.format("score %d does not rank", score)) return end
    phase = "name"
    return
  end

  if phase == "name" then
    if state == FLOW_NAME_ENTRY then
      -- Countdown reachability: the drawn seconds must follow entry.idle (rounded up; one frame of draw/step skew).
      local shown = mem:read_u8(namesec_addr)
      local idle = mem:read_u16(flow_addr + O_EIDLE)
      local want = (NAME_TIMEOUT - idle + 59) // 60
      if shown ~= 0xff then
        cd_frames = cd_frames + 1
        if shown > cd_max then cd_max = shown end
        if math.abs(shown - want) > 1 then
          cd_bad = cd_bad + 1
          cd_note = string.format("shown %d, idle %d wants %d", shown, idle, want)
        end
      end
      -- One action = hold the button HOLD frames, release, wait GAP frames for the game to step, decide again.
      if entry_gap > 0 then
        entry_gap = entry_gap - 1
        if entry_gap <= GAP then release_all() end
        return
      end
      local pos = mem:read_u8(flow_addr + O_EPOS)
      local want = NAME:sub(pos + 1, pos + 1)
      local target = (want:byte() - ("A"):byte())          -- all name characters here are A-Z
      local sym = mem:read_u8(flow_addr + O_ESYM + pos)
      if sym ~= target then ubtn:set_value(1) else abtn:set_value(1) end
      entry_gap = HOLD + GAP
      return
    end
    if state == FLOW_SAVE_REMINDER or state == FLOW_ATTRACT_TITLE then
      if cd_frames == 0 or cd_bad > 0 or cd_max ~= NAME_TIMEOUT // 60 then
        finish(false, string.format("name countdown: %d frames drawn, %d wrong (%s), max %d, want %d",
          cd_frames, cd_bad, cd_note, cd_max, NAME_TIMEOUT // 60))
        return
      end
      phase = "saved"
    else finish(false, string.format("name entry left to state %d", state)) return end
  end

  if phase == "saved" then
    if state ~= FLOW_ATTRACT_TITLE then return end
    local saves = mem:read_u32(saves_addr)
    if saves ~= saves0 + 1 then
      finish(false, string.format("save sentinel %d -> %d, expected +1", saves0, saves)) return
    end
    local iname, iscore = image_row(exp_row)
    if iname ~= NAME or iscore ~= exp_score then
      finish(false, string.format("boot 1 backup RAM row %d is '%s' %d, expected '%s' %d", exp_row, iname, iscore, NAME, exp_score))
      return
    end
    local f = io.open(expect, "w")
    f:write(string.format("%s|%d|%d\n", NAME, exp_score, exp_row))
    f:close()
    saved_msg = string.format("boot 1 saved '%s' %d at row %d (saves %d -> %d)", NAME, exp_score, exp_row, saves0, saves)
    phase = "after"; after_n, after_fc, last_fc, stall, pal_zero = 0, mem:read_u32(frame_addr), mem:read_u32(frame_addr), 0, 0
    return
  end

  -- After the save the game returns to the BIOS (SYSTEM_RETURN) and is re-entered through USER; the attract
  -- loop must keep running past the BIOS title timeout. Before the PLAYER_START fix the credit was never
  -- taken, so UniBIOS forced a start at the title timeout, the game refused it, and UniBIOS re-entered USER 3
  -- about every 12 frames: palette cleared, video_init restarted, game_loop never ran (blink, only the sky).
  -- Asserts over AFTER_FRAMES: the game frame counter never stalls for STALL_MAX frames, it advances for at
  -- least 90% of the frames, and the fix text palette (colour 1) is zero for at most PAL_ZERO_MAX frames.
  if phase == "after" then
    after_n = after_n + 1
    local fc = mem:read_u32(frame_addr)
    if fc == last_fc then stall = stall + 1 else stall = 0 end
    last_fc = fc
    if mem:read_u16(PAL_TEXT_C1) == 0 then pal_zero = pal_zero + 1 end
    if stall >= STALL_MAX then
      finish(false, string.format("%s, then game loop stalled %d frames at frame %d after the save (state %d, palette zero %d frames)",
        saved_msg, stall, after_n, state, pal_zero))
      return
    end
    if after_n < AFTER_FRAMES then return end
    local ran = fc - after_fc
    if ran < AFTER_FRAMES * 9 // 10 then
      finish(false, string.format("%s, then game loop ran only %d of %d frames after the save", saved_msg, ran, AFTER_FRAMES)) return
    end
    if pal_zero > PAL_ZERO_MAX then
      finish(false, string.format("%s, then text palette was zero %d of %d frames after the save", saved_msg, pal_zero, AFTER_FRAMES)) return
    end
    finish(true, string.format("%s; attract ran %d of %d frames after it (palette zero %d)", saved_msg, ran, AFTER_FRAMES, pal_zero))
  end
end)
