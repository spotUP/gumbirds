---
date: 2026-11-09
topic: Gameplay spec for the Bubblegum Brawl flier, extracted from the reference skeddles/balloon-fight-arena
tags: [brawl, flier, physics, reference-spec, neo-geo, fixed-point, balloon-fight]
status: draft
---

# Bubblegum Brawl flier: gameplay spec taken from the reference

## 0. Read this first: what the reference is and is not

The reference is `github.com/skeddles/balloon-fight-arena`, commit `e4ef30398f15888b936352aba586fcfb568bbddb` (2024-05-11, version 4.0.0 in `project.godot:12`), a Godot 4.2 project. It was cloned shallow and only read; nothing was run or installed. No licence exists, so this document describes behaviour and numbers only. No code or assets are reproduced, and all names, art and theme in Bubblegum Brawl stay our own.

Findings that change the plan:

1. **The reference has exactly one game mode: a local versus arena match** (2 to 4 fighters, humans or CPU, last fighter standing wins). It has no endless mode, no trip-like scrolling mode, no scoring, no waves, no collectibles, no fish, no lightning, and no difficulty ramp. A search of all scripts and scenes for score, wave, fish, lightning, wrap and spark found only the CPU "priority score" variable. `scripts/enemy.gd` is an unused stub whose input function returns neutral input on its first lines (`enemy.gd:17-22`).
2. **There is no side-edge wrap.** Left and right edges are solid bouncing walls (section 3.6). The brief asked for wrap; the reference does not do it.
3. **There is no terminal velocity.** Nothing clamps vertical speed (section 3.5).
4. Everything the endless flier needs beyond the physics (scroll, spawns, hazards, scoring, game over) is therefore NOT IN REFERENCE and section 8 gives one default for each, built from the reference's own constants where possible.

Source paths below are relative to the repo root. Line numbers refer to that commit.

## 1. Time base and engine facts

| Fact | Value | Source |
|---|---|---|
| Physics tick | 60 Hz (Godot default; `physics_ticks_per_second` is not set anywhere in the project) | `project.godot:181-183` (the `[physics]` section holds only gravity) |
| Gravity constant | 200 px/s^2 (Godot default is 980, so this is deliberate) | `project.godot:183` |
| Reference screen | 640 x 360 viewport, integer-scaled to 1920 x 1080 | `project.godot:23-28` |
| Tile size | 8 x 8 reference px | `scenes/tileset.tres:1360` |
| Movement call | `CharacterBody2D.move_and_slide()`, velocity in px/s, Godot default up direction, floor angle 45 degrees, floor snap 1 px (no override found in `character.gd`) | `character.gd:157` |
| Integration order per tick | `v += g*dt` first, then position moves by `v*dt` (semi-implicit Euler) | `character.gd:65,84,87,157` |
| Timers | Wall clock milliseconds (`Time.get_ticks_msec()`), not tick counts | `character.gd:60,314-316` |

Conversion rule used everywhere below: a time in milliseconds becomes `ms * 60 / 1000` frames (1000 ms = 60 frames, 500 ms = 30, 250 ms = 15, 100 ms = 6).

## 2. Scale factor and fixed-point choice

### 2.1 Scale factor

- Reference viewport 640 x 360, ours 320 x 224.
- Horizontal factor: 320 / 640 = **0.5** exactly.
- Vertical factor if stretched to fit: 224 / 360 = 0.622. Rejected: a non-uniform factor would make vertical and horizontal physics disagree and distort sprite proportions.
- **Chosen: uniform factor s = 0.5 on both axes.** The world becomes 320 x 180 ours; the remaining 44 px of the 224-line screen is spare (see NIR-11).
- Velocity conversion: `v_ours [px/frame] = v_ref [px/s] * s / 60 = v_ref / 120`.
- Acceleration conversion: `a_ours [px/frame^2] = a_ref [px/s^2] * s / 3600 = a_ref / 7200`.
- Length conversion: `x_ours = x_ref / 2`.
- Trade-off to know: the reference characters are about 16 x 16 reference px, so they shrink to about 8 x 11 px. Reference 8 x 8 tiles become 4 x 4. If the art needs larger sprites, draw them larger than the hitbox; do not change the physics numbers.

### 2.2 Fixed point: use 16.16 for position and velocity

Per-frame code needs only add, shift, and 16 x 16 multiplies. There is no division anywhere in the per-frame path (every lerp weight below is a constant, replaced by shift-add).

