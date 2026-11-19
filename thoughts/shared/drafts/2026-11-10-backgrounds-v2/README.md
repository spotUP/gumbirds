# Bubblegum Brawl backgrounds, draft round 2 (fix pass on v1)

Drafts only. Nothing here is game data. Open `index.html` and view at 100 percent browser zoom.

Generator: `draw_backgrounds_v2.py` (copy of the v1 script, edited). Run with
`/opt/homebrew/bin/python3.14 -I -B draw_backgrounds_v2.py [--nogif] [--only moon,storm,dusk] [--nov1]`.
`numbers.txt` and `index.html` are written on a full run only. `--nov1` skips the v1 play-area lines (they need the v1 script next to this directory).

Files per mood (moon, storm, dusk): `compare_<mood>_2x.png` (v1 left, v2 right), `anim_<mood>_3x.gif`,
`scene_<mood>_3x.png`, `scene_<mood>_1x.png`, `planes_<mood>_2x.png`.

## What changed, fix by fix

1. Near rooftop walls. The noise dither and the cast-light noise dither are gone. Each of the four rooftops has its own
   drawn material: brick courses, panel seams with bolts and stain drips, riveted metal sheets with louvre vents, brick piers.
   The cast light is drawn in the tiles as six ordered meshes (full, 3/4, 1/2, 1/4, 1/8, 1/16), each a subset of the one below,
   with hand-set wobble on every band edge (table `WOB`). The palette level is now one per 16 px column for the whole
   height, so no level step crosses a tile row and the line at y 176 is gone. Near dither pixels 12173 -> 4183.
2. Sky. Band edges come from three hand-authored cluster strips (`STRIPS` A, B, C: cumulus tops, stratus streaks, lumps with
   flecks), placed per edge by a hand-set sequence (`BANDSEQ`). No seeded noise and no ordered matrix in the sky.
   The sky ramps have 5 / 5 / 6 shades (v1: 4) about 30 apart. The violet horizon in moon is kept.
3. Flier and bubble contrast. Value design in `MOODS[...]['val']`, `skyl`, `deckl`: large wall shapes sit above luminance 24,
   only outlines and small details go darker; unlit glass is lifted; far haze is lighter. Dusk: smaller sun (radius 24 -> 22),
   weaker halo, sun bands at 214 / 180 / 148, near rim light capped at 148. Storm: search beams at 147.
4. Facades. Five hand-designed types (apartment grid, office ribbons with roof sign, deco piers with neon blade sign,
   brick warehouse with painted wall sign, curtain glass with reflection bands), assigned by hand in `FAR`, `MIDA`, `MIDB`
   so that neighbours differ. Far skyline: flat shadow face and lit face per tower, rim light on the side that faces the
   moon or sun (towers right of x 262 are lit from the left), haze toward the base with one hand-drawn cluster edge.
5. Storm sprite budget. Rain is 2 full columns plus 6 columns with a gap over lines 80..143 (v1: 3 plus 7, gap 80..159).
   Both search beams and the lightning are kept.

## Numbers, v1 against v2

Sky dither, median / minimum pair step (luminance of 255):

| mood  | v1 dither px | v1 median / min | v2 dither px | v2 median / min |
|-------|--------------|-----------------|--------------|-----------------|
| moon  | 18703        | 37.2 / 29.4     | 14498        | 29.9 / 29.8     |
| storm | 16762        | 58.0 / 35.1     | 20307        | 30.1 / 29.8     |
| dusk  | 19134        | 62.4 / 30.3     | 12023        | 30.0 / 29.6     |

Other planes (v2 dither px, median / min per mood moon, storm, dusk; v1 in brackets):

- far: 4279 px (7571); 32.4, 41.4, 33.7, median equals minimum (v1 33.4, 44.1, 58.5)
- mid A: 4759 px (7979); 44.7 / 30.1, 50.4 / 30.1, 74.6 / 31.1 (v1 52.3 / 31.1, 59.8 / 32.9, 76.4 / 32.9)
- mid B: 5780 px (7054); 32.9 / 28.6, 35.7 / 28.8, 59.2 / 30.3 (v1 44.9 / 30.0, 49.1 / 30.5, 59.6 / 30.7)
- near: 4183 px (12173); cast-light pair 30 / 42 / 54 at palette level 1 / 2 / 3 (v1 at level 2: 72.1, 94.8, 78.3)
- clouds and airship: unchanged from v1

