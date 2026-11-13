-- Headless attract check (make test-attract). Real ROM, no input for three attract cycles (title, table, demo):
--   T1. the game mode during the demo phases is arena, Gum Trip, arcade in turn, and Flow.demo is 1 in each;
--   T3. in every demo the caption, lever, A and Start cells hold the overlay tiles, the captions differ per mode, the action word changes, and 20 frames after the demo no overlay icon is left;
--   T2. g_frame_counter never stalls for 30 screen frames and the title highlight (Flow.mode) never changes;
-- Env: BRAWL_FLOW_ADDR, BRAWL_FRAME_ADDR (hex), BRAWL_ATTRACT_LAYOUT (attract_probe.c output), BRAWL_RESULT.
local flow_addr  = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local frame_addr = tonumber(os.getenv("BRAWL_FRAME_ADDR"), 16)
local result     = os.getenv("BRAWL_RESULT")
local L = {}
for v in (os.getenv("BRAWL_ATTRACT_LAYOUT") or ""):gmatch("%d+") do L[#L + 1] = tonumber(v) end
local O_FLOW, O_DEMO, O_HMODE, O_MODE = L[1], L[2], L[3], L[4]
local K = { title = L[5], demo = L[6], arena = L[7], trip = L[8], arcade = L[9] }
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local function b(o) return mem:read_u8(flow_addr + o) end

-- VRAM shadow through a write tap on the video port (as left_column_check.lua): the fix layer cell (c, r) is word 0x7000 + c * 32 + r.
local vram, vaddr, vmod = {}, 0, 1
tap_vram = mem:install_write_tap(0x3c0000, 0x3c0007, "attractvram", function(offset, data, mask)
  local r = offset & 0xe
  if r == 0 then vaddr = data
  elseif r == 2 then vram[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
  elseif r == 4 then vmod = data end
end)
local ICON_MIN, ICON_MAX = 0x400, 0x400 + 59 - 1   -- ATTRACT_FIX_BASE .. + ATTRACT_ICON_TILES - 1 (src/vram_layout.h, build/gen/attract_icons.h)
local function tile(c, r) return (vram[0x7000 + c * 32 + r] or 0) & 0xfff end
local function is_icon(c, r) local t = tile(c, r); return t >= ICON_MIN and t <= ICON_MAX end
local function overlay_icons()
  local n = 0
  for c = 1, 13 do for r = 21, 26 do if is_icon(c, r) then n = n + 1 end end end
  return n
end
local caps, words, exit_at = {}, {}, nil

local done = false
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

-- The coin-in-attract path is covered by host test_flow (flow_coin in every demo) and make test-unibios; nullbios does not take it.
local stall, max_stall = 0, 0
local want = { K.arena, K.trip, K.arcade, K.arena }
local seen, in_demo, n, fc_last, hmode, done_at, lens, demo_n = 0, false, 0, nil, nil, nil, {}, 0
emu.register_frame_done(function()
  n = n + 1
  if n > 9000 then finish(false, "watchdog: demos seen " .. seen) return end
  local fc = mem:read_u32(frame_addr)
  if n < 240 then fc_last = fc return end   -- the BIOS boot holds g_frame_counter at 0 for a while: sample after it settles
  -- a single repeated value is a long frame (the table and title redraws); a stall is 30 screen frames without a tick
  stall = fc == fc_last and stall + 1 or 0
  max_stall = math.max(max_stall, stall)
  if stall >= 30 then finish(false, "T2 g_frame_counter stalled at " .. fc .. " in flow " .. b(O_FLOW)) return end
  fc_last = fc
  hmode = hmode or b(O_HMODE)
  if b(O_HMODE) ~= hmode then finish(false, "T2 title highlight changed to " .. b(O_HMODE)) return end
  if exit_at and n >= exit_at then
    exit_at = nil
    if overlay_icons() ~= 0 then finish(false, "T3 overlay icons still on screen " .. overlay_icons() .. " cells after the demo") return end
  end
  if b(O_FLOW) == K.demo then
    demo_n = demo_n + 1
    if demo_n == 200 then
      local lever = false; for c = 1, 4 do for r = 25, 26 do lever = lever or is_icon(c, r) end end
      if not (lever and is_icon(6, 24) and is_icon(10, 25)) then finish(false, string.format("T3 demo %d: lever/A/Start cells hold no icon tiles (%x %x %x)", seen, tile(1, 25), tile(6, 24), tile(10, 25))) return end
      caps[seen] = tile(1, 21)
      if caps[seen] == 0 or caps[seen] == 255 or tile(1, 22) == 0 then finish(false, "T3 demo " .. seen .. ": caption cells blank") return end
      for k = 1, seen - 1 do if caps[k] == caps[seen] and seen <= 3 then finish(false, "T3 demos " .. k .. " and " .. seen .. " show the same caption tile") return end end
    end
    words[tile(1, 23) * 256 + tile(2, 23)] = true
    if not in_demo then
      in_demo, demo_n = true, 1
      seen = seen + 1
      if b(O_MODE) ~= want[seen] or b(O_DEMO) ~= 1 then finish(false, string.format("T1 demo %d mode %d demo flag %d, want mode %d", seen, b(O_MODE), b(O_DEMO), want[seen])) return end
      print(string.format("BRAWL_TEST demo %d mode %d starts at frame %d", seen, b(O_MODE), n))
      if seen == 4 then done_at = n + 60 end
    end
    if done_at and n == done_at then
      finish(true, string.format("modes arena, trip, arcade, arena; demo lengths %s; longest counter stall %d screen frames", table.concat(lens, ","), max_stall))
    end
  elseif in_demo then
    lens[#lens + 1] = demo_n; in_demo = false
    exit_at = n + 20
    local nw = 0; for _ in pairs(words) do nw = nw + 1 end
    if nw < 2 then finish(false, "T3 action word never changed in demo " .. seen) return end
    words = {}
  end
end)
