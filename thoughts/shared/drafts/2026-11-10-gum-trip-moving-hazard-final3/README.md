# Gum Trip moving hazards: second hand pass (final3)

Draft art only. Nothing here is wired into the game. Before: `../2026-11-10-gum-trip-moving-hazard-final2/`.
Rebuild: `/opt/homebrew/bin/python3.14 -I draw_moving_hazard_final3.py`. Open `index.html` to compare.

## What changed

- **A. Cloud top**: The top billows of frames 2 to 9, 16 and 17 are drawn by hand, pixel by pixel (table _TOPS in the script). The fault (a flat top outline of 7 to 19 px) was in frames 2, 4 to 9, 16 and 17; frame 3 is redrawn so the shapes flow through it. The right billow rises in frame 2, splits in 3 and 4 and sinks from 5 to 7; one small nub stays in place from 4 to 9; the left shoulder lump drifts left.
- **A. Charge trail**: At rest the trail is now 3 px dashes of periwinkle with one cyan head pixel each (final2: 2 px periwinkle). While the charge builds the dash grows to 4, 5 and 6 px and 1, 2 and 3 of its pixels are cyan (final2 used deep blue there, which is darker than the moon sky). The strike frame is unchanged: white core, cyan halo, one frame.
- **B. Vent base ring**: The lip of the base ring (row 21) glows orange with red orange ends and rust at the shaded end; its underside (row 22) is rust and deep red. One yellow glint and one red orange pixel move along it by a hand-set table, different in each of the 16 frames. Blades, collar and chain are untouched: steel, no stripes, no dither.
- **C. Coal**: The lump is no longer convex. Four lumps stand out of it (a long spur, two knobs, a stub) and four bites are scooped out beside them; one bite is a hot break with a glowing edge. All eight are fixed to the lump, so the same breaks tumble with it. Their positions are hand-picked so that every frame shows a break in the outline.
- **Kept**: Frame sizes, frame counts, ticks per frame, hit boxes, two palettes of 15 colours, JSON format, one strike frame per loop.

## Hand-placed pixels

- Cloud: 990 pixels listed one by one for 10 frames (this count includes pixels set to transparent to cut the old flat top away); 172 of them differ from what the rules drew.
- Vent: 29 listed (the flicker table), 29 changed.
- Coal: 0. The breaks are 8 hand-picked positions on the lump, not single pixels.

## Tiles

Unique tiles 207 + 91 + 96 = 394. Final2: 203 + 91 + 96 = 390. Difference +4. Frame sizes, counts, timing, hit boxes, palettes and JSON format are unchanged. All numbers: `numbers.txt`.

## Weak points left

1. Coal: the lumps are built from small rounded shapes, so in some frames a break reads as a bump, not a sharp chip. No coal pixel is placed by hand; only the positions of the eight breaks are hand-picked.
2. Cloud: the hand-drawn tops cover the top 3 or 4 rows only. The shading under them is still the rule-drawn one, frames 10 and 11 keep a flat run of 6 px, and the right flank of frames 8 to 10 is still a straight wall.
3. Vent: the hot rim is 2 px on a ring 11 px wide. It reads as a warm line, not as glowing metal, and the flicker is one or two pixels per frame.
