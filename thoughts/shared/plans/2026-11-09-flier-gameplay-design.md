---
date: 2026-11-09
topic: Flier physics and gameplay design (arena mode + endless Gum Trip mode), every gameplay rule equal to skeddles/balloon-fight-arena
tags: [gameplay, physics, flier, design, modes, scoring, object-pool, plan, reference-audit]
status: final
---

# Flier gameplay design (reference-exact revision)

Scope: design only. Replaces the runner gameplay (user direction 2026-11-09: flap-to-float flier, keep the scrolling city).
User rule (2026-11-09): "everything should be exactly like the reference that's why it's the reference". Every gameplay and physics
rule below equals the reference unless it is marked NOT IN REFERENCE (then it is open for the user) or is one of the kept
non-gameplay picks: k = 1.0 scale, 16x32 flier, glowing gas pod theme, original names and art, fixed-point arithmetic.

Inputs: `thoughts/shared/research/2026-11-09_flier-physics.md`, `thoughts/spot/todos.md` (section "flier design decisions (user)"),
`thoughts/shared/plans/2026-11-09-city-background.md`, art direction Mega Man X SNES style, art locked at v9.

Reference audited again on 2026-11-09 (github.com/skeddles/balloon-fight-arena, default branch): `scripts/character.gd`,
`scripts/player-controller.gd`, `scripts/computer-controller.gd`, `scripts/level.gd`, `scripts/debug_launcher.gd`,
`scenes/character.tscn`, `scenes/characters/*.tscn`, all eight `scenes/stages/*.tscn`, `project.godot`, `CHANGELOG.md`, `README.md`.
Line numbers below refer to those files as fetched on that date. The repo has NO license and is a fangame of a commercial game:
only behaviour is taken, in our own words and numbers. No code, names, characters, art, sounds, music or layouts are copied.
On-screen names in this doc (Gumbirds, earlier Bubblegum Brawl, gas pods, Rooftop Arena, Gum Trip) are ours and are working names.

Words: **flier** = any flying character (player or computer). **Pod** = the lift device a flier hangs from (our balloon, D3).
**Stomp** = the feet zone of one flier entering the pod zone of another.

## Corrections (claims in the previous draft that were wrong about the reference)

1. **Ceiling bounce minimum is 50 px/s, not 100.** `character.gd` 190-192 calls the bounce with 100 and then again with 50 for the
   same contact; the second call recomputes velocity from the contact data and overwrites the first, so the 100 never takes effect.
   The old "hard push down stops ceiling camping" claim is false for the reference. Ceiling = same as every other bounce surface.
2. **A pod-less flier that is touched does not stop the toucher bouncing.** Lines 183-187: the toucher still bounces (min 50) after the
   pod-less flier is killed. Only when the flier itself is pod-less (179-182) does it die with no bounce.
3. **The parachute is not default behaviour.** `HasParachute` defaults to false (line 21); only some characters (for example
   `balloon-bird-green.tscn` line 10) have it. The default last-pod-in-air result is the dead fall (lines 231-237). The old doc made
   the chute the enemy default and invented a "re-inflate one tier higher" rule; the reference re-inflates only through the
   ground refill with stored pods (lines 104-121, 258-266), never by timer.
4. **Parachute sway is not a smooth 3 s sine.** Line 70 uses `ticks_msec / 500` fed to `sin` and then a 0.1 lerp. The division is
   integer division in GDScript (unverified by running it), so the sway target changes in steps every 0.5 s following sin(n) for
   integer n. Amplitude 32 px/s and follow fraction 0.1 are right.
5. **Starting pods are 0 to 4 and stored pods 0 to 95** (`debug_launcher.tscn` max_value on the two spin boxes). The changelog's
   "up to 99" and the old doc's "1 to 99" are stale.
6. **No tie-break exists for simultaneous stomps** (the old doc invented "higher feet wins"). Each flier's pod zone reacts
   independently to the other's feet zone (`character.gd` 280-300), so both can pop in one frame.
7. **Jump without pods is -100 px/s** (twice the pod jump, lines 94-98). The old doc had no pod-less jump at all.
8. **Gravity with 1 pod equals gravity with 2, 3 or 4 pods** (0.4 x 200 = 80 px/s^2, line 86-87). The old 1-pod 107 px/s^2, the
   180 px/s fall cap, the parachute 30 px/s cap, the stomp sideways push, the respawn invulnerability, the ground-friction snap to
   zero, the stomp tie-break and the 40 s anti-camp timer are not in the reference and are removed.
9. **Fixed point is widened to 16 fractional bits for velocity.** 80 px/s^2 is 5.69 in 8.8 and rounds to 6 (5 percent too heavy);
   with 16 fractional bits it is 1456 (0.02 percent). Same for 20 px/s^2 (1.42 in 8.8, rounded to 1, 30 percent too light).
   This keeps "numbers match the reference". Veto in the Reference audit table, row "fixed point".
10. **Side edges: see section 1.5.** The reference source shows bouncing boundary shapes on both sides in all eight stages and no
    wrap code anywhere. The user states the reference wraps. This doc writes wrap (user instruction) and records that the wrap
    line could not be found.

## Reference audit

Source column: file and line (or constant) in the reference. Doc value column: value in this doc after revision.
Units: reference px = our px (k = 1.0); 60 Hz; `px/s` converted per frame in 1.3.