| Format | Smallest step | Gravity 0.4 g = 0.011111 px/frame^2 | Verdict |
|---|---|---|---|
| 8.8 | 1/256 = 0.0039 | 2.84 steps, rounds to 3 (+5.6 percent error that accumulates every frame) | Rejected for velocity and acceleration |
| 16.16 | 1/65536 | 728.2 steps, rounds to 728 (0.03 percent) | **Chosen** (`add.l`, 8 cycles) |

Position is 32-bit 16.16 too (screen pixel is the high word). Largest speed in the reference: free fall from the top of the world with no balloons reaches sqrt(2 * 200 * 360) = 379 px/s = 3.16 px/frame, which fits in the 16.16 integer part with room to spare.

Lerp weights (`lerp(a, b, w)` is `a + (b - a) * w`) are applied per physics tick, so they carry over unchanged at 60 Hz. Replace the multiply with shift-add approximations of `d = b - a`:

| Weight w | Shift-add on d | Result | Source of w |
|---|---|---|---|
| 0.2 (flap strength default, land friction default, air horizontal blend) | `(d>>3)+(d>>4)+(d>>7)+(d>>8)` | 0.1992 | `character.gd:29,39,129` |
| 0.25 | `d>>2` | exact | `balloon-bird-*.tscn` |
| 0.5 | `d>>1` | exact | `alice.tscn`, `samm.tscn`, `tingle.tscn` |
| 0.18 | `(d>>3)+(d>>5)+(d>>6)+(d>>7)` | 0.1797 | `luigi.tscn:15` |
| 0.15 | `(d>>3)+(d>>5)` | 0.1563 | `balloon-bird-gbc.tscn:11`, `tingle.tscn:10` |
| 0.1 (parachute sway) | `(d>>4)+(d>>5)+(d>>7)` | 0.1016 | `character.gd:70` |
| 0.05 (Luigi friction) | `(d>>5)+(d>>6)` | 0.0469 | `luigi.tscn:12` |

Sine and angle functions (parachute sway, pop knockback) use a 256-entry table; no division is needed.

## 3. Player physics (the flier)

Per-tick order inside `_physics_process` (`character.gd:58-206`): (1) clear invincibility if its deadline passed; (2) pick one gravity branch by state; (3) read input; (4) flap / fill / horizontal control / special action; (5) `move_and_slide`; (6) scan slide collisions and react. Area overlaps (balloon pops) are resolved by the physics server around step 5 and run their handler on entry only.

### 3.1 Constants (default character, every other character overrides some)

| Constant | Ref value | Ours (px/frame or px/frame^2) | 16.16 raw | Source |
|---|---|---|---|---|
| Gravity, no balloons (and all non-floor airborne with 0 balloons) | 200 px/s^2 | 0.027778 | 1820 | `project.godot:183`, `character.gd:83-84` |
| Balloon gravity multiplier | 0.4 | | | `character.gd:37` |
| Gravity, with balloons | 80 px/s^2 | 0.011111 | 728 | `character.gd:86-87` |
| Top air speed (default) | 100 px/s | 0.83333 | 54613 | `character.gd:31` |
| Top air speed (Balloon Fighter red, recommended preset) | 120 px/s | 1.00000 | 65536 | `balloon-fighter-red.tscn:10` |
| Top land speed | 100 px/s | 0.83333 | 54613 | `character.gd:33` |
| Jump height (ground jump speed, with balloons) | 50 px/s upward | 0.41667 | 27307 | `character.gd:35,96` |
| Ground jump speed, no balloons | 2 x JumpHeight = 100 px/s upward | 0.83333 | 54613 | `character.gd:98` |
| Flap strength (lerp weight toward -TopAirSpeed) | 0.2 | w = 0.2 | | `character.gd:39,102` |
| Land friction (lerp weight to 0 per tick) | 0.2 | w = 0.2 | | `character.gd:29,131` |
| Air horizontal blend on a flap | 0.2 | w = 0.2 | | `character.gd:129` |
| Horizontal air drag | none (vx persists) | 0 | | no code path changes vx in air except flap and bounce |
| Terminal velocity | none | NOT IN REFERENCE (NIR-2) | | |
| Fill allowed only when vx below | 5 px/s (signed) | 0.04167 | 2731 | `character.gd:107` |

### 3.2 Flap (the core verb)

