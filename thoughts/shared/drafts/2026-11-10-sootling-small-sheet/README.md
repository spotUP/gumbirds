# Small Sootling, full sheet at 24 x 32 (draft)

Draft for a feature-branch trial. Nothing in `src/`, `assets/`, `tests/` or `cfg/` is changed.

## Files

- `sootling_small_sheet.png`: 192 x 512 RGBA, 8 frames per row, frame 24 x 32. Player rows y 0..255, rival rows y 256..511.
- `sootling_small_sheet.json`: same keys as `assets/flier/sootling_sheet.json` (`source`, `animations`, `palettes`, `defines`, `tables`). 63 frames, same order, same clips, same `clip_first`, `clip_count`, `clip_loop`, `frame_ticks`. Palettes are copied unchanged (15 colours, all 15 used, no new ones).
- `contact_4x.png`: every clip at 4x with its name and frame numbers, player on dark, rival on bright ground.
- `sheet_on_grounds_1x.png`: the whole sheet at real size on dark, mid and bright ground.
- `anim_flap2_3x.gif`, `anim_pop2_3x.gif`, `anim_pop1_3x.gif`, `anim_inflate_3x.gif`, `anim_fall_3x.gif`: 3x, real frame timing.
- `measure.txt`: measured columns and rows per pose class, tile count.
- `draw_sheet.py`: builds everything. Run `/opt/homebrew/bin/python3.14 -I draw_sheet.py`. It reads only the palettes and tables of the current sheet JSON.
- `index.html`: gallery.

## Numbers the import needs

- `ART_W 24`, `ART_H 32`, `FEET_ROW 31`, `BOX_FIRST_COL 10`, `BOX_LAST_COL 13` (written to `defines`). They satisfy both asserts in `src/main.c`: box 4 px wide, `BOX_FIRST_COL * 2 + 4 == ART_W`.
- Art is centred on the line between columns 11 and 12. Rest body covers columns 4..19 (16 px with outline, fur 14 x 14).
- Feet bottom is on row 31 when the body is at rest. Flight frames lift the body 1 or 2 px as part of the bob, and the two tucked-feet flap frames end on row 30.
- 16 x 16 tiles: 149 unique with the frame left-aligned in 32 x 32, 156 unique with the frame centred (x 4). The current sheet has 294 unique.

## Weak points of the key-frame draft

- Boxed eyes (goggles): fixed. No outline box. Whites sit in the fur, pupils on the facing side, one mid-tone fur column between the eyes.
- Mid wing merged with the body: fixed. Every wing position has a full outline, sticks 3 to 4 px past the body edge, and is darker than the beak (light only on the leading edge). Checked in the rival palette on the bright ground.
- Gum string without outline: fixed. 1 px light core with a dark pixel on both sides, drawn under gum and body.
- Body squatter than the big Sootling: partly fixed. Rest body is 16 x 16 with outline (round), and stretch frames reach 18 px tall. A taller rest body does not fit: gum (10 rows) plus string plus tuft already use rows 0..14.
- Tufts read as ears: changed to one swept-back quiff. In the fall clip the quiff stands up and can read as a cone at 4x. This is the weakest remaining part.

## Doubts

1. The brief asks for walk and landing GIFs. The current sheet has no walk clip and no landing clip (7 clips: flap2, flap1, pop2, pop1, inflate, fall, idle), and idle is one frame. I kept the frame list identical, so the key frames walk 1, walk 2 and landing have no slot. GIFs are flap2, pop2, pop1, inflate, fall instead. Adding walk or landing needs new `CLIP_*` defines and game code.
2. The eyes differ from the approved key frames (the box is gone, pupils moved to the facing side). This is the change most likely to need a second opinion.
3. Squash and stretch remove or double a hand-chosen body row or column (never a row through the eyes). The face keeps its columns. It is a rule applied to the hand-drawn body, not a redraw per frame; the 15 and 17 px bodies were checked by eye, the 14 and 18 px ones appear only in pop, inflate and fall frames.
4. Mapping of the 10 approved key frames: idle = frame 62, flap up = 0, glide = 2 and 6, flap down = 4, one-gum float = 8..15, pop reaction = 29 and 30, fall = 52. They are redrawn with the fixes above, not pixel-identical.
5. Frames identical by design (clip hand-over without a jump): 27 = 8, 37 = 52, 49 = 4, 50 = 6, 51 = 7.
6. The gum wad on the beak in idle (2 gum pixels at columns 21..22) may read as a tongue.
7. Physics and collision constants tuned for the 32 x 48 art (gum position, stomp height) are not touched here. Gum boxes per class are in `measure.txt`.
8. GIFs were checked as frame strips (contact sheet rows), not as moving pictures.
