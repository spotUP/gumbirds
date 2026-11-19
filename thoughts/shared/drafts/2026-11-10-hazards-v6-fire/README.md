# Fire hazard, version 6 (draft)

Round 6 of the fire variant of the deadly strip at the bottom of the screen. It answers the verdict on version 5:
the tip was a thick rounded column, the tall flame always stood in the same place, and the smoke had to go.

Drafts only. Nothing in `src/`, `assets/` or the Makefile is changed. Versions 3, 4 and 5 are untouched.

## Files

- `index.html`: version 4, 5 and 6 side by side. View at 100 percent browser zoom.
- `anim_B_16f_4x.gif`: the 16 frame loop in the scene, 4x.
- `scene_B_3x.png`: frame 2 in the full 320 pixel scene, 3x.
- `frames_B_16_3x.png`: all 16 frames in the scene at full width, 3x.
- `frames_B_1x.png`: build input, 16 frames per row, row 0 is tile A, row 1 is tile B.
- `draw_fire_v6.py`: generator. Run with `/opt/homebrew/bin/python3.14 -I -B draw_fire_v6.py`.
  `--metrics` prints the numbers only. `--check DIR` writes the two frame sheets into DIR only.
  The environment variable `FIRE6='NAME=value;NAME=value'` overrides constants for a tuning run.

## Verdict per fault

All numbers are measured on the final frames by `mask_metrics` in the script. The same code measured the
version 4 and version 5 sheets. Embers are excluded.

### 1. Tip: FIXED by the numbers, body PARTLY

| Measure | Version 5 | Version 6 |
| --- | --- | --- |
| Taper (width at 70 percent / width at 25 percent of the tallest tongue), mean | 0.51 | 0.38 |
| Taper, lowest to highest frame | 0.25 to 0.73 | 0.18 to 0.50 |
| Width at 90 percent of the height, mean | 5.3 px | 2.9 px |
| Tallest tongue, mean (lowest, highest) | 21.3 (20, 23) | 21.6 (19, 23) |
| Flame pixels per 64 px, mean (lowest) | 392 (351) | 403 (370) |

The version 5 README gave taper 0.40 to 0.48. This script measures the version 5 sheet at 0.51, so the
before and after values above come from one measure.

The mechanism is new. Rim cooling and the entrainment cone are not what sharpens the tip. Three parts do it:

- Necking strain in the velocity field (`STRAIN`): air flows toward the axis of each tongue, more with height,
  and part of that is given back as upward speed. The tongue is stretched to a point.
- Sway (`SWAY`): the axis moves sideways as a wave that travels upward, so the tip bends and licks.
- Render (`tip_mask`, `TIP_GROW`, `FRONT_BLUR`): tips of 1 pixel survive the majority filter and the despeckle,
  and the front is blurred less than in version 5.

### 2. Repeat: PARTLY

The leader role moves over four sources in the loop, two in tile A and two in tile B:

| Frames | Tile | Position in the 128 px pair |
| --- | --- | --- |
| 15, 0, 1, 2 | B | 109 to 112 |
| 3, 4, 5, 6 | A | 6 to 12 |
| 7, 8, 9, 10 | B | 83 to 85 |
| 11, 12, 13, 14 | A | 36 to 41 |

Leader position per frame: 112 112 109 6 9 11 12 85 84 83 84 41 38 36 36 111.

No frame has the two tallest tongues within 1 pixel. The smallest gap is 2 (frames 2 and 7). Per frame,
tallest/second: 23/15 23/14 21/19 21/17 21/14 22/11 22/14 19/17 23/13 23/14 21/18 21/16 21/12 21/13 21/18 22/18.

Why only PARTLY: the strip is laid out A B A B A, so in any single frame the tall flame still stands once
per 128 pixels (2 or 3 times across the screen). The position is no longer fixed, but the spacing is.

### 3. Smoke: FIXED

The soot field, the `SMOKE` constant and the smoke render are removed. Embers are unchanged (20, same paths
as version 5).

## Kept

- Seamless time loop: the simulation asserts a converged periodic loop. Changed pixels per step: wrap 634,
  other steps 475 to 609.
- Seamless x loop: differing pixels across the joint B|A 103, A|B 44; inside tiles 12 to 215, median 91.
- 16 frames, 4 video frames each. Coal bed rows 25 to 31. Back row depth and cast light as in version 5.
- Tiles, counted by `tile_count` from the final frames: 256 raw, 230 unique.
- Palette: 13 entries, 11 used. The two smoke colours (`S`, `s`) are free.

## Weak points

- The gap margin is thin. Smallest gap 2, and it depends on the schedule phase: `LEAD_T0` 0.04 or 0.05,
  `LEAD_PRE` 0.12 or 0.16, and `LEAD_LAG` 0.03 or 0.11 each gave a frame with gap 0 or 1. Any later retune
  must re-check this.
- The leader stands out less than in version 5. Second tongue mean 15.2 against 13.4. At each handover
  (frames 2, 7, 10, 14) two tongues of 17 to 19 and 19 to 21 stand next to each other for one frame.
- The tallest tongue falls to 19 in frame 7 (version 5 lowest: 20). The mean of 21.6 holds.
- Each source leads for 4 frames only (0.27 s). The tall flame may read as jumping rather than wandering.
- Body: the tongues are slimmer above mid height than in version 5. The pixel count is higher (403 against
  392) because the low bed is fuller, not because the tall flame is wider.
- The white core of a resting source is a round blob low on the bed in some frames (position 39 in frames
  4 to 6, 12 and 13).
- One frame of tile B shows a tongue remnant 1 pixel wide (tile sheet, lower row, about frame 6).
- The taper measure is noisy: the width at 25 percent height includes the bed in some frames.
- Two palette slots are free. They could become two more flame shades for more depth.
- The window function `win` has a wrap branch that no current schedule entry uses.

## Not viewed

- `anim_B_16f_4x.gif` in motion. Sway, licking and the handover are judged from still frames only.
- `scene_B_3x.png`. Frame 2 was viewed in the 16 frame sheet, not in the full scene.
