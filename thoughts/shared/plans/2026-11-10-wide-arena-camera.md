---
date: 2026-11-10
topic: Wide arena (384 px), camera follow and city parallax
tags: [plan, arena, camera, parallax, wrap, sprite-budget, hazard]
status: draft (design note; four user decisions open in section 8)
---

# Wide arena, camera follow and city parallax

User decisions taken as final (relayed by the parent session):

- The arena is 384 px wide. The screen stays 320 px. Camera travel is 64 px.
- The camera follows the midpoint of the human players, clamped to the arena.
- The side edges wrap at the arena width (384).
- Camera parallax on the city planes replaces "Orbit sway" (graphics plan D1).
- Sky objects (airship, clouds, far Sootlings) keep their own drift and do not follow the camera.

User quote: "all flying objects in the sky, the zepeliner etc should move like they do. but the city will look best
as a parallax so we should make the levels a little wider than the screen to allow parallax scrolling".

Correction to the brief: wrap does **not** exist today. `flier.c:221-230` bounces and clamps at the walls `hw` and
`FL_PX(FLIER_WORLD_W) - hw`, and `tests/host/test_flier.c:151-168` asserts "no wrap: a long flight never leaves
0..320". The gameplay design (`2026-11-09-flier-gameplay-design.md:204-217`, D7) specifies wrap at 320 with the seam
drawn twice, but no code implements it. This plan therefore adds wrap for the first time, at 384.

## 1. Where 320 is assumed today

Counted by `grep -rn "320\|FLIER_WORLD_W\|SCREEN_W\|BG_ART_COLS\|HAZARD_STRIP_COLS"` over `src/`, `tests/`,
`tools/`, then each hit read in context and sorted by meaning. Grep proves spellings only; the second check for the
x readers in gameplay was made from the call structure (`game_step_arena`, `ai_nearest`, `flier_step`), not from
grep. Not counted twice: art scripts in `thoughts/shared/drafts/` (draft tools, not product code).

Arena width (must become 384):

| Place | What |
|---|---|
| `src/core/flier.h:41` | `FLIER_WORLD_W 320`; comment `flier.h:6` |
| `src/core/flier.c:221-230` | wall bounce/clamp at 0 and 320 (becomes wrap) |
| `src/core/stage.c` | platform and spawn layout designed for 320 (shores and top corners touch x=0 and x=320) |
| `src/core/tuning.h` | `FLIER_START_X 160` (centre of 320); comment `tuning.h:78` |
| `src/core/game.h:6`, `src/core/ai.h:9` | comments that say 320 |
| `src/core/bg_scroll.h` | `BG_ART_COLS 20` (320 period), `BG_RING 21` |
| `src/core/hazard.h:14`, `hazard.c:7,44-54` | `HAZARD_STRIP_COLS 20`, two banks of 20 columns, SCB4 written once at x 0 |
| `tests/host/test_flier.c:151-168` | asserts right wall 320, no wrap |
| `tests/host/test_stage.c:16,20-23` | platform bounds 0..320, floor probe at x 160 |
| `tests/host/test_bg.c:42-50` | asserts 320 period |
| `tests/host/test_core.c:141,181,187`, `test_ai.c:45,81` | `FLIER_START_X`, `mk(250,...)` (positions; change only if layout moves) |
| `tests/mame/hazard_check.lua:25` | `STRIP_W 320`; asserts zero SCB1/SCB2/SCB4 CPU writes |
| `tests/mame/flier_check.lua:193-194`, `flier_drive.lua:14` | `fx < 212` (middle island right edge 208) |
| `tests/mame/scroll_check.lua` | asserts `g_bg_scroll_px` constant in play |
| `tools/check_bg_pixels.py:34-137` | 320 literals for art width |

Screen width (stays 320, hardware fact): `tuning.h:19 SCREEN_W`, `tools/pixel_common.py:41-45`, the culls in
`main.c:243,274` (they become screen-space culls after the transform), exemptions in `tests/host/run.sh:57`.
`boot_check.lua:82 n == 320` is a frame count, not a width.

X readers that need the shortest wrapped distance (mod 384) once wrap exists:

