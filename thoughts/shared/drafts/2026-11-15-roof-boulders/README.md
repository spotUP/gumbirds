# Roof boulders: upright fix for the sloped trip cave roof (draft)

Draft only. No game code, no import, no commit. Gallery: `index.html`.

## Problem
The smooth-fade draft (`../2026-11-15-trip-cave-smoothfade`) builds the roof above the two curve pieces by sliding each pixel
column of the flat fade rows down by the lip height. That shears every boulder above the sloped rim, and it also cuts the lit
rim boulders of the curve piece on a diagonal.

## Change
`roof_boulders_art.py` holds hand-typed pixel rows for the roof part of both sloped blocks (gentle S16: block rows 0-47,
steep S32: block rows 0-63). Every boulder is typed upright. Along the slope a boulder sits a whole number of pixels lower or
higher than its neighbour; nothing is slanted. `.` in a row means "the v3 curve piece pixel", so the lit rim boulders are the
piece's own pixels, whole again. Rows below the typed part are the unchanged piece.

Rim edge next to the boulders: checked in the 6x crops. The cyan lip and the lit boulders are the v3 piece pixels and are not
redrawn; the diagonal cuts through the first and third lit boulder (gentle) and the left and middle lit boulder (steep) are gone.

`build_roof.py` places the rows, cuts tiles, asserts the checks below and writes the gallery images. It draws nothing.
Run: `python3.14 -I build_roof.py`.

## Tiles
- Changed: all 18 roof tiles R0 to R17 (pixels only).
- Unchanged: 19 floor tiles F0 to F18, 14 flat fade tiles, the curve pieces.
- Counts: 37 sloped + 14 flat, same as before. Palette: the same 11 roof colours, no new colour. Typed rows use tones 0-4 only.
- Lookup: identical to the smooth-fade `fade_map.json` (asserted; a copy is in this folder). Top-right tile of both blocks stays black.

Three outline rows differ by one or two pixels from the piece. Without this the tile above the piece would equal a piece tile
and the lookup (and tile count) would change:
- S16 block row 32, columns 0-15: `1211111111111211` (piece: `1111211111112111`)
- S32 block row 32, columns 0-15: `1211111111111211` (piece: `1111121111111211`)
- S32 block row 48, columns 16-31: `1111111211111111` (piece: `1112111111112111`)

## Re-import
`tools/import_trip_cave.py` (worktrees beta1, gum-burst) reads only `S.NEW["roof"]` (tile bytes to name) from `build_smooth`
for the roof tiles. `build_roof.NEW` has the same form and the same names. Suggested hook, not applied and not tested:
add this folder to `sys.path`, `import build_roof`, then `S.NEW["roof"] = build_roof.NEW` after `import build_smooth as S`.
`roof_tiles_R0-R17_1x.png` (18 tiles, 16 px, name order) and `sloped_tiles_F0-F18_R0-R17_1x.png` are for viewing; the importer
does not read PNG sheets.

## Not checked
Not run in MAME. Importer hook not run. The flipped placement of each block uses the same tiles; its join with the flat
neighbour was only seen in the strip and deep roof images.
