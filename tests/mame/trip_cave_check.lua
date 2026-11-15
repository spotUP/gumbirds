-- Cave checks for tests/mame/trip_check.lua (loaded by dofile into the global CAVE: the main chunk is at Lua's 200 local limit).
-- An independent restatement of the cave spec (thoughts/spot/2026-11-15-trip-cave-facts.md, drafts trip-cave-v3 / -fade /
-- -smoothfade), not the core code:
--   piece per 16 px column k of a chunk: flat (y0 roof win_top - 16, floor win_bottom); where the window edge moves 16 / 32 px
--   to the previous chunk (k < 3, in_known) or the next one (k >= COLS - 3, out_known, mirrored) and this chunk's window is the
--   narrower one there, an eased curve S16 (2 rows) / S32 (3 rows) whose rows start at y0 (roof y0 = other edge - 16).
--   Floor sprite from y0 down to the screen bottom, roof sprite ending at the piece bottom y0 + 16 rows.
--   Tiles: tripstrip range, palette slot floor S_PAL (gum), roof S_PAL + 1 (slate), never vflipped; only the floor piece rows
--   auto-animate; a curve piece row is hflipped with the piece, a flat one never.
--   Fade rows present on flat columns: floor = lip, 1 fill row, fade A, fade B, then one solid tile; roof (up from the rim) =
--   rim, fade A, fade B, then one black tile. Solid / black / fill are each one tile everywhere.
CAVE = { bad = 0, first = nil, flat_rows = 0, curve_cols = 0, cols = {} }
local L, mem, s16, COLS
function CAVE.init(tlay, mem_, s16_, chunk_px)
  L = { in_top = tlay[85], in_bot = tlay[86], out_top = tlay[87], out_bot = tlay[88], in_known = tlay[89], out_known = tlay[90],
        wtop = tlay[34], wbot = tlay[35], base = tlay[28], tiles = tlay[29], pal = tlay[30] }
  mem, s16, COLS = mem_, s16_, chunk_px // 16
end
local function rd(base, off) return s16(mem:read_u16(base + off)) end
local function kind(d) return d == 16 and 1 or d == 32 and 2 or 0 end
-- kind (0 flat, 1 S16, 2 S32), hflip, y0 of column k of the chunk at base
function CAVE.piece(base, k, ceiling)
  local own = rd(base, ceiling and L.wtop or L.wbot)
  if k < 3 and mem:read_u8(base + L.in_known) ~= 0 then
    local o = rd(base, ceiling and L.in_top or L.in_bot)
    local kd = kind(ceiling and own - o or o - own)
    if kd > 0 then return kd, 0, ceiling and o - 16 or own end
  elseif k >= COLS - 3 and mem:read_u8(base + L.out_known) ~= 0 then
    local o = rd(base, ceiling and L.out_top or L.out_bot)
    local kd = kind(ceiling and own - o or o - own)
    if kd > 0 then return kd, 1, ceiling and o - 16 or own end
  end
  return 0, 0, ceiling and own - 16 or own
end
local function fail(msg) CAVE.bad = CAVE.bad + 1; CAVE.first = CAVE.first or msg end
local same = {}   -- "solid" / "black" / "fill" -> the one tile seen first
local function one(name, tile, msg) same[name] = same[name] or tile; if same[name] ~= tile then fail(msg .. " " .. name) end end
-- Checks the tiles of a visible strip sprite at world column j; vram is the VRAM shadow, sprite its slot, rows its height.
function CAVE.tiles(vram, sprite, rows, ceiling, j)
  local c = CAVE.cols[j]
  if not c then fail("no chunk for column " .. j); return end
  local kd, hf = CAVE.piece(c[1], c[2], ceiling)
  local prow = kd == 0 and 1 or kd + 1
  if kd > 0 then CAVE.curve_cols = CAVE.curve_cols + 1 end
  for r = 0, rows - 1 do
    local tile, attr = vram[sprite * 64 + r * 2] or 0, vram[sprite * 64 + r * 2 + 1] or 0
    local d = ceiling and rows - 1 - r or r   -- rows away from the window edge side of the piece
    local msg = string.format("sprite %d row %d tile %d attr 0x%04x", sprite, r, tile, attr)
    if tile < L.base or tile >= L.base + L.tiles then fail(msg .. " range") end
    if (attr >> 8) ~= L.pal + (ceiling and 1 or 0) then fail(msg .. " palette") end
    if (attr & 2) ~= 0 then fail(msg .. " vflip") end
    local anim = (attr & 0x08) ~= 0
    if anim ~= (not ceiling and d < prow) then fail(msg .. " animation") end
    if d < prow and (attr & 1) ~= hf then fail(msg .. " hflip") end
    if kd == 0 and d > 0 then
      CAVE.flat_rows = CAVE.flat_rows + 1
      if (attr & 1) ~= 0 then fail(msg .. " flat hflip") end
      if not ceiling then
        if d == 1 then one("fill", tile, msg) elseif d >= 4 then one("solid", tile, msg)
        elseif tile == same.fill or tile == same.solid then fail(msg .. " floor fade row missing") end
      else
        if d >= 3 then one("black", tile, msg) elseif tile == same.black then fail(msg .. " roof fade row missing") end
      end
    end
  end
end
