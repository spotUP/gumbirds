---
date: 2026-11-09
topic: Art direction for the Neo Geo highscore dodger
tags: [design, art, palette, neo-geo]
status: draft
---

# Art direction: B "Roofline" (theme picked 2026-11-09; art style REJECTED)

User feedback 2026-11-09: "i hate the art style in you mockup", "it needs to look genuinely neo geo". The draft art (small flat rect sprites, few shades) is not the target. The palette and sprite notes below describe the rejected draft only.

## New direction (2026-11-09, user)

- "your mockup looks dry and modern". Target: peak Neo Geo pixel art, with the Metal Slug series as
  style inspiration. Take the style traits only; never copy Metal Slug characters, sprites or layouts.
- Hero: a night security guard running the rooftops (the company makes software for the guarding industry).
- The Roofline theme stays: night city rooftops, jump and duck hazards.
- Next step: one hand-pixelled gameplay test screen at full fidelity. The user judges it before any
  other screens are made.

## Test screen v1 (2026-11-09)

- File `design/roofline-test.html`, published at https://claude.ai/artifact/KGPNLd5NKVMRGaFx1m6qoD
  (private). Native 320x224, 4-frame loop, `#raw` shows a static frame. Tile check PASS (every
  16x16 sprite tile has 15 or fewer colours; every HUD cell has 7 or fewer).
- Self-rating: about 6.5 of 10 against Metal Slug. The background is strongest.
- Weak points: the hero is built from shaded primitives, which gives blocky shading and slab boots.
  The 4-frame run cycle is stiff. The dithered light cones look mechanical. The lives icons are too small.
- Decision (user): hand-pixel the hero. Redraw the guard as hand-placed pixel rows (not
  generated from primitives), with an 8 to 10 frame run cycle. Also fix the light cones and lives icons.
  The background stays as it is.

Source drafts: `design/art-directions.html`, published at
https://claude.ai/artifact/7zYTGwUs888XWDrQkYZXHt (private). The drafts showed three directions
(A Coffee Run, B Roofline, C Torchlight). The user picked **B Roofline**.

## Concept

A courier with a glowing cyan visor runs the city rooftops at night. Hazards:
- Low (jump): rooftop vent unit, 28 x 22 px.
- High (duck): patrol drone with spinning rotors and a red blinking light, 26 x ~11 px, hovers at
  about 36 px above the roof line.
- Floor (jump): sparking live cable, 30 px wide, animated sparks.

Near miss under a drone gives `+500`, shown as floating sprite text.

## Screen layout (320 x 224)

- Roof line (ground) at y = 176. The player sprite is 16 x 32, with the feet on the roof line, at x = 72.
- Sky: four bands from dark navy to magenta, with dithered transitions (no blending on Neo Geo).
- Moon at (252, 32), radius 11.
- Parallax: the far skyline scrolls at 0.25x, the mid skyline at 0.55x, and the roof at 1x. Mid buildings
  have antennas with blinking tips and occasional cyan billboards.
- HUD on the fix layer, row 1 labels, row 2 values: SCORE at column 2, HI at column 17, LIVES at
  column 32. Lives are shown as cyan visor icons.
- Keep the HUD inside the 8 px side border that many MVS monitors crop.
- Title: the logo "ROOFLINE" in 4x sprite letters with an outline and a moving highlight band.
  The tagline "RUN THE CITY AT NIGHT" and a blinking "PRESS START" go on the fix layer.
- Name entry and the top 10 table use a solid panel (sky0 fill, roofEdge border, sky3 inner line).

## Palettes (source hex; hardware rounds each channel to 5 bits)

Each group fits in one Neo Geo palette (max 15 colours plus transparent).

Background (13): sky0 #0d0b24, sky1 #1c1240, sky2 #3a1856, sky3 #6a1f6a, moon #f4e8ff,
far #251b48, farWin #5b50a2, mid #130e2a, midWin #ffd36b, midWin2 #3ee3e0, roof #29233f,
roofTop #463c6a, roofEdge #8a76d6

Player (10): ol #07060f, skin #e8a87c, skinD #b9765a, hood #26304f, top #34467a, topD #26304f,
visor #48f0ff, legs #141a2c, legsD #0f1322, shoe #ff3f9a (trail uses the same pink)

Props (12): ol #07060f, vent #5d6584, ventL #8b93b3, ventD #3d4460, body #3b3f55, bodyL #6e7396,
rotor #a6acd0, light #ff3355, cable #1d1a2b, spark1 #48f0ff, spark2 #ffffff, spark3 #ffd36b

