-- Arena instant join check (make test-arena-join): UniBIOS 4.0, two coins, Arena 1P Start, play, then P2 Start:
--   J1. the BIOS takes the credit (1 -> 0) and the whole match restarts at once: players 2, both heroes ALIVE, Game.score, lives scores and
--       matches_won back to 0 (the script pokes score 777 and matches_won 3 first, so a restart is visible);
--   J2. the CREDITS plate shows on fix row 29 cols 28..36 in play, before and after the join (the Start press changed the count).
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_JOIN_LAYOUT (arena_join_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_JOIN_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { flow = L[1], players = L[2], mode = L[3], score = L[4], won = L[5], hstate = L[6], szf = L[7], lscore = L[8], szl = L[9] }
local K = { playing = L[10], alive = L[11], arena = L[12] }
local CREDIT = 0x10fe00
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, match)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname:find(match, 1, true) then return f end end
end
local coin, start1 = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start")
local start2 = field(":edge:joy:START", "2 Players Start") or field(":edge:joy:START", "2 Player")
local ss = dofile("tests/mame/start_seq.lua")(coin, start1, nil)
local function b(o) return mem:read_u8(flow_addr + o) end
local function w32(o) return mem:read_u32(flow_addr + o) end
local fix, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "joinvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then fix[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
  elseif r == 4 then vmod = data end
end)
local function plate_lit() -- cells of the CREDITS plate that differ from an empty cell of the same row
  local blank, n = (fix[0x7000 + 20 * 32 + 29] or 0) & 0xfff, 0
  for c = 28, 36 do if ((fix[0x7000 + c * 32 + 29] or 0) & 0xfff) ~= blank then n = n + 1 end end
  return n
end
local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end
if not (coin and start1 and start2) then finish(false, "missing ports") end

local n, phase, t0 = 0, "boot", 0
local function press(f, k, from) f:set_value((k >= from and (k - from) < 15) and 1 or 0) end
emu.register_frame_done(function()
  n = n + 1
  local playing = b(O.flow) == K.playing and b(O.mode) == K.arena
  if n > 30000 then finish(false, "watchdog in phase " .. phase) return end
  local k = n - t0
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    if ss.step(n, playing, nil) then phase = "play"; t0 = n end
  elseif phase == "play" then
    if k == 5 then coin:set_value(1) end
    if k == 20 then coin:set_value(0) end
    if k == 200 then
      mem:write_u32(flow_addr + O.score, 777); mem:write_u32(flow_addr + O.won, 3); mem:write_u32(flow_addr + O.lscore, 555)
      if b(O.players) ~= 1 or mem:read_u8(CREDIT) ~= 1 then finish(false, "setup: players " .. b(O.players) .. " credit " .. mem:read_u8(CREDIT) .. ", want 1 and 1") return end
      if plate_lit() < 8 then finish(false, "CREDITS plate not shown in play: " .. plate_lit() .. " of 9 cells (the space cell reads as empty, so 8 is full)") return end
    end
    if k >= 210 then press(start2, k, 210) end
    if k == 330 then
      if mem:read_u8(CREDIT) ~= 0 then finish(false, "credit " .. mem:read_u8(CREDIT) .. " after P2 Start, want 0") return end
      if b(O.players) ~= 2 then finish(false, "players " .. b(O.players) .. " after P2 Start, want 2") return end
      local s0, s1 = b(O.hstate), mem:read_u8(flow_addr + O.hstate + O.szf)
      if s0 ~= K.alive or s1 ~= K.alive then finish(false, "hero states " .. s0 .. "/" .. s1 .. ", want ALIVE " .. K.alive) return end
      if w32(O.score) ~= 0 or w32(O.lscore) ~= 0 or w32(O.lscore + O.szl) ~= 0 or w32(O.won) ~= 0 then
        finish(false, "scores not reset: score " .. w32(O.score) .. " lives0 " .. w32(O.lscore) .. " lives1 " .. w32(O.lscore + O.szl) .. " won " .. w32(O.won)) return end
      if plate_lit() < 8 then finish(false, "CREDITS plate gone after the join: " .. plate_lit() .. " of 9 cells (the space cell reads as empty, so 8 is full)") return end
      finish(true, "Arena P2 join restarted the match: credit 1 -> 0, both ALIVE, scores and rounds 0, credits plate shown")
    end
  end
end)
