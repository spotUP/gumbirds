# Dither round 3: visible dither (draft, 2026-11-10)

Drafts only. Nothing in `src/`, `assets/` or the Makefile changed. Open `index.html` and view at 100 percent browser zoom.

## Why round 2 was invisible

The round 2 patterns were there, but the two colours in each pattern were too close in luminance (0.299R + 0.587G + 0.114B, scale 0-255):

| Material | Old ramp steps | Verdict |
|---|---|---|
| Sky (5 shades) | 11 each | far below the visible threshold; this is the main cause |
| Water `onubBTc` | 20 19 19 39 37 43 | deep half too close |
| Lava melt `mPDrOyY` | 15 21 39 52 50 43 | dark half too close |
| Lava crust `okKQH` | 20 32 70 67 | dark step too close |
| Cast light face vs building | 23.7 | too close |
| Steel `Ddmlh` | 32 61 59 48 | already wide; problem was small area, not contrast |

The earlier "12.2 on water and spikes" figure was dominated by sky pixels inside the comparison cell, not by the hazard art itself.

## Method

Fewer, further-apart shades per ramp; the dither supplies the in-between tones. Shapes and animation are the v4 ones, unchanged. Rule asserted by the script: the 10th-percentile luminance step of every dither pair is at least 28.

- Steel, crust, rock: sparse stipple. Steel holds 50 percent density for the first half of the band, then 25 percent.
- Water: ripple dashes, half band (medium).
- Lava melt and glow: checker, half band (medium). Cast light: checker with a heavy fade.
- Sky: clustered threshold map with a cloud-shaped warp field (seeded, rng 7), so the band breaks are irregular, not an ordered grid. Wide ramp to a violet horizon.

## Palettes

V1 (pair step about 30):

- Steel: D (26,30,80); d, m, l, h unchanged from round 2.
- Water: o (6,6,30) n (22,36,104) u (44,66,164) b (28,120,198) B (48,156,224) T (66,204,212) c (118,228,244) f (200,244,255). 14 colours.
- Lava melt: m (36,0,44) P (110,12,58) D (184,32,36) r (232,62,28) O (250,116,24) y (255,186,48) Y (255,246,184). Crust: o (18,4,18) k (74,24,42) K (128,52,54), Q and H unchanged. 14 colours.
- Sky: 4 shades (4,4,18) (26,30,88) (66,50,138) (116,70,170), band edges at y 40 / 92 / 144.
- Cast light: face (86,26,58), dim (170,54,46), hot (255,150,62).

V2 (pair step about 42):

- Steel: D (22,24,72) d (60,70,138) m (116,136,200) l (178,200,238) h (232,244,255).
- Water: u merged into n. o (4,4,26) n (28,44,120) b (28,102,188) B (50,154,224) T (76,214,216) c (150,244,250) f (214,250,255). 13 colours.
- Lava melt: P merged into m. m (40,0,48) D (146,18,44) r (224,52,28) O (250,116,24) y (255,190,50) Y (255,248,190). Crust: o (16,2,16) k (86,28,44) K (146,66,58) Q (204,120,88) H (250,200,150). 13 colours.
- Sky: 3 shades (4,4,18) (38,42,110) (108,68,166), band edges at y 60 / 130.
- Cast light: face (108,30,60), dim (200,64,46).

Rock ramp unchanged (steps 69, 79). The lurker sprite takes o and f from the level's water palette.

## Numbers

A dither pixel is one that differs from the hard-edged render with the same palette. Step is the luminance difference of the two shades in the pair. Hazards are counted over the 16-frame loop from index frames; sky from the backdrop. Full output: `numbers.txt`.

| Subject | Level | Dither px | Median step | p10 step | Colours | Unique tiles |
|---|---|---|---|---|---|---|
| Sky | old H | 10396 | 11.2 | 11.0 | 5 | 224 of 280 |
| Sky | V1 | 7370 | 29.8 | 29.4 | 4 | 205 of 280 |
| Sky | V2 | 9525 | 43.0 | 42.6 | 3 | 187 of 280 |
| Spikes | old H | 3636 (16.1%) | 58.9 | 32.2 | 15 | 47 of 128 |
| Spikes | V1 | 3636 | 58.9 | 36.2 | 15 | 47 of 128 |
| Spikes | V2 | 3636 | 60.4 | 43.9 | 15 | 47 of 128 |
| Water | old H | 4046 (20.0%) | 18.9 | 18.7 | 14 | 101 |
| Water | V1 | 2836 (14.0%) | 30.8 | 30.8 | 14 | 99 |
| Water | V2 | 2424 (12.0%) | 41.8 | 41.8 | 13 | 99 |
| Lava | old H | 14890 (32.7%) | 21.2 | 15.0 | 14 | 256 of 256 |
| Lava | V1 | 9350 (20.5%) | 31.4 | 30.8 | 14 | 256 of 256 |
| Lava | V2 | 8340 (18.3%) | 41.8 | 41.5 | 13 | 256 of 256 |