Logo (6): ol #07060f, sh #2a0b3a, a #b8fbff, b #48f0ff, c #ff3f9a, hl #ffffff

Fix-layer text (5): sh #07060f, hud #ffffff, dim #b9b2ea, hi #48f0ff, accent #ff3f9a

## Implementation notes

- Background layers will likely need splitting across several palettes when built as real tiles.
  The single-palette counts above are a ceiling per layer, not a hard plan.
- The 1 px dark outline is baked into sprite tiles (colour `ol`).
- Font: 5 x 7 glyphs in 8 x 8 fix-layer cells, with a 1 px drop shadow baked into the tile.
- Working title "Roofline". The final name is decided in P4.3.

## Feedback on v1 gradients (2026-11-09, user)

- "the gradients in the art looks very generated and digital, pixel artists use more organic
  gradients the image could be more contrasting as well its a bit meh"
- Cause: the background shading comes from `lv()` ramps driven by fbm noise plus Bayer dither,
  so the bands are smooth and machine-regular.
- Rules for every art pass:
  - Use hand-shaped tone clusters with irregular band edges that follow the form.
  - Use fewer, bigger value steps.
  - Shift hue along each ramp: cool or purple shadows, warm lights.
  - Use near-black darks and crisp highlights only at key points.
  - Dither sparsely, only at a few transitions.
  - Push the contrast so the layers separate.
- Plan: the hero agent applies the rules now. A background pass follows after it.

## Test screen v2 and change to a simpler style (2026-11-09)

- v2 (hand-placed hero rows, 8-frame cycle, banded light cones) is published at the same link as
  v1, as version 2. Self-rating 5 of 10: upright pose, oversized head, slab torso, the flashlight
  reads as a gun, and frames 4 to 7 differ mostly in tone. The background was not changed.
- User: "i saw it it doesnt look nice. lets try a simpler art style. try something similiar to
  super mario bros 3".
- New direction: simple flat style with SMB3 traits. Bold dark outlines, flat fills with 1 or 2
  shade steps, chunky readable shapes, a bright saturated palette, and simple patterned tiles.
  Take the style traits only. Never copy SMB3 characters, blocks, pipes, enemies, tiles or layouts.
- The theme stays Roofline (rooftops, night guard hero). The next step is test screen v3 in
  `design/roofline-test-v3.html`.
- Update, same day: the user changed the target twice. First: "megaman for snes is a much better
  target than super mario bros 3". Then: "megaman x is even better". The current target is the
  Mega Man X (SNES) style: clean outlines, cel shading with 3 or 4 hard tone steps, hue-shifted
  ramps, glossy metal highlights, a sleek hero about 4 to 5 heads tall, and a dark high-tech
  night city. Take the style traits only. Copy nothing from Mega Man X.

## Test screen v3 (2026-11-09)

- File `design/roofline-test-v3.html`, published at https://claude.ai/artifact/MpiykVT4cz2n7uSDBcHxWd
  (private). 12-frame loop at 100 ms, `#raw` / `#rawN` show static frames. Tile check PASS (worst
  sprite tile 13 colours, worst HUD cell 8).
- Self-rating 7 of 10.
- Weak points: the hero is small at 1x and the shoulder pad reads as a white blob on the chest.
  The hazards are under-scaled (thin cable, tiny spark, small drone). The background is busy, with
  flat panel blocks and repeating window-strip rhythms.
- Awaiting the user's verdict.
- Verdict (user): "the backgrounds are good the guard looks bad he should not be bigger probably
  smaller". Decisions: the v3 background, hazards and HUD are frozen. Redraw only the guard,
  smaller: about 32 px tall (2 sprite tiles high) instead of about 45 px. Every pose is drawn as
  hand-placed pixel rows; no capsule `limb()` shading. Output goes to `design/roofline-test-v4.html`
  so v3 stays as the baseline.

## Test screen v4 (2026-11-09)

- File `design/roofline-test-v4.html`, published as a new artifact. The guard is now 32 px tall
  in a 36x33 buffer. Its 6 run frames are hand-placed row maps (`HERO_FRAMES`). It uses 15 colours,
  the worst tile has 14, and the verdict is PASS. Self-rating 7 of 10.
- Weak points: the navy uniform blends into the blue-violet buildings, the torso is boxy, the
  flashlight arm is identical in all 6 frames, and the "up" frames are too close to "contact".
- New art need from the shooting mechanic (see the game design doc): a fire pose or arm recoil,
  a laser beam sprite, and enemy explosion frames.
