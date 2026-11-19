# Toss Gum poses, wing pass (2026-11-18)

Draft only. No game code touched, no MAME run. Script: `draw_toss_poses2.py` (run `python3.14 -I draw_toss_poses2.py`),
reuses `../poses/draw_toss_poses.py` for the body rows, palettes, loops, field and toss scene. Gallery: `index.html`.
Numbers: `numbers.txt`.

## What changed

- Only the wing rows of the 8 side-view grids were retyped by hand. Cells stay 32 x 32 (owner decision: 2-tile-wide sprite
  during throw and catch).
- The wing is now a broad blade in place of the 3 pixel stick: lit edge and feather tips in `Z`, feather body in `Y`,
  slits between feathers and the underside in `X`, outline `K`. Light from the upper left, as on the body. Slits and the
  underside use hand-placed `Y`/`X` alternation, no pattern fill.
- Feather tips show in the silhouette as steps: three on the trailing edge of the upright blade (carry, release A,
  reach A, reach B, recoil), three splayed primaries on the cocked-back wing (windup B), stepped tips past the brow on the
  flat wing (release B), and a deeper cap with slits on the folded wing (absorb).
- Widest run of wing pixels per frame, old to new: carry 3 to 6, windup B 5 to 8, release A 4 to 6, release B 10 to 12,
  reach A 4 to 6, reach B 4 to 7, absorb 12 to 16, recoil 3 to 6 (outline not counted).
- Unchanged: body, head, eyes, beak, feet, gum knot pixels, palette letters (sheet order `KabcdeXYZ12345W`), frame timing
  (throw 15 frames, catch 17, toss 39), H-mirror for left-facing birds. The script asserts that every body, eye and gum
  pixel sits where it sat before.
- Changed on purpose: the wing-tip anchors for the gum knot moved with the new tips, and seven grids start higher
  (carry row 6, release A row 3, release B row 9, reach A row 5, reach B row 0, absorb row 12, recoil row 5).

## Files

`poses2_sheet_1x.png`, `poses2_sheet_3x.png`, `throw_3x.gif`, `catch_3x.gif`, `cmp_<frame>_6x.png` (old and new on grass
and over the city backdrop), `cmp_all_1x.png`, `toss_3x.gif`, `toss_keys_1x.png` (toss in the scene with the new wings).

## Open weak points

- No crowd art exists in the toss drafts, so the busy backdrop test uses the city behind the back seat. Not tested
  against a real crowd.
- The CPU1 wing is teal and the city has teal and blue lights; the outline carries the silhouette there, the fill does not.
- Windup B reads as a three-fingered fan more than as layered feathers.
- Release B: the primaries past the brow are only 1 to 2 pixels apart in length, so the tips read weakly at 1x.
- Recoil reuses the carry blade one row higher; the two frames differ mostly in the body.
- Reach B fills the cell from row 0, so there is no headroom left for a taller stretch.
- The gum flight positions in the two loop GIFs were typed for the old wing tips, so the gum jumps a few pixels at release
  and at the catch.
- Tile count not redone: the wider wings touch more 16 x 16 tiles than the 30 unique counted before.
- Gummed and white palettes not shown.
