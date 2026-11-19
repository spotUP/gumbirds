# Final hazard set (draft, input for the ROM build)

Date: 2026-11-10. Draft only: nothing in `src/`, `assets/`, the Makefile or git was touched.

Regenerate everything (about 1 minute, Pillow + numpy):

    /opt/homebrew/bin/python3.14 -I draw_hazards_final.py

The script prints the numbers below, writes them to `numbers.txt`, and rewrites `index.html`.
View `index.html` at 100 percent browser zoom.

## Files

| File | Content |
|---|---|
| `frames_<name>_1x.png` | Build input. 16 frames per row, 64 x 32 px each. Spikes and water: one row (one tile variant). Fire and lava: two rows (row 0 = tile A, row 1 = tile B). |
| `scene_<name>_4x.png` | Frame 2 in the scene, crop x 0..320, y 136..224, 1280 px wide. |
| `anim_<name>_4x.gif` | 16-frame loop in the same crop. |
| `compare_<name>_4x.png` | Fire and water only: before / after, labelled. |
| `zoom_<name>_8x.png` | Fire and water only: 48 x 32 px window where the dither is densest. |
| `numbers.txt` | Script output. |
| `draw_hazards_final.py` | Generator. |
| `hazards_v4_base.py`, `dither_round1.py`, `draw_dither_s6_strong.py`, `dither_visible_base.py` | Unchanged copies of earlier draft scripts (`dither_visible_base.py` = `draw_dither_visible.py`). |
| `fire_v6_base.py` | Copy of `draw_fire_v6.py` with one hook added (`FLAME_FIX`, called before coal bed and embers are drawn). |

The generator reads two files from older draft directories, read-only: `../2026-11-10-hazards-v4/frames_A_1x.png`
(spikes identity check) and `../2026-11-10-hazards-v6-fire/frames_B_1x.png` (fire before / after), plus the scene
backdrop `../2026-11-10-flier/A_v5_scene_3x.png` through `hazards_v4_base.base_scene()`.

## Numbers

Tile counts come from the tile builder (`hazards_v4_base.tile_count`, 16 x 16 px tiles over all 16 frames).
Pair step = luminance difference (0.299 R + 0.587 G + 0.114 B, scale 0..255) between the hard colour and the
colour the dither put in its place, per dithered pixel.

| Hazard | Colours | Tiles raw | Tiles unique | Dither px | Share of opaque | Pair step median | Pair step p10 |
|---|---|---|---|---|---|---|---|
| spikes | 15 | 128 | 47 | 0 | 0.0 % | none | none |
| fire | 11 | 256 | 230 | 4208 | 13.4 % | 33.4 | 31.5 |
| water | 13 | 128 | 100 | 2986 | 14.8 % | 41.8 | 41.8 |
| lava | 14 | 256 | 256 | 9350 | 20.5 % | 31.4 | 30.8 |

Asserted by the script: p10 >= 28 wherever dither exists; spikes sheet pixel-identical to the v4 sheet (dither count
0, same as v4); silhouette of every frame unchanged by the dither; no colour added by the dither; white fire core
untouched by the dither; fire gap >= 2 px; every PNG except the frame strips at most 1400 px wide.

Extra layers outside the tile palettes:

- Water lurker sprite (own 8-colour palette, unchanged from round 3 V2): 771 dither px per loop, pair step 41.4.
- Lava cast light (3 colours in the city palette): 13048 dither px per loop, pair step 33.7.
- Fire cast light (same 3 colours as lava): 13111 dither px per loop, pair step 33.7.

Fire gap (height difference between the two tallest tongues, per frame):

- Shapes, hard: minimum 2. Per frame 8 9 2 4 7 11 8 2 10 9 3 5 9 8 3 4.
- As drawn, dithered: minimum 2. Per frame 8 9 2 4 7 11 8 2 10 9 3 5 8 8 3 4 (frame 12 goes from 9 to 8).
- v6 sheet: minimum 2, same per-frame values as the hard shapes. Tallest tongue per frame is identical in all three.

## Palettes (RGB; `*` = slot not used by the tile frames)

- spikes: o(12,10,26) D(30,34,84) d(58,66,128) m(112,130,192) l(172,192,232) h(228,240,255) w(255,255,255) a(64,224,255) y(250,200,44) Y(198,108,28) g(74,68,112) R(255,62,54) r(104,22,44) s(255,150,60) A(112,92,255)
- fire: o(30,6,24) c(56,20,44) C(104,44,60) a(176,104,92) S*(40,26,62) s*(86,54,92) M(120,12,70) D(196,32,44) r(240,70,36) O(252,122,30) y(255,176,46) Y(255,222,84) w(255,252,222)
- water: o(4,4,26) n(28,44,120) u*(30,44,128) b(28,102,188) B(50,154,224) T(76,214,216) c(150,244,250) f(214,250,255) w(255,255,255) p(46,28,74) P(112,96,156) q(188,180,220) W(70,206,120) x(18,112,98)
- lava: o(18,4,18) k(74,24,42) K(128,52,54) Q(196,112,84) H(246,190,140) V(88,54,100) G(184,60,30) m(36,0,44) P(110,12,58) D(184,32,36) r(232,62,28) O(250,116,24) y(255,186,48) Y(255,246,184)