| Item | Reference value | Source | Doc value |
|---|---|---|---|
| Physics rate | engine default 60 Hz (no override set) | `project.godot` (no physics tick key) | 60 Hz |
| World gravity | 200 px/s^2 | `project.godot` 183 `2d/default_gravity` | 200 (dead fall) |
| Gravity, 1 to 4 pods, airborne | 0.4 x world = 80 px/s^2, same for all counts | `character.gd` 37, 86-87 | 80, same for 1 to 4 pods |
| Gravity, 0 pods, airborne, not falling | full 200 | `character.gd` 83-84 | 200 |
| Gravity on ground | none (only applied when not on floor) | `character.gd` 83, 86 | none |
| Flap | on button press edge only: vy moves 0.2 of the way to -100 px/s | `character.gd` 38-39, 102; `player-controller.gd` 19 | same |
| Flap needs pods | yes (`current_balloons > 0`) in air | `character.gd` 99 | same |
| Steering in air | only on a press frame with direction held: vx moves 0.2 to dir x 100 | `character.gd` 128-129 | same |
| Drag in air | none | `character.gd` (no air branch), `CHANGELOG.md` 44 | none |
| Ground walk | vx = dir x 100 at once | `character.gd` 33, 126-127 | same |
| Ground friction | no direction: vx moves 0.2 to 0 per frame, no snap | `character.gd` 29, 130-131 | 0.2 per frame, no snap |
| Jump off ground | vy = -50 with pods, -100 without | `character.gd` 35, 94-98 | same |
| Fall speed cap | none | `character.gd` (no clamp anywhere) | none |
| Bounce rule | velocity reflected about contact normal; if result slower than min, set to min along normal | `character.gd` 208-217 | same |
| Bounce min: tiles/walls/ceiling (air only) | 50 (ceiling 100 is overwritten, see Correction 1) | `character.gd` 189-193 | 50 |
| Bounce min: flier vs flier | 50 | `character.gd` 187 | 50 |
| Bounce min: kill tile | 25, and pop one pod | `character.gd` 169-175 | 25 |
| Bounce on ground contact | none (bounce branch needs not on floor) | `character.gd` 189 | none |
| Left, right edge | boundary shapes at x = 0 and x = 640, group "bounce" (bounce); no wrap code found | `scenes/stages/lake.tscn` 47-63 (same in all 8 stages); `CHANGELOG.md` 11-12 | wrap per user (see 1.5) |
| Ceiling | boundary shape at y = 0, group "ceiling" | `lake.tscn` 55-58 | y = 16 (below HUD fix rows 0 and 1), bounce |
| Bottom | "water" boundary at y = 360 (screen bottom): kills at once, even with pods; no bounce | `lake.tscn` 90-94; `character.gd` 201-206 | screen bottom kills at once |
| Dead fall | vx = 0, vy = -50, full gravity, collisions off, removed below y = 400 | `character.gd` 242-252, 64-66 | same (removed 40 px below screen) |
| Pod pop invulnerability | 1000 ms; parachute 500 ms | `character.gd` 235, 240 | 60 frames; 30 frames |
| Pod pop sources | stomp, kill tile | `character.gd` 175, 300 | same |
| Stomp trigger | other's feet zone enters my pod zone; ignored if I am invulnerable, have 0 pods, or the other is falling | `character.gd` 283-290 | same |
| Stomp result | victim speed 40, attacker speed 75, directions 90 degrees either side of the line angle; victim loses one pod | `character.gd` 292-300 | same magnitudes |
| Last pod popped in air | dead fall by default; parachute only if `HasParachute` | `character.gd` 226-237, 21-22 | dead fall by default (D10) |
| Last pod popped on ground | stays standing, pod-less, can walk and jump | `character.gd` 228-230 | same |
| Parachute | gravity 0.1 x world = 20 px/s^2, no cap; vx lerps 0.1 to sin(n) x 32, n changing every 0.5 s | `character.gd` 22, 68-73 | same, in D10 profile |
| Touch pod-less flier | the pod-less flier dies (dead fall) | `character.gd` 179-186 | same |
| Pod refill | B press on ground, vx < 5, stored pods > 0, pods < 4; four fill steps, cancelled by move or jump | `character.gd` 104-121, 254-266 | same; stored count N12 |
| Pod count limits | start 0 to 4, stored 0 to 95 | `debug_launcher.tscn` (SpinBox max_value), `debug_launcher.gd` 111-112 | start N12, stored N12 |
| Controls | A flap, B fill, Y special (only characters with dropping); stick left/right; nothing for up/down | `player-controller.gd` 11-21; `character.gd` 133-145 | A, B, none (Y unused) |
| Lives | none: pod-less in air or in water = out of the match, removed | `character.gd` 66, 375; `level.gd` 15 | NOT IN REFERENCE (N2) |
| Respawn | none | `character.gd` (no respawn path) | NOT IN REFERENCE (N5) |
| Scoring, high scores | none | whole repo | NOT IN REFERENCE (N3) |
| Waves, 1P campaign | none: match of 2 to 4 fliers (human or computer), ends when one is left | `level.gd` 14-25; `debug_launcher.gd` 76-82 | NOT IN REFERENCE (N1) |
| Win rule | last flier alive | `level.gd` 15-17 | same |
| Timers | invulnerability only; computer re-think 500 ms | `character.gd` 60, 314-316; `computer-controller.gd` 9 | same; no anti-camp timer |
| Randomness | computer re-think jitter +-125 ms; random stage pick | `computer-controller.gd` 86; `debug_launcher.gd` 87 | physics deterministic; N9 |
| Computer players | re-think each 500 ms: nearest rival; states chase, flee, fill; one flap per 500 ms | `computer-controller.gd` 5-69, 75-86 | same (N4 for difficulty) |
| Body size | capsule 8x22 with pods, 8x14 without; feet zone 6x10; pod zone 12x16 | `scenes/character.tscn` 15-21, 524-531 | own art boxes (1.6), same roles |
| Max fliers | 4 (`MAX_PLAYERS`) | `debug_launcher.gd` | 8 on screen (own engine limit, 5.1) |
| Hazards | kill tiles only | `lake.tscn`, `character.gd` 169-175 | kill tiles only; others N6 |
| Fixed point | engine floats | n/a | 16 fractional bits for velocity and position (Correction 9) |
| Scale | NES-size sprites in a 640x360 room | `project.godot` 23-24 | k = 1.0, 320x224 (kept pick) |

