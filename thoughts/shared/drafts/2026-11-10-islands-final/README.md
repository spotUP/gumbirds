# Gumbirds floating islands, final sheets and layout proposal

Date: 2026-11-10. Status: art sheets and a layout proposal for review. Nothing
in `src/`, `tests/`, `tools/` or `assets/` was changed. All art is original.

Open `index.html` for the gallery. Every number below is measured by
`draw_islands_final.py` and written to `numbers.txt`; rerun the script with
`/opt/homebrew/bin/python3.14 -I draw_islands_final.py` from this folder to
rebuild every file.

## The three looks

One look per mood, and one island palette on screen at a time.

| Look | Mood | Files |
| --- | --- | --- |
| A roof chunk | moon night | `sheet_roof_1x.png`, `tiles_roof_1x.png` |
| B garden slab | ember dusk | `sheet_garden_1x.png`, `tiles_garden_1x.png` |
| C airship deck | storm | `sheet_deck_1x.png`, `tiles_deck_1x.png` |

Each sheet holds the widths 64, 80, 96 and 112, first the tall variant
(32 px, two tiles) and then the thin variant (16 px, one tile). The
transparent colour is 255,0,255. Each look has one palette of 15 colours at
5 bits per channel; the values and luminances are in `numbers.txt`. The deck
look uses 14 of its 15 entries.

An island is a left cap, a row of middle pieces and a right cap, all on the
16 px grid. There are five different middle pieces per look, so no width
repeats a piece: 64 uses m0 m3, 80 uses m0 m2 m4, 96 uses m0 m1 m3 m4 and 112
uses all five.

## Collision line

The standing line is sheet row 4 in every piece. Rows 4 and 5 are the bright
straight line. Rows 0 to 3 hold decoration above the line (aerial and vent
pipe, grass blades and blossoms, lamp posts); it is one or two pixels wide so
that it does not look standable. To place an island, set the sprite top to the
stage y minus 4.

## Tile counts

Unique 16x16 tiles for all four widths together. No tile flips are counted.

| Look | Thin static | Thin with animation | Tall static | Tall with animation | Both static | Both with animation |
| --- | --- | --- | --- | --- | --- | --- |
| A roof | 7 | 11 | 14 | 22 | 21 | 33 |
| B garden | 7 | 9 | 14 | 28 | 21 | 37 |
| C deck | 7 | 21 | 14 | 28 | 21 | 49 |

## Animation

Eight frames at 110 ms per look, done with tile swaps in the two cap pieces
only; the middle pieces never change.

- Roof: a lantern hangs under each cap and swings as a pendulum, the two a
  quarter cycle apart. Cost: 4 extra tiles thin, 8 tall.
- Garden: vines under each cap carry a travelling wave. Cost: 2 extra tiles
  thin (only 3 distinct frames), 14 tall.
- Deck: a two-blade rotor under each cap makes a half turn over the eight
  frames, the two counter-rotating. Cost: 14 extra tiles thin, 14 tall.

`anim_<look>_3x.gif` shows each loop and `contact_<look>_4x.png` shows all
eight frames of the 64 px island side by side.

## Lower edge against the backdrop

The lower edge is a dark keyline with a bright rim below it (blue for the
roof, orange for the garden, cyan for the deck). The share of lower edge
pixels that sit less than 24 luminance steps from the backdrop pixel below:

| Look | Proposal layout | Sweep over the whole play area |
| --- | --- | --- |
| A roof on moon | 5.0 % | 3.7 % |
| B garden on dusk | 7.6 % | 7.1 % |
| C deck on storm | 6.1 % | 4.8 % |

The draft measured 18 to 27 percent. The standing line is under 24 steps from
the backdrop pixel above it in at most 1.2 percent of the cases.

## Layout proposal

These values are a proposal for the user, not a decision. The stage table in
`src/core/stage.c` is unchanged. Format: x, y, width, tiles tall.

| Proposal | Stage table now | Differs in |
| --- | --- | --- |
| 0, 148, 80, 1 | 0, 164, 80 | y |
| 304, 164, 80, 1 | 304, 164, 80 | nothing |
| 136, 128, 112, 1 | 136, 140, 112 | y |
| 32, 92, 80, 1 | 32, 104, 80 | y |
| 280, 108, 80, 1 | 280, 104, 80 | y |
| 144, 68, 96, 1 | 144, 72, 96 | y |
| 0, 36, 64, 1 | 0, 40, 56 | y, width |
| 320, 52, 64, 1 | 328, 40, 56 | x, y, width |

The two width changes from 56 to 64 are the user's decision. Every other
difference is proposed here to stagger the heights.

Sprite load per scanline, counted as one sprite per 16 px strip and with every
island counted whatever its screen x:

- Stage table with all islands tall: worst line 17 (lines 160 to 167).
- Stage table with all islands thin: worst line 10.
- Proposal: worst line 7 (lines 124 to 139). No scanline is shared by two
  islands.

The gameplay budget is 24 sprites per line (`SB_GAMEPLAY_PER_LINE`), the limit
is 90 and the hardware limit is 96.

Assumptions made for the proposal, which the user may overrule:

- Islands that overlap in x keep at least 56 px between their standing lines
  (a 48 px Sootling plus 8 px).
- The lowest island stays at y 164 because the water line at y 180 kills on
  contact.
- All eight islands are thin. With eight islands in 180 px of height the tall
  variant has no place in this stage without sharing scanlines. The tall
  sheets are kept for stages with fewer islands.

## Scenes

`scene_<mood>_384_1x.png` and `_2x.png` show the full 384 px arena with the
proposed layout and Sootlings from the final Sootling sheets. The backdrops
are composites made by `make_backdrops.py` from the wide background draft:
arena x 32 to 351 is the true screen at camera x 32, and the far planes and
the sky jump at x 32 and x 352. Those jumps are an artefact of the composite,
not of the islands.

## Weak points left

- Roof: the thin variant shows only one brick course, so the torn underside
  and the lanterns shrink to a few pixels; the brick body is close in value to
  the lit city windows behind it.
- Garden: the soil is dark and sits near the dusk skyline in value, so the
  island reads mostly through its turf line and orange rim; the vines of the
  thin variant move in only 3 distinct frames.
- Deck: the rotors are thin two-pixel blades and read as antennae at 1x; the
  hull is a plain trapezoid and one palette entry is unused.
- Because the proposal uses only thin islands, the scenes never show the tall
  art. Judge the tall variant from the previews and contact sheets.

## Gallery page

The page uses a dark slate background, plain sans-serif text and squared
elements, with orange marking the values that differ from the stage table.
