# Backgrounds, final pass (five fixes on v3)

Drafts only. Nothing here is game data. All art is original and drawn by `draw_backgrounds_final.py`
(copy of the v3 script with the five changes below; everything else is unchanged).

Run: `/opt/homebrew/bin/python3.14 -I draw_backgrounds_final.py [--nogif] [--only <mood>] [--nov1]`.
`numbers.txt` and `index.html` are written only on a run without `--only`. About 15 s without GIFs.

## What changed, per item

1. Storm deck hue. The deck anchors are the v2 grey-green values again (`deck` = (8,12,22), (34,50,66), (88,112,120),
   (124,150,150)); the two darkest sky colours (the black mass and the dark behind the deck) use the v2 hue as well.
   The black mass above the play area keeps the v3 outline (`VOID`). Deck luminances are 39 / 68 / 97 / 126
   (v3: 25.5 / 55 / 84.5 / 114), see item 2 for the reason.
2. Storm deck bands and mass edge. The three full-width layers are gone. The deck is now a dark ceiling (`BASE`) plus
   nine closed cloud masses (`MASSES`), each with its own size, height, belly brightness and depth, drawn back to
   front so that they overlap; three of them carry a rim light. The mass edge: a skirt of the darkest deck colour
   (`SKIRT`) lies under the black mass as the intermediate shade, and both edges (black to skirt, skirt to deck) are
   broken into hand cluster strips over 5 px (`fringe`). The black after colour quantisation has luminance about 10,
   so the darkest deck colour had to go up to 39 to keep the step; smallest pair step in the storm sky is 28.8.
3. Sky top band. Two new calm strips (`T`, `U`: long low clusters, no cluster under 16 px) form the top band edge of
   all moods (`SKYSEQ[0] = 'TUtu'`). The shared wobble table is replaced by `EDGEWOBS`: six hand tables with different
   spacing (21 to 32 px), one per band edge, blended by height between two edges (`edge_disp`).
4. Mid material and far facades. `material()` is rewritten with few, large features, drawn counterchanged (dark line
   on the lit wall, light line on the shadow wall): brick courses 4 px (mid A) or 5 px (mid B) with bricks 8 or 10 px
   long and a few lit bricks, panel seams every third window column with a lit edge, stone blocks, 2 px stains.
   Pipes are 2 px wide with a hopper head and wide brackets; apartment floor bands are ledges (lit line plus shadow
   line). Far plane: the roof follows the facade type (apartment flat or stepped, glass slanted wedge, office
   overhanging slab with two masts, deco spire or dome, warehouse sawtooth with a stack), office windows are 2 px
   ribbon bands, deco slits are unbroken, openings use the darkest wall colour and run down to line 118.
5. Moon halo and near streaks. Each halo ring edge is broken into hand cluster strips that run along the arc
   (`HALOPAT`, 5 px wide, pair = neighbouring sky colours, no radial drips); same code for the dusk sun rings.
   Cast light: every near building has its own table `DASHB` (foot height, streak rows, lengths, offsets) and its own
   wobble phase.

## Build notes

- Screen 320 x 224. Planes and sway unchanged: sky still (rows 0..127), far rows 48..127 sway 6 px, mid A rows 88..143
  (tile grid from 80) sway 4 px, mid B rows 112..175 sway 2 px, near rows 128..223 still. Swaying planes are 336 px
  wide (21 tiles), shown from x = 8.
- Build sheets `plane_<mood>_<plane>_1x.png` at true size and full tiling width. Transparent colour: magenta
  255, 0, 255 (asserted not to occur in the art). Sizes: sky 320 x 128, far 336 x 80, midA 336 x 64, midB 336 x 64,
  near 320 x 96 (level 3 lit palette, so the cast-light role is a colour of its own), cloudsfront 320 x 32,
  cloudsback 160 x 32 (period 160), airship 256 x 32 (4 frames of 64), storm: beams 320 x 88 (frame 2 of 5) instead of
  clouds and airship. The sheets hold frame 0 only; animated tiles (windows, beacons, steam) come from the script.
- Palettes (15 colours + transparent each): moon 14, storm 13, dusk 14, plus the lit copies of the near palettes.
- Tiles: moon 892, storm 886, dusk 883 (v3: 894 / 890 / 886).
- Sprites per scanline: flat 67 / 65 / 67, trimmed 58 / 60 / 58 (same as v3).
- Dither pair step, minimum over all planes: moon 29.8, storm 28.8, dusk 29.6. Per plane values in `numbers.txt`.
- Play area lines 16..175, darker than 24 / brighter than 150: moon 6.3 / 5.0 percent, storm 5.2 / 6.8, dusk 3.7 / 6.3.
- Hazard strip lines 192..223: no new detail there.

## Weak points

- Storm deck: the cloud masses are lighter overall than the v3 layers because the darkest deck colour went from 25.5
  to 39. The heavy part is now the black mass and its skirt; the lower deck reads more open than in v3.
- Storm brighter-than-150 share is 6.8 percent (v3 6.7), still under 8 but the highest of the three moods.
- Mid material: readable on the build sheets at 1x, but in the composed scene the near plane, the platforms and the
  windows cover most of the mid walls, so the gain in the scene is small. Brick and seams show best on mid B.
- Far warehouse type has only a few square windows; on narrow buildings it can be confused with the apartment type
  apart from the sawtooth roof.
- Halo edge is ragged at 3x rather than smooth; it is a cluster edge, not a clean ring, by request.
- Top band edge: one detached long cluster per strip repeat remains under the edge (period 220 px).
- The sheets are one frame; the build must take the animation frames from the script, not from the PNGs.
