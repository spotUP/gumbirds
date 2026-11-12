-- Shared sprites-per-scanline counter for the MAME Lua checks (sprite_peak_check.lua, trip_check.lua).
-- count(vram, first, last): vram is the shadow of the LSPC video RAM (SCB3 at 0x8200, SCB4 at 0x8400 plus the sprite index);
-- returns cnt, cnt_screen (each [0..223]): how many sprites with index first .. last-1 cover each screen line. A sticky sprite
-- (SCB3 bit 6) takes y and height of its head and x = head x + 16 per column.
--   cnt        every sprite with height > 0, wherever its x is: the LSPC picks sprites per line by y only, so parked and off screen
--              sprites count against the hardware limit of 96 per line. This is the figure the limits are checked against.
--   cnt_screen only sprites with screen x in -15..319 (the earlier figure of this counter): printed next to cnt, never asserted.
local M = {}
local SCB3, SCB4 = 0x8200, 0x8400
function M.count(vram, first, last)
  local cnt, cnt_screen = {}, {}
  for y = 0, 223 do cnt[y] = 0; cnt_screen[y] = 0 end
  local head_top, head_h, head_x, col = nil, 0, 0, 0
  for s = first, last - 1 do
    local w3 = vram[SCB3 + s] or 0
    local w4 = vram[SCB4 + s] or 0
    if (w3 & 0x40) ~= 0 and head_top then
      col = col + 1                                   -- sticky: head y and height, x one column on
    else
      head_top = (496 - (w3 >> 7)) & 0x1ff
      head_h = w3 & 0x3f
      head_x = (w4 >> 7) & 0x1ff
      col = 0
    end
    local x = head_x + 16 * col
    if x >= 384 then x = x - 512 end
    if head_h > 0 then
      local on_screen = x > -16 and x < 320
      for y = 0, 223 do
        if ((y - head_top) & 0x1ff) < head_h * 16 then
          cnt[y] = cnt[y] + 1
          if on_screen then cnt_screen[y] = cnt_screen[y] + 1 end
        end
      end
    end
  end
  return cnt, cnt_screen
end
return M
