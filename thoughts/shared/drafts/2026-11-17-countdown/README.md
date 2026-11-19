# Countdown word drafts (GET SET / GO!)

Draft only, no game code. Run `python3.14 -I draw_countdown.py`; view `index.html`.

| Option | Letter height | Colours (+ transparent) | Palettes | Unique 16x16 tiles (6 glyphs) | Sprite columns GET SET / GO! |
|---|---|---|---|---|---|
| A | 32 | 9 | 1 | 22 | 12 / 5 |
| A-hot | 32 | 9 | 1 | 22 | 12 / 5 |
| B | 32 | 4 | 2 | 22 | 12 / 5 |
| C | 40 | 9 | 1 | 33 | 12 / 5 |

- A: each stroke shaded as a glossy gum tube (inset highlight, magenta to purple shade, violet bounce light).
- A-hot: A's tiles with a second palette; costs one palette, no tiles.
- B: neon tube like the GUM sign in the city; two 4-colour palettes on the same tiles.
- C: 40 px slab in the Hot Gum bubble palette (yellow top to maroon foot, hand-broken band edges).
- Tiles are counted per glyph cell (ceil(w/16) x ceil(h/16)), glyphs G E T S O ! stored once and reused.
- GO! pop-in uses sprite shrink and y offset only.
- Mock plate: ../2026-11-10-backgrounds-final/compare_dusk_2x.png (final half) scaled back to 320x224.
