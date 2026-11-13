-- Shared start sequence for MAME checks (BG4): ONE coin, then Start presses until the game is PLAYING.
-- One Start press takes the credit and begins the highlighted mode; Down (trip) is pressed before it. Later presses are retries.
-- Usage: local ss = dofile("tests/mame/start_seq.lua")(coin, start, down)   (down optional: P1 Down button field)
--   ss.begin(n)                 call on the frame the coin is inserted (sets the coin)
--   ss.step(n, playing, trip)   call every frame after begin(); returns true once `playing` is true (buttons released).
--                               trip = true presses Down once before Start (Gum Trip); a number n presses Down n times (2 = Arcade).
-- Timing from begin(): coin held 15 frames; Down at +70..+78 (trip only);
-- Start at +100..+115; later presses every 60 frames (15 on) as a retry.
return function(coin, start, down)
  local s, t0 = {}, nil
  -- Optional credit probe (BIOS credit byte 0x10FE00, found by diffing BIOS RAM on a coin under UniBIOS 4.0; BCD, 1 = one credit):
  -- s.watch(mem) records the credit before the first press, between the presses and when play starts; s.verdict(expect)
  -- returns nil when it was (before, after_first, in_play) = expect, else a message. Only meaningful under UniBIOS (test-reach).
  local CREDIT, mem = 0x10fe00, nil
  function s.watch(m) mem = m end
  function s.begin(n) t0 = n; coin:set_value(1) end
  function s.step(n, playing, trip)
    local k = n - t0
    if k >= 15 then coin:set_value(0) end
    if mem then
      if k == 39 then s.c_before = mem:read_u8(CREDIT) end
    end
    if playing then
      start:set_value(0); if down then down:set_value(0) end
      if mem and not s.c_play then s.c_play = mem:read_u8(CREDIT); s.c_first = s.c_play end -- one Start press: no second sample
      return true
    end
    local on = 0
    if k >= 100 and ((k - 100) % 60) < 16 then on = 1 end
    start:set_value(on)
    if trip and down then
      local d = 0
      for i = 0, (trip == true and 1 or trip) - 1 do if k >= 70 + 10 * i and k < 79 + 10 * i then d = 1 end end
      down:set_value(d)
    end
    return false
  end
  function s.verdict(b, f, p)
    if s.c_before == b and s.c_first == f and s.c_play == p then return nil end
    return string.format("credits (before first Start, after first Start, in play) = (%s, %s, %s), want (%d, %d, %d)",
      tostring(s.c_before), tostring(s.c_first), tostring(s.c_play), b, f, p)
  end
  return s
end