- Trigger: the flap button **just pressed this tick** (edge, not held), and the character is not falling, not dropping, not parachuting (`character.gd:93`).
- In the air with at least one balloon: `vy = lerp(vy, -TopAirSpeed, FlapStrength)` (`character.gd:99-102`). Positive y is down.
  - Ours with the red preset: `vy = vy + (-1.0 - vy) * 0.2`, that is `vy -= 0.2 * (1.0 + vy)`.
  - From rest the first flap gives `-0.2 px/frame` (-24 px/s reference, raw -13107). Repeated flaps converge to -1.0 px/frame; there is no cooldown, so mashing is the speed limit.
  - A flap on a falling flier is stronger in absolute terms (it adds `0.2 * (1.0 + vy)`).
- In the air with zero balloons: flap does nothing (the branch needs `current_balloons > 0`).
- On the floor: sets `vy = -JumpHeight` with balloons, `vy = -2 * JumpHeight` without (`character.gd:94-98`). The walk/jump button is the same button.

Derived feel numbers (red preset, ours): one gravity step with balloons is 0.011111 px/frame^2, so one flap from rest (0.2 px/frame) is cancelled by 18 frames of gravity. Holding altitude needs about one flap every 18 frames (3.3 per second). A flap from rest rises only (0.2)^2 / (2 * 0.011111) = 1.8 px before gravity wins, so climbing needs repeated taps.

### 3.3 Horizontal control

| Situation | Rule | Source |
|---|---|---|
| Direction input | analog axis from keyboard (-1, 0, +1), gamepad stick rounded to -1, 0, +1; sprite flips to face it | `player-controller.gd:11,18`, `character.gd:124-125` |
| On floor, direction held | `vx = dir * TopLandSpeed` instantly (no acceleration) | `character.gd:126-127` |
| On floor, no direction | `vx = lerp(vx, 0, LandFriction)` per tick | `character.gd:130-131` |
| In air, direction held, **flap pressed this tick** | `vx = lerp(vx, dir * TopAirSpeed, 0.2)` | `character.gd:128-129` |
| In air, direction held, no flap | vx unchanged | `character.gd:124-129` (no branch) |
| In air, no direction | vx unchanged (no drag at all) | same |
| Air steering after n flaps held in one direction from vx = 0 | `vx = TopAirSpeed * (1 - 0.8^n)` | derived from the 0.2 blend |

So the reference is a pure "steer only by flapping" model, and horizontal speed in the air never decays except through wall bounces. This was an intentional change noted in the changelog: "air movement only during flap, no friction" (`CHANGELOG.md`, 2.0.0).

### 3.4 Floor behaviour

- No gravity is applied while `is_on_floor()` (`character.gd:83,86`).
- Landing on a "ground" group collider while dropping or parachuting ends those states (`character.gd:194-200`).
- Floor geometry is tile-based and stage-specific (NIR-15).

### 3.5 Falling states

| State | Entry | Per-tick vertical | Horizontal | Exit | Source |
|---|---|---|---|---|---|
| Falling (dead) | last balloon lost in air without parachute, or touching a balloonless-vulnerable body, or drowned | `vy += 200 px/s^2` (full gravity), no clamp | input ignored | removed when y > 400 ref (200 ours), or when drown sound ends | `character.gd:64-67,242-252,374-375` |
| Fall start | `startFalling` | `vx = 0`, `vy = -50 px/s` (-0.41667, raw -27307), collision mask cleared so nothing is hit | | | `character.gd:246-249` |
| Parachute | last balloon lost in air, character has the ability, 500 ms invincibility | `vy += 0.1 * 200 = 20 px/s^2` (0.0027778 px/frame^2, raw 182), no clamp | `vx = lerp(vx, sin(ms/500) * 32, 0.1)`; note `ms/500` is integer division, so the target changes once per 500 ms (30 frames) to `sin(n) * 32 px/s` (0.26667 px/frame, raw 17476) for integer n | landing on ground | `character.gd:68-73,231-235` |
| Dropping (Alice, Samm only) | action pressed in air with a balloon: all balloons set to 0, `vx = 0`, `vy = +50 px/s` | `vy += 200 * DroppingGravity` (0.9 default, Samm 1.0) | no control | lands, or after DroppingDistance (default 999 px, effectively never) | `character.gd:23-25,75-81,134-146` |

