---
date: 2026-11-09
topic: City parallax background (ledger item 3), purple-magenta night skyline art v9, built from Neo Geo sprites
tags: [neogeo, sprites, parallax, background, palette, crom, plan, art-v9]
status: in-progress
---

# City background plan

Scope: ledger item 3 in `thoughts/spot/todos.md`. Fix layer stays HUD only. Today the screen is black.
Done when (definition used here): `make test` has a headless MAME check that drives the real game loop, proves the new
code ran (sentinel counter), and asserts that the three layers scroll at 0.25x / 0.5625x / 1.0x of the game speed.

## Inputs read and what is missing

- Source art: `design/roofline-test-v5.html`. Its background palette `P` is already purple-magenta (sky `#1a1238`, mid rim `#c0508a`),
  which matches the "v7 purple city" entry in `2026-11-09_art-direction.md`. v8 and v9 changed only the guard rim. **v9 itself is not local
  (unverified that v5 background == v9 background).** The locked v9 page must be saved next to v5 (design/ is owned by the design session)
  or the user must confirm v5 background == v9 background. The numbers below were measured by running the v5 drawing code under node
  (scratchpad `m.js`, `m2.js`; not committed).
- v5 uses `GROUND = 184` for the roof; the game uses `GROUND_Y = 176` (`src/core/tuning.h:49`), hero feet at 176. Art must move up 8 px
  (recommended: it also makes the roof tile-aligned, row 11). See open question Q2.
- v5 composes: sky, lights (16 stars, 5 antenna lamps), moon, clouds, far, mid, roof. Sky is one flat colour (no gradient, no bands; the
  4-band sky in the older research is the rejected draft).

## 1. Layers (measured from v5, tile = 16 x 16)

Game speed `g->speed` is 8.8 px per frame, 2.0 (SPEED_BASE 512) to 5.0 (SPEED_MAX 1280). Obstacles move `-speed` per `game_step`
(`game.c:217`), so the roof at exactly 1.0x keeps obstacles standing still on the deck texture.

| Layer | Rate | Rows (y range) | Ring sprites x tiles tall | Unique tiles | Palette colours |
|---|---|---|---|---|---|
| Sky | none | whole screen | backdrop colour only, 0 sprites | 0 | 1 (backdrop) |
| Stars | static | y 30..84 | 16 x 1 | up to 32 (dot + plus per star, blink = swap tile) | 2 (shared with sky objects) |
| Sky objects (moon + 4 cloud bars, composited) | static | moon cols 13..17 rows 2..4, left clouds cols 1..5 row 3 | 10 sprites (5 x 3 tall, 5 x 1 tall) | measured 12 moon + 14 cloud separately; merged <= 26 | 6 + 3 = 9 |
| Far skyline | 0.25x = 0.5..1.25 px/frame | rows 4..9 (y 64..160, 6 tiles) | 21 x 6 | 88 (87 with hflip, not used) | 6 + lamp on/off/white = 9 |
| Mid skyline | 0.5625x (9/16, within 2 percent of the locked 0.55) = 1.1..2.8 px/frame | rows 6..10 (y 96..176, 5 tiles) | 21 x 5 | 68 | 12 + 3 lamp = 15 (no headroom) |
| Roof deck | 1.0x = 2..5 px/frame | rows 11..13 (y 176..224, 3 tiles) | 21 x 3 | 6 | 8 |

Notes:
- Far is cropped at y 160: the mid layer hides everything below its tops (126..150). There are 2 px slits between mid buildings (x 41-42 and
  similar) where far or sky shows through down to the roof; cleaner to close the gaps in the Python drawing (artist call, Q5).
- Palette colour counts are per layer (max 15 plus transparent). v5 `prep()` already forces every 16 x 16 tile to <= 15 colours.
- Art period: 320 px (20 columns) for far and mid, roof period 2 to 4 columns. v5 buildings straddle x=0 and x=320 (mid x -6, last mid
  building ends at 326), so the drawing must be done on a 320 px torus (x mod 320) to get a seamless wrap. Longer period costs ROM only
  (tiles x2, still tiny), see Q3.
