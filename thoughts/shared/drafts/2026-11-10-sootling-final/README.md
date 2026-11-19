# Sootling final (32 x 48, 63 frames)

Art files only. No game code changed. Nothing committed.

## What this is

The final pixel-art pass for the flier "Sootling" after the user verdict on takes A and B:

- Body of take A (wide soot ball) with the two white eyes of take B. Cap and goggle are gone, the soot head shows.
- Gum is solid candy: full dark keyline, smooth bands, rim light, one fixed specular stamp. No checker, no dither mesh, no window.
- Body is five hand-authored pixel maps (squash 26 x 17, in-between 25 x 18, rest 24 x 19, in-between 23 x 20,
  stretch 22 x 21; area 361 to 385 px, within 4 percent of rest). Bottom keyline on row 45 in every pose, feet on
  row 47, hit box columns 14..17.
- Pops use one outlined gum rope and outlined droplets (2 x 2, then 1 x 2). Fragments under 6 px are removed.
- Fall has 10 frames (draft had 6).

## Run

```
/opt/homebrew/bin/python3.14 -I draw_sootling_final.py          # everything
/opt/homebrew/bin/python3.14 -I draw_sootling_final.py --nogif  # skip the GIFs (fast)
```

The script imports the draft generator `../2026-11-10-sootling-b-32x48/draw_sootling_b.py` (wing, springs, lobe
layout, neck chain, statistics, GIF writer) and reads the backdrops from `../2026-11-10-backgrounds-final/`.
It writes only into this folder.

## Files

| File | Content |
|---|---|
| `sootling_final_sheet_1x.png` | 63 frames, 8 columns x 8 rows, row-major, indexed, index 0 = magenta 255,0,255 = transparent, player palette |
| `sootling_final_sheet_cpu_1x.png` | same indices, computer palette (preview of the swap) |
| `frames.json` | per animation: name, first frame, count, ticks per frame at 60 Hz, loop; both palettes as RGB lists |
| `anim_<name>_4x.gif` | each animation at 4x on the three moods, both palettes |
| `contact_<name>_4x.png` | every frame of each animation side by side (used for the frame-by-frame check) |
| `scene_<mood>_2x.png` | 8 fliers on dusk, moon, storm |
| `sheet_both_3x.png` | both palettes, 3x |
| `numbers.txt` | colours, tiles, dither, outline steps, body size, motion before and after (script output) |
| `index.html` | gallery page |

## Frame order

| Animation | First | Count | Ticks | Loop |
|---|---|---|---|---|
| flap2 (two lobes) | 0 | 8 | 4 each | yes |
| flap1 (one lobe) | 8 | 8 | 4 each | yes |
| pop2 (first pop, pull-round) | 16 | 12 | 3 3 3 4 4 5 5 5 5 6 6 6 | no |
| pop1 (last pop) | 28 | 10 | 3 3 3 4 4 5 5 5 6 6 | no |
| inflate (respawn) | 38 | 14 | 5 each | no |
| fall | 52 | 10 | 4 each | yes |
| idle (no gum) | 62 | 1 | 60 | yes |

The draft split was pop1 12, inflate 16, fall 6. The fall got 4 more frames; pop1 and inflate gave 2 each so the
total stays 63.

## Palette

Index 0 transparent. Indices 1..15: keyline 1, soot fur 2..5 (dark to light), rim and eye white 6, ember 7..9,
gum 10..14 (10 = deep line), white 15. The computer palette changes indices 1..14; index 15 is the same.
All channels are 5-bit values expanded to 8 bits. RGB lists are in `frames.json` and `numbers.txt`.

