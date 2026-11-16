-- PARTY two-player name entry check (make test-party-name): UniBIOS 4.0, 1P Start, P2 joins, then the script ends the run as a PARTY game
-- with both scores ranking (flow state GAME_OVER, last_mode PARTY, last_players 2). Both players type a name (P1 on joy 1, P2 on joy 2),
-- and then, for 1500 frames past the BIOS title timeout:
--   N1. both names are in the backup RAM image party table (g_hiscore_image) after the save;
--   N2. the game frame counter keeps advancing (no stall);
--   N3. the fix text palette (colour 1) is not zero for more than a few frames: the screen is not blank after the return to the BIOS.
-- Env: BRAWL_FLOW_ADDR, BRAWL_FRAME_ADDR, BRAWL_HISCORE_ADDR (hex), BRAWL_NAME_LAYOUT (party_name_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local frame_addr = tonumber(os.getenv("BRAWL_FRAME_ADDR"), 16)
local hs_addr = tonumber(os.getenv("BRAWL_HISCORE_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_NAME_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { state = L[1], timer = L[2], score = L[3], players = L[4], h = L[5], lmode = L[6], lrule = L[7], pos = L[8], sym = L[9] }
local K = { party = L[11], playing = L[12], over = L[13], entry = L[14], title = L[15] }
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, match)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname == match then return f end end
end
local coin, start1, start2 = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start"), field(":edge:joy:START", "2 Players Start")
local up = { field(":edge:joy:JOY1", "P1 Up"), field(":edge:joy:JOY2", "P2 Up") }
local a = { field(":edge:joy:JOY1", "P1 A"), field(":edge:joy:JOY2", "P2 A") }
local ss = dofile("tests/mame/start_seq.lua")(coin, start1, nil)
local function b(o) return mem:read_u8(flow_addr + o) end
local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and start2 and up[1] and up[2] and a[1] and a[2]) then finish(false, "missing ports") end
local function str(addr, len) local t = {} for i = 0, len - 1 do t[#t + 1] = string.char(mem:read_u8(addr + i)) end return table.concat(t) end

local NAMES = { "BBBBBBBB", "CCCCCCCC" }
local AFTER, PAL_C1 = 1500, 0x400002
local n, phase, t0, gap = 0, "boot", 0, 0
local fc_last, stall, stall_max, pal_zero, after_n, fc0 = 0, 0, 0, 0, 0, 0
local seen = {}
emu.register_frame_done(function()
  if done then return end
  n = n + 1
  if n > 30000 then finish(false, "watchdog in phase " .. phase .. " state " .. b(O.state)) return end
  local k = n - t0
  local state = b(O.state)
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    if ss.step(n, state == K.playing, nil) then phase = "join"; t0 = n end
  elseif phase == "join" then
    if k == 5 then coin:set_value(1) end
    if k == 20 then coin:set_value(0) end
    start2:set_value((k >= 110 and k < 125) and 1 or 0)
    if k == 300 then
      if state ~= K.playing then finish(false, "not playing after join, state " .. state) return end
      -- end the run as a two-player PARTY game with both scores ranking
      mem:write_u8(flow_addr + O.lmode, K.party); mem:write_u8(flow_addr + O.lrule, 0); mem:write_u8(flow_addr + O.players, 2)
      mem:write_u32(flow_addr + O.score, 7000); mem:write_u32(flow_addr + O.score + 4, 6000)
      mem:write_u8(flow_addr + O.h, 0); mem:write_u16(flow_addr + O.timer, 0)
      mem:write_u8(flow_addr + O.state, K.over)
      phase = "name"; t0 = n
    end
  elseif phase == "name" then
    if state == K.entry then
      seen[b(O.h)] = true
      if gap > 0 then
        gap = gap - 1
        if gap <= 4 then for i = 1, 2 do up[i]:set_value(0); a[i]:set_value(0) end end
        return
      end
      local h, pos = b(O.h), b(O.pos)
      local target = NAMES[h + 1]:byte(pos + 1) - 65
      if b(O.sym + pos) ~= target then up[h + 1]:set_value(1) else a[h + 1]:set_value(1) end
      gap = 7
    elseif state == K.title and seen[0] and seen[1] then
      for i = 1, 2 do up[i]:set_value(0); a[i]:set_value(0) end
      phase = "after"; fc0 = mem:read_u32(frame_addr); fc_last = fc0
    elseif k > 6000 then
      finish(false, "name entry did not finish, state " .. state .. ", entry 1 seen " .. tostring(seen[0]) .. ", entry 2 seen " .. tostring(seen[1]))
    end
  elseif phase == "after" then
    after_n = after_n + 1
    local fc = mem:read_u32(frame_addr)
    if fc == fc_last then stall = stall + 1; if stall > stall_max then stall_max = stall end else stall = 0 end
    fc_last = fc
    if mem:read_u16(PAL_C1) == 0 then pal_zero = pal_zero + 1 end
    if after_n < AFTER then return end
    local found = 0
    for i = 0, 9 do
      local nm = str(hs_addr + 6 + K.party * 120 + i * 12, 8)
      if nm == NAMES[1] or nm == NAMES[2] then found = found + 1 end
    end
    local ran = fc_last - fc0
    local msg = string.format("names in party image %d of 2, frames ran %d of %d, max stall %d, palette zero %d, state %d", found, ran, AFTER, stall_max, pal_zero, b(O.state))
    if found ~= 2 then finish(false, msg)
    elseif ran < AFTER * 9 // 10 or stall_max >= 60 then finish(false, "game loop stalled: " .. msg)
    elseif pal_zero > 60 then finish(false, "screen blank: " .. msg)
    else finish(true, msg) end
  end
end)
