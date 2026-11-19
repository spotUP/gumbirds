# Gum Trip endless background planes (T-B4b, step 1)

Drafts only. Nothing here is game data. All art is original and comes from the accepted wide-arena backgrounds
(`../2026-11-10-backgrounds-wide/`). Open `index.html` to review. All figures are in `numbers.txt`.

Follows option A of `thoughts/spot/2026-11-10-tb4b-endless-background-study.md`: each parallax plane keeps its
arena width and becomes a ring. The sky stays a still plane.

## Files

- `draw_endless_planes.py`: the generator. Run `/opt/homebrew/bin/python3.14 -I draw_endless_planes.py`
  (about 30 seconds; `--nogif` prints the numbers only and writes the plane and join images).
- `gt_base.py`: copy of `../2026-11-10-backgrounds-wide/draw_backgrounds_wide.py` with one change (`RING_DX`,
  two lines): a far tower chooses its light side from its x position, and a wrap copy must keep the side of its
  home position. Nothing is imported from another draft folder. The hazard strips are read from
  `../2026-11-10-dither-s6-strong/` as before.
- `plane_<mood>_<plane>_1x.png`: the ring sheets (far 336 x 80, midA 352 x 64, midB 368 x 64, near 384 x 96),
  magenta = transparent. Sky, clouds, airship, beams and rain are not redrawn: use the accepted sheets.
- `join_<mood>_<plane>_2x.png`: the plane twice side by side, join at the centre under the yellow ticks.
- `trip_<mood>_3x.gif`: 9.6 seconds of trip scroll. `still_<mood>_2x.png`: first frame.

## How the joins are made

No blending and no mirroring. The join is drawn by the same building tables and functions as the rest.

- far: the building row already ended at 336. Only the end columns 0 and 335 change (the rim of the last tower
  now lies over the first tower, as at every other tower edge).
- midA: the last house (x 338, 26 wide) ran 12 px past the ring end. It is now a slim 16 px tower at 336..351.
  Columns 335..351 and column 0 change.
- midB: the last two houses (336..359 and 356..383) ran 16 px past the end. They are now one house at 336..367.
  Columns 335..367 and column 0 change.
- near: the fifth roof is 4 px narrower (324..379), so the ring has a 4 px alley at the join like the alleys between
  the other roofs. Columns 332..383 change (the roof furniture moves with the narrower roof).
- The haze cluster strips of far, midA and midB are cut to the ring width and repeated; a run of one or two
  pixels left at the cut goes to its neighbour.
- Palettes, colours and shading are the accepted ones. Each plane stays within 15 colours per palette.

## Seam measures

- Measure 1 (all rings): rows in which the last column differs from the first column, next to the same count for
  all neighbouring column pairs inside the plane. A join at a house edge cannot be 0: it must look like the other
  house edges. Far 3 of 80 (before 5), midA 39 of 64 (before 41), midB 44 of 64 (before 60), near 61 of 96
  (before 65). These values lie inside the range of the interior house edges (see `numbers.txt`).
- Measure 2 (far, midA, midB): the skyline is drawn 64 px past the ring end with the same tables. Count of those
  64 columns, over all 8 animation frames, that differ from columns 0..63 of the ring. Result: 0 for all three.
  This is the pixel proof that the right end continues into the left end.
- Near has no measure 2: it is drawn on a canvas that wraps in x, so there is no separate continuation to compare.
  Its proof is the join image and measure 1.

## Speeds

Pixels per 60 Hz frame at the capped trip speed 1.0: sky 0, clouds back 0.0625, clouds front 0.125, far 0.25,
midA 0.5, midB 0.75, near 1.0, hazard strip 1.0 (one variant, period 64), airship 0.1 leftward in screen space.
The GIFs show 3 px of scroll per 50 ms frame: true speed, coarser motion than on the machine.

## Departures from the study and the brief

- The view in the GIFs is the 320 x 224 screen, not 384 x 224: the sky plane is 320 wide and does not move.
- Cloud speeds are my choice (1/16 and 2/16). The study says "k 0 or k 0.1 ring" without a split for two layers.
- The study counts midA at 146 and midB at 179 tiles in the wide arena; the tile totals here use the same count
  (all 8 animation frames).
- ROM figure: the study gives none. Against the arena planes the rings cost +9 tiles if the arena adopts them,
  or +48 tiles if the trip keeps its own copy (only tiles the arena set does not hold).
- Sprites per scanline, ring-valid trim: worst 65 at lines 128..143, the same as the study. Two bands are 1 higher
  than the study (49 and 63 against 48 and 62).
- Left out of the GIFs: lightning flash and the dusk birds.

## Doubts

- Near repeats every 6.4 seconds. The GUM sign, the flag and the lamp cable are the first things the eye catches.
  The study rule says unique objects stay out of looping planes; I kept the sign because it is accepted art.
  A second roof set or a sign-less variant is the fix if the repeat reads badly in play.
- midB repeats every 8.2 seconds (pink billboard, chevron sign). Less visible, same kind of doubt.
- Far towers are lit from the side that faces the moon or sun at their arena position. In the trip they scroll
  past the moon, so the light side is wrong for part of the ring. At 0.25 px per frame and under haze I do not
  see it in the animation.
- The arena art changes in the columns listed above if the arena takes the ring planes. If that is not wanted,
  the trip needs its own copy (+48 tiles).
- Storm stays at 91 of 90 sprites in the worst band by the study's count; this draft does not change that.
- The GIFs are 12 to 14 MB each.