- `flier.c:88` `body_overlap` dx
- `flier.c:242-243` `flier_feet_hit` (x >> 15)
- `flier.c:272` stomp knockback angle (`v->x - a->x`)
- `flier.c:156-162` FALLING path moves x with no wall step: must wrap too
- `ai.c:9` `dist2` (used by `ai_nearest`, `ai.c:27-39`), `ai.c:61` steer angle
- `game.c:110-117` broad phase `hx` with `|d| <= 9` half pixels; the comment at `game.c:93-102` ("positions stay on
  the stage") must be rewritten
- `stage.c:21-31` `stage_floor_y` x overlap (line 28): a platform that crosses the seam must test both sides

View code that reads world x (becomes world-to-screen): `main.c:78-91 hero_show`, `main.c:170-183 pool_sync_stage`,
`main.c:186-208 pool_sync_cpus`, `main.c:237-257 pool_show_hero`, `main.c:259-293 pool_show`, `main.c:602
bg_update(0, g_frame_counter)`, `main.c:601 hazard_step`. `main.c:212-231 pool_stress` is a screen-space test hook and
stays screen space.

## 2. Camera rule

One core module, `src/core/camera.c/.h`, pure C, host tested. State `int32_t cam` in 16.16 fixed point, world x of
the left screen edge. Output `cam_px = cam >> 16`, a whole pixel in 0..64 (`ARENA_W - SCREEN_W`).

Target:

- Humans counted: those with `state < FLIER_DROWNED`. In attract mode the demo flier counts as a human.
- One human: `target = x - 160`.
- Two humans: `target = mid - 160` where `mid` is the linear midpoint of the two world x values, when their linear
  span is at most 304 px (320 minus a 16 px sprite). See section 3 for a span above 304 (seam straddle).
- No human alive, game over, or title: target 32 (arena centre).
- Clamp the target to 0..64 before smoothing.

Smoothing (fixed point, no division):

- `d = target - cam`. Dead zone: if `|d| < 4 px` and the camera is at rest, do not move.
- `step = d >> 3` (one eighth per frame), clamped to +-2 px/frame (`CAM_MAX_STEP = 2 << 16`).
- Max speed 2 px/frame is twice the human top speed (`FLIER_TOP_AIR_SPEED`, 1 px/frame, `flier.h:23`), so the camera
  can always catch up; 1/8 easing settles a 64 px move in about 32 frames.
- New tuning constants in `tuning.h`: `CAM_DEAD_ZONE_PX 4`, `CAM_EASE_SHIFT 3`, `CAM_MAX_STEP_PX 2`.

Seam wrap, no snap: when a single human wraps from 383 to 0, the target jumps from 64 to 0. The camera does not
snap; it pans at most 2 px/frame. For about 16 frames the human is past the right screen edge, which is inherent in a
clamped camera with a wrapping arena (the human is at the far left of the arena while the camera still shows the
right part). The offscreen marker (section 3) covers those frames.

## 3. Wrap at 384 with a clamped camera

Wrap rule: every x write in `flier_step` (normal and FALLING paths) ends with `x = wrap(x)`, `0 <= x < ARENA_W`. A
new helper `arena_wrap_x()` and `arena_dx(a, b)` (shortest signed distance, in `(-192, 192]` px) in
`src/core/arena.h` is the one source for all readers in section 1.

Seam duplicate: not needed. The view is 320 px and the arena 384 px. Two copies of a 16 px sprite are 384 px apart,
so both can never be on screen at once (384 > 320 + 16). The view picks one copy: `sx = wx - cam_px`, normalised into
`[-16, 368)`, then culled outside the screen. This saves the 8 seam duplicate slots reserved in gameplay design 5.2
(line 384). Collision, AI and the broad phase use `arena_dx`, which is the logical "copy shifted by the width".

Offscreen fliers: a clamped camera shows world x `cam_px .. cam_px+320`. 64 px of the arena is always off screen.

- Computer fliers in the hidden 64 px are simply not drawn (they fly in from the edge).
- Two humans straddling the seam (linear span above 304, wrapped span small): the clamped camera cannot show both.
  Proposed rule: hold the camera at its current clamped end (hysteresis, no snap to the other end) until the linear
  span drops below 304 again; show an edge marker (fix layer arrow with player colour, at the human's screen y) for
  the human who is off screen. User decision D1.
- One human off screen during the seam pan (section 2): same edge marker.

HUD: stays on the fix layer, camera factor 0. Unchanged.

## 4. World-to-screen transform

One function `cam_screen_x(wx, cam_px)` in `camera.h` (the `[-16, 368)` normalisation of section 3). Users:

- `hero_show` (`main.c:78-91`), `pool_sync_cpus` (`main.c:186-208`), `pool_sync_stage` (`main.c:170-183`, islands),
  `pool_show_hero`/`pool_show` culls (`main.c:243,274` stay `x >= SCREEN_W` in screen space after the transform),
  pops and spray (factor 1, world objects).
- Not transformed (factor 0): HUD, stars, sky objects, clouds, airship, rain, `pool_stress`.

Hazard strip (water/fire/lava at the bottom): recommendation **scroll with the world (factor 1)**. Reasons: the near
city plane is factor 1 (section 5) and its cast light is tied to the hazard columns (graphics plan lines 155-161,
column modulo 4 palettes); a fixed hazard under a moving near plane breaks that alignment, and a fixed liquid under
moving islands reads as a sliding floor.

Cost:

- Banks grow from 20 to 24 columns each (384 = 6 tiles of 64; fire `A B C A B C` becomes seamless, replacing the cut
  `A B C A B` 192 period; lava period 128 fits 384). `HAZARD_COUNT` 40 -> 48 slots.
- No per-column culling (sticky chain): +4 sprites per line on lines 192..223. Estimated bands: moon ~81, storm ~89
  of 90 (unverified; the table in `sprite_budget.c` must prove it).
- Per moved frame: 2 SCB4 head words (one per bank). Still zero SCB1/SCB2 writes in play.
- `hazard_check.lua` zero-SCB4 assertion becomes "SCB4 writes only on frames where `g_cam_px` changed, at most 2".
- Slots: rain, spray and edge cable move up 8 (`sprite_slots.h`).

Alternative (user decision D4): keep the hazard fixed (factor 0), no cost, near-plane cast light then also fixed.

## 5. Parallax planes

Factors in Q4 (k/16) applied to the whole-pixel `cam_px`, so every plane moves in whole pixels and the far planes
move less than 1 px per camera pixel:

| Plane | Rows | k/16 | Travel (px) | Art width needed | Draft art width | Extend by |
|---|---|---|---|---|---|---|
| sky | 0..127 | 0 | 0 | 320 | 320 | 0 |
| far | 48..127 | 4 | 16 | 336 | 336 | 0 |
| midA | 88..143 | 8 | 32 | 352 | 336 | 16 |
| midB | 112..175 | 12 | 48 | 368 | 336 | 32 |
| near | 128..223 | 16 | 64 | 384 | 320 | 64 |
| islands, fliers, pops, spray, hazard | | 16 | 64 | world | | |
| HUD, stars, sky objects, clouds, airship, rain | | 0 (own drift) | | | | |

Draft art widths from `thoughts/shared/drafts/2026-11-10-backgrounds-final/README.md:38-44` and `numbers.txt`. Far,
midA and midB were drawn 336 wide for the 8 px orbit sway; the sway (`g_bg_sway_px`, graphics plan G5) is removed.
Near at factor 1.0 keeps cast-light alignment with the hazard.

Art extension: midA +16 px (1 column), midB +32 px (2 columns), near +64 px (4 columns), for each of moon, dusk and
storm. Near is lit per column (per-column palettes, modulo 4): 4 new columns keep the modulo pattern. The extension
must be drawn by hand to the same rules (memory: organic gradients, 16-bit depth), not stretched; the draft script
`draw_backgrounds_final.py` gets wider canvases.

Hardware: the Neo Geo counts sprites per line whatever their x (per hardware docs; not verified here). Columns
wholly off screen must be culled (height 0 in SCB3, or moved out of the chain) or they still cost budget. Each plane
becomes a chain whose visible window is at most 21 columns of 16 px (320/16 = 20, plus one partly visible at a
non-multiple-of-16 offset).

Budget per line (limit `SB_LIMIT` 90 including `SB_GAMEPLAY_PER_LINE` 30):

- far, midA, midB: 21 visible columns, as today with sway: no change.
- near: 20 -> 21 visible columns (scrolling by a non-multiple of 16 shows 21). Worst band 128..143 (moon/dusk) goes
  from 90 to 91: over limit by 1. Needs a lever (user decision D3): gameplay reserve 30 -> 29, or trim the last
  near row in that band, or cut midA's last row (budget proof `thoughts/spot/2026-11-10-background-budget.md`).
- hazard: +4 on 192..223 (section 4).
- `sprite_budget.c` static table becomes a function of `cam_px`; `test_sprite_budget.c` checks the maximum over
  `cam_px` 0..64 (65 cases; cheap on host).

Slots: planes 103 -> 110 (midA +1, midB +2, near +4); hazard 40 -> 48. Background range is already over the 120 slot
window before the pool (~149 slots, budget proof) and needs the renumber that note proposes; with this plan about 320
of 381 slots are used (estimate, to be proven by the static asserts in `main.c` and `sprite_slots.h`).

Scroll writes: the background ring logic in `bg_scroll.h` (`bg_columns_to_write` redraws the whole ring for anything
but `now == prev + 1`) is built for one-way scrolling. Camera motion goes both ways. Replace it with sticky chains
moved by SCB4 head writes (one or two words per plane per moved frame, 5 planes + 2 hazard banks = at most ~10 words)
and per-column SCB3 height toggles for culling at the two edges (at most 2 words per plane per moved frame). No SCB1
writes in play (tile maps are static).

## 6. Island layout

Today's layout (`stage.c`) is designed for 320 and uses the seam: the shore islands `{0,164,64}`/`{256,164,64}` and
top corners `{0,40,48}`/`{272,40,48}` touch both edges.

| Option | Layout | Pros | Cons |
|---|---|---|---|
| A: shift +32 | every x + 32; spawns + 32; `FLIER_START_X` 192 | simplest; tests shift by a constant | 64 px empty strip across the seam; shores no longer join |
| B: spread x * 1.2 | every x and width * 1.2 rounded to 8 | keeps shore/corner islands touching the seam (they join across it); same feel, more air | all coordinates change; widths change (ai tuning, `flier_check.lua fx < 212`) |
| C: centred + seam island | layout centred, one new island over the seam | adds a seam landmark | new design, more test work |

Recommendation: **B**. Wrap only makes sense if the seam is used; B keeps the joined shore and corner islands that
make the seam a place to fight across, and a 384 arena with the same platform count gets more air for flapping.
Spawns and `FLIER_START_X` scale with it (160 -> 192). User decision D2.

## 7. Checklist

Rule: core logic in `src/core` with host tests (`tests/host`); one reachability test through the real entry point
(boot ROM in MAME, headless with `SDL_VIDEODRIVER=dummy`) with a sentinel.

| ID | Item | Files | Test | Depends |
|---|---|---|---|---|
| C1 | `ARENA_W 384` replaces `FLIER_WORLD_W`; `arena_wrap_x`, `arena_dx` helpers | `src/core/arena.h` (new), `flier.h`, `tuning.h` | `tests/host/test_arena.c`: wrap, dx at seam (383 vs 1 = -2) | - |
| C2 | Flier wraps (normal and FALLING paths), walls removed | `flier.c:156-162,221-230` | `test_flier.c:151-168` rewritten: long flight crosses 383 -> 0 | C1 |
| C3 | Wrapped dx in all x readers | `flier.c:88,242-243,272`, `ai.c:9,61`, `game.c:110-117` (+ comment 93-102) | host: stomp and body contact across the seam; `ai_nearest` picks the rival across the seam; broad phase pair at x 382 and 2 | C1 |
| C4 | Stage layout for 384 (D2) with seam-crossing floor test | `stage.c`, `tuning.h FLIER_START_X` | `test_stage.c` bounds 0..384, floor at a seam-joined island from both sides; `test_core.c`, `test_ai.c` positions | C1, D2 |
| C5 | Camera module (section 2, D1 rule) | `src/core/camera.c/.h` (new), `tuning.h` | `tests/host/test_camera.c`: clamp 0..64, dead zone, max 2 px/frame, single-human seam pan no snap, two-human straddle hold, no-human centre 32 | C1, D1 |
| C6 | Game owns camera state, steps it each frame | `game.c/.h` | covered by C5 + C10 | C5 |
| C7 | World-to-screen transform in all views; offscreen edge marker | `main.c` view functions (section 4), fix layer marker | C10 | C5, C6 |
| C8 | Background planes: sticky chains, SCB4 per camera move, edge culling, factors k/16; sway removed | `src/bg.c`, `src/core/bg_scroll.h/.c` | `test_bg.c` rewritten (factor maths, visible column window per `cam_px`); `scroll_check.lua` replaced by per-plane offset check | C5 |
| C9 | Hazard 24 columns per bank, scrolls factor 1 (D4) | `hazard.h`, `hazard.c`, `assets/hazard/build_sheet.py` (fire 6-tile period) | `hazard_check.lua`: STRIP_W 384, SCB4 only on camera-move frames | C5, D4 |
| C10 | Reachability: boot ROM, drive the human right across the seam and back, assert sentinel `g_cam_px` moved 0 -> 64 -> eases back, near-plane SCB4 x equals `-g_cam_px & 0x1FF`, far plane moved `g_cam_px * 4 / 16`, zero SCB1 writes in play | `tests/mame/camera_check.lua` (new), Makefile target | itself | C2-C9 |
| C11 | Sprite budget per camera position + slot renumber + lever (D3) | `sprite_budget.c/.h`, `sprite_slots.h`, static asserts in `main.c` | `test_sprite_budget.c`: max over `cam_px` 0..64 <= 90 per line | C8, C9, D3 |
| C12 | Art extension midA +16, midB +32, near +64 for moon/dusk/storm | `thoughts/shared/drafts/2026-11-10-backgrounds-final/draw_backgrounds_final.py`, then asset build | `tools/check_bg_pixels.py` 320 literals -> per-plane widths; draft gallery page for user review before import | D-none (art review by user) |
| C13 | Docs: gameplay design D7 wrap at 384, 5.2 seam slots dropped; graphics plan D1 sway replaced | `2026-11-09-flier-gameplay-design.md`, `2026-11-10-neo-geo-graphics-max.md` | - | all |

Two players are not implemented (only `Game.flier` exists, `game.h`). The camera module takes a list of human
positions now, so the second player only adds an entry; until then the target is the single human.

## 8. Open user decisions

| ID | Question | Options | Recommendation |
|---|---|---|---|
| D1 | Camera when the two humans straddle the seam (one must be off screen) | (a) hold the camera at its current end, edge marker for the hidden human; (b) follow player 1, marker for player 2; (c) follow the leader by score | (a): no snap, fair to both, marker shows the hidden human |
| D2 | Island layout for 384 | A shift +32; B spread x 1.2; C centred + seam island | B: keeps the seam-joined shore and corner islands |
| D3 | Budget lever for the 21st near column (band 128..143 reaches 91 of 90) | gameplay reserve 30 -> 29; trim near last row in that band; cut midA last row | gameplay reserve 30 -> 29 (no art loss; 29 gameplay sprites per line is still above the 7 fliers + pops measured) - unverified, check measured peak first |
| D4 | Hazard strip | scroll with the world (factor 1, +8 slots, +4 per line on 192..223, 2 SCB4 words per moved frame); fixed (factor 0, no cost) | scroll: keeps cast light aligned with the near plane and islands |

Unverified in this note: per-line counts with the 21st near column and the 24-column hazard (estimates from the
budget proof, not computed), the hardware rule that off-screen sprites still count per line, total slot count ~320.

## 9. User decisions (2026-11-10, question tool)

- Side edges: wrap at 384 (the game bounces today; wrap is new work in the fly and fall
  paths plus one shortest-distance helper).
- Islands: spread all x by 1.2.
- Hazard strip: scrolls with the world.
- Budget lever: measure the real gameplay sprite peak per line in MAME first, then lower
  the gameplay reserve from 30 to 29 if the measurement allows it.
- D1: hold the camera while the two humans are split across the seam; an edge marker
  shows the human who is off screen.
- Related, decided the same day: flier art grows to 32x48 (2 sprite columns per flier)
  with the same hit box. The gameplay reserve must be measured for 2 columns per flier
  before any reserve is lowered.