Dropping and the parachute are optional character abilities. Recommended for Bubblegum Brawl: omit both (they only matter in the versus arena); NIR-5 covers the choice.

### 3.6 Ceiling, side edges, floor of the world

Walls are three infinite half-plane shapes in group "bounce": left edge at x = 0 (normal +x), right edge at x = 640 (normal -x), top edge at y = 0 (normal +y, also in group "ceiling"). Source: `scenes/stages/lake.tscn:47-63` (identical in every stage). Water is a half-plane at y = 360, in group "water" (`lake.tscn:90-94`).

| Edge | Behaviour | Ours |
|---|---|---|
| Left x=0, right x=640 | elastic bounce, no wrap | x=0 and x=320 |
| Top y=0 | elastic bounce | y=0 |
| Bottom y=360 (water) | touching water kills the character (section 4.4) | y=180 |
| Wrap | does not exist | NIR-1 |

Bounce rule (`character.gd:208-217`, called from `189-193`): when the character touches a "bounce" collider and is not on the floor, take the full attempted motion of the slide, divide by dt to get velocity, reflect it about the contact normal (restitution exactly 1.0, tangential speed kept), and if the speed is below the minimum, replace the velocity with `minimum * normal`. The minimum is 50 px/s (0.41667 px/frame, raw 27307). The ceiling branch calls bounce with minimum 100 first (`character.gd:191`) and then immediately again with 50 (`character.gd:192`); the second call recomputes the velocity from the collision data and overwrites the first, so **the ceiling minimum is effectively 50, not 100** (the 100 is dead). Reproduce the effective behaviour.

Bounce also happens against other characters (minimum 50, `character.gd:187`) and against kill tiles (minimum 25 px/s = 0.20833 px/frame, raw 13653, `character.gd:173`).

## 4. Balloons, lives, pops and collisions

### 4.1 Balloon count is the life count

| Rule | Value | Source |
|---|---|---|
| Balloons on body | 0 to 4 (UI maximum), start value default 2 | `debug_launcher.tscn:137-144` (`max_value = 4`, `value = 2`) |
| Spare balloons (refillable) | 0 to 95, default 2 | `debug_launcher.tscn:158-165` |
| Death | a character with 0 balloons that is not on the floor falls; a character with 0 balloons on the floor may walk but is killed by any body contact with a character (4.3) | `character.gd:226-237,179-182` |
| Respawn | none; a dead character is removed | `character.gd:66,374-375` |

### 4.2 Losing a balloon

`loseBalloon` (`character.gd:219-240`): returns at once if invincible. Otherwise `current_balloons -= 1` and:

| New count | Result | Invincibility |
|---|---|---|
| greater than 0 | keep flying | **1000 ms = 60 frames** |
| 0, on the floor | stand without balloons (small hitbox) | none |
| 0, in air, character has parachute | parachute | **500 ms = 30 frames** |
| 0, in air, no parachute | `startFalling` (dead) | none needed |

Hitbox swaps when the count reaches 0 or returns above 0 (`character.gd:302-312`).

### 4.3 Who pops whom

1. **Feet pop balloons (stomp).** A character's `FeetArea` overlapping another character's `BalloonArea` pops one of the **victim's** balloons. Handler runs on the victim, on area entry only (`character.gd:280-300`). Skipped if the victim is invincible, the victim has 0 balloons, or the attacker is falling. The attacker is never hurt by this and gets no invincibility check.
2. **Knockback on a pop** (`character.gd:292-299`): `collision_angle = position.angle_to(other.position)` where `angle_to` here is the angle between the two position vectors measured from the world origin (not the direction between the two characters, which looks like a reference bug). Victim velocity = unit vector at `angle + 90 degrees` times 40 px/s (0.33333 px/frame, raw 21845); attacker velocity = unit vector at `angle - 90 degrees` times 75 px/s (0.625 px/frame, raw 40960). The victim's velocity is then overwritten again if its last balloon went and it started falling (`vx=0, vy=-0.41667`). Ours: replicate with `atan2` and sine tables (256 entries), or take the direction-between-characters reading (NIR-12 flags this choice; default below).
3. **Body contact** (`character.gd:177-188`): if the character itself has 0 balloons and is not falling or dropping, it starts falling. Else if the other body has 0 balloons and is not falling and the toucher is not dropping (the code checks its own `dropping` flag, a reference quirk), the other starts falling. Then both bounce with minimum 50.
4. **Balloon area against balloon area** is ignored (name check, `character.gd:288`).
5. **Kill tiles** (`Kill` custom data on the tileset): bounce (minimum 25 px/s) then lose one balloon, unless invincible (`character.gd:169-175`). Only atlas tile (8,22) has the Kill flag (`scenes/tileset.tres:1316-1317`). Tiles (7..10, 2) and (8,22) are "Hazard" tiles that the CPU avoids (`cpu2.gd:11`).
6. **Water**: any contact kills (`character.gd:201-206`), regardless of balloons or invincibility. It sets `falling` without the collision-mask change used by `startFalling`, plays splash, and the node is freed when the drown sound ends.

