# Backgrounds, draft round 1 (2026-11-10)

Drafts only. Nothing here is game data. Open `index.html` and view at 100 percent browser zoom.

Regenerate everything:

```
/opt/homebrew/bin/python3.14 -I draw_backgrounds_v1.py            # all files, about 1 minute
/opt/homebrew/bin/python3.14 -I draw_backgrounds_v1.py --nogif    # stills, plane sheets and numbers only
/opt/homebrew/bin/python3.14 -I draw_backgrounds_v1.py --only moon --nogif
```

The script reads the hazard frame sheets from `../2026-11-10-dither-s6-strong/` (water M, lava M, spikes H).
`numbers.txt` holds the full printed numbers of the last complete run.

## Files

- `scene_<mood>_3x.png`, `scene_<mood>_1x.png`: full 320 x 224 scene, all planes, 3 placeholder islands, 5 placeholder fliers, hazard strip.
- `planes_<mood>_2x.png`: each plane alone, labelled, plus the near plane with its cast-light palettes.
- `anim_<mood>_3x.gif`: sway, drift, tile loops, cast light, seamless loop.
- Moods: `moon` (clear night, water), `storm` (rain, search beams, lightning, spikes), `dusk` (low sun, lava).

All three moods use the same city tiles. A mood is a palette set, its own sky plane and one extra (clouds and airship, or beams and rain).

## Planes (back to front)

| Plane | Lines | Motion | Holds |
|---|---|---|---|
| Sky, tiles | 0..111 shown (drawn to 127) | still | 4-shade ramp with hand-cluster dither bands, cloud-shaped wisps, moon with craters and halo (moon), sun disc (dusk), baked cloud deck (storm), stars with 4-frame twinkle |
| Clouds | 20..46 and 56..74 | drift, two speeds | cel clouds with lit rim, dithered body, 4-frame trailing wisps. Not in storm |
| Search beams (storm only) | 0..79 | 8-frame swing | two checker-mesh beams behind the far skyline |
| Far skyline | 48..127, opaque from 112 | sway 6 px | towers, spires, dome, dot windows, antenna blinkers, haze dither at the base |
| Airship (moon, dusk) | about 52..88 | crosses the screen | shaded envelope, patch, fins, gondola windows, 4-frame propeller, beacon. Birds in dusk |
| Mid skyline A | 88..151, opaque from 128 | sway 4 px | 2 x 3 windows in lit clusters, water towers, billboards with chasing bulbs, chimneys with 8-frame steam (mesh edges) |
| Mid skyline B | 112..175, opaque from 152 | sway 2 px | 3 x 4 windows with highlight and sill, TV-flicker windows, chevron sign (4 frames), tanks, steam |
| Near rooftops | 128..223, opaque from 176 | still | large windows, parapets, pipes, fans (rotating), flag, big water tower, lamp cable with alternating bulbs, GUM neon sign with an inflating and popping bubble (8 frames), cast light |
| Rain (storm only) | 0..223, in front | 8-frame tile loop | one 16 x 16 mesh tile, 3 full columns and 7 columns with a gap at lines 80..159 |

## Tricks

- Depth: sway amplitudes 6 / 4 / 2 / 0 px, haze dither at the base of each far plane, window size grows toward the viewer, saturation and contrast rise toward the viewer.
- Dither: threshold maps made of uneven horizontal dashes (2 to 6 px), eighth steps. The sky map does not repeat. The city map has period 16, so it is tile-safe. Each ramp step keeps flat colour at both ends, so the dither sits in bands.
- Dither rule from the correction: every dither pair is at least 28 of 255 apart in luminance. The script records the two colours of each dither call and measures the result (table below).
- Cast light: the near plane has roles for undersides, wall glow dither and alley edges. Four palette levels. The level is set per 16 px column from the brightness of the hazard frame below it and drops one level per tile row upward. In the neutral palette the glow dither is invisible.
- Lightning (storm): palette flash on sky, far and mid A for 4 frames plus a drawn bolt.
- Moods by palette: the city index art is drawn once.

## Numbers (counted in code, see `numbers.txt`)

Per mood: 11 palettes plus the lit copies of the 2 or 3 near palettes (3 copies each). No tile needs more than 15 colours (asserted).

