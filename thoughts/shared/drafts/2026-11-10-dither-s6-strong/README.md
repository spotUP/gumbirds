# Dither style 6 (mixed by material): stronger levels M and H

Draft only. Nothing in `src/`, `assets/` or the Makefile is touched. Fire is not part of this test.

Open `index.html` and view at 100 percent browser zoom.

## Levels

| Level | Meaning |
|---|---|
| S0 | hazards v4, no dither |
| S6 | round 1 style 6 (`dither_round1.py`, unchanged copy of the round 1 script) |
| M | medium-strong: dither zone about half of each shade band, quarter steps (25 / 50 percent) |
| H | heavy: dither zone up to the full band, eighth steps (12 / 25 / 37 / 50 percent), thin bands included |

Shapes, physics, motion, frame counts and frame times are the v4 ones (spikes 4, water 6, lava 8 video frames per step, 16 steps). Only the transition between two neighbouring shades of one material ramp is redrawn. All patterns have period 16 on the tile grid.

## Regenerate

```
/opt/homebrew/bin/python3.14 -I draw_dither_s6_strong.py
```

About 30 seconds. Needs Pillow and numpy. `hazards_v4_base.py` and `dither_round1.py` are unchanged library copies. `--scratch DIR` also writes inspection sheets into DIR. The run rewrites `numbers.txt`; every number below comes from it.

## Files

- `compare_<subject>_3x.png`: S0, S6, M, H side by side at 3x, frame 2
- `strip_<subject>_1x.png`: the same four at true size
- `anim_<M|H>_<water|lava|spikes>_4x.gif`: 128 x 112 px window at 4x, v4 timing
- `frames_<M|H>_<subject>_1x.png`: all 16 tile frames at 1x (lava: tile variants A and B as two rows)
- `numbers.txt`: tile counts, colour counts, crust anchor measurement

## What changed per material

**Sky.** The ramp has 5 shades with a wide value spread instead of 3 close ones: (4,4,18), (12,14,44), (20,26,66), (32,34,90), (54,40,108), zenith near black to a violet glow at the horizon. Four band edges, each lifted by a hand-set haze profile. M: three steps (25 / 50 / 75 percent) over half of each band, flat shade between them. H: five steps, the zones meet, so no flat band is left. Pattern: ordered 4 x 4.

**Water.** Ripple dashes between neighbouring water shades, as in round 1, but the zone is half the band (M) or the whole band (H). Foam stays hard. Rock uses a broken checker. Lurker sprite: the body shadow fades out at its rim in the same ripple dashes, and the fin has a broken edge between its two shades (H adds a second, sparser row and the highlight side).

**Lava.** Melt: checker at the shade edge, thinned out in molten blobs away from it. Crust: broken checker between crust shades; M needs a 2 x 2 solid patch, H dithers 1 px bands too. Cast light on the buildings: the face band fades upward in ordered rows (M: 50 then 25 percent, 4 rows; H: 75 / 50 / 25 / 12 percent, 8 rows); the rim light breaks up into dashes where hot turns dim and where dim ends.

**Spikes.** Round 1 needed 3 px bands, so the steel showed 120 dithered pixels per loop. Now every steel band of 2 px or more is dithered: blade faces, the shadow wedge, collars and sleeves. M: zone 1 to 2 px deep, only where the borrowed shade is a solid patch, so the 1 px ridge glint and core line stay clean. H: zone up to 4 px deep, 1 px features included. The pattern rides with the blade (anchored to the piston tip), so it does not crawl when the piston moves.

## Numbers (from the tile builder `v4.tile_count`, not by eye)

Unique 16 x 16 tiles per loop:

| Hazard | raw | S0 | S6 | M | H |
|---|---|---|---|---|---|
| Spikes | 128 | 47 | 47 | 47 | 47 |
| Water | 128 | 99 | 100 | 99 | 101 |
| Lava | 256 | 256 | 256 | 256 | 256 |

Dithered pixels per loop (share of opaque pixels):

| Hazard | S6 | M | H |
|---|---|---|---|
| Spikes | 120 (0.5%) | 1156 (5.1%) | 3636 (16.1%) |
| Water | 1502 (7.4%) | 2836 (14.0%) | 4046 (20.0%) |
| Lava | 8082 (17.7%) | 9350 (20.5%) | 14890 (32.7%) |

Colours:

- Spikes palette 15 of 15, water 14 of 14, lava 14 of 14, lurker sprite 8. No level adds a hazard colour (asserted in the script).
- Sky: 3 colours in S0 and S6, 5 in M and H. The whole scene mock goes from 35 to 37 colours. Two of the five sky shades are new; three keep or replace the old ones. How the backdrop splits into 15-colour palettes is not decided in this draft, so the +2 has to be checked against the real backdrop palette.
- Cast light uses the v4 light colours only.

The script also asserts: transparency and silhouette unchanged, seamless in x (a tile dithered alone equals the same tile inside a doubled strip).

## Lava crust anchor: grid, not plate

Three anchors were tested on the same art: `grid` (pattern fixed to the tile grid), `plate` (pattern rides with the nearest crack and the surface row), `surf` (pattern rides only with the surface row). Measure: pixels on crust that change although the undithered art holds still there for three frames, and of those the ones that are back one frame later (blinks). Per 16-step loop:

| Level | Anchor | changes on still art | blinks |
|---|---|---|---|
| M | grid | 108 | 16 |
| M | plate | 285 | 102 |
| M | surf | 93 | 18 |
| H | grid | 206 | 36 |
| H | plate | 1034 | 380 |
| H | surf | 192 | 25 |

Plate anchoring is worse, 5 times the changes and 10 times the blinks at H. Cause: a pixel switches to another "nearest crack" when plates drift, and the rounded crack position jumps by one pixel, which flips the whole checker of that plate. Grid and surf are equal within noise. Grid is picked because it needs no per-frame data. Frames looked at: 8 consecutive frames of H for grid and plate, side by side; in still images the two are near identical, the difference is only in motion. The GIFs were not viewed in motion.

## Recommendation

- **Sky: H.** The five-step blend reads as a real gradient at 1x. M still shows bands with fuzzy edges.
- **Lava: M** for melt and crust. H puts checker on a third of the surface, and the melt starts to look like noise at 1x. The cast light fade is better in H (8 rows); it can be taken separately.
- **Water: M.** H breaks the lurker shadow into thin streaks, so the creature loses its shape.
- **Spikes: H.** M shows mostly on the shadow side and sleeves; at 1x it is hard to see. H is the first level where the blade faces show form shading.

## Weak points

- Sky and cast light use the ordered 4 x 4 pattern. It is regular. On the large H sky it can read as a filter, not as hand work. A hand-clustered sky pattern is not drawn yet.
- Spikes M is weak at 1x. The blades are 14 px tall with bands of 1 to 3 px; there is little room.
- Spikes H dithers 1 px features, so the ridge glint is slightly broken up.
- Water H: lurker body shadow is too thin.
- Lava has no tile saving at any level (256 of 256).
- The violet horizon changes the mood of the scene. It is close in value to the far island colour (52,60,110); contrast was judged on the comparison sheet only.
- Checked by eye: the four 3x comparison sheets, the 1x strips for spikes, lava and sky, single frames of spikes M and H, water H, lava H. Not viewed: the 1x water strip, the GIFs in motion, `frames_*_1x.png`, `index.html` in a browser.
