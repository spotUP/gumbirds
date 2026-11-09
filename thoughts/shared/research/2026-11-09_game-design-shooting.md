---
date: 2026-11-09
topic: Flashlight laser shooting mechanic
tags: [design, gameplay, controls, scoring]
status: final
---

# Flashlight laser (user idea, decided 2026-11-09)

The guard's flashlight doubles as a laser gun that fires forward.

## Decisions (user)

- Targets: enemies only. The laser destroys drones and new enemy types, for example rooftop bots.
  Vents and live cables are not affected and must still be jumped, so dodging stays the core skill.
- Limit: an overheat meter. Each shot adds heat. When the meter is full, the light goes dark for
  about 1.5 s and the guard cannot fire. Heat cools over time. The meter is shown as one HUD bar on
  the fix layer.
- Buttons: A fires, B jumps, C ducks. D is unused. (The user chose this over the suggested
  "duck on joystick down".)
- Scoring: +200 per kill. Kills close together raise a chain multiplier. The near-miss bonus stays.

## Open tuning (to go in src/tuning.h)

- Heat per shot, cool rate, overheat lockout (start: 1.5 s = 90 frames).
- Chain window in frames, and the multiplier step and cap.
- Laser speed and length, and the enemy hit box.
