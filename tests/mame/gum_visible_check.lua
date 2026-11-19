-- Gum Games / Party visibility check (make test-gum-visible), regression for the owner report 2026-11-18 "Big Blow: bird at the screen edge, no
-- bubble; Toss Gum: no gum". Scenario by BRAWL_SCEN: "blow" (menu, GUM GAMES row, Start; mash A and B) or "toss" (Arena Start, rule TOSS, P2 join).
-- On at least 90% of the frames while the bubble should show (Big Blow: blow phase; Toss Gum: hold and flight phases, after 30 settle frames):
--   V1. the hero body sprite (HERO_SPRITE) has a non-zero height and its x is inside the screen, 24..264 (not at an edge);
--   V2. the bubble sprite (Big Blow: GUM_SPRITE..+GUM_COUNT-1 any; Toss Gum: ROOST_SPRITE) has a non-zero height, an x inside 0..304, and its
--       SCB1 palette (Toss Gum: GUMBUBBLE_PAL_SLOT) holds a non-black colour.
-- Sprite state comes from a shadow of every LSPC VRAM write. Env: BRAWL_FLOW_ADDR (hex), BRAWL_VIS_LAYOUT (gum_visible_probe.c output), BRAWL_RESULT, BRAWL_SCEN.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result, scen = os.getenv("BRAWL_RESULT"), os.getenv("BRAWL_SCEN")
local L = {}
for v in (os.getenv("BRAWL_VIS_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { state = L[1], mode = L[2], toss = L[3], hx = L[4], tphase = L[5], bphase = L[6], fmode = L[7], frule = L[8] }
local K = { playing = L[9], gum = L[10], party = L[11], ptoss = L[12], hold = L[13], flight = L[14], blow = L[15],
            hero = L[16], gum1 = L[17], gumn = L[18], roost = L[19], bpal = L[20], gpal = L[21] }
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, match)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname:find(match, 1, true) then return f end end
end
local coin, start1, start2, up = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start"), field(":edge:joy:START", "2 Players Start") or field(":edge:joy:START", "2 Player"), field(":edge:joy:JOY1", "P1 Up")
local abtn, bbtn = field(":edge:joy:JOY1", "P1 A"), field(":edge:joy:JOY1", "P1 B")
local ss = dofile("tests/mame/start_seq.lua")(coin, start1, up)
local function b(o) return mem:read_u8(flow_addr + o) end
local vram, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "visvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then vram[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
  elseif r == 4 then vmod = data end
end)
local function sx(s) return ((vram[0x8400 + s] or 0xa000) >> 7) end              -- SCB4 x, 9 bits
local function sh(s) return (vram[0x8200 + s] or 0) & 0x3f end                   -- SCB3 height
local function pal_lit(p) for i = 1, 15 do if mem:read_u16(0x400000 + p * 32 + i * 2) & 0x7fff ~= 0 then return true end end return false end
local function bubble_ok(first, count, palwant)
  for s = first, first + count - 1 do
    local pal = (vram[s * 64 + 1] or 0) >> 8
    if sh(s) > 0 and sx(s) <= 304 and (not palwant or pal == palwant) and pal_lit(pal) then return true end
  end
  return false
end
local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and start2 and up and abtn and bbtn) then finish(false, "missing ports") end
local function press(f, k, from) f:set_value((k >= from and (k - from) < 15) and 1 or 0) end

local n, phase, t0, press_n, frames, hero_ok, bub_ok, hero_x = 0, "boot", 0, 0, 0, 0, 0, -1
local function judge()
  if frames < 60 then finish(false, "bubble phase seen on only " .. frames .. " frames") return end
  local hp, bp = hero_ok * 100 // frames, bub_ok * 100 // frames
  if hp < 90 then finish(false, string.format("%s: hero sprite on screen (24..264, height>0) on %d%% of %d frames (last hero sprite x %d)", scen, hp, frames, hero_x)) return end
  if bp < 90 then finish(false, string.format("%s: bubble sprite visible on %d%% of %d frames", scen, bp, frames)) return end
  finish(true, string.format("%s: hero %d%%, bubble %d%% of %d frames", scen, hp, bp, frames))
end
emu.register_frame_done(function()
  n = n + 1
  if n > 30000 then finish(false, "watchdog in phase " .. phase) return end
  local k = n - t0
  local playing = b(O.state) == K.playing
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    if scen == "blow" then
      if ss.step(n, playing, 1) then phase = "watch"; t0 = n end
    else
      if ss.step(n, playing, nil) then phase = "join"; t0 = n end
    end
  elseif phase == "join" then
    if k == 5 then coin:set_value(1) end
    if k == 20 then coin:set_value(0) end
    if k == 100 then mem:write_u8(flow_addr + O.fmode, K.party); mem:write_u8(flow_addr + O.frule, K.ptoss) end
    if k >= 110 then press(start2, k, 110) end
    if k > 130 and playing and b(O.mode) == K.gum and b(O.toss) == 1 then phase = "watch"; t0 = n end
    if k > 3000 then finish(false, "Toss Gum never started") end
  elseif phase == "watch" then
    local live
    if scen == "blow" then
      live = b(O.bphase) == K.blow
      local want = k % 4 == 0 and (k // 4) % 8 < 6   -- mash in bursts so the bubble stays below the burst size
      abtn:set_value((want and press_n % 2 == 0) and 1 or 0); bbtn:set_value((want and press_n % 2 == 1) and 1 or 0)
      if want then press_n = press_n + 1 end
    else
      local tp = b(O.tphase)
      live = tp == K.hold or tp == K.flight
    end
    if live and k > 30 then
      frames = frames + 1
      local hx = sx(K.hero); hero_x = hx
      if sh(K.hero) > 0 and hx >= 24 and hx <= 264 then hero_ok = hero_ok + 1 end
      local ok
      if scen == "blow" then ok = bubble_ok(K.gum1, K.gumn, nil) else ok = bubble_ok(K.roost, 1, K.bpal) end
      if ok then bub_ok = bub_ok + 1 end
    end
    if frames >= 300 or k > 2500 then judge() end
  end
end)
