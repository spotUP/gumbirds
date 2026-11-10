-- High score reachability (make test-reach, plan P5.1). Two MAME boots share one nvram dir; the Makefile
-- passes ROOFLINE_PHASE=1 or 2. Sentinel-driven, no fixed frame numbers (the cap is only a hang guard).
--   Phase 1: coin, start, autoplay (as laser_check.lua) until the score passes the table minimum, then idle
--            until the hero dies; GAME_OVER -> NAME_ENTRY; type ROOFLINE_NAME with the joystick (up cycles,
--            A confirms) by reading the cursor position and symbol from RAM; wait for the table screen.
--            Asserts: score > 0 and ranks, g_hiscore_saves went 0 -> 1, backup RAM image holds name and
--            score at the row computed from the pre-insert table. Writes name/score/row to ROOFLINE_EXPECT.
--            Then keeps running 1500 frames past the BIOS title timeout: the game loop must not stall and the
--            text palette must stay set (PLAYER_START regression: blink, only the sky, after the save).
--   Phase 2: fresh boot, same nvram: backup RAM image and the flow table hold that name and score at that
--            row, g_hiscore_saves is 0 (loaded, not re-saved).
-- Env (hex addresses from nm): ROOFLINE_FLOW_ADDR, ROOFLINE_FRAME_ADDR, ROOFLINE_HISCORE_ADDR,
--   ROOFLINE_SAVES_ADDR; ROOFLINE_REACH_LAYOUT (reach_probe.c output); ROOFLINE_RESULT, ROOFLINE_EXPECT (files).
local phase_no   = tonumber(os.getenv("ROOFLINE_PHASE"))
local flow_addr  = tonumber(os.getenv("ROOFLINE_FLOW_ADDR") or "", 16)
local frame_addr = tonumber(os.getenv("ROOFLINE_FRAME_ADDR") or "", 16)
local hs_addr    = tonumber(os.getenv("ROOFLINE_HISCORE_ADDR") or "", 16)
local saves_addr = tonumber(os.getenv("ROOFLINE_SAVES_ADDR") or "", 16)
local result     = os.getenv("ROOFLINE_RESULT")
local expect     = os.getenv("ROOFLINE_EXPECT")
local NAME       = "REACHTST"
local lay = {}
for v in (os.getenv("ROOFLINE_REACH_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local O_STATE, O_LAST, O_TNAME, O_TSCORE, O_ENAME, O_ESYM, O_EPOS, O_EDONE = table.unpack(lay, 1, 8)
local O_FX, O_FVX, O_FGROUND, O_SCORE = table.unpack(lay, 9, 12)   -- arena slice: flier x, vx (16.16), on_ground; game score
local mem    = manager.machine.devices[":maincpu"].spaces["program"]
local ports  = manager.machine.ioport.ports

local FLOW_ATTRACT_TABLE, FLOW_PLAYING, FLOW_GAME_OVER, FLOW_NAME_ENTRY, FLOW_SAVE_REMINDER = 1, 3, 4, 5, 6
local OB_VENT, OB_CABLE, OB_DRONE, OB_BOT = 0, 1, 2, 3
local HERO_RIGHT, FIRE_MIN, FIRE_MAX = 48 + 26, 80, 300
local TABLE_MIN = 1000             -- factory table last place; a score must beat it (ties rank below)
local JUMP_LEAD = tonumber(os.getenv("ROOFLINE_JL") or "4")
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
  print("ROOFLINE_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

local function obstacles()
  local list = {}
  for i = 0, N_OBS - 1 do
    local a = flow_addr + O_OBS + i * OBS_SZ
    if mem:read_u8(a + E_ACT) ~= 0 then
      list[#list + 1] = { t = mem:read_u8(a + E_TYPE), x = s16(mem:read_u32(a + E_X) // 256 & 0xFFFF),
                          w = s16(mem:read_u16(a + E_W)) }
    end
  end
  return list
end
local function plan(list, can_fire, speed)   -- speed in px per frame; jump lead = 10 frames of travel
  local fire, jump, duck = false, false, false
  for _, o in ipairs(list) do
    local ahead = o.x - HERO_RIGHT
    if not (o.x + o.w < 48) then
      if (o.t == OB_DRONE or o.t == OB_BOT) and o.x > FIRE_MIN and o.x < FIRE_MAX and can_fire then fire = true end
      if (o.t == OB_VENT or o.t == OB_BOT) and ahead < speed * JUMP_LEAD then jump = true end
      if o.t == OB_CABLE and ahead < speed * 8 then duck = true end
    end
  end
  return fire, jump, duck
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
      if phase_no == 2 then phase = "verify" else phase = "coin"; coin_at = n; coin:set_value(1) end
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
    if n == coin_at + 15 then coin:set_value(0) end
    if n >= coin_at + 30 then phase = "start"; start:set_value(1) end
    return
  elseif phase == "start" then
    if state == FLOW_PLAYING then start:set_value(0); phase = "play" else return end
  end

  if phase == "play" then
    if state == FLOW_PLAYING then
      if not idle_play and g32(O_SCORE) > TABLE_MIN + 200 then idle_play = true end
      -- Arena slice autoplay: stand on the middle island (no input; survival time is the score) until the score
      -- passes the table minimum, then walk off the right edge, steer back over the gap with left + flap until the
      -- horizontal speed is gone, and fall into the water (same manoeuvre as tests/mame/flier_check.lua).
      if not idle_play then
        release_all()
      else
        local fx = s32(g32(O_FX)) / 65536
        local vx = s32(g32(O_FVX)) / 65536
        local ground = mem:read_u8(flow_addr + O_FGROUND)
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
    if state == FLOW_SAVE_REMINDER or state == FLOW_ATTRACT_TABLE then phase = "saved"
    else finish(false, string.format("name entry left to state %d", state)) return end
  end

  if phase == "saved" then
    if state ~= FLOW_ATTRACT_TABLE then return end
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
