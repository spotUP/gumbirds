# Fire tile variant C (draft, 2026-11-10)

Third fire tile for the bottom hazard strip. The row becomes A B C (192 px before it repeats, was 128 px).
Draft only: nothing in `src/`, `assets/`, `tools/`, `tests/` or the accepted drafts was changed.

## What was done

- A and B are the accepted tiles from `../2026-11-10-hazards-final/frames_fire_1x.png`, copied unchanged.
  The script asserts that rows 0 and 1 of the new sheet are pixel-identical to that file.
- C is not derived from A or B. It is its own run of the same simulation (`fire_v6_base`), with its own four
  sources, its own two "minor leader" windows and its own turbulence phases.
- The simulation runs on a 192 px periodic domain laid out A B C. The A and B regions are overwritten after every
  sub-step with the original 128 px simulation (re-run in the script; rendered through the accepted pipeline it
  reproduces the accepted sheet pixel for pixel). C therefore grows against its real neighbours.
- Seams: the first 5 px of C follow A's left edge (the pixels that follow B in the accepted row) and the last
  10 px of C follow B's right edge (the pixels that precede A). Both seams continue the baked neighbour pixels.
- Gap rule: C's sources stay weaker than the leaders of A and B (strength 0.80 / 0.82 against 1.0), so the tallest
  tongue of the row is always in A or B and C never ties with it.
- Same palette (11 colours), same clean-up rules, same dither (`dither3`, same material list), 16 frames, no smoke,
  10 embers.

## Build input layout

`frames_fire_abc_1x.png`: 1024 x 96 RGBA. 16 frames per row, each frame 64 x 32. Row 0 = A, row 1 = B, row 2 = C.
Same convention as `frames_fire_1x.png`, with one more row. Screen order left to right: A B C A B ...

## Numbers (full list in `numbers.txt`)

- Gap between the two tallest tongues, wrapped 192 px A B C row, as drawn: min 2,
  per frame `6 7 2 4 6 4 4 2 9 9 3 5 3 3 3 4`. The two frames with gap 2 (frames 2 and 7) are the same two frames
  that have gap 2 in the accepted A B row; C does not set the minimum.
- Dither in C: 2107 px (14.2 % of opaque), pair luminance step median 33.4, p10 32.7 (rule: at least 28).
- Palette: C uses 11 colours, all from the existing fire palette; A B C together 11.
- Unique 16 x 16 tiles: C 115 of 128; A B C 343 of 384 (A B alone 230 of 256).
- Loop: the simulation is periodic in time (residual 0). Frame 15 to 0 changes 344 px in C; mean per step is 242,
  maximum of the other steps 326.
- Likeness: best pixel agreement of C with A or B over every x shift and frame shift is 74.4 %; A against B at
  the best shift is 68.5 %. Most of the agreement is the shared low base flame and empty sky.

## Honest weak points

- C has no white-hot core in its flames. White needs a source near strength 1.0, and such a source grows a
  tongue as tall as the leaders of A and B, which breaks the gap rule. C reads slightly calmer and less bright.
- C has only mid-height tongues (10 to 18 px; A and B reach 19 to 23). Over a long row this gives a rhythm
  "tall, tall, lower". It hides the repeat less than a third full leader would.
- The right 10 px of C copy B's right edge (98.6 % equal pixels in the last 8 columns), including a twin of B's
  source at x 122. The left 5 px copy A's left edge (79.1 % equal in the first 8 columns). A viewer who looks at the
  seams can find the same shape twice, 64 px or 128 px apart.
- The back-row flame at C's left edge and the first coal lump of C are copies of A's.
- The silhouette jump at both new seams is the same as at the accepted B|A seam (max 9 px in frame 3), not better.
- Embers of C are clipped at the tile edge. In this run no ember left the tile, so nothing pops; a change of
  ember speeds can bring that back.
- Frame 15 to 0 in C changes more pixels (344) than any other step in C (max 326). It is the same time step as
  the others; a leader window opens there. It was not judged in motion.
- The GIFs were checked as frame sheets (frames 0 to 7) and stills, not viewed in motion.
- The gap margin stays at 2 px. A later change to A or B can break the rule without touching C.

## Files

- `draw_fire_c.py` - generator. Imports the accepted scripts read-only. `--cache DIR` keeps the re-run of the
  original simulation (about 19 MB); `--scratch DIR` writes inspection frame sheets.
- `frames_fire_abc_1x.png` - build input (layout above).
- `strip_abc_3x.png` - frame 2, full 320 px row, 3x.
- `anim_abc_3x.gif`, `anim_ab_3x.gif` - 320 px row, 16 frames, 4 video frames per step.
- `tiles_abc_4x.png` - A, B, C side by side, frames 0 4 8 12.
- `numbers.txt` - every measured number of the last run.
- `index.html` - gallery.