## 0. What the reference does (behaviour summary, own words)

- 60 Hz physics, 640x360 room, integer upscaling. Body capsule about 8x22 with pods, 8x14 without.
- Airborne with at least one pod: gravity 80 px/s^2 for 1, 2, 3 or 4 pods. No pods and airborne (and not parachuting): full 200.
- Flap only on a press edge, with pods, in the air: vertical speed moves 20 percent of the way to -100 px/s.
- Horizontal speed in the air changes only on a press frame with a direction held: 20 percent of the way to dir x 100 px/s.
  Between presses: no drag, no steering.
- On the ground: horizontal speed set to dir x 100 at once; no direction: decays 20 percent per frame, no snap. Jump: -50 px/s (-100 without pods).
- No terminal fall speed. No gravity on the ground.
- Surfaces reflect velocity, with a minimum speed after the bounce of 50 (tiles, edges, ceiling, other fliers) or 25 (kill tiles, which also pop one pod).
  No bounce while standing on the floor.
- Stomp: feet zone enters pod zone, victim not invulnerable and has pods: victim loses a pod, is pushed 40 px/s, attacker 75 px/s,
  roughly apart and perpendicular to the line between them. Victim invulnerable 1 s.
- Last pod popped: in the air, dead fall (vx 0, vy -50, full gravity, no collision, removed below the screen), or, for characters
  with the parachute ability, a parachute (gravity 20, sway, 0.5 s invulnerable). On the ground: stays, pod-less.
- A pod-less flier touched by another dies (dead fall); a pod-less flier that touches another also dies.
- Water at the screen bottom: instant death, even with pods.
- Match: 2 to 4 fliers, human or computer, last flier alive wins. No lives, no score, no waves, no respawn.
- Stored pods refill on the ground with B (four steps), up to 4 pods.
- Computer: re-think about every 500 ms (+-125 ms), nearest rival, chase / flee / fill, at most one flap per 500 ms.

What we keep: all of the above. What we add (all NOT IN REFERENCE, section 3): the 1P framing, original enemies' difficulty ramp,
score table, theme, a second endless mode.

## 1. Physics spec (320x224, 60 Hz)

### 1.1 Scale: 1 reference px = 1 screen px (k = 1.0, user pick D1)

> Superseded 2026-11-10 (user decision): the game uses scale 0.5 throughout; see D1 and src/core/flier.h.

- The reference unit is an NES sprite pixel; its fliers are 16 px wide and the constants were tuned against that. Our screen is
  close to an NES screen, so at k = 1 speed, jump height and stomp timing in body lengths are the reference's. Only the room is smaller.
- Top air speed 1.667 px/frame stays above one pixel per frame (no uneven stepping).
- Flier sprite about 16 px wide body and 32 px tall with pods (D2, one Neo Geo sprite column).
- Conversion used everywhere: `v = round(px_per_s / 60 * 65536)`, `a = round(px_per_s2 / 3600 * 65536)`, `frac = round(f * 65536)`.

### 1.2 Integer rules (host and m68k must agree)

- Velocity and position: `int32_t` with 16 fractional bits (positions up to 320 px = 21 million, fits). Pixel position = `pos >> 16`.
  Reason: 80 px/s^2 must be 1456 not 6 (Correction 9). Whole-pixel sprite positions come from the shift.
- Helper `approach_frac(v, target, frac)`: `d = target - v; s = (|d| * frac) >> 16; if (s == 0 && d != 0) s = 1; v += sign(d) * s`.
  `|d| * frac` fits 32 bits (|d| below 2^18 for any speed here, frac below 2^14 gives 2^32 at the limit; use `uint32_t`). Symmetric
  left and right (a plain shifted `(d*frac)` floors negative numbers).
  The reference lerp has no minimum step; the 1-unit minimum only changes values below 1/65536 px per frame.
- No `/` or `%` in per-frame code (libgcc __modsi3 lesson).
- Order per flier per frame, equal to the reference: 1 gravity (only if not on floor), 2 flap/jump, 3 steer / walk / friction,
  4 move and resolve contacts (x pass then y pass with axis-aligned boxes; reference uses engine slide-and-collide),
  5 flier-flier, stomp, kill-tile, water contacts.

### 1.3 Constants (src/core/tuning.h names proposed)

