# Gum in mouth: Sootling drafts (2026-11-16)

Drafts only. Nothing imported, no game code touched. Rebuild: `python3.14 -I draw_gum_mouth.py`.

Owner idea: the bird holds the gum in its beak, tilts up toward it, dangles under it, blows constantly to stay up,
and blows the gum back up with its mouth after a landing (replaces the pump). Gum Trip: distress from blowing too hard.

## Takes
- A, head back: side view, beak up at one o'clock, one cheek. Short 3 px gum neck. Swing 3 px each way.
- B, front hang: faces the camera, beak straight up, two cheeks, wings out to both sides. No turn frames needed.
- C, long dangle: take A body on an 11 px gum neck, swing 5 px each way. Reads most like a weight under a balloon.

## What is shared by all takes
- Bird cell stays 24 x 32 (no bigger box). Gum bubbles are the existing gum sheet cells, no new gum tiles.
- New small sprite: gum neck (3 cells, mirrored by hardware flip) + V piece for two gums = 4 tiles.
- Constant blow loop: 6 steps per breath (sunk, rest, puff, puff, puff, rest), two breaths per 12-frame swing;
  the bubble steps one or two gum levels up on the puff. Flap = 8 frames: inhale with wings up, hard puff with
  eyes squeezed, bubble swells 3 to 4 levels, settles.
- Landing blow-up: 18 frames, three breaths, each breath overshoots one level and settles; then a 3-frame lift-off.
  Two gums: first gum to level 7, then the second.

## Gum Trip distress (src/core: GUM_MAX 1024, GUM_START 768, decay 1 gum per 2 frames, 2 gums at >= 512)
| stage | gum value | seconds left at entry | look | cost |
|---|---|---|---|---|
| 0 | 1024..513 | - | normal blow loop | 0 |
| 1 | 512..257 (one gum left) | 17 s | cheeks red by palette swap of 3 entries, loop at 5 ticks | 0 tiles in the game (draft counts 1 frame because the loop uses the big puff) |
| 2 | 256..129 | 8.5 s | deeper red, squint, one sweat drop, gum cue palette warm | +2 frames (8 tiles) + sweat sprite 1 tile |
| 3 | 128..1 | 4.3 s | dark red, eyes shut, two drops, 1 px tremble, gum cue palette hot | +3 frames (12 tiles) |

Cheeks and gum neck use flier palette entries 12, 13, 14 (the old string colours), so the swap touches nothing else.

## Tile counts
See numbers.txt. Per take about 16 to 17 bird frames (64 to 68 tiles as 4 tiles per frame, 33 to 38 unique tiles),
against 30 frames (120 tiles) of flap2, flap1 and inflate that they replace.

## Recommendation
Take C for the dangle (the long neck is what makes the bird read as hanging), with take B's front pose kept as the
turn frame and as the Gum Trip distress pose, because two red cheeks read far better than one at 1x.

## Known weak points
- Bodies are hand-typed grids, but cheek, eye, wing and feet states are typed patches layered on one body per take;
  the body itself does not rotate with the swing (only offset, feet trail and neck lean). A final pass needs a
  hand-pixelled body per swing pose.
- Dither on the body is light. Not compared side by side with 2026-11-10-dither-s6-strong.
- Take B hides the tuft and looks less like the current Sootling than take A.
- Player 2 and rival bubbles are recoloured mock-ups of the gum sheet, not real gum palettes.
- Hitboxes: the gum box in flier.h sits 22..31 above the feet; take C puts the bubble about 8 px higher.
