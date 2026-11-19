# Gumbirds: title logo, fix font and HUD drafts

Draft round of 10 November 2026. Nothing here is read by the build. Open `index.html` to compare the options side by side; `numbers.txt` holds palettes, colour counts, tile counts and sprite counts.

Regenerate everything with:

    /opt/homebrew/bin/python3.14 -I draw_hud_title.py

The script reads earlier draft renders as backdrops (`../2026-11-10-islands/scene_roof_*_3x.png` for the match, `../2026-11-10-backgrounds-wide/cams_*_2x.png` for the title) and the Sootling sheets from `../2026-11-10-sootling-final/`.

## Title logo

All letters come from stroke skeletons written for this draft (lines and arcs in a unit box) and are rasterised with three different brushes. No existing font or logo was used as a source. None of the three uses slanted yellow or orange gradient lettering with a blue outline, so none resembles the logo of the older shooter with the similar name.

- **A. Stretched gum** (sprites). Fat round pink letters on an uneven baseline, hard cel bands and white highlights, no dither. Gum strands join G to U and D to S, a drip hangs under the U and a bubble sits on the I. Animation, 10 frames: the bubble inflates and pops while the drip stretches, breaks and falls. Cost: 79 unique 16x16 tiles for the still picture, 155 with all animation frames, at most 19 sprites on one scanline, 1 palette.
- **B. Enamel rooftop sign** (fix tiles). A teal enamel plate on two chains with cream block capitals, a red drop shade, hard gloss bands, rust chips and a border of bulbs. Hard metal, so no dither. Animation, 6 frames: the bulbs chase by rotating 3 palette entries, which costs no tiles. Cost: 174 unique 8x8 fix tiles in 204 cells, 0 sprites, 1 fix palette of 15 colours.
- **C. Floating soot letters** (sprites). Each sooty letter with an ember rim hangs under its own gum bubble, pink or lime, like the Sootlings in play. Animation, 12 frames: every letter bobs with its own phase (sprite position only) and the bubbles sway. Cost: 16 sprites, 16 on one scanline, 58 unique 16x16 tiles for the still picture, 92 with sway frames, 3 palettes of which 2 are the Sootling gum ramps.

## Fix font

Both fonts are drawn by hand as bitmaps inside the script: A to Z, 0 to 9, `. , : ! ? - ' / < >`, a heart, a gum bubble and a Sootling face. That is 49 tiles each. One fix palette per text colour (white, pink, lime, gold, dim); the icons keep fixed palette slots, and the lime palette turns the gum icon lime for player 2.

- **Font A, Gumdrop**. 7x7 glyphs with two pixel stems, rounded corners, four shades from top to bottom and a one pixel drop shadow. It also has 8x16 score digits (20 more tiles).
- **Font B, Signwriter**. 6x7 glyphs with a heavy left stem and a thin right stem, a hard two-tone split and a side extrusion.

## HUD

The play ceiling is y = 16, so fix rows 0 and 1 cover no play area. Both layouts use only rows 0, 1 and 27 (the bottom row lies over the hazard strip). The design has one life per match, so the HUD shows the stored gum count instead of lives.

- **Layout 1, Roof strip**. An opaque dark band on rows 0 and 1 with `PLAYER 1`, `HIGH SCORE`, `PLAYER 2`, the three scores and a gum icon with a count. The bottom row shows the round with the mood name and `CREDITS`. The band needs 20 sprites of one dark tile behind the text, or 49 more glyph tiles with a filled background.
- **Layout 2, Corner tags**. No band. Tall score digits in the top corners, the player label and one gum icon per stored gum beside them, and `HIGH SCORE`, `ROUND` and `CREDITS` on the bottom row. The mood name would move to a round intro card.

The results screen and the three-letter name entry are drawn for layout 2 with font A. The score values on the results screen are placeholders, because the design fixes "points for stomps and wins" but no values.

## Own choices

- Recommendation: logo A, font A, layout 2. Logo A says "gum" at a glance and gives the title its animation; font A stays readable over all three moods and owns the tall digits; layout 2 costs no sprites and leaves the sky open.
- Six-digit scores, although `src/main.c` prints eight digits today. Eight tall digits per player would not fit beside the labels in layout 2.
- A `PRESS START` join prompt in the player 2 corner when only one player is in.
- Text colours: pink for player 1, lime for player 2 (the two gum colours), gold for high score and headings.

## Weak points that remain

- Logo A is the most expensive option, and on the ember dusk sky only the dark keyline separates pink gum from pink cloud.
- Logo B is a flat rectangle and the least gum-like. Logo C has small letters whose ragged edge reads as noise at 1x.
- The two fonts are close relatives. In font A, the pairs 0 and O, and M and W, are close at 1x.
- The Sootling face icon is too small to read as a bird; no HUD layout uses it.
- Unbacked text on row 27 is hard to read over the yellow and black stripes of the storm hazard strip, in both layouts.
- Cabinet overscan is unchecked: rows 0, 1 and 27 and the outer columns may be cut off on the real monitor.
- GIF files with a backdrop are reduced to 255 colours, so their skies band slightly; the PNG files are exact.
