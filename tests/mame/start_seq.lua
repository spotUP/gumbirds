-- Shared start sequence for MAME checks (BG4): ONE coin, then Start presses until the game is PLAYING.
-- The first Start press opens the title mode select (no credit is taken), the second begins play (credit taken).
-- Usage: local ss = dofile("tests/mame/start_seq.lua")(coin, start, down)   (down optional: P1 Down button field)
--   ss.begin(n)                 call on the frame the coin is inserted (sets the coin)
--   ss.step(n, playing, trip)   call every frame after begin(); returns true once `playing` is true (buttons released).
--                               trip = true presses Down between the two Starts (mode select: Gum Trip).
-- Timing from begin(): coin held 15 frames; Start press 1 at +40..+55; Down at +70..+78 (trip only);
-- Start press 2 at +100..+115; later presses every 60 frames (15 on) as a retry.
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
      if k == 90 then s.c_first = mem:read_u8(CREDIT) end
    end
    if playing then
      start:set_value(0); if down then down:set_value(0) end
      if mem and not s.c_play then s.c_play = mem:read_u8(CREDIT) end
      return true
    end
    local on = 0
    if k >= 40 and k < 56 then on = 1
    elseif k >= 100 and ((k - 100) % 60) < 16 then on = 1 end
    start:set_value(on)
    if trip and down then down:set_value((k >= 70 and k < 79) and 1 or 0) end
    return false
  end
  function s.verdict(b, f, p)
    if s.c_before == b and s.c_first == f and s.c_play == p then return nil end
    return string.format("credits (before first Start, after first Start, in play) = (%s, %s, %s), want (%d, %d, %d)",
      tostring(s.c_before), tostring(s.c_first), tostring(s.c_play), b, f, p)
  end
  return s
end
