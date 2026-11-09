-- Headless hit-look reachability check (make test-hit). Starts a game with coin + start, does not move,
-- waits for the first obstacle hit (invuln set) and then records, frame by frame, the hero animation and
-- frame the game wrote to the sprite registers (sentinels g_hero_shown_anim / g_hero_shown_frame, 0xFFFF
-- while the hero sprite is hidden). Asserts: HIT pose during the first HIT_POSE_FRAMES, afterwards the
-- run pose with some frames hidden and some shown, and the normal look once invulnerability ends.
-- Env: ROOFLINE_FLOW_ADDR, ROOFLINE_HERO_ANIM_ADDR, ROOFLINE_HERO_FRAME_ADDR (hex), ROOFLINE_HIT_LAYOUT
-- (hit_probe.c output), ROOFLINE_RESULT (file).
local flow_addr  = tonumber(os.getenv("ROOFLINE_FLOW_ADDR"), 16)
local anim_addr  = tonumber(os.getenv("ROOFLINE_HERO_ANIM_ADDR"), 16)
local frame_addr = tonumber(os.getenv("ROOFLINE_HERO_FRAME_ADDR"), 16)
local result     = os.getenv("ROOFLINE_RESULT")
local lay = {}
for v in (os.getenv("ROOFLINE_HIT_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local O_STATE, O_INVULN, O_LIVES, INVULN, POSE, BLINK, ANIM_HIT, ANIM_RUN =
  lay[1], lay[2], lay[3], lay[4], lay[5], lay[6], lay[7], lay[8]
local mem   = manager.machine.devices[":maincpu"].spaces["program"]
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
  print("ROOFLINE_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

local n, hit_at = 0, nil
local rec = {}   -- rec[k] = {anim, frame} for k frames after the first frame seen with invuln > 0
local pre_hit_bad = false
emu.register_frame_done(function()
  n = n + 1
  if n == 320 and coin then coin:set_value(1)
  elseif n == 335 and coin then coin:set_value(0)
  elseif n == 360 and start then start:set_value(1)
  elseif n == 375 and start then start:set_value(0) end
  if mem:read_u8(flow_addr + O_STATE) ~= 3 then
    if n > 2400 then finish(false, "never reached PLAYING") end
    return
  end
  local inv  = mem:read_u16(flow_addr + O_INVULN)
  local anim = mem:read_u16(anim_addr)
  local frm  = mem:read_u16(frame_addr)
  if not hit_at then
    if inv > 0 then hit_at = n
    else
      if anim == ANIM_HIT then pre_hit_bad = true end
      if n > 5000 then finish(false, "no hit by frame 5000") end
      return
    end
  end
  rec[#rec + 1] = {anim, frm, inv}
  if #rec < INVULN + 8 then return end
  -- k = 1 is the first frame seen with invuln > 0; the sentinel may lag the counter by one frame.
  local pose_bad, run_shown, hidden, bad_run = 0, 0, 0, 0
  for k = 2, POSE - 1 do if rec[k][1] ~= ANIM_HIT then pose_bad = pose_bad + 1 end end
  for k = POSE + 3, INVULN - 2 do
    local a = rec[k][1]
    if a == 0xFFFF then hidden = hidden + 1
    elseif a == ANIM_RUN then run_shown = run_shown + 1
    else bad_run = bad_run + 1 end
  end
  local after = rec[INVULN + 6]
  local ok = (not pre_hit_bad) and pose_bad == 0 and bad_run == 0 and hidden >= BLINK and run_shown >= BLINK
             and after[3] == 0 and after[1] == ANIM_RUN
  finish(ok, string.format("hit at frame %d: HIT pose bad %d, blink phase hidden %d shown(run) %d other %d, after invuln anim %d inv %d, pre-hit HIT pose %s",
    hit_at, pose_bad, hidden, run_shown, bad_run, after[1], after[3], tostring(pre_hit_bad)))
end)
