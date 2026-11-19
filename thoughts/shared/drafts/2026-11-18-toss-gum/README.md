# Toss Gum drafts, 2026-11-18

Gallery: `index.html` (open in a browser). Redraw everything: `python3.14 -I draw_toss_gum.py` (Pillow).

Mini game: 4 seated birds in a ring (1P left, 2P right, computer birds back and front) on the Gum Fling field.
The carrier picks A = left neighbour, B = across, C = right neighbour (seat + 1, + 2, + 3 clockwise seen from above).

## Files
- `scene_ellipse_1x/3x.png`  layout 1: ellipse ring on the Fling floor as is (turf top line 160)
- `scene_diamond_1x/3x.png`  layout 2: diamond with chalk lines, turf raised to line 128 (turf rows 1 and 2 used twice)
- `toss_arc_3x.gif` (29 frames), `toss_arc_keys_1x.png`
- `fuse_strip_1x/4x.png` (3 stages x 6 frames), `fuse_cues_6x.gif`
- `burst_3x.gif` (52 frames), `burst_keys_1x/2x.png`
- `birds_palettes_4x.png`  1P, 2P, computer 1, computer 2
- `cmp_ingame_vs_toss_2x.png`  in-game Gum Fling (run-up, dusk) beside layout 1

## Reused from the game (no new pixels)
- Sootling frames (breathe, idle, fall, land clips) and the player / computer palettes: `assets/flier/sootling_sheet.*`
- Gum levels 6..16, `pop_large`, the warm and hot cue palettes: `assets/gum/gum_sheet.*`
- Turf and dusk city planes: imported from `../2026-11-18-fling-field/draw_fling_field.py`

## New in this draft
- Hand grids in the script: A/B/C tags (Neo Geo button colours), seat pad with shadow, 1P/2P chips, 9 shred and splat shapes, burst flash, strain ticks.
- Palettes: 2P gold and computer 2 violet (15 colours each, same index order as the sheet); "gummed" = body ramp swapped to gum pinks.
- Motion is simulated (toss: ballistic arc; burst: shreds and the carrier with gravity, drag, bounce, stick; fixed seed 1118).

## Known weak points / open
- The ellipse ring line is computed from the ellipse equation, not hand-placed; needs a hand pass if layout 1 is picked.
- Layout 1: tags of the back and right birds sit over the busy city and read weaker than in layout 2.
- Layout 2 repeats turf rows; the repeat shows as banding.
- Birds only have side-view frames: back and front birds do not face the middle. A front/back view would be new art.
- Burst shreds are small (1 to 6 px); no shadows under flying shreds; splats do not land on other birds.
- No throw or catch pose (thrower hops 2 px, catcher dips 2 px).
- Only the dusk mood is drawn. No tile or sprite budget counted.