Ramp steps: V1 sky 30 29 30; V2 sky 43 43. V1 steel 36 61 59 48; V2 steel 46 63 60 44. V1 water 31 31 31 30 32 33; V2 water 41 42 41 42 44. V1 melt 31 31 31 37 45 51, crust 31 34 59 67; V2 melt 42 41 45 48 50, crust 39 42 52 68.

Lurker sprite: 770 dither px per loop; V1 median 61.9, p10 30.8; V2 41.4 / 41.4. Cast light: 13048 px per loop; V1 33.7 / 33.7; V2 42.8 / 42.8.

## Lava crust flicker check

Same result at V1 and V2 (pattern changes on still art / blinks per loop):

- grid anchor: 108 / 16
- surface anchor: 93 / 18
- plate anchor: 285 / 102

The grid anchor stays: fewest blinks, and the surface anchor's 15 fewer changes do not offset its 2 extra blinks.

## Visible at 1x (viewed by the author of the draft, in still images)

- Sky: yes at V1 and V2. Checker bands with cloud-shaped breaks read clearly; old H reads as a flat gradient.
- Lava: yes at V1 and V2. The cast light checker on the building faces is the most obvious dither in the set; the melt checker is visible.
- Spikes: yes, but the area is small. Checker grain is visible on spike faces and sleeves. V1 and V2 look almost the same.
- Water: borderline at V1, yes at V2. The ripple dashes read as water texture more than as dither, and there are fewer dither pixels than in round 2 (2836 and 2424 against 4046).

## Recommendation

- Sky: V1. Four shades keep a softer gradient; V2 is harsher and the upper band becomes one large checker field.
- Spikes: V2. Only the darkest step changes; the difference is small.
- Water: V2. V1 is the weakest result in the set.
- Lava: V1 for the melt and crust (keeps the P shade), V2 strength for the cast light if more punch is wanted.

## Weak points

- Water is still the least visible. The contrast is at the spec; the remaining lever is extent. `EXT['water'] = 'H'` in `draw_dither_visible.py` gives the full band, which goes beyond the "medium on water" spec, so it was not applied.
- Steel dither pixel count is identical to round 2 (3636). The 50 percent hold changed density order inside the same zone, not the zone size. Steel contrast was already wide, so V1 and V2 differ little there.
- V1 steps exceed the 28-34 target on steel, the upper crust and the hot end of the melt (those ramps were already wide and were not narrowed).
- The sky cluster map is generated from a seed, not placed by hand pixel by pixel.
- The brighter violet horizon changes the mood of the scene and sits lighter than the far buildings.
- Lava saves no tiles: 256 of 256 unique at every level.
- V2 drops one water shade and one melt shade.
- Rock is unchanged.

## Not viewed

- The six GIFs in motion (only still frames were checked).
- `index.html` in a browser.
- `compare_spikes_4x.png`, `compare_water_4x.png`, `compare_lava_4x.png`, the 1x strips for sky, spikes and lava, and the 8x zooms for sky, spikes and lava as files. Their content was checked through 1x and 4x crops of the same renders.

## Files

- `draw_dither_visible.py`: generator; prints the numbers and asserts p10 >= 28. Run with `/opt/homebrew/bin/python3.14 -I draw_dither_visible.py`.
- `hazards_v4_base.py`, `dither_round1.py`, `draw_dither_s6_strong.py`: unchanged copies used as libraries.
- `compare_<subject>_4x.png`, `strip_<subject>_1x.png`, `zoom_<subject>_8x.png`, `anim_<level>_<subject>_4x.gif`, `numbers.txt`, `index.html`.

Page design: dark page, plain sans-serif labels, square corners, no accent styling.
