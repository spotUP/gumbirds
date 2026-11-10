-- Headless background scroll check (make test-scroll). Runs the real game (attract, coin, start, flaps, walk off the island
-- into the water, game over, coin and start again) and keeps a Lua shadow of LSPC VRAM from the writes to REG_VRAMADDR /
-- REG_VRAMRW / REG_VRAMMOD. At every frame end (MAME frame_done is at vblank start, and make test-vblank asserts every VRAM
-- write lands in vblank) the shadow is what the frame just shown displayed. For each of the five background planes
-- (src/bg.c: one sprite per 16 px column, plane x = -((camera * k) >> 4) + 16 * column) it asserts every column shows the
-- x of the camera the game committed for that frame: g_cam_px at the previous vblank start, when the main loop parked
-- and the vblank flush took that step's queue. Slots, factors and column counts come from tests/mame/camera_probe.c.
-- Fails on a late scroll write (step committed, but the screen shows an older camera: the flush ran out of budget before
-- the plane words) and on a skipped step (main loop not parked at vblank start while PLAYING, so the flush was skipped).
-- Camera changes are counted so the report says whether the run exercised scrolling.
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_HIT_LAYOUT (hit_probe.c output, first value = flow state offset),
-- BRAWL_CAMERA_LAYOUT (camera_probe.c output), BRAWL_FLIER_LAYOUT, BRAWL_RESULT (file), BRAWL_SCROLL_LOG (optional per-frame log).
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result    = os.getenv("BRAWL_RESULT")
local log_path  = os.getenv("BRAWL_SCROLL_LOG")
local lay = {}
for v in (os.getenv("BRAWL_HIT_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local O_STATE = lay[1]

local function sym_addrs()
  local gcc
  for line in io.lines("config.mk") do gcc = gcc or line:match("^M68KGCC=(.*)$") end
  local nm = (gcc or "m68k-neogeo-elf-gcc"):gsub("gcc$", "nm")
  local t = {}
  local h = io.popen(nm .. " build/rom.elf")
  for line in h:lines() do
    local a, name = line:match("^(%x+) %a (%S+)$")
    if a then t[name] = tonumber(a, 16) end
  end
  h:close()
  return t
end
local syms = sym_addrs()
local A_CAM, A_PARKED, A_FC = syms.g_cam_px, syms.g_parked, syms.g_frame_counter

local STATE_PLAYING = 3
local END_FRAME = 3600
local MIN_CHECKED = 1500       -- PLAYING frames whose screen was checked
local SETTLE = 5               -- PLAYING frames after start not checked (the full plane redraw at start spreads over about 3 frames of flush budget)
local clay = {}
for v in (os.getenv("BRAWL_CAMERA_LAYOUT") or ""):gmatch("%d+") do clay[#clay + 1] = tonumber(v) end
local PLANES = {}  -- first sprite slot, parallax factor in sixteenths, column count, in draw order (camera_probe.c)
for p = 1, 5 do PLANES[p] = { slot = clay[9 + p], k = clay[14 + p], cols = clay[19 + p] } end
local SCB4 = 0x8400

local mem    = manager.machine.devices[":maincpu"].spaces["program"]
local ports  = manager.machine.ioport.ports
local function field(tag, name)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname == name then return f end end
end
local coin  = field(":AUDIO_COIN", "Coin 1")
local start = field(":edge:joy:START", "1 Player Start")
local rbtn  = field(":edge:joy:JOY1", "P1 Right")
local lbtn  = field(":edge:joy:JOY1", "P1 Left")
local abtn  = field(":edge:joy:JOY1", "P1 A")
local flay = {}
for v in (os.getenv("BRAWL_FLIER_LAYOUT") or ""):gmatch("%d+") do flay[#flay + 1] = tonumber(v) end
local drive = dofile("tests/mame/flier_drive.lua")(mem, flow_addr, flay, abtn, lbtn, rbtn)

local logf = log_path and io.open(log_path, "w") or nil
local function finish(ok, msg)
  if logf then logf:close() end
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

-- VRAM shadow
local vram, vaddr, vmod = {}, 0, 1
local words_frame = 0
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "scrollvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then
    vram[vaddr] = data
    vaddr = (vaddr + vmod) & 0xffff
    words_frame = words_frame + 1
  elseif r == 4 then vmod = data end
end)

-- nil when the shadow shows every plane column at camera cam, else a short reason
local function planes_bad(cam)
  for p, pl in ipairs(PLANES) do
    for c = 0, pl.cols - 1 do
      local want = ((-((cam * pl.k) >> 4) + 16 * c) & 0x1ff) << 7
      local got = vram[SCB4 + pl.slot + c] or -1
      if got ~= want then return string.format("plane %d column %d x word %d, want %d", p, c, got, want) end
    end
  end
  return nil
end

local n = 0
local phase, phase_at = "boot", 0
local pend = nil              -- camera the flush of the current vblank takes (nil: none committed)
local pend_fc = nil
local prev_fc = nil
local checked, late, skipped, playing = 0, 0, 0, 0
local first_fail = nil
local cam_prev, cam_moves, runs = nil, 0, 0
local prev_state = nil
local since_start = 0

emu.register_frame_done(function()
  n = n + 1
  local state = mem:read_u8(flow_addr + O_STATE)
  local fc = mem:read_u32(A_FC)
  if state == STATE_PLAYING and prev_state ~= STATE_PLAYING then runs = runs + 1 end
  prev_state = state
  local parked = mem:read_u8(A_PARKED) ~= 0
  -- inputs: coin + start from attract, flaps, steer off the island, restart after game over
  if state ~= STATE_PLAYING then
    since_start = 0
    if n > 300 and phase ~= "coin" and phase ~= "start" then phase = "coin"; phase_at = n; coin:set_value(1) end
    if phase == "coin" and n == phase_at + 15 then coin:set_value(0) end
    if phase == "coin" and n >= phase_at + 40 then phase = "start"; phase_at = n; start:set_value(1) end
    if phase == "start" and n == phase_at + 15 then start:set_value(0) end
    if phase == "start" and n >= phase_at + 120 then phase = "idle" end
  else
    if phase == "start" then start:set_value(0); phase = "play" end
    since_start = since_start + 1
    -- flap every 20 frames (3 held), walk right from frame 200 so the flier leaves the island and drowns
    if since_start < 200 then
      if since_start % 20 == 0 then abtn:set_value(1) elseif since_start % 20 == 3 then abtn:set_value(0) end
    end
    if since_start >= 200 then drive() end   -- walk off the island and drown (tests/mame/flier_drive.lua)
  end
  -- check the frame just shown against the step its vblank flush took
  if state == STATE_PLAYING and since_start > SETTLE and pend then
    checked = checked + 1
    local why = planes_bad(pend)
    if why then
      late = late + 1
      local msg = string.format("frame %d fc %d camera %d: %s", n, pend_fc or -1, pend, why)
      if not first_fail then first_fail = msg end
      if logf then logf:write("LATE " .. msg .. "\n") end
    end
  end
  if state == STATE_PLAYING then
    playing = playing + 1
    local cam = mem:read_u8(A_CAM)
    if cam_prev and cam ~= cam_prev then cam_moves = cam_moves + 1 end
    cam_prev = cam
    if since_start > SETTLE and not parked then
      skipped = skipped + 1
      local msg = string.format("frame %d fc %d main loop not parked at vblank start (flush skipped)", n, fc)
      if not first_fail then first_fail = msg end
      if logf then logf:write("SKIP " .. msg .. "\n") end
    end
  end
  if logf and state == STATE_PLAYING then
    logf:write(string.format("F %d fc %d dfc %d parked %d words %d camera %d\n", n, fc, prev_fc and (fc - prev_fc) or -1, parked and 1 or 0, words_frame, mem:read_u8(A_CAM)))
  end
  prev_fc = fc
  words_frame = 0
  -- the step this vblank's flush takes
  if parked then pend = mem:read_u8(A_CAM); pend_fc = fc end
  if n >= END_FRAME then
    local msg = string.format("PLAYING frames %d in %d runs, checked %d, late scroll frames %d, skipped steps %d, camera changed on %d frames%s",
      playing, runs, checked, late, skipped, cam_moves, first_fail and (", first: " .. first_fail) or "")
    finish(checked >= MIN_CHECKED and late == 0 and skipped == 0 and cam_moves > 0 and runs >= 2, msg)
  end
end)