- Verdict (user): "the guard still looks like shit isn't there some free aset we can remix to look
  nice?". AI-drawn guard work stops here. Next: find a free human-drawn character sheet (CC0 or
  CC-BY) and remix it (navy uniform, cap, flashlight laser). Shortlist:
  `thoughts/shared/research/2026-11-09_free-hero-assets.md`.
- Pick (user): Space Police Hero by Master484 (CC-BY 4.0). Credit "Hero sprites based on Space
  Police Hero by Master484 (CC-BY 4.0)" on the attract screen. The hero is about 38-42 px tall.
  The remix goes to `design/roofline-test-v5.html` and `assets/hero/guard_sheet.png`, with
  `assets/CREDITS.md`.

## Test screen v5 (2026-11-09) - hero ACCEPTED

- `design/roofline-test-v5.html`, published at https://claude.ai/artifact/Dp7hipLm3QtfSKLnBoB5aB.
  The guard is remixed from Space Police Hero: 40 px tall, 13 colours, worst tile 11, PASS.
  The engine source is `assets/hero/guard_sheet.png` + `guard_sheet.json`; credits are in
  `assets/CREDITS.md`.
- Verdict (user): good, tweak later. Polish list for later: a darker navy, softer or smaller
  shoulder pads, a flashlight-shaped gun, a smoother laser angle, and a cap on the hit and aim frames.
- Polish pass done (version 2 of the same artifact): darker navy with rim tone, fabric epaulettes,
  flashlight head with bezel and lens, stepped laser, cap on all frames. 14 colours, worst tile 12, PASS.
- Verdict (user) on version 2: "he holds the flashlight like a gun". Cause: the source sprite holds
  a rifle extended forward, so the arm pose itself reads as a gun.
- Decision (user): overhand cop grip. One fist raised near the shoulder or ear, flashlight lying
  over the fist and pointing forward, lens forward. No second hand on the flashlight. The laser
  fires from the lens. Redraw the arm in the run, shoot, jump and aim frames.
- Grip redraw published as version 3 of the same artifact (24 of 29 frames, 14 colours, PASS).
  Verdict (user): good, lock it. The hit frame and the 4 aim-angle frames keep the old two-hand
  hold. They are deferred: the game fires forward only, so the aim frames are unused. Redrawing
  the hit frame is a polish item. Details: `2026-11-09_guard-grip.md`.
- User: "he is light blue as well not navy blue like a guard". Recoloured the GUARD palette
  (page and guard_sheet.png) to a darker, greyer navy: K #0a0a18, D #141a36, N #1c2650,
  L #2a3a6c, rim R #44609c, G #34385a, steel A #9aa2b4, W #e2e6ee. PASS. Published as version 4.
  Image check: reads as midnight navy. Contrast against the purple-navy buildings is marginal;
  the rim, cap, face and steel trim carry the silhouette. Backups of the old page and sheet are in
  the scratchpad `grip/` folder (`*_before_navy.*`).
- User preferred the old blue guard ("oldblue is better but the background is too similiar"), so
  the navy recolour was reverted. Decision (user): purple-magenta city. Shifted the sky, clouds,
  far/mid buildings, pipes, glows and roof stone in palette `P` to plum, purple and magenta; the
  AC unit and vent stay teal as accents. Then (user: "add value pop") the buildings were darkened
  one step and the guard N/L/R were brightened one step (#283476, #3c4ea6, #8cacf6), in both the
  page and guard_sheet.png. PASS. Published as version 7.
  Image check: hue separation is good, but brightness separation is only "somewhat". The next lever
  is a lighter rim or outline on the guard. Backups are in the scratchpad `grip/*_before_city*`
  and `*_before_pop*`.

## v8: guard rim light (2026-11-09)

User chose "Add light rim". Body-tone pixels (D, N, L, G) next to a back (left) or top K outline pixel that touches transparency are set to R (#8cacf6). No new colour; the K outline stays. 237 px on the page frames, 1022 px on assets/hero/guard_sheet.png. The tile check passes (hero max 12 colours). Script: scratchpad grip/rim.py. Backups: grip/page_before_rim.html, grip/sheet_before_rim.png. Note: C() rounds channels (round(v*31/255)), not floor; sheet colour matching must use the same rounding.

## v9: cyan rim (2026-11-09)

The version 8 rim shared the front highlight colour R, so the light direction read as ambiguous (sonnet check: separation "somewhat"). User chose "Cyan rim colour". The rim was re-applied from the pre-rim backups with the existing lens cyan c (#5ce8ff) instead of R, so the palette gains no new colour. Hero max per tile is now 13 colours (limit 15); the tile check passes.

Locked by user at version 9 (2026-11-09).
