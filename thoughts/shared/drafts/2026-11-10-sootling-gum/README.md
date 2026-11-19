# Sootling with bubble gum bubbles (drafts)

Drafts only. Nothing here is game data. Open `index.html` at 100 percent browser zoom.
Regenerate everything: `/opt/homebrew/bin/python3.14 -I draw_sootling_gum.py` (`--nogif` skips GIFs, `--rebg` re-renders the three backdrops).

## What is here

- `draw_sootling_gum.py`: draws everything (sheets, GIFs, scenes, `numbers.txt`, `index.html`).
- `<V>_sheet_1x.png`: build layout, 112 x 64, 7 frames of 16 x 32, player row then computer row, magenta 255,0,255 transparent.
- `<V>_import_1x.png`: the same 7 frames in the layout `tools/import_flier_sheet.py` reads (142 x 74, frames at x = 2 + 20 i, rows at y = 2 and 38).
- `<V>_ext_1x.png`: extended sheet, 62 frames per palette (flap with two 8, flap with one 8, pop 12, last pop 12, respawn 16, fall 6).
- `<V>_sheet_4x.png`, `<V>_ext_4x.png`: 4x viewing copies.
- `<V>_anim_<state>_4x.gif`: player (left) and computer (right), each over a flat tone sampled from a backdrop.
- `<V>_anim_scene_3x.gif`: eight fliers looping over a crop of the moon backdrop.
- `<V>_scene_<mood>_3x.png`: ten fliers over the moon, storm and dusk backdrops (backgrounds-final renders, placeholder islands).
- `bg_<mood>_1x.png`: cached clean backdrops (no placeholder fliers).

`<V>` is the bubble design: A, B or C.

## The three bubble designs

- **A, twin bubbles on gum strands.** Two separate bubbles side by side above the head, each on a strand to the lips. Closest to the old balloon silhouette. After a pop the survivor swings to the middle.
- **B, double-lobed bubble from the mouth.** One membrane with two lobes and a crease, on a short neck from the lips. After a pop it pulls round into one bubble.
- **C, stacked bubble.** A big bubble from the lips with a small one budded on top. The top one pops first.

My pick is A: the count (2, 1, 0) reads fastest and the strand makes the "blown from the mouth" idea visible. B is the most gum-like but its count reads worst.

## Choices and assumptions

- Frame box, feet row and hit box are unchanged: 16 x 32, feet on row 31, hit box columns 6..9. The body sits on rows 20..31; bubbles use rows 1..19. The old art left rows 0..7 empty; these drafts use them.
- One palette of 15 colours + transparent per flier holds soot, ember and gum together, so the sheet drops into the current importer. All colours are snapped to 5 bits per channel in the script and asserted distinct. A second gum palette is possible on the hardware (palette is per tile in the sprite control block, top tile gum, bottom tile body), but then the strand and face splat that cross the tile border would need care. Not used here.
- Player: blue-grey soot, ember wing, amber goggle lens, pink gum. Computer: rust soot, teal wing, cyan lens, lime gum. Same tiles.
- Kept from the old Sootling: round soot body, goggle, ember wing at the back, wide stance. Dropped: the cap (the bubble sits where it was).
- Light from the upper right: rim on the right cheek, sphere shading on the gum, hard white gloss kept clean, checker dither only on the fur shadow and the gum shadow edge.
- Backdrop shows through the gum only through a small checker mesh window in the lower left of each bubble. No real alpha.
- Motion is simulated, not hand keyed: damped springs for squash (area preserving), lag and sway driven by the flap acceleration and run to a periodic steady state; pop = tear front running from the puncture toward the lips with a pale retracting rim, ballistic droplets, strands springing back, gum landing on the face in four fading stages; respawn = breath-pulsed growth with overshoot and ringing.
- The build layout picks 7 key frames from the extended set (glide, flap up, flap down with two; glide, flap up with one; no bubble; fall). The extended set is for the pop and respawn effects in the graphics plan.
- No walk or stand frames: the current sheet has none.

## Numbers

See `numbers.txt` (script output). Summary:

- Colours: 15 per palette defined, 14 used (the dark ember key `e` is always hidden behind the body; one slot is spare).
- Frames: 7 in the build layout, 62 in the extended set.
- 16 x 16 tiles: build layout 13 unique (current sheet: 19). Extended set 115 or 116 unique of 117 non-empty per design; almost no reuse.
- Minimum dither pair step: player 34.4, computer 28.2 (floor 28).
- Soot outline against median backdrop luminance: player 62 / 58 / 77, computer 60 / 56 / 75 (moon / storm / dusk).
- Gum outline against median backdrop: player 32 / 28 / 47, computer 30 / 25 / 45. Against the hazard strip it falls to 18..31.

## Weak points

- The character is still 16 px wide and 12 px tall. It reads cleaner than v5 but is not rich by 16-bit standards: four fur shades, one rim colour, one gloss pixel on the lens. A larger frame box is the real fix and is a game-rules decision (hit box).
- Bubbles are 8 to 12 px across. Room for three or four shades, one gloss tick and a mesh window of 3 to 6 pixels. On the flat test tone the mesh reads as a dark speck more than as transparency.
- The gum outline is the weakest contrast in the set (18..47). Bubbles are carried by their bright fill, not their outline.
- Player pink gum sits close to the pink and orange dusk sky and to the pink GUM sign. Computer lime is clear on all three moods.
- Player blue soot is close to the moon and storm building colours; the rim light and the lens carry it.
- C: the count reads by height only and the outline is lumpy; weakest of the three.
- B: the crease is 2 to 3 pixels; two lobes can read as one wide oval. In the squashed flap frames the lobes touch both box edges.
- A: strands are 1 px and nearly vanish over bright windows; the twins fill the full 16 px width, so sideways sway is clipped.
- Pop droplets are clipped by the 16 x 32 box. A separate pop puff sprite (already in the graphics plan) would fix that.
- Horizontal flip reverses the light direction (lit from the upper left when facing left).
- The fall strand reads as a thin squiggle; it may be noise at 1x.
- Tile cost of the extended set is high (about 115 tiles per design against 19 today).
- Computer palette fur dither step is 28.2, just over the floor.

## Not looked at in motion

No GIF was watched playing. I inspected still frames only: the build sheets and extended sheets at 4x (A, B, C), and three scene stills (C on moon, B on dusk, A through its extended sheet). The storm scenes, the scene GIFs and the per-state GIFs were written and their frame counts checked, but not viewed. Timing (70 to 90 ms per frame), the wobble amplitude and whether the tear reads as a tear in motion are unverified.
