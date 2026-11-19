# Dither variants on hazards v4 (test for the user to pick from)

Date: 2026-11-10. Drafts only, no game code. Open `index.html` at browser zoom 100 percent (any other zoom blurs dither).

Same art as `../2026-11-10-hazards-v4/` (water C, lava D, spikes A, and the sky of the draft scene). Fire is not
included. Shapes, physics, animation, timing and palettes are the v4 ones: `hazards_v4_base.py` is an unchanged
copy of `draw_hazards_v4.py`, used as a library. `draw_dither_variants.py` only redraws the transition between two
NEIGHBOURING shades of one material ramp. Outlines, rim lights, foam white, stripes, weed and every shade step that
skips a shade stay hard. Shapes thinner than 3 px (caustics, glints, cracks) are left alone.

Run: `/opt/homebrew/bin/python3.14 -I draw_dither_variants.py` (about 30 seconds). `--check DIR` writes only the
comparison sheets into DIR.

## Files

- `compare_<C|D|A|sky>_3x.png`: reference + six styles at 3x, last cell all seven at 1x (cabinet size).
- `anim_S<n>_<K>_4x.gif`: 16 frame loop, 128 x 112 px window at 4x. S0 is the undithered reference.
- `scene_S<n>_<K>_3x.png`: full screen at 3x. `frames_S<n>_<K>_1x.png`: build-input style frame strip at 1x.

## How the dither follows form

For each pair of neighbouring shades the script measures the distance of every pixel to the boundary between the
two. The v4 cel bands already follow the simulated form and the light, so the dither zone does too. The zone is
capped at a third of the local band thickness, so thin bands keep a solid core. The style then decides which of the
two shades each pixel in the zone gets. Sky: the two flat band edges are lifted by a hand-set profile (one value
per 16 px column) into uneven haze banks before dithering.

## Styles

1. Sparse transition. A one pixel row of alternating pixels on the dark side of each edge, interrupted by a
   hand-set 16 x 16 break mask (runs of 3 to 5, then a gap); on water, melt and sky a second row of single stray
   pixels. Works: steel, crust, rocks, any sprite; nearly free. Fails: too quiet to soften sky or deep water;
   at 1x it is close to the reference.
2. Checker blend bands. A 50 percent checker zone between each pair, 2 px each side on water and melt, 1 px on
   small parts, 3 px on sky. Works: lava glow and water on a CRT, where the checker fuses to an in-between shade.
   Fails: on a sharp screen it reads as mesh; heavy on the blades; the widest zones start to look like a filter.
3. Graded pattern. Ordered 4 x 4 steps: 25 percent, 50 percent, 75 percent, one row each (three rows each on sky).
   Works: sky and calm large areas, the smoothest result. Fails: the regular dot lattice looks mechanical on small
   shapes; hazard bands are too thin (2 to 5 px) to show all three steps everywhere.
4. Clustered by material. Hand-placed threshold maps per material: staggered ripple dashes for water, irregular
   blobs for melt, grit stipple for crust and rock, vertical brushed grain for steel, long soft streaks for sky.
   Works: dither doubles as texture; sky gets small cloud shapes. Fails: busiest style; on fast water the dashes
   compete with the wave motion.
5. Line and hatch. Horizontal line dither on sky, water and melt (1 of 4, 2 of 4, 3 of 4 rows), diagonal hatch on
   steel, opposite diagonal on crust and rock. Works: scanline haze on sky, calm in motion (lines do not move
   sideways). Fails: horizontal lines flatten the curved wave and convection shapes; lava reads as striped.
6. Mixed by material (recommended). Steel, crust, rock: style 1. Water: style 4 ripple dashes. Melt: style 2
   checker. Sky: style 3 graded. Foam: no dither. Sprites stay crisp, glow blends, large calm areas get the
   smooth pattern.

## Recommendation

Style 6. Characters, steel and crust are small, high-contrast shapes: any dither wider than a broken edge eats
their form, so they get style 1. Emissive melt gains most from checker blending. Sky is the only truly large
surface and the only place the graded pattern has room. Water takes the ripple dashes because they read as surface
texture. If one single style must cover everything, take style 1 for sprites and accept style 3 for backgrounds;
that pair is what most Neo Geo games do.

## Numbers (from the script output)

No style adds a colour (asserted). Palettes stay 15 + transparent. Unique 16 x 16 tiles over the 16 frame loop:

| Hazard | v4 | S1 | S2 | S3 | S4 | S5 | S6 |
|--------|----|----|----|----|----|----|----|
| Water (128 raw) | 99 | 99 | 100 | 99 | 100 | 102 | 100 |
| Lava (256 raw) | 256 | 256 | 256 | 256 | 256 | 256 | 256 |
| Spikes (128 raw) | 47 | 47 | 47 | 47 | 47 | 47 | 47 |

Dither costs almost no tiles here because v4 already has little reuse left: every lava tile is unique, and in water
and spikes the tiles that repeat are the ones whose content is identical before and after dithering. This will
not hold for static backgrounds built from repeating tiles; grid-anchored patterns with a period that divides 16
keep those reusable, shape-following zones do not.

## Anchoring and seams

- All patterns have a period that divides 16 and are anchored to the 16 px tile grid (water, melt, crust, rock,
  sky, sleeves, rail). A pattern pixel never slides; only the zone moves. No crawl inside a zone.
- Spike blades and shafts: pattern y is measured from the piston tip, so the dither rides with the blade.
- Asserted per style and hazard: no new colours; transparency unchanged; a tile dithered alone equals the same tile
  inside a doubled strip (seam in x); for water and lava a one tile shift of the art shifts the result by one tile;
  the wrap step 15 to 0 changes no more pixels than an ordinary step (loop in time). Each frame depends only on its
  own v4 frame, so the loop closes exactly as v4 does.

## Weak points

- Hazards are 32 px tall with bands of 2 to 5 px: the styles differ clearly on lava and sky, less on water, and
  only slightly on the spikes. Judge the spikes in the 4x GIFs.
- Sky colours are very close in value, so sky dither is subtle on purpose; a real sky ramp needs more shades.
- Lava crust plates drift, their dither is grid-anchored: single pixels on a plate can change as it moves (styles
  1 and 6 keep this to an edge row).
- The lurker sprite and the scene light on buildings are not dithered. Fire is not covered.
- GIF motion was not viewed by the author (stills at 3x and 1x only).