| Name | Reference | Fixed value | Meaning |
|---|---|---|---|
| FLY_GRAVITY | 80 px/s^2 | 1456 | airborne with 1 to 4 pods |
| FALL_GRAVITY | 200 px/s^2 | 3641 | no pods airborne, dead fall |
| CHUTE_GRAVITY | 20 px/s^2 | 364 | parachute descent, no cap |
| CHUTE_SWAY_X | 32 px/s | 17476 | sway target amplitude |
| CHUTE_SWAY_FRAC | 0.1 | 6554 | follow fraction per frame |
| CHUTE_SWAY_STEP | 0.5 s | 30 frames | sway target = sin(n) x amplitude, n up by 1 each step; 64-entry table of sin(0..63 radians) |
| TOP_SPEED | 100 px/s | 109227 | flap target (up) and steer target (sideways) |
| FLAP_FRAC | 0.2 | 13107 | flap fraction |
| STEER_FRAC | 0.2 | 13107 | steer fraction, only on a press frame with direction |
| GROUND_SPEED | 100 px/s | 109227 | walk speed, set at once |
| GROUND_FRICTION_FRAC | 0.2 | 13107 | decay with no direction, no snap |
| JUMP_SPEED | 50 px/s | -54613 | jump with pods; pod-less jump = 2x (-109227) |
| BOUNCE_MIN | 50 px/s | 54613 | tiles, edges, ceiling, flier vs flier |
| BOUNCE_MIN_KILL | 25 px/s | 27307 | kill tile (also pops one pod) |
| STOMP_VICTIM | 40 px/s | 43691 | speed given to the flier that lost the pod |
| STOMP_ATTACKER | 75 px/s | 81920 | speed given to the flier that stomped |
| DEAD_FALL_START | 50 px/s | -54613 | vx = 0, vy = this, then FALL_GRAVITY, no collision |
| INVULN_POD_POP | 1000 ms | 60 frames | after a pod (not the last) is lost |
| INVULN_CHUTE | 500 ms | 30 frames | after the last pod pops into a parachute |
| REFILL_STEPS | 4 | 4 | fill steps to add one pod |
| THINK_INTERVAL | 500 ms (+-125 ms) | 30 frames (+-8) | computer re-think and flap limit |

All fliers share one physics function. Per-character stat differences exist in the reference (for example faster, higher jump,
weaker gravity) as exported stats; we use the defaults for every flier except where N4 says otherwise.

### 1.4 States and what applies in each

| State | Gravity | Input | Collides with |
|---|---|---|---|
| FLY (1 to 4 pods) | FLY_GRAVITY | flap, steer on flap | platforms, edges, fliers, kill tiles |
| GROUND (pods > 0) | none | walk, flap = jump, B = refill | same |
| GROUND (0 pods) | none | walk, jump at 2x | fliers (any touch kills) |
| AIR (0 pods, no parachute ability) | does not occur: becomes DEAD_FALL at once | | |
| CHUTE (0 pods, parachute ability) | CHUTE_GRAVITY, sway, no cap | none | platforms (lands, becomes pod-less ground), fliers |
| DEAD_FALL | FALL_GRAVITY | none | nothing; removed when y > 224 + 40 |

Reference quirks kept: steering needs a press frame; flapping without pods does nothing; B refill needs |vx| small and standing.

### 1.5 Edges, ceiling, bottom

- **Side edges: horizontal wrap (user states the reference wraps; D7).** A flier leaving x = 320 reappears at x = 0 with unchanged
  velocity and the reverse. Seam: objects within a body width of an edge are drawn twice and collision tests run with the other
  copy shifted by 320. **Source status: no wrap line found.** All eight stage files define left and right boundary shapes in the
  "bounce" group (`lake.tscn` 47-63 and the same block in `canyon`, `cliffs`, `island`, `mountain`, `ocean`, `pencilvania`,
  `terrace`), `character.gd` 189-193 bounces off them, `CHANGELOG.md` 4.0.0 says "bounce off tiles and world boundaries", and
  grep of every script found no `wrap`, `posmod` or position reset. The user should confirm which reference build they mean
  (an older release than 4.0.0 would be the place to look). Until confirmed: wrap, as instructed.