### 4.4 Hit boxes (reference px, then ours at s = 0.5)

| Box | Shape | Size ref | Offset ref | Ours (width x height, offset) | Source |
|---|---|---|---|---|---|
| Body with balloons | capsule r4, h22 | 8 x 22 | (0, +1) | 4 x 11, (0, +0.5) | `character.tscn:15-18,536-538` |
| Body without balloons | capsule r4, h14 | 8 x 14 | (0, +5) | 4 x 7, (0, +2.5) | `character.tscn:19-22,540-544` |
| Balloon area (can be stomped) | capsule r6, h16 | 12 x 16 | (+1, -6) | 6 x 8, (+0.5, -3) | `character.tscn:528-531,573-581` |
| Feet area (stomps) | capsule r3, h10 | 6 x 10 | (0, +10) | 3 x 5, (0, +5) | `character.tscn:524-527,563-571` |

Shapes are capsules; we approximate with axis-aligned boxes of the same bounding size (NIR-12).

### 4.5 Refilling balloons (versus-arena feature)

Standing on the floor with `vx < 5 px/s`, spare balloons greater than 0 and current less than 4: each press of fill starts a refill animation of 24 frames (3 frames lasting 1, 2, 1 units at 10 animation fps = 0.4 s, `character.tscn` refill animation, speed 10); a new press is accepted only after the previous animation ends. After the fourth completed press one spare balloon becomes a current balloon. Any direction input or flap resets progress to 0 (`character.gd:104-121,254-266`). Bubblegum Brawl default: omit (NIR-5).

## 5. Enemies and AI

The reference has no scripted enemies. Opponents are other fighters driven by the same physics, controlled by CPU (`scenes/controls/cpu.tscn` uses `scripts/cpu2.gd`, see `cpu.tscn` line 3). `enemy.gd` is a stub and `computer-controller.gd` is an older unused controller (`computer-controller.gd` is not referenced from `cpu.tscn`). The CPU produces the same inputs a human does (direction axis, flap, fill), so it obeys all physics above.

CPU decision loop (`cpu2.gd:21-62`): every 100 ms (6 frames, `cpu2.gd:28`) score every state and take the highest. States and constants:

| State | Score constants | Target refresh | Source |
|---|---|---|---|
| Avoid hazard tile | active only within 96 px; score `(96 * velocity^(-ln(dist/96)) + 10^(4-balloons)) / 2` | 100 ms; state lock 1000 ms (60 frames) | `state-avoid.gd:6,11,13-17,21` |
| Flee | `280 * 4^(-ln(d/280)) + 10^(4-balloons)`, times `(1 - enemyDir)` | 250 ms (15 frames) | `state-flee.gd:6,13-17,21` |
| Fill | `640 * 2^(ln(d/640)) + 12^(4-balloons)`, times `(1-enemyDir)*0.75*1.5`; presses fill every 100 ms when on floor | 100 ms | `state-fill.gd:6-10,14` |
| Attack | `640 * 2^(-ln(d/640)) + 14^(balloons/1.05)`, times `(1.25 + enemyDir)` | 100 ms | `state-attack.gd:6,15-19,23` |
| Movement helper | flap at most every 150 ms (9 frames) when the path direction points up; direction change at most every 200 ms (12 frames), dead zone 0.1 | | `move-towards-point.gd:4-20` |

Paths come from Godot navigation grids placed in each stage (README, "Stages"). That part needs an engine feature we do not have. For Bubblegum Brawl the recommendation in section 8 (NIR-6) replaces it with simple steering.

## 6. Game modes

