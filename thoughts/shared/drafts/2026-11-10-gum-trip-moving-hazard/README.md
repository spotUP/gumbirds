# Gum Trip moving hazard: three art candidates

Drafts for the ONE moving hazard type of the Gum Trip mode (the mode also has floor and ceiling kill strips).
Pick one. Nothing here is wired into the game. Open `index.html` in a browser to compare.

All three candidates are original designs. Every sheet has 16 frames per loop, plays at 4 ticks per frame
(15 frames per second), uses the magenta key (255, 0, 255) and 5-bit colour values.

## Candidates

| | A Skip-rope squall | B Flue spinner | C Cinder flock |
|---|---|---|---|
| Frame size | 48 x 48 | 32 x 48 | 32 x 32 |
| Frames per loop | 16 | 16 | 16 |
| Colours (plus key) | 12 | 12 | 10 |
| Sprite columns (16 px) | 3 | 2 | 2 |
| Worst sprites per scanline, one instance | 3 | 2 | 2 |
| Tiles, non-empty / unique | 144 / 139 | 96 / 96 | 64 / 64 |
| Opaque bounding box | x 0..47, y 9..36 | x 0..31, y 0..47 | x 0..31, y 6..27 |
| Hit box proposal | x 6..41, y 10..35 (36 x 26) | x 6..25, y 5..24 (20 x 20) | x 8..23, y 9..22 (16 x 14) |
| Time on screen on the proposed path | 314 frames | 206 frames | 280 frames |

`numbers.txt` holds the same numbers as the generator measured them from the sheets.

### A. Skip-rope squall

A small violet storm cloud that swings a lightning arc around itself like a skipping rope. The arc passes in front
of the cloud, dips under the base, then goes behind the cloud for about four frames. The cloud lights up cyan where
the arc is close. Yellow sparks sit at the two ends of the arc.

- Material: vapour. Five violet shades from near-black plum to pale lilac, with clustered-dot dither between shades.
- Path: slow drift (0.25 px per frame in the world, 1.25 on screen) with a tall sine weave, 46 px amplitude,
  period 200 frames. The hazard blocks a lane for a long time and the player times the weave.
- 48 x 48 is earned by the arc: the arc needs clear space on both flanks of the cloud.

### B. Flue spinner

A turbine roof vent torn off a chimney. A steel globe with five slanted vanes spins. The slots between the vanes
glow furnace red, orange and yellow. Saw fins grow at the edge of the globe as the vanes turn. A yellow and dark
striped collar with a torn rust edge hangs under the globe, and a broken chain with a hook trails from the collar.

- Material: metal. No dither. Hard specular band, cool steel shadows that shift to navy.
- Path: skips like a stone on gusts. 0.9 px per frame in the world (1.9 on screen), gravity 0.05, a gust kicks it
  up at y 150. Hops are about 73 px high and about 108 frames apart.
- The hit box covers the globe only. Collar and chain do not hurt.

### C. Cinder flock

A tumbling chimney coal with glowing cracks, circled by seven embers. The embers leave short trails that the wind
drags to the right.

- Material: coal (hard clusters) plus a soft dithered glow around it.
- Path: rises from the floor strip on a thermal. 0.4 px per frame in the world (1.4 on screen), 140 px eased
  climb, 9 px sway.
- Smallest and cheapest in tiles.

## How the motion was simulated

No frame is a hand-keyed tween. Each sheet is the last period of a physics simulation that runs until the start-up
motion has died out (30 to 40 periods). Frame 15 therefore leads into frame 0. `numbers.txt` records the loop seam:
the largest position difference between the last two periods (A 0.0008 px, B 0.0000 px, C 0.0000 px).

- A: ten cloud puffs are damped springs that chase wobbling anchor points (position and radius). The cloud is the
  height field of those spheres, lit from the upper left. The arc is a chain of 13 nodes joined by springs
  (total rest length 68 px, stiffness 5, drag 0.30). The chain ends are pinned on the cloud flanks. A force that
  rotates once per loop drives the chain in depth, so the chain lags and bows like a real rope. The depth of each
  node decides whether the node is drawn in front of or behind the cloud.
- B: the globe is a ray-cast ellipsoid. Vane positions advance three vane pitches per loop, so the loop closes
  exactly. The tilt precesses at 13 degrees. The chain is six spring links under gravity 0.22, steady wind 0.10
  and a gust, attached to the moving collar.
- C: the coal is an irregular solid that makes one turn per loop. Each ember is a damped spring that chases a
  point on a tilted ring (ring speeds 1x, 2x and -1x). The trails are the stored past positions of each ember,
  shifted by the relative wind.

The path gifs show a proposed trajectory on the 320 x 224 screen over the storm scene, with the kill strips
hatched in red and a Sootling at x 72 for scale. One gif frame is 4 game ticks.

## Ranking

1. **B Flue spinner.** It reads as "do not touch" fastest: hot slots, saw fins, hazard stripes. Steel links it to
   the spike kill strip. It costs 2 sprite columns. It has the strongest contrast on the storm sky. The trailing
   chain gives the most visible secondary motion at 1x.
2. **A Skip-rope squall.** The most original motion and the one that best fits a storm level. It costs 3 sprite
   columns and 139 tiles. For about four frames per loop the arc is behind the cloud, and in those frames the
   sprite looks like a friendly cloud.
3. **C Cinder flock.** Cheapest, but the coal is a dark blob at 1x and the bright embers can read as pickups.

## Doubts

- Sprite budget. The build plan gives a margin of 1 sprite at lines 128..143. One instance of B or C adds 2 on its
  lines, one instance of A adds 3. Several instances on the same lines add up. This is not measured in the build.
- Tile reuse is close to nil. A costs 139 tiles, B 96, C 64.
- The jagged shape of the arc in A is seeded noise added on top of the simulated chain. The chain motion is
  simulated; the zigzag is not.
- The arc of A never passes over the top of the cloud. It sweeps the front, the underside and the back.
- The hit box of A leaves out the outer 4 px of the arc. Players may expect the whole arc to hurt.
- Only the storm sky was tested. Contrast on the moon and dusk skies was not checked.
- The gifs were judged from still frames and contact sheets, not from playback.
- B moves at 1.9 px per frame on screen. That may be too fast to dodge at the planned density of 3 per chunk.
- All path constants are proposals. None is in `tuning.h`.
- `path_a_1x.gif` (1.4 MB) and `path_c_1x.gif` (1.2 MB) are over 1 MB. They are required outputs, not helpers.

## Files

- `index.html`: gallery. Dark neutral grey page, sans-serif text, square bordered figures.
- `sheet_<a|b|c>_1x.png`: sprite sheets, frames in one row.
- `contact_<a|b|c>_4x.png`: the frames at 4x on a dark ground, two rows.
- `anim_<a|b|c>_3x.gif`: animation at 3x over a crop of the storm sky, with a Sootling for scale.
- `path_<a|b|c>_1x.gif`: proposed motion path on the 320 x 224 screen.
- `numbers.txt`: measured numbers.
- `draw_moving_hazard.py`: generator. It writes everything except this README.
- `bg_storm_1x.png`, `sootling_sheet_1x.png`: copies of the storm scene and the Sootling sheet from the
  backgrounds-final and sootling-final draft folders, used as inputs.

Regenerate (about 20 seconds):

```
cd thoughts/shared/drafts/2026-11-10-gum-trip-moving-hazard
/opt/homebrew/bin/python3.14 -I draw_moving_hazard.py
```

No file outside this folder was written or changed.
