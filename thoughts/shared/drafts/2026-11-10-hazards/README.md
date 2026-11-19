---
date: 2026-11-10
topic: Roofline bottom hazards, visual drafts
status: draft, waiting for the user's pick
---

# Bottom hazard drafts

Problem: a flier that falls to the screen bottom dies on what looks like plain ground (the old flat blue band).
Four replacement hazards, drafts only, no game code.

Common format for all four: one seamless 32x32 tile (2x2 Neo Geo 16x16 tiles) repeated 10 times across the
320 px screen, top at screen row 192, 4 loop frames at about 8 fps, one palette per hazard (count below, limit 15
plus transparent). Art is hand-placed pixel clusters with hard cel steps, hue-shifted shades, no ramps, no dither.

| Option | What it is | Colours | Frames | Tile |
|---|---|---|---|---|
| A Spikes | steel spike row (tall/short alternating, lit from upper left) on a yellow/black warning rail; a glint runs along the tips, one spike per frame, with a fading after-glint | 11 | 4 | 32x32 |
| B Fire | four flame tongues per tile (deep red edge, red, orange, yellow, white-hot root) rising from a bed of coals with flickering ember cracks, detached flame licks and sparks | 10 | 4 | 32x32 |
| C Water | dark deep water, asymmetric wave crest with a foam lip rolling right 8 px per frame, shimmer dashes; plus a separate "lurker" sprite (fin cutting the surface, two glowing eyes in a dark shape below, bobbing, eyes blink on frame 3) sharing the water palette | 12 (tile + lurker) | 4 | 32x32 tile, lurker about 30x24 sprite |
| D Lava | molten surface with crest highlights, dark crust rafts with a glowing crack, two bubbles per tile on offset phases (swell, big dome, pop, droplets), pulsing molten streaks, rising embers | 9 | 4 | 32x32 |

What would change in the game to use each:
- A: new 4-frame fix/sprite strip along the bottom plus the existing screen-bottom kill; optional: bounce-kill instead of fall-through (spikes are solid).
- B: same strip; death animation could swap to a burnt/smoke puff instead of the plain dead fall.
- C: closest to the current design ("water at the screen bottom: instant death"); needs one extra roaming lurker sprite (its own small state machine: drift, surface near a flier, sink) and a splash on death.
- D: same strip; a splash/flare effect on death; bubbles could later spit a damaging droplet (new hazard, not in the design yet).

Files:
- `hazards_sheet_1x.png`, `hazards_sheet_4x.png`: all options, all frames, each frame shown as two tile repeats to expose the seam; lurker frames beside C.
- `scene_A_3x.png` .. `scene_D_3x.png`: 320x224 arena at 3x, background, islands and Sootlings pasted from `../2026-11-10-flier/A_v5_scene_3x.png` (city extended down behind the hazard), frame 1 of the hazard.
- `anim_A_4x.gif` .. `anim_D_4x.gif`: bottom-left 160x74 of the scene at 4x, 4 frames at 120 ms, looping.
- `draw_hazards.py`: generates everything; `python3.14 -I draw_hazards.py` (needs Pillow), deterministic; asserts the colour limit.

Known weak points: spikes read slender at 1x against the dark city; the wave crest repeats every 32 px and looks regular;
lava's deep-red bands have a zig-zag edge that reads a little mechanical. Lava and fire have no glow on the buildings
above (a glow would be a gradient; if wanted, a few hand-placed warm rim pixels on the building bases would do it).
