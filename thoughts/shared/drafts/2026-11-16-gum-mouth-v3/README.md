# Gum-mouth bird drafts, round 3 (2026-11-16)

Drafts only. No game code, nothing in `assets/`. Gallery: `index.html`.

Owner feedback on round 2 that this round answers:

1. Body was tall and boxy (about 15 x 19). It is now a 16 x 14 ball, the same size as the in-game Sootling body.
2. Eyes were small and pale. They are now 3 x 3 white with a black pupil on a dark face band, with the in-game
   light patch under each eye.
3. Belly dither was a regular diagonal weave. It is re-typed by hand as broken feather clusters (no repeating period).
4. Lean was a 2-4 pixel shear. Each swing pose (`R1 R2 L1 L2`, puffed `R1p L1p`) is its own grid: the whole bird
   turns around the grip. The grip moves 3 columns (about 20 degrees) and 5 columns (about 35 degrees) off the body
   centre; eyes, beak, cheeks, tuft, wings and feet all move with it. Light stays top-left.
5. Flap had one wing frame. It now has four upstroke frames (`f1`-`f4`) and two downstroke frames (`d1`, `d2`).

Kept: beak bites the gum directly, no stalk, front view, two red-orange cheeks, distress stages 1-3 by palette swap.

## Files

- `frames_B.txt`: 21 hand-typed 24-wide grids. This is the art.
- `draw_gum_mouth_v3.py`: assembles, palette-maps and packs only. Run `python3.14 -I draw_gum_mouth_v3.py`.
- `numbers.txt`: tile counts per animation.

## Open doubts

- Wings are short stubs (3 x 4 pixels). The flap reads in motion but is small at 1x.
- `R2` and `L2` put one foot beside the body. Check that it reads as a swing and not as a kick.
- The puff and blast frames hide the wings behind the cheeks.
