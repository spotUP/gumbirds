# Gumbirds stadium background, polish pass 2026-11-18

Art draft, not game code. Builds on `../draw_stadium.py` (imported, not copied): same layout, palettes, confetti, rain, cones.
Run: `/opt/homebrew/bin/python3.14 -I draw_polish.py [--nogif]`. Gallery: `index.html` (old vs new side by side).
All new art is typed pixel grids in `draw_polish.py`; the script only stamps, shifts in whole pixels, mirrors, palette-maps and counts.

## Changes

1. Team colour on the birds. Near crowd: type a wears a striped scarf with a team shirt, type b a bobble beanie plus scarf,
   type c a peaked cap plus a two-row shirt. Far crowd: type a has a two-row team shirt, type b a big team cap.
   Boards and banners unchanged. Near birds are no longer mirrored, so the rim light stays on one side.
2. Roof scoreboard, 7 x 2 tiles on plane columns 7..13 (screen x 104..216, y 0..31): frame with lamp columns, P1 header on blue,
   P2 header on yellow, four digit tiles and a colon. Digit area per tile: x 4..10, y 1..11 (7 x 11 lamp digits, 0..9 drawn).
   The game swaps one tile per digit. Sample shown: 03 : 05.
3. Bigger jumps. Near cheer peaks 8 / 10 / 6 px (types a / b / c), near wave 6 px, far cheer 4 px, far wave 3 px
   (old 2 / 2 / 1 / 1). Each crowd row is its own sprite strip with one tile of head room, so a bird rises into the row above.
4. Dusk light: a low sun half disc on the roof line at the right with a hand-dithered glow along the roof, a warm rim line on the
   top edge of roof, balcony front and boards (hotter toward the sun), hotter rim colour on the plumage, and a long dithered
   stand shadow with saw-tooth edge on the first 32 px of turf.
5. Fling scroll: see below.
6. GIFs: delta frames (unchanged pixels transparent). Largest file 1.26 MB, all twelve 8.6 MB. Storm cheer / wave / win
   previews show the first 32 of 64 frames; the animations keep 64 frames.

## Numbers (full list: numbers.txt)

| | old | new |
|---|---|---|
| stand tiles, moon | 110 | 197 (structure 30, near 61, far 107) |
| stand tiles, dusk | 110 | 227 + 9 light tiles (30 sun-rim variants of structure tiles) |
| stand tiles, storm | 194 | 355 (near 81, far 245) |
| all three moods in one ROM | not stated | 385 + 9 dusk light + 4 tower + 10 digits + 1 rain + 4 confetti |
| palettes per mood | 19 | 19 |
| sprites per scanline, worst (limit 96) | 55 moon, 66 storm | 61 dusk, 55 moon, 66 storm |
| stand sprite strips | 42 | 126 (upper structure, far A, far B, three near rows, 21 each) |
| tile words written per animation step, worst | 86 | 172 |

Cost of the tall jumps: near crowd 35 to 61 tiles, far crowd 57 to 107 (storm 138 to 245), 84 more sprites, twice the tile
writes per step. The scoreboard costs 8 frame tiles + 10 digit tiles and no palette (near structure palettes of both teams).

## Gum Fling scroll decision

Field 512 px, so field scroll is 0..192 px and the stands at 1/4 speed travel 48 px (shift -24..+24 around the centre).
Stand offsets of 64 and 128 px are never reached at 1/4 speed; the strip shows them anyway (rows 5 and 6).
- The team split (centre stairs) stays on screen for the whole travel: screen x 136..184. At raw shifts 64 and 128 it is at x 96 and 32.
- The repeat seam shows. The 336 px plane is only 16 px wider than the screen, so beyond a shift of 8 px up to 16 px of the
  other team appears at the screen edge at both field ends.
- Fix proposed: widen the stand plane by one tile column on each side (23 tiles, 368 px). Then 48 px of travel never reaches the
  seam. Cost: 2 more sprites per strip, no new tiles if the outer column repeats a crowd column of the same team.

## Open weak points

- Storm far crowd is 245 tiles; umbrellas and 4 px jumps multiply the 4-birds-per-tile combinations. Cheaper: far crowd as 8 px
  rows with fewer phases, or no far jump in storm.
- Dusk rim is one pixel row and reads only on the right half at 1x; stair edges and seat ledges have no sun rim.
- Dusk shadow is a flat 50 % mesh; it does not follow the roof outline or the towers.
- The sun sits beside the right tower and does not move with the Fling scroll (it is sky, the towers are stand).
- Players stand in front of the board text (BLOW, POP are partly hidden), as in the approved draft.
- Scoreboard lamps do not blink; the header shows P1 / P2 only, no round or timer field.
- Storm preview GIFs stop at frame 32, so the Player 2 cheer burst (starts at frame 36) is not in the storm cheer preview.
- Sprite strip plan and per-line counts are hand arithmetic in the script text, not measured on hardware or in MAME.
- Jump tables are typed parabolas at 70 ms steps; not tested at 1x on a CRT.