- Lamps: bake the 2 x 2 lamp pixels into the layer tiles using two palette entries (lamp on, lamp off); the blink is a palette word swap
  every 2 frames. This loses v5's per-lamp phase offset (all lamps of one layer blink together). Acceptable, say so in the report.
- Stars twinkle by tile swap, not by palette; stars are not parallax.

## 2. Neo Geo budget

Sprites: stars 16 + sky objects 10 + far 21 + mid 21 + roof 21 = **89** background sprites. Hero 3 today, obstacles/enemies/laser
(item 1, 2) reserve 60. 381 limit: 89 + 3 + 60 = 152, fine. Screen 320 px / 16 = 20 columns, +1 for the partly visible wrap column = 21 per ring.

Per scanline (hardware limit 96 sprites per line, counted by y overlap regardless of x):
- y 176..223: roof 21.
- y 96..159: far 21 + mid 21 = 42.
- y 64..95: far 21 + sky objects up to 10 + stars up to 16 (upper bound, they are spread over 55 px) = <= 47.
- Worst background line <= 47. Leaves >= 49 for hero (3), obstacles, laser. Margin is fine; re-check after items 1 and 2 add sprites.

C-ROM: <= 220 unique tiles x 128 bytes (64 in c1, 64 in c2) = <= 28,160 bytes (27.5 KiB; 162 tiles = 20,736 bytes are measured, the
rest is the unmeasured star and merged sky object tiles). Slot is 2 MB per file. Tile numbers: logo 0..255, hero 256..357 (102 tiles),
background from 358. The base must not be hardcoded twice (see B4).

## 3. Scrolling method

- No SCB2 shrinking, no SCB4 chain-head trick. A sticky chain of 21 cannot wrap: sprite x is 9 bits (period 512), the art period is 320, so
  column 0 would reappear at 512 - s instead of 320 - s. Rewriting all 21 strips on every 16 px step would also be 21 x H x 2 words.
- Recommended: **ring of 21 independent (non-sticky) sprites per layer**, driven by a pure function of `game->distance` (8.8 px travelled,
  `game.h:51`). World column w sits in slot `w % 21`, screen x = `16*w - s`, art column = `w % PERIOD`.
  - `s_far = distance >> 10` (0.25x, 8.8 -> px), `s_mid = ((distance >> 4) * 9) >> 8` px (9/16 of the roof), `s_roof = distance >> 8`.
    Sub-pixel position stays in the 8.8 value; hardware x is the integer pixel. Each layer is reduced mod `PERIOD*16` px before use.
  - Per frame: write SCB4 (x) for 63 sprites, `(x & 0x1FF) << 7`. When `floor((s+319)/16)` changes, the entering slot gets new SCB1
    tile strip (H x 2 words): far 12, mid 10, roof 6 words. At most one column per layer per frame (speed < 16 px).
    Total per frame <= 63 + 28 words. No vblank pressure.
  - Sprite y/height (SCB3) and size (SCB2 = 0xFFF) are written once in `bg_init()`, which `video_init()` calls.
- Because scroll is a function of `distance`, there is no accumulator state to keep in sync, it is host-testable, and the roof matches
  obstacles by construction. Side effect: scroll jumps back when a new game resets `distance` to 0. Acceptable, flag it to the user.
- Scrolling runs in ATTRACT demo and PLAYING, because `flow.c:117` and `:126` both call `game_step`. It is frozen on title/table/name
  entry (distance does not change), which is also what the user would expect. Not verified whether GAME_OVER should freeze it (it does: no step).
- Alternative (not recommended): sticky chain plus full strip rewrite per 16 px step. Simpler register code, 336 to 700 words in one frame
  at worst, with mid and roof steps able to collide in the same frame.

