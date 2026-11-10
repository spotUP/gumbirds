-- Headless background scroll check (make test-scroll). Arena: the city is a still backdrop in play. Runs the real
-- game (attract, coin, start, flaps, walk off the island into the water, game over, coin and start again) and keeps a Lua shadow of LSPC VRAM from the writes to
-- REG_VRAMADDR / REG_VRAMRW / REG_VRAMMOD. At every frame end (MAME frame_done is at vblank start, and make
-- test-vblank asserts every VRAM write lands in vblank) the shadow is what the frame just shown displayed. For each
-- of the three city rings (src/bg.c update_ring) it asserts the on-screen chain matches the scroll the game
-- committed for that frame: the g_bg_scroll_px value at the previous vblank start, when the main loop parked and
-- the vblank flush took that step's queue. Checked words per ring: head SCB3 (not sticky) and SCB4 x of the first
-- visible world column, SCB4 x of slot 0 (always a chain head), sticky SCB3 of every other slot.
-- Fails on a late scroll write (step committed, but the screen shows an older scroll: the flush ran out of budget
-- before the ring words) and on a skipped step (main loop not parked at vblank start while PLAYING, so the flush
-- was skipped and the screen holds the old scroll for a frame). Still city: g_bg_scroll_px must be identical on every
-- PLAYING frame of every run (no scroll in the arena), and the shadow must show exactly that scroll (a ring redrawn
-- or moved in play fails the ring check). The old g_bg_rebases sentinel is dropped: bg_update gets distance 0 forever,
-- so it can never count.
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_HIT_LAYOUT (hit_probe.c output, first value = flow state offset),
-- BRAWL_RESULT (file), BRAWL_SCROLL_LOG (optional per-frame log file).
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
local A_SCROLL, A_PARKED, A_FC = syms.g_bg_scroll_px, syms.g_parked, syms.g_frame_counter

local STATE_PLAYING = 3
local END_FRAME = 3600
local MIN_CHECKED = 1500       -- PLAYING frames whose screen was checked
local SETTLE = 2               -- PLAYING frames after start not checked (first ring write is a full redraw)
local RING_FIRST = { 26, 47, 68 }  -- src/sprite_slots.h BG_FAR_SPRITE, BG_MID_SPRITE, BG_ROOF_SPRITE
local RING, COL = 21, 16
local SCB3, SCB4 = 0x8200, 0x8400

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

local function sx(v) return v >= 0x8000 and v - 0x10000 or v end
-- 0 when the shadow shows ring l at scroll s, else a short reason
local function ring_bad(l, s)
  local base = RING_FIRST[l]
  local first = s // COL
  local fs = first % RING
  local want4 = ((COL * first - s) & 0x1ff) << 7
  if (vram[SCB4 + base + fs] or -1) ~= want4 then return "head x" end
  if ((vram[SCB3 + base + fs] or 0x40) & 0x40) ~= 0 then return "head sticky" end
  if fs ~= 0 then
    local w0 = first + RING - fs
    if (vram[SCB4 + base] or -1) ~= ((COL * w0 - s) & 0x1ff) << 7 then return "slot0 x" end
  end
  for k = 1, RING - 1 do
    if k ~= fs and ((vram[SCB3 + base + k] or 0) & 0x40) == 0 then return "extra head " .. k end
  end
  return nil
end
-- scroll actually shown by ring l: head slot and its x give the scroll modulo the ring period
local function shown(l)
  local base = RING_FIRST[l]
  for k = 1, RING - 1 do
    if ((vram[SCB3 + base + k] or 0x40) & 0x40) == 0 then
      local x = (vram[SCB4 + base + k] or 0) >> 7
      if x >= 256 then x = x - 512 end
      return k, x
    end
  end
  return 0, ((vram[SCB4 + base] or 0) >> 7)
end

local n = 0
local phase, phase_at = "boot", 0
local pend = nil              -- scroll triple the flush of the current vblank takes (nil: none committed)
local pend_fc = nil
local prev_fc = nil
local checked, late, skipped, playing = 0, 0, 0, 0
local first_fail = nil
local still0, moved, runs = nil, 0, 0
local prev_state = nil
local since_start = 0

local function scroll3()
  return { mem:read_u32(A_SCROLL), mem:read_u32(A_SCROLL + 4), mem:read_u32(A_SCROLL + 8) }
end

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
    for l = 1, 3 do
      local why = ring_bad(l, pend[l])
      if why then
        late = late + 1
        local hk, hx = shown(l)
        local msg = string.format("frame %d fc %d ring %d want scroll %d, shows head slot %d x %d (%s)", n, pend_fc or -1, l - 1, pend[l], hk, hx, why)
        if not first_fail then first_fail = msg end
        if logf then logf:write("LATE " .. msg .. "\n") end
        break
      end
    end
  end
  if state == STATE_PLAYING then
    playing = playing + 1
    local s3 = scroll3()
    still0 = still0 or s3
    if s3[1] ~= still0[1] or s3[2] ~= still0[2] or s3[3] ~= still0[3] then
      moved = moved + 1
      if not first_fail then first_fail = string.format("frame %d city scroll moved in play: %d %d %d -> %d %d %d", n, still0[1], still0[2], still0[3], s3[1], s3[2], s3[3]) end
    end
    if since_start > SETTLE and not parked then
      skipped = skipped + 1
      local msg = string.format("frame %d fc %d main loop not parked at vblank start (flush skipped)", n, fc)
      if not first_fail then first_fail = msg end
      if logf then logf:write("SKIP " .. msg .. "\n") end
    end
  end
  if logf and state == STATE_PLAYING then
    local s = scroll3()
    logf:write(string.format("F %d fc %d dfc %d parked %d words %d scroll %d %d %d\n", n, fc, prev_fc and (fc - prev_fc) or -1, parked and 1 or 0, words_frame, s[1], s[2], s[3]))
  end
  prev_fc = fc
  words_frame = 0
  -- the step this vblank's flush takes
  if parked then pend = scroll3(); pend_fc = fc end
  if n >= END_FRAME then
    local msg = string.format("PLAYING frames %d in %d runs, checked %d, late scroll frames %d, skipped steps %d, scroll moved in %d frames%s",
      playing, runs, checked, late, skipped, moved, first_fail and (", first: " .. first_fail) or "")
    finish(checked >= MIN_CHECKED and late == 0 and skipped == 0 and moved == 0 and runs >= 2, msg)
  end
end)
