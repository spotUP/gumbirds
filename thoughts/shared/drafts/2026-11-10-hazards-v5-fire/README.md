# Fire hazard, version 5 (draft)

Draft only. No game code. One more pass on the fire after hazards version 4 was approved for spikes, water and lava.

Run: `/opt/homebrew/bin/python3.14 -I -B draw_fire_v5.py` (Pillow and numpy, about 12 seconds).
`--check DIR` writes only the 16-frame sheet into DIR.

Files: `anim_B_16f_4x.gif`, `scene_B_3x.png` (still, frame 2), `frames_B_1x.png` (tile sheet),
`frames_B_16_3x.png` (all 16 frames in the scene), `index.html` (version 3, 4 and 5 side by side).

The stills and the 16-frame sheet were looked at. The GIF was not played: motion is unjudged.

## What changed against version 4

1. **Height and body.** The sources now have a strict rank: one leader in tile A (x 9), one clear second in
   tile B (x 85), seven lower ones. Bases are wider. Each source has its own pulse depth: the leader pulses 10 %,
   the small ones 32 to 42 %, so the leader never dies down. The low flame along the whole bed is stronger.
2. **Cooling.** The per-source cooling term from version 4 is **kept** and made stronger (K1 0.90 to 0.98).
   Reverting to uniform cooling was tested: tallest tongue mean 17.1, lowest 13, even pairs in 5 frames. Uniform low
   cooling gave a wall of fire (626 flame pixels per tile) with pairs. Two new terms: a cold-air lid per source
   rank (`CEIL`), and cold air entrained from the sides of each source (`CONE`, a teardrop-shaped warm zone).
3. **Smoke.** Soot is shed in puffs (a travelling gate), not as one sheet. The cut-off rises toward the top of the
   strip, so a puff shrinks and breaks into pieces as it climbs. Three shades: violet body, dark side on the upper
   right, warm 1-pixel rim on the lower left. The warm rim appears only where the puff is near a hot tongue.
4. **Embers.** 20 (13 in version 4), longer lives. They cool as they rise: white, yellow, amber, orange, red,
   crimson.
5. **Haze.** The dark magenta and crimson bands start at a higher temperature, front and back row, so the flames
   stand as separate shapes and not as one dark wall.

## Measured numbers

Measure: flame pixel = red, orange, amber, yellow or white. Single hot pixels (embers) are excluded.
Height = pixels above the coal line. Same measure on the version 3 and version 4 tile sheets.
Note: the tongue report printed by version 4 counted embers as tongues; these numbers do not.

| | Version 3 | Version 4 | Version 5 |
|---|---|---|---|
| Tallest tongue, mean (lowest, highest) | 14.9 (10, 18) | 18.2 (14, 22) | 21.3 (20, 23) |
| Second tongue, mean | 11.4 | 14.6 | 13.4 |
| Frames with the two tallest within 1 pixel | 4, 9, 10, 13 | 4, 5, 8 | none |
| Smallest gap between the two tallest | 0 | 0 | 5 |
| Flame pixels per 64-pixel tile, mean (lowest) | 363 (277) | 334 (280) | 392 (351) |
| Flame column height, mean | 5.82 | 5.47 | 6.24 |

Version 5 per frame, tallest / second:

| Frame | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Tallest | 22 | 22 | 20 | 20 | 22 | 22 | 22 | 23 | 20 | 21 | 20 | 20 | 20 | 22 | 23 | 22 |
| Second | 15 | 13 | 14 | 14 | 11 | 13 | 15 | 15 | 15 | 12 | 11 | 11 | 13 | 15 | 13 | 15 |

- Colours: 13 plus transparent (same palette as version 4, limit 15).
- Tiles (16x16): 256 raw, 256 unique.
- Loop in time: asserted. Changed pixels at the wrap step 846; other steps 748 to 987.
- Loop in x: asserted. Differing pixels across the joints 100 and 74; inside the tiles up to 331.
- Dither: none.

Height limit: the strip is 32 pixels and the coal bed takes rows 25 to 31. A flame can be 25 pixels at most.
The leader stays at 20 to 23, so it does not sit flat against the top edge of the strip.

## What is still weak

- The leader is a thick column with a rounded tip. Version 3 and version 4 had sharper teardrop points. Rim cooling
  and the side-entrainment cone did not sharpen the tip in a measurable way (width at 70 % of the height against
  width at 25 %: 0.40 to 0.48 in every setting tested).
- The leader is always the source at x 9 in tile A. With the A B A B A layout the eye can find the repeat:
  the same tall flame every 128 pixels. The rank that removes the even pairs causes this.
- The second tongue is lower than in version 4 (13.4 against 14.6). This is the price for the gap.
- Smoke has three shades and breaks up, but the puffs read as violet shards more than as round clouds. Against
  the dark scene the violet body has low contrast. Removing the smoke is one constant (`SMOKE` threshold above 1).
- All 256 tiles are unique: no saving against version 4.
- Motion was not seen (GIF not played).
