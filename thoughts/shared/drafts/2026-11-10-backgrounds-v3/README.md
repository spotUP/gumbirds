# Backgrounds v3 (polish pass on v2)

Drafts only. Nothing here is game data. All art is original and drawn by `draw_backgrounds_v3.py`.

Run: `/opt/homebrew/bin/python3.14 -I -B draw_backgrounds_v3.py [--nogif] [--only moon|storm|dusk] [--nov1]`
A full run writes `numbers.txt` and `index.html`; a run with `--only` or `--nogif` does not.

Unchanged from v2: near wall shapes, facade types, far skyline shading, plane count and sway (far 6, mid A 4, mid B 2,
near still), city palettes, actors, hazards.

## What changed per item

### 1. Storm menace
- Black cloud mass over lines 0..15 and a little below, with a hand-set uneven lower edge (ellipse table `VOID`).
  Hard edge, no dither. Sky colour 0 lowered to luminance 9.
- Cloud deck hue moved from grey-green to indigo and violet; the open sky below stays teal, so the lifted values sit
  behind the fliers only. Deck ramp 25.5 / 55 / 84.5 / 114.
- Deck built from three layers of hand-placed ellipses with uneven widths and depths (`DECKA`, `DECKB`, `DECKC`).
  The v2 circle rows and the sine stripe term are gone. Each layer: dark body above, lit belly at the lower edge.
  Rim light only on the lowest layer, broken.
- Play area share darker than 24: 5.5 percent (v2 5.2). Brighter than 150: 6.7 percent (v2 6.7).

### 2. Sky teeth and repeats
- Five new hand-authored strips (D shelf with towers, E small puffs, F windswept streaks, G uneven mounds, H thin
  lines with flecks) next to the three from v2. Eight strips, also used mirrored.
- Every band edge has its own hand-set order of all eight strips, each strip once. One order is 672 px long, so no
  strip appears twice on one edge inside the 320 px screen.
- Cause of the teeth in v2: the strip height followed the gradient, so slow gradients stretched the strips into tall
  points. v3 sets the strip height from the pixel distance to the band edge: 11 px where the gradient is slow.
- Band edges no longer run level: a hand-set rise and fall of up to 6 px (`EDGEWOB`, one value per 24 px).

### 3. Sun and moon
- Dusk sun: radius 30 (v2 22), centre moved 8 px to the left and 2 px down. Orange body (luminance 148), dimmed red
  core and lower half (118), thin gold limb on the upper edge only (190), five cloud slits. No white or pale area.
- Halo for moon and sun: two flat concentric rings, each one sky ramp step brighter. The halo no longer drives the
  cluster edges, so the drip shapes under the moon are gone. Band edges continue through the rings.

### 4. Mid planes and near cast light
- Mid A and mid B: v1 streak dither removed (wall gradient and haze). Walls are flat colour with a flat street-canyon
  shadow below a clean stepped diagonal edge and a flat form shadow on the left.
- Material drawn in the lit part, per facade type: brick courses with staggered joints (warehouse), brick patches
  where render fell off plus floor seams (apartment, mid B), vertical panel seams with bolts (office), stone block
  joints (deco), stain drips under the cornice, drain pipes with brackets.
- Haze at the foot of the mid planes: hand cluster edge instead of streaks. Steps 32.9 and up.
- Near wall cast light: checker meshes removed. Solid lit foot, then broken horizontal light streaks that thin out
  upward (hand table `DASH`).

### Extra items
- Mid B minimum dither step: 32.9 moon, 35.7 storm, 59.2 dusk (v2 28.6 / 28.8 / 30.3). Done.
- Scalloped storm deck: done with item 1.
- Far facade variety at 1x: not done. The brief accepts the far skyline shading, and a change there moves tile counts.

## Numbers (full list in `numbers.txt`)

| mood | sky dither px, median, min | min step over all planes | darker than 24 | brighter than 150 | sprites flat | sprites trimmed | palettes | tiles |
|---|---|---|---|---|---|---|---|---|
| moon | 11213, 29.9, 29.8 | 29.8 | 6.4 % | 5.0 % | 67 | 58 | 14 | 894 |
| storm | 14700, 29.8, 29.7 | 29.7 | 5.5 % | 6.7 % | 65 | 60 | 13 | 890 |
| dusk | 11019, 30.0, 29.6 | 29.6 | 3.7 % | 6.2 % | 67 | 58 | 14 | 886 |

Sprite counts equal v2 both ways. Limit 96 per line. Every palette has 15 colours or fewer plus transparent.
v2 tiles: 892 / 893 / 886.

## Weak points (own list)

- Mid plane material is hard to see at 1x. Windows, signs and the near plane cover most of the mid walls; the free wall
  area is small, so brick and seams read as a few dark lines. The streaks are gone, but the material is not rich.
- Storm deck layers still read as three parallel wavy bands. The scallops are uneven now, but each layer has a similar
  depth. Larger differences between the layers would help.
- The storm black mass has a hard edge against the darkest deck colour (step 16.5, too small to dither by the
  28 rule). At 3x the edge looks cut out in places.
- Moon mood: darker than 24 rose from 6.3 to 6.4 percent. Under the limit, but the margin is 1.6 points.
- Top band edge of moon and dusk still shows small peaks from the strips. No regular tooth row, but it is a
  silhouette of bumps, not soft cloud.
- The edge rise and fall (`EDGEWOB`) is one table for all bands of a mood, so the band edges run parallel.
- Halo rings are plain circles. Clean, but flat; the outer ring edge is a hard step without clusters.
- Sun slits are straight lines of the sky colour. They read as blinds more than as cloud bars at 3x.
- Near wall light streaks follow a table by height. All near buildings show the same streak rows at the same height.
- Repeat check for the sky is by construction (strip order), not by a measured autocorrelation.
- Far facade variety not addressed.
- Storm moves to violet for the deck. This is a hue change from v2 that the brief did not ask for by name; it was
  chosen to bring the menace back. The v2 hue anchors are still in the v2 script.
