-- Left column regression (make test-left-column): a sprite placed in screen columns x 0..15 must be drawn like one at x 16.
-- Bug: sprite slot 0 (the sky column at x 0, y 0..96) was drawn in front of every other sprite in x 0..15, so the ceiling,
-- the hero and islands vanished there. Fix invariant: slot 0 carries no sprite (SCB3 height 0) while PLAYING.
-- Drives the real ROM from boot to PLAYING (Arena, or Gum Trip when BRAWL_LC_MODE=trip: Down on the title, then Start).
-- In PLAYING it writes a test sprite through the video port into slot 380 (beyond SPRITE_SLOT_END 377, unused by the game),
-- tiles 0x319/0x31a (opaque ROM tiles, override with BRAWL_LC_TILE), and for each case counts the screen pixels that change
-- between sprite on and sprite off inside the sprite's 16 pixel column (pixels that also change between two off captures,
-- i.e. moving background, are ignored). Cases: A x 0 y 60, B x 16 y 60 (control), C x 0 y 150 (control below the sky column).
-- PASS: changed(A) >= changed(B) / 2, changed(B) > 0, changed(C) > 0, and slot 0 SCB3 height 0 on every checked frame.
-- Env: BRAWL_FLOW_ADDR (g_flow), BRAWL_FRAME_ADDR (g_frame_counter), BRAWL_LC_MODE (arena | trip), BRAWL_LC_TILE (optional,
-- hex first tile), BRAWL_RESULT.
local flow_addr  = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local frame_addr = tonumber(os.getenv("BRAWL_FRAME_ADDR"), 16)
local result     = os.getenv("BRAWL_RESULT")
local mode       = os.getenv("BRAWL_LC_MODE") or "arena"
local TILE       = tonumber(os.getenv("BRAWL_LC_TILE") or "319", 16)
local O_STATE    = 0          -- Flow.state is the first byte (as small_sootling_check.lua via flier_probe)
local FLOW_PLAYING = 3
local TEST_SLOT  = 380
local CASES = { { name = "x0_y60", x = 0, y = 60 }, { name = "x16_y60", x = 16, y = 60 }, { name = "x0_y150", x = 0, y = 150 } }
local SLOT_STEP_SETTLE = 90   -- PLAYING frames before the first case

local mem    = manager.machine.devices[":maincpu"].spaces["program"]
local screen = manager.machine.screens[":screen"]
local ports  = manager.machine.ioport.ports
local function field(tag, name)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname == name then return f end end
end
local coin  = field(":AUDIO_COIN", "Coin 1")
local start = field(":edge:joy:START", "1 Player Start")
local down  = field(":edge:joy:JOY1", "P1 Down")
local ss = dofile("tests/mame/start_seq.lua")(coin, start, down)
local abtn  = field(":edge:joy:JOY1", "P1 A")

-- VRAM shadow through a write tap on the video port, as small_sootling_check.lua
local vram, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "leftcolvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then vram[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
  elseif r == 4 then vmod = data end
end)

local done = false
local bd_checked, bd_bad, bd_last = 0, 0, 0
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

local function vw(addr, val) mem:write_u16(0x3c0004, 1); mem:write_u16(0x3c0000, addr); mem:write_u16(0x3c0002, val) end
local function place(x, y)
  vw(TEST_SLOT * 64, TILE); vw(TEST_SLOT * 64 + 1, 0x0e00)
  vw(TEST_SLOT * 64 + 2, TILE + 1); vw(TEST_SLOT * 64 + 3, 0x0e00)
  vw(0x8000 + TEST_SLOT, 0x0fff)
  vw(0x8200 + TEST_SLOT, (((496 - y) & 0x1ff) << 7) | 2)
  vw(0x8400 + TEST_SLOT, (x & 0x1ff) << 7)
end
local function hide() vw(0x8200 + TEST_SLOT, 0) end

local W, H
local function grab()
  local px = screen:pixels()
  W, H = screen.width, screen.height
  return px
