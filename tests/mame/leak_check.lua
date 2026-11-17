-- Gum leak jets (make test-leak): start an arena game, hold the player and computer flier 0 at one balloon, then read the pool in RAM:
-- a player jet (type 0xF0 | leak frame) and a computer jet (0xE0 | leak frame) must exist, and every computer jet must sit at a higher
-- pool index than the lowest gum bubble (0xC0 | frame), so it draws over it. Env: BRAWL_FLOW_ADDR, BRAWL_FRAME_ADDR, BRAWL_FLIER_LAYOUT,
-- BRAWL_POOL_ADDR (g_pool, hex), BRAWL_RESULT.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local frame_addr = tonumber(os.getenv("BRAWL_FRAME_ADDR"), 16)
local pool_addr = tonumber(os.getenv("BRAWL_POOL_ADDR"), 16)
local result = os.getenv("BRAWL_RESULT")
local lay = {}
for v in (os.getenv("BRAWL_FLIER_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local O_STATE, O_BAL, O_C0BAL = lay[1], lay[11], lay[24]
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local ports = manager.machine.ioport.ports
local function field(tag, pred)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if pred(fname) then return f end end
end
local coin = field(":AUDIO_COIN", function(nm) return nm == "Coin 1" end)
local start = field(":edge:joy:START", function(nm) return nm == "1 Player Start" end)
local ss = dofile("tests/mame/start_seq.lua")(coin, start)
local STRIDE, POOL_MAX, TYPE_OFF = 20, 32, 16   -- sizeof(PoolObj), POOL_MAX, offsetof(PoolObj, type) (src/core/obj_pool.h)
local n, phase, fc0, play_n, done = 0, "boot", nil, nil, false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w"); f:write((ok and "PASS " or "FAIL ") .. msg .. "\n"); f:close()
  manager.machine:exit()
end
emu.register_frame_done(function()
  if done then return end
  n = n + 1
  if n > 3000 then finish(false, "watchdog in phase " .. phase) return end
  local state, fc = mem:read_u8(flow_addr + O_STATE), mem:read_u32(frame_addr)
  if phase == "boot" then
    fc0 = fc0 or (fc ~= 0 and fc or nil)
    if fc0 and fc - fc0 >= 30 then phase = "coin"; ss.begin(n) end
  elseif phase == "coin" then
    if ss.step(n, state == 3) then phase = "play"; play_n = n end
  else
    mem:write_u8(flow_addr + O_BAL, 1); mem:write_u8(flow_addr + O_C0BAL, 1)
    if n - play_n < 120 then return end
    local t, low, jetp, jetc, bad = {}, 99, 0, 0, nil
    for i = 0, POOL_MAX - 1 do
      t[i] = mem:read_u8(pool_addr + i * STRIDE + TYPE_OFF)
      if t[i] >= 0xC0 and t[i] < 0xE0 and i < low then low = i end
    end
    for i = 0, POOL_MAX - 1 do
      if t[i] >= 0xF0 then jetp = jetp + 1
      elseif t[i] >= 0xE0 then jetc = jetc + 1; if i < low then bad = i end end
    end
    if jetp < 1 or jetc < 1 then finish(false, string.format("player jets %d, computer jets %d at one balloon, want at least 1 of each", jetp, jetc)) return end
    if bad then finish(false, string.format("computer jet at pool index %d is below every gum bubble (lowest %d): it would draw behind", bad, low)) return end
    finish(true, string.format("one balloon: %d player jet(s), %d computer jet(s), every computer jet above the lowest bubble (index %d)", jetp, jetc, low))
  end
end)
