-- Stadium hook for the Gum Games check scripts (Big Blow, Burst Race, Gum Fling).
-- Snapshot (optional): STADIUM_MOOD (0 moon, 1 dusk, 2 storm), STADIUM_MOOD_OFF (offsetof(Flow, game.mood), tests/mame/stadium_mood_probe.c),
-- STADIUM_NAME (snapshot file name, saved in MAME's -snapshot_directory). Without STADIUM_MOOD, poke and shot do nothing.
-- Sprite peak (always): poke() runs every PLAYING frame; it counts the sprites covering each scanline over ALL slots (SCB3/SCB4 shadow
-- via a write tap, tests/mame/sprite_line_count.lua) and keeps the maximum. The hardware limit is 96 per line (checks fail above it).
-- peak_max() is the maximum, peak_text() a result suffix.
local line_count = dofile(((debug and debug.getinfo and debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$")) or "tests/mame") .. "/sprite_line_count.lua")
return function(mem, flow_addr)
  local mood, off = tonumber(os.getenv("STADIUM_MOOD") or ""), tonumber(os.getenv("STADIUM_MOOD_OFF") or "")
  local name = os.getenv("STADIUM_NAME")
  local H = { on = mood ~= nil and off ~= nil and name ~= nil }
  local vram, vaddr, vmod, peak, at = {}, 0, 1, 0, 0
  stadium_peak_tap = mem:install_write_tap(0x3c0000, 0x3c0007, "stadiumpeak", function(offset, data, mask)
    local r = offset & 0xe
    if r == 0 then vaddr = data
    elseif r == 2 then vram[vaddr] = data; vaddr = (vaddr + vmod) & 0xffff
    elseif r == 4 then vmod = data end
  end)
  local frames = 0
  function H.poke()
    if H.on then mem:write_u8(flow_addr + off, mood) end   -- the match start picks its own mood; the next frame shows this one
    frames = frames + 1
    local cnt = line_count.count(vram, 0, 381)
    for y = 0, 223 do if cnt[y] > peak then peak = cnt[y]; at = y end end
  end
  function H.shot(n2) if H.on then manager.machine.screens[":screen"]:snapshot(n2 or name) end end
  function H.peak_max() return peak end
  function H.peak_text() return string.format(" [sprite peak %d per line (limit 96) at line %d, %d frames]", peak, at, frames) end
  return H
end
