# Gum leak, round 3: the escaping air

Draft only. Nothing in `src/`, `assets/` or `Makefile` is touched.

Round 2 (`../2026-11-17-gum-leak-hole/`) fixed the holes (D, E, F). Owner verdict on its air:
"looks more like a fuse burning than air blowing out". The cause, seen on the round-2 sheets: a thin
diagonal line with a ring or ball at its end, on a dark-outlined round body, is a cartoon bomb with a fuse.

Round 3 keeps the round-2 hole stamps unchanged and redraws only the air.

## What changed in the air

- No line. The base of the jet is a 6 x 6 dithered fan (two phases) that widens away from the hole.
- No bright core at the hole. The fan starts in the blue-grey rim entry (c) and turns pale (a) further out. White (b) is used only inside grown puffs.
- Puffs are round stamps that grow with age (3 x 3 wisp, 4 x 4, 5 x 5, 6 x 6), then break into a checker and a sparse dither before they end.
- Puffs leave at spread angles (12 to 72 degrees), so the air fills a cone and not one diagonal.
- Short curved speed dashes (entry c only) run beside the cone.
- Motion is the round-1 simulation (`puff_xy`: drag 0.62, rise 0.22 per leak frame, one leak frame = 3 game frames). Each stamp is a hand-placed grid; the simulation only places it.
- The bubble wobble is the faster round-2 wobble.

## Variants

| Variant | Hole (round 2) | Air | Frames | Tiles per frame | Extra sprites |
|---|---|---|---|---|---|
| D | round puncture | steady blow, six puffs per loop, fan flickers every frame | 12 | 1 | 1 |
| E | jagged split | two gusts per loop, fan only during a gust | 8 | 1 | 1 |
| F | puncture plus torn tongue | thinner stream, four puffs per loop | 12 (round 2: 6) | 1 | 1 |
| W | D's puncture | air in a 32 x 16 tile pair: wider fan, larger late puff stages, long speed lines, three times the reach | 12 | 2 | 2 |

W exists because 16 x 16 leaves the air about 8 px to the right and 10 px up from the hole. In that room
a puff cannot travel far enough to slow down and dissolve visibly. W costs 24 tiles and a second sprite
per holed bubble (a Neo Geo sprite is 16 px wide).

Exact counts: `numbers.txt`. Air uses gum palette entries a, b, c only (asserted in the script).

## Files

- `draw_gum_leak_air.py`: stamps, simulation placement, sheets, GIFs, gallery. Run: `nice -n 19 python3.14 -I draw_gum_leak_air.py`.
- `index.html`: gallery. Per variant: frame sheets at 1x and 3x (rows alternate round 2 / round 3), animated GIFs (round 2 left, round 3 right) on flat, dusk, moon and storm, and the tile strip at 6x.
- `cue_3x.png`: D, E, F on the normal, warm and hot bubble cue palettes.
- `numbers.txt`: frames, tiles, sprites, palette entries per variant.

## Open points

- F is the weakest. Its white torn tongue is part of the round-2 hole stamp and is itself a thin diagonal line; with a small puff at its tip it still reads close to a fuse. A real fix needs a change to the F hole, which was out of scope.
- Hot cue: entries a and c turn cream and orange, so the air goes yellow on an orange bubble and reads as a lit fuse again. Options: draw the air in entry b only, or give the leak sprite its own fixed palette (one palette slot).
- D and E at 16 x 16 read as a small cloud at the hole more than as a jet. W shows the jet. The choice between 1 tile and 2 tiles per frame is the owner's.
- At 1x on the storm scene the pale air competes with the rain; it reads best on dusk.
- Round 2 had only the dusk mood. Round 3 renders dusk, moon and storm for both rounds.