| Mode | Present in reference | Rules | Source |
|---|---|---|---|
| Arena versus match | **yes, the only one** | 2 to 4 combatants (human slots or CPU), one of 8 stages or random, start with 1-4 balloons (default 2), 0-95 spares (default 2). Needs at least two combatants and no duplicate input device. No scroll, no timer, no score. Ends when exactly one character node remains: shows winner name, plays a jingle, returns to the launcher. | `debug_launcher.gd:63-125`, `level.gd:14-25` |
| Pause | yes | Escape pauses and unpauses the tree; menu has exit | `pause.gd:1-27` |
| Endless / trip / score attack | **no** | | NIR-3 |

Eight stages: canyon, cliffs, island, lake, mountain, ocean, pencilvania, terrace (`scenes/stages/`). All have one water body at y=360 and four spawn markers; for example lake spawns (82,290), (626,290), (136,144), (536,144) (`lake.tscn:65-75`), ours (41,145), (313,145), (68,72), (268,72).

## 7. Input mapping and tick

| Action | Behaviour | Reference binding (keyboard / pad) | Source |
|---|---|---|---|
| Move | held, analog axis rounded for pad | A/D, Left/Right arrows, J/L, numpad 4/6; pad stick X or d-pad | `project.godot:41-180`, `player-controller.gd:11,18` |
| Flap and ground jump | **just pressed** (edge) | W, Up arrow, I, numpad 8; pad button A | `player-controller.gd:12,19` |
| Fill balloons | just pressed | S, Down arrow, K, numpad 2; pad B | `player-controller.gd:13,20` |
| Special action | just pressed | E or Space, numpad 5 or 9, arrows 0 or other, pad Y | `player-controller.gd:14,21` |
| Pause | Escape and one more key | | `project.godot` pause action |

Inputs are sampled once per 60 Hz physics tick. A flap is a single-tick edge, so on Neo Geo read the joystick once per frame and compare with the previous frame.

## 8. Items NOT IN REFERENCE, each with one recommended default

Defaults are chosen to follow the reference constants and keep one rule set; all are Bubblegum Brawl decisions awaiting approval.

| ID | Missing | Recommended default (ours) |
|---|---|---|
| NIR-1 | Side-edge wrap | Do not wrap. Keep the reference's bounce (section 3.6) at x=0 and x=320. If an endless side-scroller needs wrap later, wrap x in 16.16 modulo 320. |
| NIR-2 | Terminal velocity | Clamp downward speed at 3.2 px/frame (raw 209715), which is the reference's own free-fall maximum from the top of the world. |
| NIR-3 | Endless / scrolling mode | Single auto-scroll lane at 0.25 px/frame (30 px/s reference-equivalent: slow enough that a flap of 0.2 px/frame outpaces it); camera follows world; the water line scrolls with the bottom edge. Start this at one rule: run until the last balloon pops. |
| NIR-4 | Scoring | 1 point per 8 px scrolled, 50 per stomp of an enemy balloon, 25 per collectible. |
| NIR-5 | Dropping, parachute, refill | Omit all three; the flier has up to 3 balloons, no spares. Pop with 0 balloons left means fall and game over. |
| NIR-6 | Enemies (NPC) and waves | Enemy fliers use the same physics and hit boxes as the player (so section 3 applies unchanged), steered by a pared-down version of the flee and attack states: target refresh every 15 frames, flap when the target is above by more than 16 px, direction toward the target with a 4 px dead zone, flap cooldown 9 frames. One new enemy every 600 frames (10 s), cap of 4 on screen. |
| NIR-7 | Fish / lightning hazards | None; use only the reference's hazards: water, kill tiles (4.3 item 5), and walls. |
| NIR-8 | Collectibles | One floating balloon pickup (restores one balloon up to the cap), spawned every 1200 frames (20 s) at a random free spot. |
| NIR-9 | Difficulty ramp | Every 1800 frames (30 s) cut the enemy spawn interval by 60 frames to a floor of 240, and raise enemy flap strength by 0.02 up to 0.3. |
| NIR-10 | Draw (all fighters die in the same tick) | Result is a tie: treat as game over and resolve by score. |
| NIR-11 | Vertical room for a 224-line screen (reference world is 180 ours high) | Play area 320 x 180 starting at screen line 16; 16 lines HUD above, 28 lines for water art below the y=180 kill line. |
| NIR-12 | Capsule collision and the origin-based knockback angle | Use AABBs of the same size; for knockback use the direction between the two characters (victim away at 40 px/s, attacker away at 75 px/s) to avoid the reference's screen-position-dependent angle. If bit-exact copying is wanted, say so and use the formula in 4.3 item 2. |
| NIR-13 | Neo Geo input mapping | Stick left/right = move, A = flap, B/C/D unused. |
| NIR-14 | Respawn after death | None (matches reference); game over screen with score. |
| NIR-15 | Stage tile and platform layout for Bubblegum Brawl | Own level data; keep 8 px (16 reference px) platforms spaced so a 22-reference-px-tall body fits through gaps of at least 12 px ours. |

