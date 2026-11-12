-- Shared helpers for MAME checks that must walk through the rounds of one game (round order: water, spikes, lava, fire).
-- Usage: local rs = dofile("tests/mame/round_skip.lua")(mem, flow_addr, flay)   (flay = BRAWL_FLIER_LAYOUT numbers)
--   rs.win()   RAM poke: every computer flier becomes GONE, so game_step_arena wins the round on its next step
--   rs.live()  true when no round end (banner hold, camera slide) and no round start text (ROUND nn, GO!) is running
-- Needs BRAWL_RE_ADDR (nm symbol g_round_end_s, src/main.c): u16 round_end, round_timer, round_start, flier visible.
return function(mem, flow_addr, flay)
  local O_COUNT, O_C0X, O_C1X, O_C0STATE = flay[13], flay[17], flay[20], flay[23]
  local stride = O_C1X - O_C0X -- sizeof(Flier), from the probe
  local re = tonumber(os.getenv("BRAWL_RE_ADDR") or "", 16)
  assert(re, "round_skip: BRAWL_RE_ADDR missing")
  local FL_GONE = 4
  local rs = {}
  function rs.win()
    for i = 0, mem:read_u8(flow_addr + O_COUNT) - 1 do mem:write_u8(flow_addr + O_C0STATE + i * stride, FL_GONE) end
  end
  function rs.live() return mem:read_u16(re) == 0 and mem:read_u16(re + 4) == 0 end
  return rs
end