| Plane | Palettes (colours) | Unique tiles | Animated tile positions | Loop frames |
|---|---|---|---|---|
| Sky moon / storm / dusk | 1 (10) / 1 (6) / 1 (10) | 172 / 146 / 158 | 12 / 0 / 7 | 4 / 1 / 4 |
| Far | 1 (10) | 94 | 11 | 8 |
| Mid A | 2 (15, 12) | 171 | 29 | 8 |
| Mid B | 2 (15, 14 or 15) | 174 | 30 | 8 |
| Near | 2 (15, 15); storm 3 (15, 15, 3) | 226 | 28 | 8 |
| Clouds front / back | 1 (4) / 1 (4) | 45 / 32 | 11 / 9 | 4 |
| Airship | 1 (9) | 11 | 2 | 5 distinct |
| Beams (storm) | 1 (1) | 86 | 22 | 5 distinct |
| Rain (storm) | 1 (2) | 8 | 17 sprites | 8 |

Totals: moon 925 tiles, 132 animated positions. Storm 905 tiles, 120. Dusk 911 tiles, 127.
Unique tiles count every animation frame.

Scenery sprites per scanline (hazard strip and gameplay not counted, limit 66): moon 63, storm 66 (lines 112..127), dusk 63.

Dither pixels and luminance step of the dither pairs (median / minimum):

| Plane | Dither px | moon | storm | dusk |
|---|---|---|---|---|
| Sky | 18703 / 16762 / 19134 | 37.2 / 29.4 | 58.0 / 35.1 | 62.4 / 30.3 |
| Far | 7571 | 33.4 / 33.4 | 44.1 / 44.1 | 58.5 / 58.5 |
| Mid A | 7979 | 52.3 / 31.1 | 59.8 / 32.9 | 76.4 / 32.9 |
| Mid B | 7054 | 44.9 / 30.0 | 49.1 / 30.5 | 59.6 / 30.7 |
| Near (level 2 palette) | 12173 | 72.1 / 30.4 | 94.8 / 30.4 | 78.3 / 28.3 |
| Clouds front | 1224 | 33.5 | none | 44.5 |
| Clouds back | 249 | 33.5 | none | 44.5 |
| Airship | 486 | 39.3 | none | 35.4 |

Play area background luminance (lines 16..191, placeholder flier body 11, bubble 196):

| Mood | p5 | median | p95 | darker than 24 | brighter than 150 |
|---|---|---|---|---|---|
| moon | 3 | 45 | 149 | 19.4 % | 4.7 % |
| storm | 3 | 47 | 180 | 24.2 % | 7.1 % |
| dusk | 8 | 66 | 189 | 8.5 % | 14.7 % |

GIFs: moon 80 frames 2.03 MB, storm 64 frames 2.82 MB, dusk 80 frames 2.13 MB. Decode check on 4 frames per file: equal to the source frames.

## Weak points

- The near walls are the weakest part. The wall dither plus the cast-light dither give a rough, blotchy texture, and the lit palette levels change in hard 16 px steps (visible line at y 176). The glow pair is 72 to 95 apart in luminance, which is harsh.
- The sky dither is one generated dash map. It is plainly visible and banded, but the dashes have one texture everywhere. It does not yet look hand placed in the way a drawn sky does.
- The storm scene sits at the sprite limit (66 of 66 on lines 112..127) and needs the rain gap to get there. Any extra scenery sprite on those lines does not fit.
- The storm sky deck is scalloped and repetitive. The rain hides part of the GUM sign.
- The dark placeholder flier bodies vanish against the near walls in moon and storm (19 to 24 percent of the play area is darker than 24). The real fliers are pale, so this may not matter, but it was not tested with real flier art.
- Dusk has 14.7 percent of the play area brighter than 150. Pale bubbles lose contrast against the sun and the far skyline.
- The sun disc and the far skyline are plain. The far plane has no form shading, only haze dither.
- Buildings come from one generic generator with layout tables. Silhouettes vary, facades do not. Window lighting is random per seed, not composed.
- Cloud drift, airship and sway in the GIFs are much faster than in the game, so that a short loop closes (clouds 2 and 4 px per frame).
- About 900 unique tiles per mood, counting all frames. No attempt was made to reduce this.
- Palette counts come from a greedy packing in the script, not from a real converter.

## Not viewed

- The three GIFs in motion. Only frame count, size and a 4-frame decode check were done.
- `index.html` in a browser.
- `planes_storm_2x.png` and `planes_dusk_2x.png` (only the moon sheet was viewed).
- `scene_moon_1x.png` and `scene_storm_1x.png` (the 3x stills of all moods and the dusk 1x still were viewed).
