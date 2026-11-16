-- Party Rule of the Round check (make test-party): UniBIOS 4.0, one coin, Up to the PARTY row, Start:
--   P1. the title PARTY row shows the goal line on fix row 27 (lit cells >= 19: "A NEW TWIST EVERY ROUND" is 19 letters, spaces read as empty);
--   P2. the round starts as Arena with party_rule ROUND and a twist 1..6; the round-start banner (RS_ROUND) lights fix row 12 (twist
--       name) and row 13 (goal line, >= 19 lit cells) and ROUND nn on row 11; at RS_GO rows 11..13 hold only the GO! cells
--       (row 12 and 11 blank, row 13 at most 3 lit);
--   P3. the round then plays (round_start RS_NONE, flow still PLAYING).
-- Env: BRAWL_FLOW_ADDR (hex), BRAWL_PARTY_LAYOUT (party_probe.c output), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_PARTY_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O = { flow = L[1], frule = L[2], rule = L[3], twist = L[4], rs = L[5], mode = L[6] }
local K = { playing = L[7], round = L[8], rs_round = L[9], rs_go = L[10], arena = L[11] }
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, match)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname:find(match, 1, true) then return f end end
end
local coin, start1, up = field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start"), field(":edge:joy:JOY1", "P1 Up")
local ss = dofile("tests/mame/start_seq.lua")(coin, start1, up)
local function b(o) return mem:read_u8(flow_addr + o) end
local fix, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "partyvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then fix[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
  elseif r == 4 then vmod = data end
end)
local function lit(row) -- cells of a fix row that differ from an empty cell (column 0 of row 27 is never written)
  local blank, n = (fix[0x7000 + 0 * 32 + 27] or 0) & 0xfff, 0
  for c = 0, 39 do if ((fix[0x7000 + c * 32 + row] or 0) & 0xfff) ~= blank then n = n + 1 end end
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
if not (coin and start1 and up) then finish(false, "missing ports") end

local n, phase, t0, title_goal, banner = 0, "boot", 0, nil, nil
emu.register_frame_done(function()
  n = n + 1
  if n > 30000 then finish(false, "watchdog in phase " .. phase) return end
  local playing = b(O.flow) == K.playing
  if phase == "boot" then
    if n == 600 then phase = "start"; t0 = n; ss.begin(n) end
  elseif phase == "start" then
    local k = n - t0
    if k == 95 then title_goal = lit(27) end -- before Start (frame 100): Up has moved the cursor to PARTY
    if ss.step(n, playing, true) then phase = "banner"; t0 = n end
  elseif phase == "banner" then
    local rs = b(O.rs)
    if title_goal == nil or title_goal < 19 then finish(false, "title goal row 27 lit cells " .. tostring(title_goal) .. ", want >= 19") return end
    if b(O.frule) ~= K.round or b(O.rule) ~= K.round then finish(false, "party rule flow " .. b(O.frule) .. " game " .. b(O.rule) .. ", want ROUND " .. K.round) return end
    if b(O.mode) ~= K.arena then finish(false, "mode " .. b(O.mode) .. ", want ARENA") return end
    if rs == K.rs_round then
      local tw = b(O.twist)
      if tw < 1 or tw > 6 then finish(false, "twist " .. tw .. ", want 1..6") return end
      if lit(12) >= 5 and lit(13) >= 19 and lit(11) >= 5 then banner = { tw, lit(11), lit(12), lit(13) } end
    elseif rs == K.rs_go and banner then
      phase = "go"; t0 = n
    elseif n - t0 > 1500 then finish(false, "banner never lit: round_start " .. rs) end
  elseif phase == "go" then
    local k = n - t0
    if k == 5 then
      if lit(11) ~= 0 or lit(12) ~= 0 or lit(13) > 3 then finish(false, "banner not cleared at GO: rows 11/12/13 lit " .. lit(11) .. "/" .. lit(12) .. "/" .. lit(13)) return end
    elseif k == 200 then
      if not playing or b(O.rs) ~= 0 then finish(false, "round does not play: flow " .. b(O.flow) .. " round_start " .. b(O.rs)) return end
      finish(true, string.format("PARTY Rule of the Round: title goal row lit %d; twist %d banner rows 11/12/13 lit %d/%d/%d; cleared at GO; round plays", title_goal, banner[1], banner[2], banner[3], banner[4]))
    end
  end
end)