end
-- changed pixels in columns x..x+15, rows y..y+31 between on and off, ignoring pixels that differ between off1 and off2
local function changed(on, off1, off2, x, y)
  local n = 0
  for row = y, y + 31 do
    if row >= 0 and row < H then
      for col = x, x + 15 do
        local o = (row * W + col) * 4 + 1
        local a, b, c = on:sub(o, o + 3), off1:sub(o, o + 3), off2:sub(o, o + 3)
        if b == c and a ~= b then n = n + 1 end
      end
    end
  end
  return n
end

local n, phase, fc0, coin_at, pa, playing = 0, "boot", nil, nil, 0, 0
local ci, step, counts, caps = 1, 0, {}, {}
local slot0_bad, slot0_checked, slot0_w3 = 0, 0, 0

emu.register_frame_done(function() local ok_, err_ = pcall(function()
  if done then return end
  n = n + 1
  if n > 3000 then finish(false, "watchdog in phase " .. phase) return end
  if not (coin and start and down and flow_addr and frame_addr and result) then
    finish(false, "missing input field, address or result path") return
  end
  local state = mem:read_u8(flow_addr + O_STATE)
  local fc = mem:read_u32(frame_addr)
  if phase == "boot" then
    if fc ~= 0 then fc0 = fc0 or fc end
    if fc0 and fc - fc0 >= 30 then phase = "coin"; coin_at = n; ss.begin(n) end
    return
  elseif phase == "coin" then
    if ss.step(n, state == FLOW_PLAYING, mode == "trip") then phase = "play"; pa = n end
    return
  end
  -- phase "play"
  if state ~= FLOW_PLAYING then finish(false, "left PLAYING in case " .. ci) return end
  playing = n - pa
  -- keep the flier up: with gravity it would fall into the water and the flow would leave PLAYING. One flap every 16 frames gains
  -- height (impulse 40960 against 16 * 2048 of gravity), the 9 frame cooldown is respected.
  if abtn then abtn:set_value((playing % 16) < 2 and 1 or 0) end
  -- invariant: slot 0 has no height on every checked PLAYING frame
  local w3 = vram[0x8200] or 0
  slot0_w3 = w3
  slot0_checked = slot0_checked + 1
  if (w3 & 0x3f) ~= 0 then slot0_bad = slot0_bad + 1 end
  -- backdrop (palette RAM entry 4095): Gum Trip shows the sky colour (115,82,165) = 0x075A, the arena keeps #1a1238 = 0x5113
  if playing >= 3 then
    local bd = mem:read_u16(0x401FFE)
    bd_checked = bd_checked + 1
    if bd ~= (mode == "trip" and 0x075A or 0x5113) then bd_bad = bd_bad + 1; bd_last = bd end
  end
  if playing < SLOT_STEP_SETTLE then return end
  if ci > #CASES then
    local a, b, c = counts[1], counts[2], counts[3]
    local pass = b > 0 and c > 0 and 2 * a >= b and slot0_bad == 0 and bd_bad == 0 and bd_checked > 0
    finish(pass, string.format("mode %s: changed(x0,y60)=%d want >= %d (half of changed(x16,y60)); changed(x16,y60)=%d want > 0; changed(x0,y150)=%d want > 0; slot 0 SCB3=%04x height 0 wanted, bad frames %d of %d; backdrop word 0x%04x wanted, bad frames %d of %d (last bad read 0x%04x)",
      mode, a, (b + 1) // 2, b, c, slot0_w3, slot0_bad, slot0_checked, mode == "trip" and 0x075A or 0x5113, bd_bad, bd_checked, bd_last))
    return
  end
  -- per case: step 0 capture off1, 1 place, 3 capture on + hide, 5 capture off2 + count + restore (SCB3 0)
  local cs = CASES[ci]
  if step == 0 then caps.off1 = grab()
  elseif step == 1 then place(cs.x, cs.y)
  elseif step == 3 then caps.on = grab(); hide()
  elseif step == 5 then
    local off2 = grab()
    counts[ci] = changed(caps.on, caps.off1, off2, cs.x, cs.y)
    hide(); ci = ci + 1; step = -1
  end
  step = step + 1
end) if not ok_ then print("BRAWL_TEST ERROR " .. tostring(err_)); finish(false, "Lua error: " .. tostring(err_)) end end)