## 4. Asset pipeline

- Art source: **original**. The v5 page draws the whole background with its own JavaScript (`drawSky`, `drawMoon`, `drawClouds`, `drawFar`,
  `drawMid`, `drawRoof`, `drawLights`); no CC0/CC-BY source is involved and no credit line is needed (hero CC-BY credit stays as is).
  Port these drawing functions to Python/Pillow as `assets/city/draw_city.py` (checked in, deterministic, on a 320 px torus, GROUND 176),
  writing `assets/city/city_sheet.png` (palette-indexed layer strips) and `city_sheet.json` (layer name, y, rows, period, palette, colour
  names). The PNG is committed like `guard_sheet.png`. Reuse the `Buf/rect/outline/enforceTiles` logic one-to-one.
- Tile/palette conversion: do **not** write a second converter. Move the generic parts of `tools/build_hero_sprites.py` (`rgb_to_ng`, 5-bit
  check, atlas build, `tiletool.py --sprite -c`, dedupe, round-trip verify) into `tools/ng_tiles.py` (a module, not a tool), keep
  `build_hero_sprites.py` as the entry point, and add a city mode (`--city assets/city/city_sheet.png`) or rename it `build_sprites.py`
  with both inputs. One run emits `hero.*`, `city.c1/c2`, `city_sprites.h/.c` with `CITY_TILE_COUNT`, palettes, per-layer column tables
  (`city_far_cols[PERIOD][H]` of tile numbers relative to the layer base). A single tool invocation lets it compute the base
  (256 + hero tiles) once and emit `BG_TILE_BASE` into the header; main.c must not hardcode it (today `HERO_TILE_BASE 256` is hardcoded).