- Ceiling at y = 16 (below the HUD's top fix rows 0 and 1; the HUD also uses fix row 27 at the bottom, see 5.2a): reflect, minimum BOUNCE_MIN (50 px/s). Same rule as any bounce surface.
- Platform tops: standing (on floor) = no bounce, no gravity. Platform sides and undersides in the air: reflect, minimum 50.
  Kill tiles: reflect minimum 25 and pop one pod (skipped when invulnerable).
- Bottom: the screen bottom (reference water at the bottom edge). A flier whose box reaches y = 224 dies at once in any state,
  with or without pods, and does not bounce. Our theme: street/void gap instead of water.
- Gum Trip mode edges: section 4 (left edge pushes, right edge blocks).
- Cabinet overscan unverified: if the MiSTer CRT cuts the side 8 px, the wrap seam moves (one tuning constant).

### 1.6 Collisions between fliers

Boxes relative to the 16x32 figure (placeholders until art; roles equal the reference capsules: pod zone 12x16, body 8x22 with
pods or 8x14 without, feet 6x10):
- pod box: x 2..14, y 0..12 (only while pods > 0)
- body box: x 4..12, y 10..30 (shrinks to the pod-less box when pods = 0)
- feet box: x 4..12, y 26..32

Per pair per frame (both directions evaluated independently):
1. A flier that is DEAD_FALL: no interaction.
2. Body contact where this flier has 0 pods and is not DEAD_FALL: it dies (DEAD_FALL), no bounce for it.
3. Body contact where the other flier has 0 pods: the other dies; this flier bounces (minimum 50). Both rules apply per contact.
4. Otherwise body contact: both reflect (minimum 50).
5. A's feet box inside B's pod box, B not invulnerable, B has pods, A not DEAD_FALL: B loses one pod, B speed 40 and A speed 75 in
   directions 90 degrees either side of the A-to-B line angle; B invulnerable. No tie-break: if both feet-in-pods overlaps hold in
   the same frame, both flier lose a pod (invulnerability applies from the first processed).
Pod loss: pods = pods - 1. At 0 pods: in the air without parachute ability, DEAD_FALL; with parachute ability, CHUTE (invulnerable
30 frames); on the floor, stays standing pod-less.

### 1.7 Host-testable numbers (computed with the rules above, 16-bit fractions; scratch script deleted, rebuild from 1.2)

vy displayed in 8.8 units (px/frame x 256) for readability.

Flap from rest, no gravity between taps (vy after N taps):

| Taps | 1 | 2 | 3 | 4 | 5 | 10 | 15 | 20 | 30 |
|---|---|---|---|---|---|---|---|---|---|
| vy | -85 | -154 | -208 | -252 | -287 | -381 | -412 | -422 | -426 |

Steer from vx = 0 with right held: same magnitudes, positive. Symmetry is a test (left and right reach the same magnitude).
Steer reversal from +427 with left held, per tap: 256, 119, 10, -77, -147, -203, -248, -283, -312, -335.

Free fall from vy = 0 (vy / pixels fallen, truncated), same for 1, 2, 3, 4 pods:

| Frames | 1 | 10 | 30 | 60 | 120 |
|---|---|---|---|---|---|
| Pods (g 1456, no cap) | 6 / 0 | 57 / 1 | 171 / 10 | 341 / 40 | 682 / 161 |
| Parachute (g 364, no cap, no sway) | 1 / 0 | 14 / 0 | 43 / 2 | 85 / 10 | 171 / 40 |
| Dead fall (start -213, g 3641) | -199 / 0 | -71 / -5 | 213 / 0 | 640 / 51 | 1493 / 303 |

One tap from rest: rises for 16 frames, about 2.4 px. Pod count makes no difference.

Steady tapping, net vertical speed after settling (negative = rising), identical for every pod count:

| Tap every N frames | 4 | 6 | 8 | 10 | 12 | 15 | 20 |
|---|---|---|---|---|---|---|---|
| px/s | -76.7 | -64.7 | -52.7 | -40.7 | -28.7 | -10.7 | +19.2 |

Hovering takes about 3 taps per second with any pod count (the old "5 per second with 1 pod" is removed).

Ground friction from vx = 427, no input: 341 after 1 frame, 273 after 2, 140 after 5, 46 after 10, 15 after 15, 5 after 20, 1
after 30, 0 after 31 (the 1-unit minimum step finishes it; the reference lerp only approaches 0).

The host test asserts every number in these tables exactly, using the helper in 1.2.

## 2. Controls (Neo Geo stick + A/B/C/D)

| Input | In play | Source |
|---|---|---|
| A | Flap (press edge only); on the ground: jump | `player-controller.gd` 12, 19 |
| B | Refill a pod on the ground (press edge; needs stored pods) | `player-controller.gd` 13, 20; `character.gd` 107-117 |
| C | Nothing (reference Y "action" only exists for the dropping ability, not used) | `character.gd` 133-145 |
| D | Nothing | |
| Stick left/right | Steer on a flap press frame in air; walk on the ground. Digital: -1, 0, +1 | `player-controller.gd` 11, 18 |
| Stick up/down | Nothing | |
| Start | Join (2P) per Neo Geo convention (MVS has no pause) | cabinet convention, not gameplay |

The B auto-flap and the dive option are removed. Name entry for the score table (if N3 keeps one) uses stick + A.

## 3. Main mode: arena match (working name Rooftop Arena)

### 3.1 What equals the reference

User decision 2026-11-10 after playtest (gravity, "too floaty like i am on the moon"): gravity x1.5 (FLY 728 to 1092, FALL 1820 to 2730), launch speeds x sqrt(1.5) so peak height stays the same (ground jump -27307 to -33444, pod-less -54613 to -66887, air flap lerp target -65536 to -80268, new FLIER_FLAP_TARGET_VY). This supersedes the 80 / 200 px/s^2 values in section 1.3 for the arena.

- A match has 2 or more fliers on one screen; humans and computer fliers mix freely; last flier alive wins (`level.gd` 14-25).
- Every flier is equal: any flier can stomp any other (no teams, no friendly-fire rule). 2P on one cabinet = two humans who can stomp
  each other, plus computer fliers.
- Arena 384 px wide with a wrapping camera (64 px of scroll): the camera follows the midpoint of the human players and holds at the seam, where an edge marker shows. Superseded 2026-11-10 (user decision): the earlier "one screen, no scroll" rule; see the 384 px arena decision and src/core/bg_scroll.c. The city parallax layers stay behind (our art). Platform layouts are ours, at most 8
  rectangles per stage; kill tiles are the only hazard.
- Stages: several layouts; the reference picks a stage by menu or at random (`debug_launcher.gd` 86-88).
- Computer fliers follow the reference AI exactly (states, 500 ms think, one flap per think, nearest target, thresholds in
  `computer-controller.gd` 15-69): FILL when pod-less and the target is more than 50 away, or standing with pods below 4 and stored
  pods and the target farther than 150; FLEE when pod-less, or within 75 and not above the target by 32; CHASE otherwise. Chase and
  flee steer when the horizontal direction component exceeds 0.25 and flap when the vertical component is below 0.5.
- Pods: starting pods and stored pods are per match settings in the reference (N12 sets ours).

### 3.2 NOT IN REFERENCE (decide before implementation; recommended first)

User decision 2026-11-10 after playtest (stomp, "i cant pop gums but they can pop mine"): stomp boxes follow the drawn art. Feet box 10 px wide (half 5) and 4 px high at the feet bottom; gum box 18 px wide with 2 or more balloons, 12 px with one, from 20 to 41 px above the owner's feet bottom. Same rule for player and computer. The old 3x5 feet and 6x8 gum boxes are gone. Body box (4 px wide) unchanged, open.

N1. **1P structure.** The reference has no 1P mode and no waves. (a) 1P vs computer fliers as a match, rematch on a new stage after a win
    (matches the reference loop); (b) endless waves of computer fliers (needs N2 to N4); (c) fixed best-of rounds.
N2. **Lives.** The reference has one life per match. (a) one life per match, game over on loss, counted in rounds won (recommended);
    (b) 3 lives per run; (c) 3 lives with extras every 50000.
N3. **Score and high-score table.** None in the reference. (a) points per stomp/defeat plus bonus per match won, one table
    (recommended, needed for the cabinet competition); (b) table of consecutive matches won only; (c) no table.
N4. **Computer difficulty.** The reference has one AI and per-character stat profiles. (a) one AI, difficulty only by stat profile per
    opponent (speed, flap strength, gravity as reference characters vary) and count (recommended); (b) three tiers with own think
    intervals (the old Scout/Raider/Ace); (c) none, fixed.
N5. **Respawn.** None in the reference (a dead flier is removed). (a) no respawn; a loss ends the run under N2a (recommended);
    (b) respawn at the spawn ledge with 1 s invulnerability under N2b/c; (c) respawn only for humans.
N6. **Other hazards** (patrol drones, updraft vents, moving cables). Reference has static kill tiles only. (a) kill tiles only
    (recommended); (b) add updraft vents later; (c) add drones.
N7. **Bonus wave.** Not in the reference (the solo scrolling run covers this need, see section 4). (a) none; Gum Trip mode instead
    (recommended); (b) bonus round every 4th match.
N8. **Co-op teams.** The reference is free-for-all. (a) 2P free-for-all with computer fliers, humans may stomp each other
    (recommended, equals the reference and the D9 pick); (b) teams without friendly stomps; (c) 1P first, 2P later.
N9. **Randomness.** Reference physics is deterministic; random only in computer think jitter and stage choice. (a) a fixed seed per
    match number for jitter and stage (fair for the office competition, recommended); (b) free random per run.
N10. **Stored pods and starting pods.** Reference: start 0 to 4, stored 0 to 95 as launcher settings, defaults not found. (a) start
    2 pods, stored 0 (refill mechanism present, so the user's D12 "no refill" holds); (b) start 2, stored 2; (c) start 3, stored 0.
N11. **Parachute profile.** Reference characters differ: default has no parachute, some have it. (a) dead fall for all (default
     profile, recommended); (b) parachute for computer fliers only (the user's D10 pick, matches a reference profile); (c) parachute for all.

Items removed because the reference has no rule and the user rule forbids invention: heavier 1-pod gravity, B auto-flap, fall cap,
stomp sideways push, respawn invulnerability, friction snap, stomp tie-break, anti-camp timer, re-inflate by timer and tier, DOWNED
and INFLATE states, pod-pop score chain, lasers.

### 3.3 Scoring placeholder (only if N3a)

Points are ours (reference has none); keep the table minimal so it can change: stomp pop 500, defeat of a pod-less flier 1000,
fall into the bottom 250, match win 1000, no pod lost in match +2000. Marked NOT IN REFERENCE, values for the user to tune.

## 4. Gum Trip mode (solo, endless; decisions of 2026-11-10, tuning numbers and hazards open)

### 4.4 Playtest tuning shared with Gum Trip

User decision 2026-11-10 after playtest: Gum Trip uses the same flier physics as the arena, so the gravity x1.5 and art-sized stomp boxes of sections 3.1 and 3.2 apply here too.

Not part of the reference. Physics identical to 1. Renamed from "Gum Trip" on 2026-11-10 (user decision).

Settled 2026-11-10 (user, by multiple-choice questions):
- Gum level replaces lives. The flier's gum bubble decays slowly during the run; gum pickups, collected on touch, grow it back.
  The player must keep the gum level up. The user's words: "the gums should be slowly decaying and we add pickups that are gums that
  makes them grow again so you have to keep the gum level up during the gum trip". The alternative the user floated, a blow button
  for a leaking gum, was not chosen. Supersedes the earlier T1 (lives) and T2 (what pickups are) points.
- Scroll: endless forced scroll, no wrap. The left screen edge pushes the flier, the right screen edge blocks it. This needs camera
  code separate from the 384 px wrapping arena camera (1.5). Superseded 2026-11-10 (user decision): the earlier skeleton rule that the
  right edge reflects (bounce rule, min 50); the right edge now blocks.
- Rooftops: the flier is always airborne; the roofline below is scenery only. Superseded 2026-11-10 (user decision): the placeholder
  "rooftops (landing allowed)". Supersedes T5.
- Enemies: rival Sootlings appear during the run and can pop the player's gum. The user chose this over "no enemies". Supersedes T6.
- Gum level zero: the gum is gone, the flier falls and the run ends. Hits from hazards and rival Sootlings take a chunk of gum
  instead of ending the run outright.
- Streak (T3): only a hit breaks the pickup streak; a missed pickup that scrolls off does not.
- Course (T7): random per run.
- Unlock (T8): the mode is always selectable at start for one player and has its own high-score table.

Core loop (kept from the skeleton):
- The screen scrolls right over the city endlessly. Same flier physics as the arena.
- Scroll speed starts at 0.75 px/frame and ramps to 1.25 px/frame, below top air speed so the player can always reach the right side.
- Bottom kills at once (as arena).
- Hazards (placeholders): kill tiles / spark cables, drones, searchlight beams, vents. Pickups: gum pickups (settled above); other
  score items are placeholders.

Score (fixed part): distance 1 point per 8 px scrolled; pickups with a streak counter that grows per pickup and resets on a hit
(a missed pickup does not break it); every N pickups the scroll gets a step faster and pickups are worth more.

Open points:
- T4: which hazards, their density curve over distance (to tune), any fixed sequences vs random?
- Decay rate and refill amount per gum pickup: to tune.
- Size of the gum chunk a hit takes (hazard and rival Sootling), and whether rival Sootlings drop pickups (to tune).
- Rival Sootling behaviour in a forced scroll (open).

## 5. Engine needs (input to the object-pool work)

### 5.1 Object counts (maximum on screen at once)

| Kind | Max | Notes |
|---|---|---|
| Players | 2 | |
| Computer fliers | 6 | includes CHUTE, standing pod-less, DEAD_FALL (same object) |
| Hazards | 8 | kill tiles are platform data; moving hazards only if N6 or Gum Trip mode |
| Pickups | 10 | Gum Trip mode (and N7b) |
| Projectiles | 0 | laser dropped (reference has none) |
| Effects | 8 | pod pop puff, defeat flash, score popups |
| Platforms | 8 | static rectangles per stage, not pool objects |

Pool: one array of 32 objects with a kind field, or one pool per kind. No allocation during play; spawn fails quietly when full.

### 5.2 Sprite budget (381 hardware sprites, 323 slots used, 96 per scanline)

| User | Sprites | Notes |
|---|---|---|
| City background (existing) | 110 (0..109): sky 20, far 21, mid A 22, mid B 23, near 24 | slots 110..119 free for clouds and airship |
| Fliers | 8 x 1 = 8 (16x32, one column each); wrap seam duplicates up to 8 more | |
| Platforms (islands) | 41 (slots 120..160, drawn by `src/island.c`) | widths from `src/core/stage.c`: 80, 80, 112, 80, 80, 96, 64, 64 px = 5 + 5 + 7 + 5 + 5 + 6 + 4 + 4 = 41 strips of 16 px, one sprite per strip when an island is one tile tall |
| Hazards | 8 x 2 = 16 | |
| Pickups | 10 x 1 = 10 | |
| Effects | 8 x 1 = 8 | |
| Total | slots 0..322 = 323 used of 381 (planes 110 + free 10 + islands 41 + pool 96 + hero 3 + hazard strip 48 + rain 10 + spray 4, with one gap slot); the rows above are the design maxima | slot ranges are in src/sprite_slots.h |

Island sprite room (user decision 2026-11-10): island heights are staggered, and islands that share scanlines are one tile tall there. The real worst-line peak is measured in MAME before any cut. The foreground edge cable reservation (2 sprites) is dropped by user decision 2026-11-10 and is not counted. The two 56 px islands are now 64 px so every island width is a multiple of 16 px.

Island looks: three looks, one per mood (moon night = roof chunk, ember dusk = garden slab, storm = airship deck; this pairing is a default the user may change), with one island palette on screen at a time. Drafts: `thoughts/shared/drafts/2026-11-10-islands/`; final sheets: `thoughts/shared/drafts/2026-11-10-islands-final/` (user verdict 2026-11-10: build as drawn).

Accepted island layout (user decision 2026-11-10; x, y, width in px, every island one tile tall; worst scanline 7 island sprites on lines 124..139). A user playtest of jump feel is owed after the build. `src/core/stage.c` is the source of truth once the build lands; until then the code may still hold old values.

| Island | x | y | Width |
|---|---|---|---|
| 1 | 0 | 148 | 80 |
| 2 | 136 | 128 | 112 |
| 3 | 32 | 92 | 80 |
| 4 | 280 | 108 | 80 |
| 5 | 144 | 68 | 96 |
| 6 | 0 | 36 | 64 |
| 7 | 320 | 52 | 64 |
| 8 | 304 | 164 | 80 |

Scanline limit is the real constraint: the background planes, islands (worst 7 on lines 124..139) and 8 fliers share the line; the recorded worst line is 89 of the project limit 90 (BG-1c report, `thoughts/spot/todos.md`). The roof ring no longer exists as a separate reservation.

### 5.2a HUD and title (user decisions 2026-11-10)

- Title logo: option A, stretched gum lettering drawn as sprites, with an inflating bubble and a drip.
- Font: option A "Gumdrop", 8x8 characters with 8x16 score digits.
- HUD layout: "corner tags" on fix rows 0, 1 and 27, no band across the screen.
- Content: six score digits, gum count icons, and a PRESS START join prompt in the player 2 corner.
- Final sheets: `thoughts/shared/drafts/2026-11-10-hud-title-final/` (user verdict 2026-11-10: build as drawn).
- Fix row 27 sits over the bottom hazard strip area: to check in build.

### 5.3 Collision types (axis-aligned boxes, integer pixels)

1. Flier body vs platform: stand on top (no bounce when on floor); reflect on sides and underside in the air.
2. Flier vs edges: wrap at the sides (arena), ceiling reflect, bottom kill.
3. Flier feet vs flier pods: stomp.
4. Flier body vs flier body: reflect; pod-less flier dies.
5. Flier vs kill tile: reflect min 25, pop one pod.
6. Flier body vs pickup: collect (Gum Trip mode).

Per-frame worst case about 230 box tests (about 2 ms on the 68000) plus the seam copies. The 60 Hz loop fix must land first (todos).

### 5.4 Other engine needs

- Edge-triggered input per player; held state for the stick.
- A 64-entry sine table (sin of 0..63 radians) for the parachute sway target.
- Seeded PRNG (16-bit xorshift or LFSR, no division) for computer jitter (N9).
- Score and score table in backup RAM if N3a/b. Mode select screen (two entries, full English words).
- Wrap-aware distance for the computer AI is not specified by the reference (it uses plain distance); keep plain distance.

## 6. Decisions D1 to D17 after the reference check

Settled (user pick, or reference rule):

1. **D1 scale** k = 1.0 (user pick 2026-11-09), REPLACED 2026-11-10 by user decision: uniform 0.5 for the whole game (room, distances, speeds, body), as in the reference spec 2.1 and src/core/flier.h. Section 1.1 numbers are k = 1.0 and superseded by flier.h.
2. **D2 sprite** 16x32 (user pick, kept).
3. **D3 theme** glowing gas pods (user pick, kept).
4. **D4 1-pod gravity** reference: same as other pod counts, 80 px/s^2 (`character.gd` 37, 86-87). User pick "heavier" overridden.
5. **D5 buttons** reference: A flap on press edge, B refill; no auto-flap (`player-controller.gd`). User pick overridden.
6. **D6 stick down** reference: nothing (the only down-like ability is a per-character special on Y, unused).
7. **D7 side edges** wrap (user statement); source line not found, see 1.5.
8. **D8 fall cap** none (reference has none, user pick).
9. **D9 2P** reference: free-for-all, all stomps allowed (user pick friendly stomps matches). See N8.
10. **D10 defeat chain** reference: stomp pops one pod; last pod in air = dead fall, or parachute only for parachute characters;
    pod-less touched = dies; re-inflate only by ground refill with stored pods. User pick parachute kept as profile choice N11;
    "re-inflate one tier higher" removed.
11. **D11 lives** NOT IN REFERENCE, N2.
12. **D12 pod refill** reference has it (B, four steps, stored pods); user pick "no refill" holds with stored = 0 (N10a).
13. **D13 laser** reference has no projectile: dropped.
14. **D14 randomness** reference deterministic physics; N9.
15. **D15 score tables** NOT IN REFERENCE, N3.
16. **D16 anti-camping** reference has none: removed.
17. **D17 bonus wave** NOT IN REFERENCE, N7.

Open for the user: N1 to N11 (section 3.2) and the Gum Trip point T4 and the numbers and rival behaviour listed in section 4; plus the wrap source question (1.5).

## Risks and unverified

- Wrap versus the reference's bouncing boundary shapes (1.5, Correction 10): user must confirm the build they mean.
- Parachute sway integer-division behaviour of the reference not run, read from source only (Correction 4).
- City ring scanline count: composed sprite peak 85 of the 96 per line limit (measured in MAME by the BG-1b build agent, moon mood only; dusk and storm not measured yet) (5.2). Cabinet overscan not checked (1.5).
- The 60 Hz main loop is not fixed yet; all per-frame numbers assume one game step per video frame.
- Box offsets in 1.6 are placeholders until flier art exists. Computer AI tuned against a 640x360 room: distances (50, 75, 150) may
  need a k-scaled review in the 320x224 room (not a rule change, a unit question).

## Decisions settled 2026-11-09

User rule: match the reference in everything. Where the reference has no rule, take the recommended option. Stop asking the user about these.

- Edges: horizontal wrap (user call; reference v4.0.0 source shows boundary bounce, user states the reference wraps).
- Precision: 16.16 fixed point for speed and position.
- N1 1P: match vs computer fliers.
- N2 lives: one per match.
- N3 score: points for stomps and wins, one top 10 table (the cabinet competition needs a table; the reference has none).
- N4 AI: one AI with stat profiles.
- N5 respawn: none.
- N6 hazards: kill tiles only.
- N7 bonus wave: none (Gum Trip mode covers it).
- N8 2P: free-for-all with stomps between humans, as in the reference.
- N9 randomness: as in the reference.
- N10 pod defaults: reference defaults.
- N11 parachute: dead fall for all (reference default).
- Gum Trip mode T1-T8 stay open until the engine runs. Superseded 2026-11-10 (user decision): T1, T2, T5, T6 are settled, see the next bullet; later the same day T3, T7, T8 were settled too; T4 stays open.
- 2026-11-10 (user): Gum Trip mode (renamed from Night Trip) uses a gum level instead of lives: slow decay, gum pickups on touch refill it; endless forced scroll without wrap (left edge pushes, right edge blocks, separate camera code); always airborne with the roofline as scenery; rival Sootlings appear and can pop the gum. Also decided 2026-11-10 (user): gum level zero ends the run (the flier falls); hazard and rival Sootling hits take a chunk of gum instead of ending the run; only a hit breaks the pickup streak, a missed pickup does not (T3); the course is random per run (T7); the mode is always selectable at start for one player with its own high-score table (T8). Open: T4 hazard mix and density curve, decay rate and refill numbers, gum chunk size per hit, rival Sootling behaviour in a forced scroll.
- 2026-11-10 (user): island widths follow the stage table (80 / 96 / 112 px, the two 56 px islands become 64 px); island looks are one per mood on one palette; title logo A, font A, corner tags HUD with six score digits, gum count icons and PRESS START in the player 2 corner; the foreground edge cable reservation is dropped. Later 2026-11-10 (user): islands art and HUD/logo/font sheets "build as drawn" (`thoughts/shared/drafts/2026-11-10-islands-final/`, `thoughts/shared/drafts/2026-11-10-hud-title-final/`); the island layout in 5.2 is accepted, with a user playtest of jump feel owed after the build.
