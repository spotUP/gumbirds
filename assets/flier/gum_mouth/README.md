# Gum-mouth bird v4 (fix pass on v3)

Draft only. No game code, nothing in assets/. Open `index.html` for the gallery (v3 and v4 side by side, in-game Sootling reference, v2 feet next to v4 feet).

## What changed versus v3

- Wings: 4-5 wide and 6-9 tall instead of 3x4 stubs. Flap arc over f1 f2 f3 f4 d1 d2: out-low, horizontal, up-out, straight up, high with puffed cheeks, long low with blast cheeks.
- Puff, blast, strain, burst, stand_puff, stand_blast, R1p, L1p: wings sit low under the cheeks, so they stay visible.
- R2 top edge rounded.
- R1/R2/L1/L2: both feet hang together under the rotated body and trail one column back toward the centre.
- Dangling feet restored: 3 leg rows as v2 (`6`, `7`, `787`) plus one row of drooping toes (`7.7`). Stand frames keep the flat foot.
- New frames `rest_fl` and `rest_fr`: body centred, feet still lagging left or right. Used only in the settle sequence (feet lag 2-3 ticks behind the body).
- New frame `rest_fwd`: pupils looking forward. Gallery only, for the owner to choose; the main set keeps pupils up at the gum.
- Kept from v3: round 16x14 body, 3x3 eyes, feather-cluster belly, whole-body rotation around the grip, beak biting the gum, cheek ramp distinct from gum pink, distress palette swap.

## Files

- `frames_B.txt`: the 24 hand-typed grids (24 wide, palette letters).
- `draw_gum_mouth_v4.py`: assembler (`python3.14 -I draw_gum_mouth_v4.py`). Assembles, mirrors, palette-maps, packs, counts tiles. Reuses helpers from `../2026-11-16-gum-mouth/draw_gum_mouth.py`.
- Sway flap frames (2026-11-17): `R1_f1..f4` and `L1_f1..f4` in `frames_B.txt` are the wing arc on the swung bodies R1 / L1, used by clips `flap_r` / `flap_l`. They add 22 unique tiles; the game sheet goes from 72 to 88 tile slots. `numbers.txt` is from before them.
- `numbers.txt`: tile counts from the assembler's tile builder. 59 unique tiles for all frames (v3: 50). idle 10, fly 22, settle 23, flap 24, landing 13, distress1 10, distress2 10, distress3 6.
- `B_*.gif`, `B_*.png`: generated sheets and animations.

## Open doubts

- Feet are 3 pixels wide, so the toe row reads as two small dots at 1x; the lag is 1 column and subtle.
- Feet lag frames exist only in settle. Fly and flap keep straight legs.
- Low wings under puffed cheeks can read as hips or hands.
- Right wing uses the dark ramp (shadow side) and reads dark red against the orange left wing.
- Wings have a shade gradient but no hand dither (too small for an S6 pattern).
- L2 top edge was left as in v3 (only R2 was named).
- Rest wings read a little like small arms.
