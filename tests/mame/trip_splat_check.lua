-- Gum Trip death splat for tests/mame/trip_check.lua (loaded by dofile into the global SPLAT: the main chunk is at Lua's 200 local limit).
-- Spec (src/core/game.h Game.trip_splat): a floor death (the bottom rock, or the kill line reached alive) starts the gum splat on
-- the death frame; a roof death starts it when the falling body reaches the floor line; a mid-air gum death makes no splat.
-- One splat per death. The splat cell top is the splat feet line (Game.trip_splat_y on the trip_splat frame) minus
-- SPLASH_SURFACE_ROW (src/core/splash_view.c splash_top).
-- Case "floor" (default): the flier is put on row 150 with no speed and A released; it sinks onto the cave floor rock and dies there.
--   Want: trip_splat on the death frame; a splat sprite goes live; on every live frame its top + SURFACE_ROW is that frame's feet
--   line (+-2 for the frame the script samples); that line is below the screen middle (TRIP_START_Y 90): the floor, not the roof.
-- Case "roof" (BRAWL_SPLAT_CASE=roof, by hand): the flier is put on row 5, inside the roof rock, which kills at once. Want: no
--   splat on the kill frame; trip_splat later, when the body falls onto the floor line; the same placement checks as "floor".
-- The death and splat start frames are printed as "BRAWL_SPLAT ..." (flier y, trip_splat_y, splat sprite top).
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
    S.dead = S.k
    print(string.format("BRAWL_SPLAT case %s death at k %d: flier y %d state %d trip_splat %d trip_splat_y %d", S.case, S.k, fy, st, mem:read_u8(flow + tlay[91]), sy))
  end
  if mem:read_u8(flow + tlay[91]) ~= 0 then
    if S.land then return string.format("a second trip_splat frame at k %d (first at k %d); want one splat per death", S.k, S.land) end
    S.land, S.y = S.k, sy
    print(string.format("BRAWL_SPLAT case %s splat start at k %d: flier y %d trip_splat_y %d", S.case, S.k, fy, sy))
  end
  if top then
    if not S.y then return string.format("splat sprite live (top %d) at k %d before any trip_splat frame", top, S.k) end
    if not S.top then print(string.format("BRAWL_SPLAT case %s splat sprite top %d (+%d = %d), trip_splat_y at start %d", S.case, top, tlay[93], top + tlay[93], S.y)) end
    S.top = top
    if not S.rock then
      -- no rectangle: the splat's solid base (rows SURFACE_ROW..) must start on the rock, not above it. The floor strip column under the
      -- splat middle (sprites TRIP_STRIP_SPRITE 323..344, 16 px each) has its top at the rock edge (SCB3 y, SCB4 x).
      local sx = ((vram[0x8400 + tlay[94] + 1] or 0) >> 7) & 0x1ff   -- middle splat column
      for c = 0, 21 do
        local w3, w4 = vram[0x8200 + 323 + c] or 0, vram[0x8400 + 323 + c] or 0
        local x = (w4 >> 7) & 0x1ff
        if (w3 & 0x3f) ~= 0 and (sx + 8 - x) % 512 < 16 then S.rock = (496 - ((w3 >> 7) & 0x1ff)) & 0x1ff end
      end
      if S.rock then
        print(string.format("BRAWL_SPLAT splat base row %d, rock edge %d", top + tlay[93], S.rock))
        if top + tlay[93] < S.rock - 1 then return string.format("splat base at row %d lies above the rock edge %d: the gum rectangle shows above the floor", top + tlay[93], S.rock) end
      end
    end
    if math.abs(top + tlay[93] - S.y) > 2 then return string.format("splat sprite top %d + %d is not the splat feet line %d", top, tlay[93], S.y) end
  end
  if S.k == 30 and not S.dead then return "trip splat check: the flier did not die within 30 frames of the " .. S.case .. " poke" end
  if S.dead and not S.land and S.k == S.dead + 90 then return "no trip_splat within 90 frames of the " .. S.case .. " death" end
  if S.land and S.k == S.land + 70 then S.late = S.live end
  if S.land then S.msg = string.format(", splat %s: death k %d, splat k %d, feet line %d, sprite top %s", S.case, S.dead, S.land, S.y, tostring(S.top)) end
  if not S.land or S.k < S.land + 75 then return nil end
  if S.case == "roof" and S.land <= S.dead then return string.format("a roof death splat started on the kill frame (k %d); want it when the body reaches the floor", S.land) end
  if S.case ~= "roof" and S.land ~= S.dead then return string.format("a floor death splat started at k %d, the death was at k %d; want the death frame", S.land, S.dead) end
  if S.live == 0 then return "no gum splat sprite went live after a Gum Trip " .. S.case .. " death (want a splat in SPLASH_SPRITE)" end
  if S.y <= 90 then return string.format("%s death splat on feet line %d, above the screen middle (want the floor)", S.case, S.y) end
  if S.live ~= S.late then return string.format("the gum splat was still live 70 frames after its start (live at +70: %d, at +75: %d; want hidden after 12 x 4 ticks)", S.late, S.live) end
  S.over = true
  return nil
end