Fire and water each have free slots (fire: S and s are unused, 11 of 15 in use; water: u is merged into n).

## What changed versus the sources

**Spikes.** Nothing. Hazards v4, no dither, as decided.

**Water.** Palette V2 from the dither-visible round, unchanged. Two changes:
1. Dither extent is the full band (`EXT['water'] = 'H'`) instead of the half band: 2986 px instead of 2424 px.
2. The threshold map is new. Before: ripple dashes (read as texture, not dither). Now: an exact 1 px checker at
   50 percent, thinned or filled in the order of the old ripple-dash map, so the fall-off still runs along the
   ripples. A 2 x 1 brick variant was rendered and rejected: it read as dashes again.

**Lava.** Palette V1, half band, crust anchored to the grid, cast-light fade: all exactly as in the dither-visible
round. The numbers reproduce that round (9350 px, 31.4 / 30.8, 256 tiles; cast light 13048 px, 33.7).

**Fire.** v6 shapes and motion. Four changes:
1. Palette: the three cool flame shades are re-spaced. v6 had M(96,8,60) D(150,16,40) r(226,44,36), luminance steps
   M-D 18.6, D-r 38.7, r-O 52.9. A dither between M and D would have broken the 28 rule, and r-O was far above the
   30 to 34 target. Now M(120,12,70) D(196,32,44) r(240,70,36); ramp steps M D r O y Y w are 31.5 34.5 33.4 34.4
   31.3 33.3. O, y, Y, w are the v6 colours.
2. Dither: checker between neighbouring flame bands in rows 0..24, full band. The white core `w` is not in the
   ramp and is never dithered. The coal bed (rows 25..31) and the embers stay hard.
3. Remnants: detached flame pieces of 1 or 2 px are removed. Three found, 1 px each: frame 3 (x 84, y 11, tile B),
   frame 11 (x 41, y 2, tile A), frame 12 (x 86, y 9, tile B). These 3 px are the only silhouette change.
4. White islands: a white core that does not reach the coal bed is recoloured to yellow `Y`. Four found: frame 5
   (23 px, x 9..11), frame 8 (5 px, x 85..86), frame 9 (7 px, x 39..40), frame 14 (19 px, x 36..39, y 12..18).
5. Cast light: now drawn with the dithered fade and the lava V1 light colours (v6 had a hard edge).

Versus the v6 sheet, before dither: 57 px changed in 16 frames, 3 of them silhouette. Tongue shapes, heights and
leader motion are unchanged.

## Weak points

- **Fire fixes do not match the reported defects exactly.** The report said "1 px remnant in tile B about frame 6":
  no remnant exists at frame 6; the nearest are frame 3 and frame 12 (both tile B), removed. The report said "white
  core blob at x 39, frames 4-6, 12, 13": frames 4-6 hold no white at x 28..50 above the coal bed. The white at
  x 35..41 in frames 7, 8, 10, 11, 12, 13 is a core attached to the bed and is NOT changed. Only the detached ones
  (frames 9 and 14 at x 36..40) are. If the frame 12 / 13 core itself is the defect, it is still there.
- **Fire palette retune was not asked for.** It is the only way to dither the outer bands inside the 28 rule
  without a new colour, but the outer flame (M, D) is visibly brighter and redder than v6. The low flame band
  between the tongues now reads as a brighter red belt.
- **Fire tile count is high:** 230 unique of 256 raw. Dither does not help tile reuse.
- **Lava uses 256 unique of 256 tiles** (unchanged from the dither-visible round): no reuse at all.
- **Fire gap in frame 12 drops from 9 to 8** as drawn, because the D-r dither moves the hot edge by one row. The
  minimum stays 2.
- **Water at 1x:** the checker is visible as a fine grain in the mid band; it is plainly dither at 4x. On a real
  CRT the 1 px checker may blend more than it does on an LCD. Not tested on hardware.
- **Water dither covers 14.8 percent** of the opaque pixels: it sits on the band edges, not on the whole body.
- **Backdrop** is the plain v4 flier scene, not the new backgrounds. Cast light and contrast were only judged
  against that backdrop.

## Dither visible at 1x

- spikes: none, as decided.
- fire: yes.
- water: yes.
- lava: yes.

## What was viewed and what was not

Viewed: frame 2 at 1x (strip crop) and 4x for water, fire and lava; fire frame 14 at 4x; the water brick
alternative at 4x; `compare_fire_4x.png`; `compare_water_4x.png`.

Not viewed: any GIF in motion (no frame other than 2 for water and lava, 2 and 14 for fire); the spikes output
(verified pixel-identical to v4 by the script only); `zoom_*_8x.png`; `scene_*_4x.png`; the frame strips;
`index.html` in a browser; anything on a CRT or in MAME.
