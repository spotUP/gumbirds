---
date: 2026-11-09
topic: Flier physics model (flap-to-float), reference read
tags: [gameplay, physics, flier]
status: draft
---

# Flier physics model

Source read: github.com/skeddles/balloon-fight-arena (Godot 4 fangame, GDScript), `scripts/character.gd`
`_physics_process`, `project.godot`. User says this one feels right. The repo has NO license (all rights
reserved) and ships third-party assets: copy nothing. Only the behaviour below is used; our code is our own C.
The earlier reference github.com/oafbot/balloontrip is rejected (user: physics wrong).

## Behaviour (Godot physics tick 60 Hz, units = viewport px, viewport 640x360 integer-scaled)

- Gravity while airborne with balloons: 200 px/s^2 * BalloonGravity 0.4 = 80 px/s^2. No terminal fall speed.
- Flap on button PRESS only (edge, not hold): `vy = lerp(vy, -TopAirSpeed, FlapStrength)` with
  TopAirSpeed 100 px/s, FlapStrength 0.2. Each flap moves vy 20 % of the way to -100 px/s, so rise speed
  approaches 100 px/s after many fast taps and one tap from rest gives -20 px/s.
- Horizontal in the air changes ONLY on a flap with a direction held: `vx = lerp(vx, dir * 100, 0.2)`.
  Without a flap there is no air drag and no steering: the flier keeps drifting at constant vx. This
  is the core of the feel.
- On the ground: vx = dir * TopLandSpeed (100) directly; no input: `vx = lerp(vx, 0, 0.2)`.
- Hitting solid geometry: velocity reflected about the surface normal, with a minimum bounce speed.
- Balloons lost: full gravity (200 px/s^2), no control.
- Per-character stats override these defaults (scenes/characters/*.tscn); defaults are the reference.

## Neo Geo conversion (60 fps, 8.8 fixed point, per frame)

Scale UNVERIFIED: the viewport px size vs our 320x224 screen depends on the fangame's sprite scale. Start at 1 viewport px = 1 screen px and tune by playtest.

| Knob | Reference | Per frame | 8.8 |
|---|---|---|---|
| FLY_GRAVITY | 80 px/s^2 | 0.0222 px/f^2 | 6 |
| FLY_TOP_SPEED | 100 px/s | 1.667 px/f | 427 |
| FLY_FLAP_FRAC | 0.2 | delta*51/256 | 51 |
| FLY_STEER_FRAC | 0.2 | delta*51/256 | 51 |
| FALL_GRAVITY (no balloons) | 200 px/s^2 | 0.0556 px/f^2 | 14 |

Flap: `vy += ((-FLY_TOP_SPEED - vy) * FLY_FLAP_FRAC) >> 8`. Steer (on flap, dir held):
`vx += ((dir * FLY_TOP_SPEED - vx) * FLY_STEER_FRAC) >> 8`. Gravity added every frame.
Host test: one tap from rest gives vy = -85 (8.8); 30 taps converge to about -427; vx constant between flaps.
