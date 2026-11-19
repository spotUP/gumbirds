# Toss Gum round 2: poses, ring, tags, burst (2026-11-18)

Draft only. No game code touched, no MAME run. Script: `draw_toss_poses.py` (run `python3.14 -I draw_toss_poses.py`),
reuses `../draw_toss_gum.py` for sheets, palettes, field, gum and stamp. Gallery: `index.html`. Numbers: `numbers.txt`.

## What is new

- **Bird poses, side view only, 8 hand grids of 32 x 32** (the sheet cell is 24 x 32; the raised wing needs the width).
  Throw: windup A (also the carry pose), windup B, release A, release B (follow through).
  Catch: reach A, reach B, absorb (squash, eyes shut), recoil.
  Sheet palette letters only, so the game's `player` / `cpu` palettes and the draft P2 gold / CPU2 violet map without change.
  Left-facing birds are the H-mirror.
- **Ring line typed by hand** as row runs for one quadrant, mirrored four ways; near arc two pixels thick; worn gaps and scuffs
  typed per quadrant so the mirror does not show.
- **Tags with a backing plate**: 15 x 18, white keyline, dark rim, bold 7 x 9 letter with a dark drop shadow.
- **Burst**: hand grids for shreds (up to 10 x 8), three stretch grids by heading, three-step landing splats, patches that stick
  on birds, dithered ground shadows. Motion is simulated: gravity, drag, tumble, one weak bounce for small shreds, secondary
  droplets on impact, one shred solved to hit each other bird, verlet strands that sag, thin and snap.

## Frame counts

| Animation | Frames | Notes |
|---|---|---|
| Throw loop | 15 | 4 poses |
| Catch loop | 17 | 4 poses |
| Toss in scene | 39 | carry 6, windup 3, release 1, flight 14, catch 7, carry 8 |
| Burst | 72 | 6 fuse heartbeats + 66 simulated; 75 shreds including droplets; 3 stick on birds |

## Tile budget (16 x 16, unique after mirror dedupe)

| Set | Non-empty | Unique |
|---|---|---|
| Bird poses, 8 frames | 32 | 30 |
| Tags A B C | 6 | 4 |
| Chalk ring (on the 16 px screen grid) | 32 | 32 |
| Seat pad + 1P/2P chips | 4 | 4 |
| Shreds, streaks, beads | 14 | 12 |
| Splats, patches | 11 | 8 |
| Shadows, flash | 5 | 5 |
| **Total new** | | **95** |

Existing tiles reused at no cost: Sootling sheet frames (idle, breathe, fall, land), gum sheet, Gum Fling field and city.
Sprite load per frame was not counted (see open points).

## P2 colour

`assets/flier/sootling_sheet.json` holds only the `player` and `cpu` palettes, and a grep of `src/` and `tools/` found no
player-2 palette. P2 gold and CPU2 violet from the first draft stay. Unverified beyond the grep.

## Open weak points

- The raised wing is 3 px wide and reads as a stick more than a wing; it needs a broader feathered shape in the next pass.
- A 32 x 32 pose cell does not fit the game's 24 x 32 bird sprite; the game needs a 2-tile-wide sprite for these frames or
  narrower grids.
- The carrier at the left seat throws shreds off the left screen edge, and shreds that fly behind the horizon are not drawn,
  so the burst looks thinner than its shred count.
- Strands are drawn as beads from simulated points; the game cannot run this per frame as is, so it needs baked frames or a
  small set of strand sprites.
- The ring costs 32 tiles because it sits on the screen grid; a fix-layer or a repeated arc piece set would cut this.
- Sprite count per scanline and total sprites in the burst were not counted.
- Only the dusk mood, only the toss 1P to 2P (button B) and only the burst at the 1P seat are shown.
- No throw pose in gummed or white palettes beyond the two flash frames.
