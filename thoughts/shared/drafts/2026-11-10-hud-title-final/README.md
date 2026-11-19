# Gumbirds: final title logo, fix font and HUD sheets

Final round of 10 November 2026 for the three choices made on the draft round
(`../2026-11-10-hud-title/`): logo A (stretched gum), font A (Gumdrop) with the 8x16 tall score digits,
and HUD layout 2 (corner tags). Open `index.html` for the gallery; every number is in `numbers.txt`.

All art here is original. No existing font or logo was used as a source. Nothing in the game source,
tests, tools or assets was changed; these are sheets and mock-ups to import later.

## How to rebuild

    /opt/homebrew/bin/python3.14 -I draw_hud_title_final.py

The script is a copy of the draft script with a final section appended. The draft functions stay in it
and draw the "before" pictures. It reads backdrops, hazards and Sootling sheets from the sibling draft
folders and writes every file in this folder, including `numbers.txt` and `index.html`.

## What each fix changed

- Logo separation: the outer line grew from 2 px to 3 px (plum keyline plus two dark pixels), the under
  shadow moved from 2,3 to 3,4 and got darker, a cool rim light (cyan with a violet step) sits on the
  lower right edges, and the top highlight is a warm cream instead of plain light pink. One palette,
  10 colours, hard clusters, no dither. The letter edges were cleaned so that no single pixel bumps remain.
- Logo animation: the bubble squashes before it grows, overshoots, settles, then bursts into shreds that
  fly out and fall; the torn rim flares and snaps flat. The drip stretches on a thinning neck, snaps, the
  stub recoils and the drop falls faster each frame. Shreds and the falling drop are free 16x16 sprites,
  so they cost position changes and not new body tiles.
- Tile count: the 16 px grid offset was searched over all 256 positions. Result: 82 tiles for the still,
  130 with all ten frames and the free pieces (draft: 79 and 155). The body is 20 strips; the worst
  scanline carries 24 sprites.
- Font look-alikes: 0 is narrow and slashed, O stays wide; M has full legs, W has split inset feet; I has
  wide serifs, 1 has a flag and no foot; 5 has a flat top and a high bar; 8 has a small head; Z has a
  cross bar. There is no lower case, so the 1/I/l question reduces to 1 and I.
- Sootling icon: replaced by a 16x8 front face on two tiles (navy outline, blue body, white goggle eyes,
  ember beak).
- Row 27: text sits on plates made from fix tiles only. A backed glyph is the same glyph with the soot
  navy filling the cell, moved down one pixel. Plate ends and joints are four more tiles. The worst cell
  over 3 moods, 4 hazard kinds and 16 frames went from -5.3 to 182.1 on the luminance gap defined in
  `numbers.txt`. Rows 0 and 1 stay unbacked so the sky stays open.
- Mock-ups: every screen is a 40x28 cell grid with one tile and one palette per cell, so the tile and
  cell counts are real. Results and name entry use a panel built from the same backed glyphs and eight
  frame tiles. The draft HUD showed an off-screen marker on row 12; it is removed here because layout 2
  uses rows 0, 1 and 27 only.

## Files

- `logo_a_still_1x.png`, `logo_a_frames_1x.png`, `logo_a_pieces_1x.png`: logo import sheets on the 16 px
  grid (transparent is 255,0,255).
- `fix_sheet_1x.png`: the fix tile sheet, 16 tiles per row; order and character map are in `numbers.txt`.
- `logo_*`, `font_*`, `icon_*`, `row27_*`: before and after pictures per fix.
- `title_*`, `hud1p_*`, `hud2p_*`, `results_*`, `entry_*`: mock-ups per mood at 1x and 3x.
- `anim_title_*_3x.gif`: the title animation per mood.

## Weak points that remain

- The still logo costs 82 tiles, three more than the draft, because of the wider line and shadow.
- The colour distance of the outermost gum pixels to the sky did not improve; the separation comes from
  the dark line and shadow, not from the gum colours.
- G/O, I/T and M/N still differ by only 4 pixels.
- Rows 0 and 1 are unbacked: over the storm sky 18 of 402 measured cells are under a gap of 70, the worst
  is the pink PLAYER 1 label at 38.7. Moon and dusk have none under 70.
- The plates hide 8 px of hazard on the bottom row.
- The name entry letters are 8 px tall. The backed copies double the glyph tiles (157 fix tiles in all);
  row 27 alone needs only 26 extra tiles.
- Cabinet overscan is not checked for rows 0, 1, 27 and the outer columns.
- Backdrops are earlier draft renders; the results score values are placeholders; the GIFs are reduced
  to 255 colours.
