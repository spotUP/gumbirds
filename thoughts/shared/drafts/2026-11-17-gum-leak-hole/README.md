# Leaking gum bubble, round 2: a hole (2026-11-17)

DRAFT ONLY. Nothing here is used by the game. Owner verdict on round 1 (`../2026-11-17-gum-leak/`): "no patch make a
hole". So: no gum patch. The damage is a hole in the bubble rim that air hisses out of.

Open `index.html`. Redraw: `python3.14 -I draw_gum_leak_hole.py` (imports the round-1 script for the puff stamps, the
puff simulation with drag 0.62 / rise 0.22, palettes and sheet helpers; reads the v4 bird, `assets/gum/gum_sheet.png`
and the dusk scene from `../2026-11-10-backgrounds-final/`).

## How it is built

- Same frame as round 1: ONE extra 16 x 16 sprite (1 tile per frame) over the unchanged bubble cell, gum palette only
  (entries 1 2 5 6 9 a b c, no new colour), hand-typed pixel stamps, only the puff positions are simulated.
- The hole: dark inside (entries 1 and 2), a lit rolled-back lip on the upper left (b, a), a shaded lower lip (9 6 5),
  and two lip ends torn outward past the rim outline with the dark mouth between them. That is the rim break: an
  overlay cannot erase bubble pixels, so the break is drawn as lip pushed outside the silhouette.
- Rim follow (round-1 open point, fixed): the tile origin is taken from the rim itself. Walk the 45 degree ray from the
  bubble centre up-right; the last gum pixel lands on tile pixel (6, 11). `numbers.txt` has the origin for all
  16 levels x 6 wobble frames in sheet-cell coordinates and the shift against wobble 0 (level 10: 0,0 / 0,+1 / 0,+1 /
  -1,+1 / 0,0 / 0,0). In game this is a 96-entry offset table, or 6 entries per level.
- Puff contrast on dusk (round-1 open point, fixed): every puff pixel gets a dark purple edge (entry 2) on its lower
  and right side. `outline_dusk_3x.png` shows plain against edged. It costs no tile and no palette entry.
- The holed bubble plays its wobble at double speed. 0 tiles.

## Variants (leak frame = 3 game frames, 20 fps)

| Variant | Look | Frames | Loop | Extra tiles | Extra sprites |
|---|---|---|---|---|---|
| D | round puncture, rolled lip, dark inside, steady hiss streak + 4 sputter puffs (round-1 C's air) | 12 | 0.60 s | 12 | 1 |
| E | jagged split running inward from the rim, lip flutters open / half / slit, air in two gusts | 8 | 0.40 s | 8 | 1 |
| F | D's puncture with a torn gum tongue on the upper lip whipping in the hiss, small puffs only | 6 | 0.30 s | 6 | 1 |

Baked alternative (picture only, `baked_*.png`): the hole cut into the bubble frames so the sky shows through. Needs a
second copy of every bubble frame: 276 tiles (16 levels x 6 wobble), static hole, puffs still the overlay sprite.

## Files

- `draw_gum_leak_hole.py`, `numbers.txt`, `index.html`
- `<V>_frames_1x.png` / `_4x.png`: level 10 bubble + hole, every frame. `<V>_tiles_1x.png` / `_6x.png`: the tiles alone.
- `<V>_<p1|p2|cpu|dusk>_4x.gif`: healthy (left) against holed (right) on the idle bird; `dusk` = player on the dusk sky.
- `compare_flat_1x/3x.png`, `compare_dusk_1x/3x.png`: healthy, D, E, F for player, player 2, computer.
- `outline_dusk_3x.png`, `compare_sizes_4x.png` (levels 5, 7, 10, 12, 16), `baked_dusk_1x/4x.png`, `baked_flat_4x.png`.

## Not done / open

- The hole stamps are drawn for the level 10 rim curve. On levels 1..7 (bubble 9..15 px) the hole is large against
  the bubble; a second, smaller stamp set for small levels is not drawn.
- The steady hiss streak in D reads close to a thin pin at 1x on some frames; E's gusts do not have that.
- Not checked against the bubble's warm / hot cue palettes (entry c changes there, puff rim light turns tan / orange).
- The dark inside is entry 1 (navy), not see-through; on a very dark background the hole interior blends with the sky.
- Mirrored (bird facing left) not rendered; the tile mirrors with the bird as in round 1.
- Pop and bird distress frames untouched.