- Makefile (other agent's file, so not edited here): add `city.c1/c2` to the `CROM1/CROM2` cat list after `hero.c1/c2`, add the new outputs
  and inputs to the generate rule, and a `city_sprites.o` link plus `main.o` dependency, mirroring lines 89..98.
- Round trip: the verify step decodes `city.c1/c2` and compares every tile against the sheet; fails on > 15 colours per tile or layer.

## 5. Draw order and palettes

- Sprite priority: higher index is drawn on top (lower index first). The hero is currently sprite 0 (`HERO_SPRITE 0`, `main.c:34`), which
  would put the whole background in front of it. Proposed map: stars 0..15, sky objects 16..25, far 26..46, mid 47..67, roof 68..88,
  reserved 89..127, obstacles/enemies 128..191, hero 192..194, laser/effects 195+. Change `HERO_SPRITE` to 192; item 1 owner uses 128..191.
- Draw order matches v5 compose: sky, stars, moon, clouds, far, mid, roof, then gameplay sprites.
- Palette slots in bank 1: 0..1 fix text, 2..3 hero, **4 far, 5 mid, 6 roof, 7 sky objects + stars**. `bg_load_palettes()` is called from
  `video_init()` next to `hero_load_palettes()` (`main.c:248`). That function runs on first boot and on every BIOS re-entry
  (`resume_game_loop`), which the real BIOS needs because it clears palette RAM. Also `bg_init()` (sprite state, all strips) in `video_init()`.
- Backdrop (the sky colour): main.c's comment says colour 0 is the backdrop, but the Neo Geo wiki says the backdrop is the last entry of
  palette RAM (palette 255, index 15, `MMAP_PALBANK1[4095]`). **VERIFIED 2026-11-09 (B2): the backdrop is the LAST palette RAM entry, MMAP_PALBANK1[4095]. Writing 0x0f00 there gave red pixels in a MAME snapshot while entry 0 of palette 0 stayed 0x8000. Original line was:** (was: unverified, from memory.) B2 verifies with a snapshot and sets the right
  word to `#1a1238`. Fallback if it cannot be set: a flat-colour block of 20 sprites, 14 tiles tall each (20 sprites, 20 more per scanline).

## 6. Reachability test

Entry point: the real ROM under headless MAME via `make test` (`tests/mame/boot_check.lua`), same as the hero check.

Sentinels the game exports (volatile, address from `nm` like `ROOFLINE_FRAME_ADDR`): `g_bg_scroll_px[3]` (far, mid, roof integer px) and
`g_bg_column_writes` (incremented in the strip writer). Lua writes these into the result file at the snapshot frames.

Lua: take two PLAYING snapshots 12 frames apart (`bg_a.png`, `bg_b.png`) plus the existing `pre_start.png`; record the scroll values
at both.

`tests/mame/check_bg_pixels.py` (python3.14 -I, Pillow), inputs: snapshots, the generated `city_sprites.c` palettes, the Lua values:
1. Colours: each layer's exclusive palette colours (colours not in any other palette, including hero) appear in the expected y band,
   with a minimum pixel count (far rim/strip in y 64..160, mid rim/window in y 96..176, roof in y 176..223, moon colour near (258,54),
   sky colour at (4,4)). Fails on the current black screen.
2. Motion: for each layer build the column histogram of its exclusive-colour mask (excluding x 60..140, the hero), find the circular
   shift between `bg_a` and `bg_b` that maximises correlation. Assert it equals the Lua delta of `g_bg_scroll_px` within 1 px, and
   `g_bg_column_writes` grew. Assert ratios far/roof = 0.25 +- 0.04 and mid/roof = 0.5625 +- 0.04 (roof shift is 24..60 px over 12 frames,
   so the quantisation error is small).
3. The existing `check_hero_pixels.py` must be changed: roof outline `#120a26` and white probably coincide with hero colours, so counting hero
   palette colours in the hero box (MAX_BEFORE) will now see background pixels. Restrict it to hero-exclusive colours (palette 0 minus
   all city colours). (Unverified which exact colours collide; B9 checks.)
4. Host test (`tests/host`): `bg_scroll_px(distance, layer)`, slot/column/x mapping, wrap at the period, rate ratios. The pure code lives in
   `src/core/bg_scroll.c`. Knobs `BG_FAR_RATE`, `BG_MID_RATE` (if exposed in `tuning.h`) need `tests/host/knobs.txt` lines and a digest that moves.
5. `make test-unibios`: add a snapshot check after the coin re-entry that the background colours are still on screen.

Mutation checks to run once each: change the mid rate in the code and see the check fail; skip `bg_load_palettes()` and see check 1 fail.

## 7. Checklist for the implementer

Tick in the open with a running count ("n of 14 done").

- [ ] B1 (UNVERIFIED per user decision, Q1 open) Get v9 background confirmation (or v9 page saved) and the answers to Q1..Q5 below.
- [x] B2 (done: backdrop = MMAP_PALBANK1[4095], verified by snapshot) Verify the backdrop word with a one-line ROM change and a snapshot (colour 0 vs last entry); record the result in this file.
- [x] B3 (done: assets/city/draw_city.py, city_sheet.png/json) `assets/city/draw_city.py`: port of the v5 background to Pillow on a 320 px torus, GROUND 176, far rows 4..9, mid rows 6..10,
      roof rows 11..13; emits `city_sheet.png/json`. Check: every tile <= 15 colours, each layer palette <= 15, mid exactly 15 or fewer.
- [x] B4 (done: tools/build_city_sprites.py via generic tools/sprite_pipeline.py (src_w/src_h widened to u16)) Refactor `tools/build_hero_sprites.py` into `tools/ng_tiles.py` + entry point, add city mode, emit tile base, round-trip verify.
      Hero output must stay byte-identical (diff `hero.c1/c2/hero_sprites.c` before and after).
- [x] B5 (done: Makefile city rule, C-ROM, ELF) Makefile: city tiles appended to c1/c2, generate rule, object link (ask the Makefile owner or do it when the other agent is done).
- [x] B6 (done: src/core/bg_scroll.c/h + tests/host/test_bg.c) `src/core/bg_scroll.c/h` pure functions + host tests + knobs.
- [x] B7 (done: src/bg.c) `src/bg.c` (or inside main.c): `bg_load_palettes`, `bg_init`, `bg_update(distance)`, strip writer, sentinels, lamp blink, star twinkle.
- [x] B8 (done: video_init/game_loop hooks, src/sprite_slots.h, HERO_SPRITE 192) `video_init()` calls `bg_load_palettes()` + `bg_init()`; `game_loop()` calls `bg_update()` every frame; `HERO_SPRITE` moved to 192
      and the sprite map above applied (coordinate with item 1).
- [x] B9 (done: hero/obstacle checks exclude city colours; roof stv colour changed to avoid the hero outline colour) Fix `check_hero_pixels.py` for colour collisions.
- [x] B10 (done: boot_check.lua bg_a.png at frame 420, playing.png at 450, result.txt.bg) `tests/mame/boot_check.lua`: two extra snapshots, export `g_bg_*` addresses (Makefile passes `ROOFLINE_BG_ADDR`).
- [x] B11 (done: tests/mame/check_bg_pixels.py in make test) `tests/mame/check_bg_pixels.py` (colours, motion, ratios, sentinel) and wire into `make test`.
- [x] B12 (done: unibios_check.lua city palettes + backdrop survive coin re-entry) `unibios_check.lua` background colours survive re-entry; run `make test-unibios`.
- [x] B13 (done: bg_update disabled once: check_bg_pixels failed 8 checks, reverted) Mutation checks (rate changed, palette load skipped) fail, then revert.
- [ ] B14 (OPEN, human only) Human check on `make run` (MAME window, say in chat which window): skyline visible, three speeds visible, lamps blink, hero in front,
      no 2 px slits (or accepted), loop seam not visible after one full period. `df -h /` before the builds (12 GiB free now).

## Open questions for the user

- Q1 Is the v5 background identical to v9 background? Recommended: yes (v8 and v9 changed only the guard rim); save v9 as `design/roofline-test-v9.html` to confirm.
- Q2 Roof line: move the art to the game's `GROUND_Y 176` (Recommended) or move the game to the art's 184 (changes jump, hero box, tests).
- Q3 Art period 320 px (Recommended for v1, skyline repeats every 320 px of layer travel, about 10 to 13 s for far) or 640 px (more art work).
- Q4 Scroll jump when a new game resets distance: accept (Recommended) or keep a persistent background offset.
- Q5 Close the 2 px slits between mid buildings in the drawing (Recommended) or keep v5 exactly.

## Risks and unverified

- v9 background not local (above). Backdrop location unverified (B2).
- 96 sprites per line and 381 sprites total are hardware facts from memory, not checked against the ngdevkit headers (the headers only define
  register addresses `ADDR_SCB1..4`).
- Mid palette is full (15 colours). Any extra accent colour for item 4 styling needs a second mid palette.
- Sprite priority claim (lower index drawn first) is taken from the project brief and the hero code; confirm in the first MAME snapshot.
- Non-sticky ring costs 63 x-writes per frame; trivial, but not measured on MiSTer.
- Star twinkle and lamp phase differ slightly from v5 (all lamps blink together).
- Pixel-shift test depends on exclusive colours; if two layers share a colour the mask is wrong (B3 must keep them exclusive).

## User decisions (2026-11-09)

- Q2 roof line: the art moves to the game's GROUND_Y 176. GROUND_Y stays unchanged.
- Q3 art period: 320 px per layer.
- Q4 scroll reset: the scroll position is a pure function of game distance and resets with each run.
- Q5 (implementer default, not asked): keep the v5 building gaps as drawn.
- Q1 (unverified): the v9 background is assumed identical to v5 (v8/v9 changed only the guard rim). Save v9 locally and compare before the art is final.
