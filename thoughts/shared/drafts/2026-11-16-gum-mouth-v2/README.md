# Gum-mouth v2: front hang

Drafts only. No game code and no tiles in `assets/` were touched.

## What changed from v1

Owner feedback on v1: the birds looked unbalanced and tipping over, they needed to hang more vertically from the gum, and gum has no long straw.

- One take, based on v1 take B (owner pick: front view, faces the camera, two cheeks).
- No stalk. The short beak points straight up and sits inside the bottom of the gum bubble.
- The body is a pear that hangs straight below the grip point: narrow head pulled up to the beak, belly lower, wings limp at the sides, feet dangling.
- Swing poses (R1, R2, L1, L2 and the puffed R1p, L1p) are separate complete grids. The grip point stays fixed and the lower body moves sideways, so the bird leans around the grip like a pendulum.
- Cheeks are a red-orange ramp, clearly apart from the gum pink. Distress stages 1 to 3 swap those three palette entries to deeper red; stages 2 and 3 add the strain and burst frames (squint, sweat, tremble).

## Files

- `frames_B.txt`: the 16 hand-typed 24 x 32 grids. `@N` after a name is the grip column.
- `draw_gum_mouth_v2.py`: assembles only (palette map, mirror, place the in-game gum cell on the grip point, pack strips and GIFs, count tiles). Run `python3.14 -I draw_gum_mouth_v2.py`.
- `numbers.txt`: tile counts. 16 frames, 50 unique 16 x 16 tiles in total.
- `index.html`: gallery.

## Recommended pick

Take this front hang forward. Use `fly` (blow loop over the swing) as the base flying animation and `settle` after a direction change.

## Doubts

- The body is taller and more box-like than the round in-game Sootling (about 15 x 19 pixels against about 16 x 14). It reads as stretched by hanging, but the identity is weaker than in v1 take B. A rounder belly is the first thing to redraw.
- The lean is small: 2 pixels at the feet for R1/L1 and 3 to 4 for R2/L2. The swing may be too subtle at 1x in game.
- Swing poses shear the lower body; the head does not rotate. A true rotation needs the head redrawn per pose.
- The belly dither is a regular diagonal weave. It is hand-typed, but it is more uniform than the S6 reference.
- Only the compare sheet was viewed after the last eye change; the GIF timing was not viewed in motion.
- Wing frames: only one raised-wing frame, so the flap has no in-between.