**Count of NOT IN REFERENCE items: 15.**

## 9. Master constants table in our units (copy into the C source)

All values 16.16 raw (px/frame or px/frame^2 at 60 Hz, s = 0.5), red-fighter preset.

| Name | Ref | Ours | Raw 16.16 |
|---|---|---|---|
| GRAVITY_NO_BALLOON | 200 px/s^2 | 0.027778 | 1820 |
| GRAVITY_BALLOON | 80 px/s^2 | 0.011111 | 728 |
| FLAP_TARGET_VY | -120 px/s | -1.0 | -65536 |
| FLAP_WEIGHT | 0.2 | shift-add 3,4,7,8 | |
| AIR_BLEND_WEIGHT | 0.2 | shift-add 3,4,7,8 | |
| TOP_AIR_SPEED | 120 px/s | 1.0 | 65536 |
| TOP_LAND_SPEED | 100 px/s | 0.83333 | 54613 |
| GROUND_JUMP_VY | -50 px/s | -0.41667 | -27307 |
| GROUND_JUMP_VY_NO_BALLOON | -100 px/s | -0.83333 | -54613 |
| LAND_FRICTION_WEIGHT | 0.2 | shift-add 3,4,7,8 | |
| MIN_BOUNCE_SPEED | 50 px/s | 0.41667 | 27307 |
| KILL_TILE_BOUNCE_SPEED | 25 px/s | 0.20833 | 13653 |
| FALL_START_VY | -50 px/s | -0.41667 | -27307 |
| PARACHUTE_GRAVITY | 20 px/s^2 | 0.0027778 | 182 |
| PARACHUTE_SWAY | 32 px/s | 0.26667 | 17476 |
| KNOCKBACK_VICTIM | 40 px/s | 0.33333 | 21845 |
| KNOCKBACK_ATTACKER | 75 px/s | 0.625 | 40960 |
| INVINCIBLE_AFTER_POP | 1000 ms | 60 frames | |
| INVINCIBLE_AFTER_PARACHUTE | 500 ms | 30 frames | |
| WORLD_W / WORLD_H | 640 x 360 | 320 x 180 | |
| WATER_Y | 360 | 180 | |

Per-character preset deltas from the defaults (in reference units; convert speeds with /120): Balloon Fighter red: TopAirSpeed 120 (`balloon-fighter-red.tscn:10`). Balloon Birds: TopLandSpeed 85, parachute, FlapStrength 0.25 (`balloon-bird-green.tscn:10-12`). Mario: JumpHeight 90 (`mario.tscn:12`). Luigi: LandFriction 0.05, TopLandSpeed 110, JumpHeight 110, FlapStrength 0.18 (`luigi.tscn:12-15`). Tingle: LandFriction 0.15, TopAirSpeed 65, TopLandSpeed 80, JumpHeight 30, BalloonGravity 0.3, FlapStrength 0.5 (`tingle.tscn:10-15`). Alice: dropping, TopAirSpeed 70, TopLandSpeed 90, BalloonGravity 0.35, FlapStrength 0.5 (`alice.tscn:10-14`). Samm: dropping with gravity 1.0, TopAirSpeed 65, TopLandSpeed 85, FlapStrength 0.5 (`samm.tscn:10-14`).

## 10. Verification status

- Constants were read directly from the files cited; nothing was run. Counts that drive decisions (only one game mode; only one tile with the Kill flag; no wrap code) were found by search and cross-checked against the structure that defines them (project input and scene files, the tileset custom data layers at `tileset.tres:1375-1378`, and the level script's single win condition at `level.gd:14-25`), but a search proves absence only in the files searched. Unverified: exact Godot slide ordering when several collisions occur in the same tick, and whether the engine applies floor snap during a flap tick.
- Godot defaults assumed, not overridden in the project: 60 Hz tick, floor angle 45 degrees, floor snap 1 px.
