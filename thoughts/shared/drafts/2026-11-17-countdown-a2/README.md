# Countdown option A "Gum tube", polish pass (A2)

Draft only, no game code. Run `python3.14 -I draw_countdown_a2.py`; view `index.html`.

- Letter height 32 px. Glyph widths: G 28, E 24, T 24, S 28, O 28, ! 10.
- Colours: 12 + transparent, one palette.
- 16x16 tiles: 22 unique (22 non-empty cells before dedupe; first draft counted 22 cells).
- Sprite columns: GET SET 12, GO! 5.
- Hot Gum palette swap kept: same tiles, second palette (`A2-hot_3x.png`).
- GO! pop-in uses sprite shrink and y offset only.
- Mock plates: ../2026-11-10-backgrounds-final/scene_<mood>_1x.png.

| Key | Pink | Hot | Role |
|---|---|---|---|
| k | #160826 | #080818 | outline |
| d | #3c1266 | #5a0c2e | deepest shade (violet) |
| m | #681a7c | #8a1430 | shade |
| r | #9c2088 | #c0201e | dark pink |
| R | #c82e90 | #e63a1e | dark mid |
| p | #ee4c9c | #ff7a1a | mid |
| P | #ff86b8 | #ffa922 | light / rim |
| l | #ffb4cc | #ffdc4a | highlight band |
| w | #ffe2dc | #fff3b0 | highlight edge |
| W | #ffffff | #ffffff | specular |
| v | #9a5ae0 | #d42a7a | bounce light |
| V | #c8a0f6 | #ff8ab8 | bounce light peak |

## Changed against the first A
- Vertical strokes 8 px -> 10 px, letters G O S 24 -> 28 px and E T 22 -> 24 px wide (same tile cells).
- 9 -> 12 colours: darker outline, a violet deepest shade, a dark-mid pink, a bounce-light peak.
- Hand dither rows/columns between light and mid pink and between dark pink and shade.
- Wider white specular on every stroke start, cast shadow under each bar, bounce light on the lower right edges.
