# Gum Games rules card: three layout drafts (2026-11-17)

Draft only, no game code. Run `python3.14 -I draw_rules_card.py`; view `index.html` (2x and 3x, nearest neighbour).
Card shows before GET SET; A skips. Example event: Gum Fling (A only: mash A for power, hold A to raise the
angle, let go to throw; two players take turns, 3 throws each; safe angle 15 to 75 degrees is the green band on
the angle bar, 6 segments of 15 degrees, red at both ends). Flap Dash is shown on draft B.

## Drafts
- A `anim_A_banner_strip.gif`: name and goal banner on top, control strip below, the example plays in the open arena.
- B `anim_B_centre_card.gif` (recommended), `anim_B_centre_card_flap_dash.gif`: one centred card, example window
  left, one row per control right, the current step lights up (others use the dim palette).
- C `anim_C_three_steps.gif`: three windows side by side, one per step, all looping at once.

## What is real, what is new
- Real: Sootling frames (assets/flier/sootling_sheet.png), dusk scene (../2026-11-10-backgrounds-final/scene_dusk_1x.png,
  it has demo fliers baked in), fix font, frame and fill tiles and palettes white, pink, gold, dim (assets/font/fix_font.json).
- New, typed by hand as character grids in the script: button cap up and down (16x16), letters A B C, stick (16x16),
  four bar segments (8x8: empty, power, safe, foul), mash spark (8x8), gum ball and trail dot (8x8), slab (16x8),
  angle needles at 20 and 45 degrees (70 is the mirror of 20).
- All text sits on the 40x28 cell grid with existing glyphs; the script asserts every string fits its panel.

## Cost (from numbers.txt, counted by the script from the tiles actually placed)

| Draft | New fix tiles (8x8) | New sprite tiles (16x16) | Sprite columns, worst frame | Frames |
|---|---|---|---|---|
| A banner and strip, Gum Fling | 12 | 5 | 12 | 7 |
| B centre card, Gum Fling | 14 | 5 | 10 | 7 |
| B centre card, Flap Dash | 18 | 1 | 5 | 4 |
| C three steps, Gum Fling | 12 | 5 | 20 | 4 |

- Whole icon set for all six events (A, B, C up and down, stick): 28 unique fix tiles, plus 4 bar and 2 spark tiles = 34.
- Panel, frame and all text: 0 new tiles (existing s:fill, s:f_*, b: glyphs).
- Colours: 14 + the panel colour = 15, one new fix palette. The same 14 + gum pink = 15 as one sprite palette for
  needle, gum, dot and slab (5-bit per channel, snapped in the script).
- Fits: fix tiles go after the 1024-tile font the same way the attract overlay icons do (ATTRACT_FIX_BASE 0x400,
  tools/build_attract_icons.py is the pipeline to reuse). Sprite columns are far under 96 per line.
- Not checked: free fix tile range after the attract icons, and the palette slot. FIX_PAL_COUNT is 5 and sprite
  palettes start right after it (src/vram_layout.h), so a sixth fix palette shifts the sprite slots (generated, not typed).

## Limits to know before picking
- Sprites draw under the fix layer, so the example window is a hole in the panel: the frozen arena shows through
  and cannot be dimmed without a palette fade. Labels inside the window use the boxed glyphs to stay readable.
- The slab under the bird is a stand-in; in game the bird can stand on a real island if the window is placed over one.
- A skips the card and A is also the mash button: the skip must be ignored for the first frames or a player who is
  already mashing will never see the card.
- C needs three windows; events with one control (Flap Dash, Big Blow) would leave windows empty or repeat.