Play area, lines 16..175, frame 0 without fliers and islands. The v1 column is the v1 script measured on the same lines:

| mood  | v1 darker than 24 | v2 darker than 24 | v1 brighter than 150 | v2 brighter than 150 |
|-------|-------------------|-------------------|----------------------|----------------------|
| moon  | 19.4 %            | 6.3 %             | 4.9 %                | 5.0 %                |
| storm | 22.1 %            | 5.2 %             | 7.5 %                | 6.7 %                |
| dusk  | 7.4 %             | 3.7 %             | 15.9 %               | 6.9 %                |

Scenery sprites per scanline, worst line:

| mood  | v1 (flat count) | v2, same flat count | v2, trimmed count |
|-------|-----------------|---------------------|-------------------|
| moon  | 63              | 67 (lines 80..87)   | 58 (128..143)     |
| storm | 66              | 65 (lines 112..127) | 60 (128..143)     |
| dusk  | 63              | 67 (lines 80..87)   | 58 (128..143)     |

Tiles and palettes: unique tiles 892 / 893 / 886 (v1 925 / 905 / 911); animated tile positions 130 / 118 / 125
(v1 132 / 120 / 127); palettes 14 / 13 / 14 plus lit copies (v1 11). Sky palette 11 / 8 / 12 colours (v1 10 / 6 / 10).
GIFs: moon 2.00 MB, storm 2.69 MB, dusk 2.10 MB. `numbers.txt` holds the full per-plane lines.

## Weak points, honestly

- The storm sprite figure of 60 rests on a new counting method. v2 counts each column sprite only over the tiles that show
  in some frame of the loop ("trimmed"). With the v1 method (every plane full width over its whole height) v2 storm is 65,
  one below v1, and moon and dusk rose from 63 to 67, because mid plane A now starts on the tile row at line 80 (v1: 88).
  The trimmed count is how the hardware would be used (sprite height is set per sprite), but it has not been proven on
  hardware or in MAME. 60 is also exactly the limit: no margin.
- Palettes rose from 11 to 13 or 14 per mood: the facade signs and the new near materials push mid A, mid B and near to
  three palettes each (v1: two).
- The storm lost some menace. Lifting the darks for flier contrast makes the cloud deck and the walls greyer; v1 was darker
  and moodier. The scalloped, repetitive deck shape from v1 is still there.
- The play-area shares pass with small margins in places: moon darker share 6.3 %, dusk brighter share 6.9 %, storm 6.7 %.
  They are measured on frame 0 only, without the lightning flash, and the limits 24 and 150 are luminance proxies, not a
  test with the real flier sprites.
- Sky cluster strips are stretched vertically where the gradient is slow. At the top of the dusk and moon skies this gives
  a row of pointed teeth that looks regular. The moon halo edge has drip shapes under the disc. Only three strips exist,
  so repeats can be found by looking for them.
- The dusk sun is smaller and paler than in v1, and its bands and slits are faint at 1x.
- The cast-light fade on the near walls is an ordered mesh. It is deliberate and crosses tile rows without a line, but at
  3x the checker reads as a pattern rather than as soft light.
- Mid planes A and B keep the v1 streak dither for the wall gradient and haze (fewer pixels than v1, same method). Only the
  far plane got the hand-drawn haze edge.
- Facade types differ clearly on mid B; on the far plane (1 px windows) the difference is mostly in rhythm and is subtle
  at 1x. Facade lighting in the new types is static (no flickering TV windows there).
- Rain is thinner over lines 80..143; the GUM sign is clearer than in v1 but the rain reads less dense in the middle band.
- Still about 890 tiles per mood, greedy palette packing, drift in the GIFs faster than in the game: unchanged from v1.

## Not viewed

- None of the three GIFs was viewed; only the decode check (4 frames each equal to the source frames) and the sizes.
- `planes_<mood>_2x.png`: not viewed in v2.
- `compare_moon_2x.png` and `compare_dusk_2x.png`: not viewed (the storm compare was).
- `scene_storm_1x.png`: not viewed. Moon and dusk were viewed at 1x and 3x, storm at 3x and in the 2x compare.
- The final dusk still after the last change (near rim light capped at 148) was viewed at 1x only.
- `index.html` was not opened in a browser.
- Lightning flash frames and palette levels 1 and 3 of the cast light were not viewed as stills.
