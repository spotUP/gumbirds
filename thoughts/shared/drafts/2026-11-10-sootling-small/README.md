# Smaller Sootling drafts

Date: 2026-11-10. Status: draft for the decision "smaller Sootlings or a bigger
world". Nothing under `src/`, `assets/`, `tests/` or `cfg/` was changed. All art
is original.

Open `index.html`. Rebuild every file with
`/opt/homebrew/bin/python3.14 -I draw_small.py` from this folder.

## Files

| File | What |
| --- | --- |
| `draw_small.py` | The pixel grids and the builder for every file below. Reads the palettes from `assets/flier/sootling_sheet.json`. |
| `small_24x32_sheet_1x.png` | 10 key frames, row 1 player palette, row 2 rival palette, transparent. Order: idle, flap up, flap down, glide, fall without gum, walk 1, walk 2, one-gum float, pop reaction, landing. |
| `small_24x32_contact_1x.png`, `_6x.png` | The same frames on a dark ground and on a night-sky tone. |
| `small_20x28_sheet_1x.png`, `small_20x28_contact_*.png` | 4 key frames at 20 x 28: idle, flap up, flap down, fall without gum. |
| `compare_sizes_1x.png`, `_5x.png` | Same four poses at 32 x 48 (current sheet), 24 x 32 and 20 x 28. |
| `mock_now_*.png`, `mock_24_*.png`, `mock_20_*.png` | One 320 x 224 screen at camera x 32, at 1x and 3x. |
| `mock_side_by_side_1x.png`, `_3x.png` | The three screens in one image. |
| `anim_flap_now_vs_24x32_3x.gif` | Current flap2 clip (8 frames) beside the 24 x 32 flap (3 key frames), player and rival. |
| `numbers.txt` | Measured sizes, tile estimates, list of lost detail. |

## Sources used in the mock-ups

- Backdrop: `thoughts/shared/drafts/2026-11-10-islands-final/backdrop_moon_384_1x.png`, cropped to x 32..351.
- Islands: `assets/islands/sheet_roof_1x.png`, thin variant, at the positions of `src/core/stage.c` (sprite top = y - 4).
- Hazard: `assets/hazard/frames_water_1x.png`, frame 0, at y 192 (`HAZARD_STRIP_Y`).
- Current Sootlings: `assets/flier/sootling_sheet.png`, frames 0 (flap), 8 (one gum), 62 (idle).

## Layout of the 24 x 32 frame

Body columns 4..19 (fur 14 wide, 14 tall with tufts), feet rows 30..31, two gum
lobes rows 1..9 (each 9 px, 17 px together), string 1 px light + 1 px dark.
Eyes 4 x 4 each with a 1 x 2 pupil. Light from the upper left.

## Doubts

- The 24 x 32 body is squatter than the current one and the tufts read a little
  like ears. The current Sootling has a taller, fluffier outline with a dithered
  fur rim; that softness is gone.
- Eyes: the boxed brow line makes the face read as "goggles" at 1x. Expressions
  are down to four: open, looking down, small pupils, heavy lids.
- The mid wing (glide, idle) is 5 x 4 px and nearly merges with the body edge in
  the rival palette.
- The gum string has no outline at this size and can vanish against bright
  backdrop pixels (moon, lit windows).
- Fur shading has no dither (the current sheet uses it in the fur). The gum
  bubbles are smooth-shaded by rule; the fur could take dither back if wanted.
- The flap GIF uses 3 key frames against 8 in the current clip, so it looks
  choppier than a finished small clip would.
- Walk frames are new poses; the current sheet has no walk clip, so the mock-ups
  use the idle frame for the flier on the right island at every size.
- The mock-up shows the moon mood only. The backdrop is the composite from the
  islands-final draft, not a capture of the running game.
- 20 x 28 costs the same tiles and sprite strips as 24 x 32 (see numbers.txt),
  so it only buys 4 px of height and loses the eye direction.
- Hit boxes, flap physics, stomp reach and gum offsets in `src/core/flier.h` are
  tuned to the 32 x 48 art; a smaller Sootling needs those retuned and the tests
  that assert them updated. Not estimated here.
- Tile estimates for the small sizes are the measured unique count of the
  current sheet times 4/6, not a count of finished frames.
