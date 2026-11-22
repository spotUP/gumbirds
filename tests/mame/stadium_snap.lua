-- Stadium hook for the Gum Games check scripts (Big Blow, Burst Race, Gum Fling).
-- Snapshot (optional): STADIUM_MOOD (0 moon, 1 dusk, 2 storm), STADIUM_MOOD_OFF (offsetof(Flow, game.mood), tests/mame/stadium_mood_probe.c),
-- STADIUM_NAME (snapshot file name, saved in MAME's -snapshot_directory). Without STADIUM_MOOD, poke and shot do nothing.
-- Sprite peak (always): poke() runs every PLAYING frame; it counts the sprites covering each scanline over ALL slots (SCB3/SCB4 shadow
-- via a write tap, tests/mame/sprite_line_count.lua) and keeps the maximum. The hardware limit is 96 per line (checks fail above it).
-- peak_max() is the maximum, peak_text() a result suffix.
-- Crowd busy (with STADIUM_ST_ADDR = g_st of src/stadium_hw.c, STADIUM_VBBUSY_ADDR = g_vb_busy, hex): poke() counts the busy vblanks
-- (frame logic overran) on frames where a side cheers or waves and the crowd animates (Stadium.t moved in the last 3 frames, so the
-- strip load on mode entry is not counted). busy_bad(ceiling) is true when more than ceiling (default 0) were seen; busy_text() a result suffix.
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
  local st_addr, busy_addr = tonumber(os.getenv("STADIUM_ST_ADDR") or "", 16), tonumber(os.getenv("STADIUM_VBBUSY_ADDR") or "", 16)
  local lt, moved, pbusy, act, abusy, pairs_seen = nil, nil, nil, 0, 0, {}
  local function crowd()
    if not (st_addr and busy_addr) then return end
    local m0, m1, t = mem:read_u8(st_addr), mem:read_u8(st_addr + 1), mem:read_u32(st_addr + 2)   -- Stadium {u8 mode[2]; u16 t[2]; ...}
    local b = mem:read_u16(busy_addr)
    if lt and t ~= lt then moved = frames end
    lt = t
    if pbusy and (m0 ~= 0 or m1 ~= 0) and moved and frames - moved <= 3 then
      act = act + 1; abusy = abusy + ((b - pbusy) & 0xffff)
      pairs_seen[m0 .. "/" .. m1] = true
    end
    pbusy = b
  end
  function H.busy_bad(ceiling) return st_addr ~= nil and busy_addr ~= nil and (abusy > (ceiling or 0) or act == 0) end
  function H.busy_text()
    if not (st_addr and busy_addr) then return " [crowd busy: STADIUM_ST_ADDR / STADIUM_VBBUSY_ADDR missing]" end
    local k = {}
    for p in pairs(pairs_seen) do k[#k + 1] = p end
    table.sort(k)
    return string.format(" [crowd busy vblanks %d in %d cheer/wave frames, modes %s]", abusy, act, table.concat(k, ","))
  end
  function H.poke()
    crowd()
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
