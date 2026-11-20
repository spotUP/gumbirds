-- Arena (normal stage play) flush saturation baseline: one coin, Start, sample the flush counters while PLAYING (measurement only, result line to BRAWL_RESULT).
-- Env: BRAWL_FLOW_ADDR, BRAWL_BLOW_LAYOUT (gum_pop_drop_probe.c: [1] state, [12] PLAYING), BRAWL_RESULT, plus flush_sample.lua's.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local L = {}
for v in (os.getenv("BRAWL_BLOW_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local function field(tag, match)
  local p = manager.machine.ioport.ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname:find(match, 1, true) then return f end end
end
local ss = dofile("tests/mame/start_seq.lua")(field(":AUDIO_COIN", "Coin 1"), field(":edge:joy:START", "1 Player Start"), nil)
local fs = dofile("tests/mame/flush_sample.lua")(mem)
local n, t0, played, started = 0, 0, 0, false
emu.register_frame_done(function()
  n = n + 1
  if n == 600 then started = true; t0 = n; ss.begin(n) end
  if not started then return end
  local playing = mem:read_u8(flow_addr + L[1]) == L[12]
  ss.step(n, playing, nil)
  if playing then fs.frame(); played = played + 1 end
  if played >= 1500 or n > 6000 then
    local f = io.open(os.getenv("BRAWL_RESULT"), "w"); f:write(fs.report("arena") .. string.format(" (PLAYING frames %d)\n", played)); f:close()
    manager.machine:exit()
  end
end)
