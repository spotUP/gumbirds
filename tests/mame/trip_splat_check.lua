-- Gum Trip death splat for tests/mame/trip_check.lua (loaded by dofile into the global SPLAT: the main chunk is at Lua's 200 local limit).
-- Spec (src/core/game.h Game.trip_splat): only a floor death (the bottom rock, or the kill line reached alive) starts the gum splat;
-- a roof death and a mid-air gum death fall on with no splat. The splat cell top is the dying feet line (Game.trip_splat_y) minus
-- SPLASH_SURFACE_ROW (src/core/splash_view.c splash_top).
-- Case "floor" (default): the flier is put on row 150 with no speed and A released; it sinks onto the cave floor rock and dies there.
--   Want: a splat sprite goes live; on every live frame its top + SURFACE_ROW is the feet line of the death frame (+-2 for the
--   frame the script samples); that line is below the screen middle (TRIP_START_Y 90): the floor, not the roof.
-- Case "roof" (BRAWL_SPLAT_CASE=roof, by hand): the flier is put on row 5, inside the roof rock, which kills at once. Want: no splat.
-- Every death frame is printed as "BRAWL_SPLAT ..." (flier y, trip_splat_y, splat sprite top).
SPLAT = { live = 0, msg = "", case = os.getenv("BRAWL_SPLAT_CASE") or "floor" }
local mem, flow, flay, tlay, vram, abtn
local function s16(v) return v >= 0x8000 and v - 0x10000 or v end
local function s32(v) return v >= 0x80000000 and v - 0x100000000 or v end
function SPLAT.init(mem_, flow_, flay_, tlay_, vram_, abtn_) mem, flow, flay, tlay, vram, abtn = mem_, flow_, flay_, tlay_, vram_, abtn_ end
-- One frame of the check; returns a failure message, or nil. Sets SPLAT.over when the case passed.
function SPLAT.step()
  local S = SPLAT
  if not S.k then
    abtn:set_value(0)
    mem:write_u32(flow + flay[7], (S.case == "roof" and 5 or 150) * 65536); mem:write_u32(flow + flay[9], 0)
    S.k = 0
  end
  S.k = S.k + 1
  local st, fy, sy = mem:read_u8(flow + flay[10]), s32(mem:read_u32(flow + flay[7])) // 65536, s16(mem:read_u16(flow + tlay[92]))
  local top
  for c = 0, tlay[95] - 1 do
    local w = vram[0x8200 + tlay[94] + c] or 0
    if (w & 0x3f) ~= 0 then local v = (496 - ((w >> 7) & 0x1ff)) & 0x1ff; top = top or (v >= 256 and v - 512 or v); S.live = S.live + 1 end
  end
  if not S.dead and st >= tlay[82] then
    S.dead, S.y = S.k, sy
    print(string.format("BRAWL_SPLAT case %s death at k %d: flier y %d state %d trip_splat %d trip_splat_y %d", S.case, S.k, fy, st, mem:read_u8(flow + tlay[91]), sy))
  end
  if top and S.y then
    if not S.top then print(string.format("BRAWL_SPLAT case %s splat sprite top %d (+%d = %d), trip_splat_y at death %d", S.case, top, tlay[93], top + tlay[93], S.y)) end
    S.top = top
    if math.abs(top + tlay[93] - S.y) > 2 then return string.format("splat sprite top %d + %d is not the death feet line %d", top, tlay[93], S.y) end
  end
  if S.k == 30 and not S.dead then return "trip splat check: the flier did not die within 30 frames of the " .. S.case .. " poke" end
  if S.k == 70 then S.late = S.live end
  if S.dead then S.msg = string.format(", splat %s: feet line %d, sprite top %s", S.case, S.y, tostring(S.top)) end
  if S.k < 75 then return nil end
  if S.case == "roof" then
    if S.live > 0 then return string.format("a roof death showed the gum splat (top %s, feet line %d); want no splat", tostring(S.top), S.y) end
  else
    if S.live == 0 then return "no gum splat sprite went live after a Gum Trip floor death (want a splat in SPLASH_SPRITE)" end
    if S.y <= 90 then return string.format("floor death splat on feet line %d, above the screen middle (want the floor)", S.y) end
    if S.live ~= S.late then return string.format("the gum splat was still live after 70 frames (live at 70: %d, at 75: %d; want hidden after 12 x 4 ticks)", S.late, S.live) end
  end
  S.over = true
  return nil
end
