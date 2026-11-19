# Stadium background for the ground party events - draft 2026-11-18

Drafts only, no game code. Gallery: `index.html`. Numbers: `numbers.txt` (written by the script from the tiles it drew).
Rebuild: `/opt/homebrew/bin/python3.14 -I draw_stadium.py` (add `--nogif` for a fast run).

## What is here

- `plane_<mood>_{sky,far,near,grass}_1x.png`, `plane_{moon,storm}_cones_1x.png`, `plane_storm_rain_1x.png` (magenta = transparent).
- `scene_<mood>_2x.png`: composed scene, idle frame 0, with the player and rival frame 0 of the flier sheet on the grass.
- `<idle|cheer|wave|win>_<mood>_3x.gif`: 12 GIFs, 70 ms per frame.
- `sheet_cells_4x.png`: every hand cell.

Layout (screen rows): sky 0..63 behind, floodlight towers 0..31, roof 32..47, far crowd 48..79 (4 rows of 8 px birds),
balcony front with team banners 80..95, near crowd 96..143 (3 rows of 16 px birds), barrier boards 144..159, turf 160..223.
Far and near planes are 336 px wide (21 tiles), shown from x = 8, same as the swaying stage planes.
Left half = Player 1 blue, right half = Player 2 yellow: shirts, banners, boards, confetti.

## Frame counts

| Animation | Frames | Typed steps |
|---|---|---|
| Idle bob and chatter | 16 (8 steps, 2 frames each) | 3 near types, 8 phase offsets from a typed table |
| Cheer burst | 64 (Player 1 half at frame 6, Player 2 half at frame 36) | 17 / 13 / 11 steps per type: crouch, rise, flutter at the peak, fall with wings up, land squash, rebound; 12-piece confetti bursts, 28 frames life |
| Stadium wave | 64 | 9 steps, delay = column x 2 + row lag + phase bit; far tier joins 4 frames later |
| Win wave | 64 | winning half repeats the wave every 16 frames plus 8 confetti bursts, losing half slumps |

Hand cells: near 3 types x 6 poses (sit, beak open, squash, wings mid, wings up, wings up narrow) + umbrella + empty seat + stairs;
far 2 types x 4 poses + umbrella; structure: roof, roof lamp, balcony front, banner, board + 9 letters, tower head, mast, rain tile, 3 cone dither patterns.

## Budget (see numbers.txt for the full table)

- Dusk and moon: 110 unique 16 x 16 stand tiles for all four animations (structure 19, near crowd 35, far crowd 57) + 4 tower tiles.
- Storm: 194 (far crowd grows to 138 because umbrellas sit inside the 4-bird far tiles). Sky and turf add 0 tiles (reused sheets). Cones 9 tiles per mood, rain 1, confetti 4.
- Palettes per mood: 6 near crowd + 6 far crowd + 4 structure + turf + cone + rain = 19.
- Sprites per scanline, stadium only: at most 55 (moon) and 66 (storm) of 96. The stadium replaces the city planes.

### How the crowd animates on Neo Geo - cost per method

| Method | Cost | Verdict |
|---|---|---|
| Sprite strips + CPU tile swap (one SCB1 tile word per changed cell) | near 50 bird cells + far 36 tiles = at most 86 VRAM words per animation step (step = 2 frames at idle); ROM 110 / 194 tiles | Use for cheer, wave, win |
| Hardware auto-animation (8 frames, global counter) | 0 CPU; ROM 8 slots per distinct sequence: near 22 x 8 = 176, far 27 x 8 = 216 (storm 256), about 390 to 430 slots, most of them repeats of the same picture | Use for idle only if the ROM room is there; else CPU swap of 86 words every second frame |
| Palette cycling | 15 words per palette, 12 crowd palettes = 180 words per step; poses must live in colour indices, so each bird drops to 3 or 4 colours | Reject for motion. Good for camera flashes and lamp flicker (1 palette, 2 words) |
| Per-column sprite Y lift (1 SCB3 word per column) | 21 words per step | Add-on for the wave only; lifts the whole column, seats included |
| Fix layer | 8 x 8, no scroll, drawn on top of the players | Reject |

Recommendation: both stand planes as sprite strips. Idle through CPU tile swap on a 2-frame tick (86 words, well under 1 percent of a frame);
cheer, wave and win through the same swap table with the typed sequences; confetti as up to 12 one-tile sprites; flashes by palette.
Auto-animation is the fallback if the tick ever costs too much.

## Honest notes: what is computed, not typed

- Straight edges of the floodlight cones (fill is 3 typed dither patterns).
- Far-plane palettes: the hand-picked palettes mixed 20 percent toward a haze colour (outline, white, lamps excluded).
- Confetti flight: typed start velocities, then gravity, drag and a sine flutter.
- Bob and jump: whole-pixel shifts of the typed cells.

## Open weak points

1. Team colour reads mainly from boards, banners and confetti; the shirt strip on each bird is 2 rows. Seat backs in team colour would be stronger.
2. Far dither steps `ab` and `bc` at dusk are 32, close to the 28 floor.
3. Storm far crowd costs 138 tiles. Cheaper: put far umbrellas only in whole tiles (4 umbrellas per tile).
4. Roof is a flat band with a truss zigzag; no depth, no scoreboard, no big screen.
5. Dusk has no light effect of its own (lamps off, no sun rim sprite); the warm rim is in the palette only.
6. Stand period is 336 px with the team split at the centre. Gum Fling scrolls a 512 px field: the split then drifts; needs a decision.
7. Board letters hide behind the players at the centre; letters are 5 x 7 block capitals, plain.
8. Cheering uses jump heights of 1 to 2 px near and 1 px far (cell height limit). Larger jumps need the bird to cross into the row above (2 tiles per bird).
9. Far tier moves as whole tiles in events (4 birds together) to hold the tile count.
10. Not tested on hardware or in MAME; sprite and VRAM numbers are from the layout, not measured.
