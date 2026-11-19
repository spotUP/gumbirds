# GUMBIRDS logo: rim redraw (draft)

Date: 2026-11-10. Input: `../2026-11-10-hud-title-final/logo_a_frames_1x.png` (accepted logo, 10 frames).
Open `index.html` to review. All numbers are in `numbers.txt`. Run `redraw.py` to rebuild every file in this folder.

## What changed

The outer edge of the logo gets its own palette index, 11 ("outer rim"). No pixel moved. The only change in the
image data is index 8 to index 11 on the rim pixels. Index 8 keeps the inner lines between letters and the counters.
The palette uses 11 of 15 entries (was 10). The 16x16 tile count does not change: still 82, body over 10 frames 123,
free pieces 7, total 130, before and after.

## The rule

1. Outside is every transparent pixel. An enclosed see-through hole under 8 pixels is not outside. This keeps the
   6 pixel gap at x 242..243, y 86..89 free of a pale speck. The 110 pixel hole in the D (x 262..270, y 76..91) is
   outside, so the sky side of the D counter gets a rim.
2. A line pixel (index 8) with an outside pixel directly above, below, left or right becomes rim (index 11).
   The outer line is 2 pixels thick, so the rim is the outer 1 pixel and the inner 1 pixel stays dark. The full
   2 pixel swap and the diagonal test were tried; the 2 pixel rim reads as a sticker edge, and the diagonal test
   leaves dotted pale diagonals between the drop shadow and the line.
3. A rim run of 4 pixels or fewer (diagonal neighbours count as connected) goes back to the dark line. These runs
   sit where the drop shadow covers the outline and leaves a few line pixels open to the sky. 13 to 17 pixels per
   frame, listed for the still in `numbers.txt`.
4. The free pieces (bubble fragments and the falling drop) follow rule 2 on their own tile.

Joins that the rule covers without a special case: an inner line that reaches the edge stays dark up to the last
pixel and the rim runs across its end; the drip under the U and the bubble on the I carry the rim like the letters;
the drop shadow (index 7) is never rim, so the lit edge is on the top and left and the shadow on the bottom and right.

## Hand corrections

None. The 6x views of the storm and moon stills show no stray pale pixel and no broken dark line after rule 3.
The check for dark line pixels cut off from the rest of the line finds 0 on all 10 frames.
`HAND` in `redraw.py` is the place for per-pixel fixes if the review finds one.

## Palettes

Only index 7 (under shadow) and index 11 (rim) differ between moods.

| mood  | rim (11)    | shadow (7) |
|-------|-------------|------------|
| dusk  | 8,8,24      | 24,8,49    |
| storm | 160,200,184 | 0,0,0      |
| moon  | 160,192,248 | 0,0,16     |

Dusk equals the accepted logo: 0 differing pixels over the 10 frames and the free pieces.
Storm and moon keep the start values. Five other rim and shadow values per mood were measured and compared by eye
(list in `numbers.txt`). Storm: a paler rim gains 0.4 points of weak edge and starts to read as a white sticker
edge; a darker rim or a lifted shadow loses edge. Moon: every other value measures the same or worse, and a paler
rim melts into the moon disc behind the D and S.

## Weak edge (share of outer logo pixels under 1.5 contrast against the sky, still frame)

| mood  | before | after | frames after |
|-------|--------|-------|--------------|
| dusk  | 3.2%   | 3.2%  | 2.9 to 4.1%  |
| storm | 17.9%  | 5.2%  | 4.6 to 6.2%  |
| moon  | 11.7%  | 4.8%  | 4.8 to 5.9%  |

## Doubts

- The 1 pixel rim measures 0.2 to 0.3 points weaker than the whole-line swap of the outline-moods draft
  (storm 5.0%, moon 4.5%). The rest of the weak edge is the drop shadow against dark sky, which a rim cannot fix.
- Free pieces: their line is 1 pixel in places, so some fragments keep no dark line and show rim directly on the
  keyline. They are on screen for 1 to 4 frames. Alternative: leave the pieces on index 8.
- The measure covers the body layer only, as `compose_moods.py` does. The free pieces are in the stills and gifs
  but not in the percentages.
- Gif timing (110 110 110 110 110 260 90 90 110 200 ms) is taken from the final folder; the game timing is not
  checked here.
- The old logo colours are not multiples of 8. Only the new values (rim and shadow for storm and moon) are.
- `redraw.py` imports `draw_hud_title_final.py` to get the free pieces. The first run left a `__pycache__` folder
  in `2026-11-10-hud-title-final`; that folder was removed again and the script no longer writes one.
- Nothing ran on hardware or in MAME. The tile count comes from the same counting method as the final folder.

## Page design

Dark neutral grey page, system sans-serif text, square figures with a thin border, numbers as plain text.