Gum deep line (index 10) was lifted against the draft (player #6c1080, computer #085040) so that every colour right
inside the keyline is at least 24 above the darkest 5 percent of each sky.

## Animation fix pass (2026-11-10)

User verdict on the previous gallery: "the animations that are cut in the middle of the body looks a bit choppy".

### What was choppy

The cause was not a tile seam. The old body was one map. Squash and stretch were made by doubling or deleting map
row 16 (frame row about 41). Everything above that row jumped 1 px; the belly and feet below it stood still. The
jumps came on some frames only; the frames between did not move.

| Animation | Frame pairs with the fault | Fault |
|---|---|---|
| flap2, flap1 | 1>2, 2>3, 4>5, 5>6, 6>7 | row doubled or deleted; upper body jumps 1 px, lower body holds |
| flap2, flap1 | 4>5 and 6>7 | whole sprite lifted 1 px on frames 4 to 6; with the row trick the head drops 2 px at 6>7 |
| flap2, flap1 | 0>1, 7>0 | no motion (1 and 2 silhouette pixels) next to jumps of 31 to 90 |
| flap2, flap1 | 3>4 | wing angle jumps 60 degrees (computed wing, angles 34 62 70 22 -38 -52 -30 4) |
| pop2, pop1 | 0>1, 2>3, 3>4, 4>5, 5>6 | row trick; frames 6 onward frozen |
| inflate | 1>2, 3>4, 8>9, 9>10, 11>12 | puff toggles one row on and off; frames between frozen |
| fall | 2>3, 4>5, 7>8, 9>0 | tuft and feet switch between two states; frames between frozen |

Other faults fixed in this pass: the far eye read as a letter C; the second lobe of the respawn looked like a bow
for frames 7 to 9; the surviving lobe had a flat cut edge in pop2 frame 1; the computer ember dark (index 7) was
too close to the dusk sky.

### What changed

- Five hand-drawn body poses (`POSES`: S, S1, R, T1, T). No pose is made from another by a row operation. The
  script asserts a closed keyline, equal volume (4 percent) and that the darkest fur never touches the keyline.
- Every body step goes between two neighbouring poses (asserted in `follow`). The bottom edge never moves.
- Flap: pose sequence S1 S S1 R T1 T T1 R, one step per frame. No whole-sprite lift. Eight hand-drawn wing
  stamps (`WINGS`), root pinned at (11, 36).
- Follow-through (`follow`): eyes sit one frame late, left tuft reacts to the top of the ball, right tuft one frame
  later, near foot one frame late, far foot two frames late.
- Pop: flinch, recoil, settle through the poses. Respawn: blow (wide) and breathe in (tall). Fall: the body holds
  the long pose; a wave runs up each tuft, the wing flutters, the feet kick in turn.
- Far eye: 5 px wide, pupil in the middle column. Respawn second lobe grows out of the flank of the first lobe
  (`bud`). Torn membrane: pixels inside the survivor's own ellipse stay (round outline).
- Computer palette index 7 is now (16, 66, 107), luminance 56; step against the dusk sky p5 (25) is 31.
- Frame counts per animation are unchanged (63 total, no frames moved).

### Before and after (body layer: fur, eyes, wing, feet; silhouette pixels changed per frame pair)

| Animation | Before: largest, smallest | After: largest, smallest | Whole-body displacement over 1 px |
|---|---|---|---|
| flap2, flap1 | 90 at 6>7, 1 | 58 at 0>1, 40 | before 6>7 by 2 px; after none |
| pop2 | 56 at 4>5, 0 | 51 at 2>3, 0 (last pair, at rest) | none, none |
| pop1 | 60 at 4>5, 0 | 51 at 2>3, 18 | none, none |
| inflate | 34 at 1>2, 0 | 52 at 5>6, 0 (pair 0>1 only) | none, none |
| fall | 24 at 2>3, 0 | 22 at 3>4, 5 | none, none |

All pairs are in `numbers.txt`. The largest change did not drop much, and for inflate it went up: the gain is that
the change is now nearly the same on every frame and is spread over the whole outline, not stacked above one row.

## Motion check

Every animation was viewed frame by frame on contact sheets at 4x. The script measures the body layer per frame
pair (`motion()`), and the old numbers are kept in `BEFORE` and `BEFORE_PAIRS`.

## Weak points

Same list as `WEAK` in the script and on `index.html`:

- A step between two poses moves 40 to 58 silhouette pixels. It is even now, but not sub-pixel smooth at this size.
- Flap is still 8 frames; a softer beat needs more frames and the sheet has no free slot.
- Fall holds one body pose and can read as stiff.
- Fur ticks are scaled from the rest pose into each pose, not redrawn per pose.
- Respawn frames 0 and 1 show the same body; the two lobes read as one lumpy bubble until frame 10.
- Pop frame 1: the torn lobe is still a ragged rule-made shape.
- Bubble bands are rule-based; tile cost is high (294 unique of 341); the blue player body is close to the
  moon-mood buildings; the keyline alone does not separate from the darkest sky.
- The GIFs were not judged in motion by a person in this pass; only contact sheets and numbers were checked.

## Page design

Dark slate page, system sans headings in plain white, square bordered table, no accent colour.
