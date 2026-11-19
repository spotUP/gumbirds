# Leaking gum bubble drafts (2026-11-17)

DRAFT ONLY. Nothing here is used by the game. Owner request: a damaged bubble (1 of 2 balloons, or Trip gum meter
below half) must be visible. Look: gum patch / tear + air "hiss" puffs + faster wobble. Visual only, no rule change.

Open `index.html`. Redraw: `python3.14 -I draw_gum_leak.py` (reads the v4 bird and `assets/gum/gum_sheet.png`).

## How it is built

- The leak is ONE extra 16 x 16 sprite (1 tile per frame) on top of the unchanged bubble cell. No bubble frame is redrawn,
  so it works on all 16 bubble levels and all 6 wobble frames. On the level 10 cell (32 x 32) the tile covers x 16..31,
  y 3..18: inside the bubble's sprite box (asserted in the script).
- Anchor: the bubble's upper right rim, from `level_shown_w` (`k = round(0.7 * shown / 2)`; tile origin =
  bubble centre x + k - 6, bubble top + shown / 2 - k - 11). Mirror with the bird's facing.
- All shapes are hand-typed pixel stamps in the script (tear x2, patch x3, puffs J0 J1 P1..P6 S1 S2). Only the puff
  positions are computed: spurt speed and angle per puff (typed emit list), drag 0.62 per frame, rise 0.22 px/frame^2,
  age picks the stamp (jet streak, dense, round, hollow, sparse, specks).
- Extra wobble: the leaking bubble plays its 6 wobble frames at double speed. 0 tiles.
- Palette: the gum palette only (assets/gum/gum_sheet.json `level16`, 12 entries), no new colour, 3 entries stay free.
  Puffs: b (white), a (pale pink), c (blue rim light). Player 2 / computer pictures use the same mock-up recolour as v4.

## Variants (leak frame = 3 game frames, 20 fps)

| Variant | Look | Frames | Loop | Tiles per frame | Extra tiles | Gum palette entries |
|---|---|---|---|---|---|---|
| A | small side tear with a fluttering flap, steady puffs (4 puffs, 2 sizes) | 8 | 0.40 s | 1 | 8 | 1 2 4 8 9 a b c |
| B | square gum patch, corner lifts, two bursts then quiet | 16 | 0.80 s | 1 | 15 | 1 2 6 9 a b c |
| C | half-peeled patch, constant thin hiss streak + 4 sputter puffs | 12 | 0.60 s | 1 | 12 | 1 2 6 9 a b c |

Every variant also costs 1 extra sprite per leaking bird. Exact numbers: `numbers.txt`.

## Files

- `draw_gum_leak.py`, `numbers.txt`, `index.html`
- `<V>_frames_1x.png` / `_4x.png`: level 10 bubble + leak, every frame. `<V>_tiles_1x.png` / `_6x.png`: the leak tiles alone.
- `<V>_<p1|p2|cpu>_4x.gif`: healthy (left) vs leaking (right) on the idle bird.
- `compare_ingame_6x.png`: healthy, A, B, C for player, player 2, computer. `compare_sizes_4x.png`: levels 5, 7, 10, 12, 16.

## Not done / open

- Not checked against the bubble's warm / hot cue palettes (entry c changes there, so puff shade turns tan / orange).
- The patch does not follow the 1 px rim shift between wobble frames; a per-wobble offset table would fix it.
- Only checked on the flat draft background, not on the bright dusk sky (white puffs may need the dark outline there).
- Pop and bird distress frames untouched.
