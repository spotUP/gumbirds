---
date: 2026-11-10
topic: Graphics plan for Gumbirds (earlier names Bubblegum Brawl, Roofline), pushing the Neo Geo MVS sprite hardware
tags: [neogeo, sprites, parallax, auto-animation, palette, raster, shrink, crom, budget, plan]
status: draft (plan only, nothing built; decisions D1 to D6 open)
---

# Neo Geo graphics plan: lush, animated, deep

Scope: the arena screen (background, hazard strip, islands, effects, HUD) plus title. Plan only. No code, build or
test was run for this document. Art rules are fixed and not reopened here: 16-bit cel style, 5 to 7 hue-shifted
shades per material, hand-placed clusters, strong contrast, no procedural ramps, no Bayer or ordered dither fields,
fluid effects baked from simulation with many frames, everything original.

Done when (finish line of the plan as a whole): every build item G1 to G17 has its headless MAME test passing through
the real ROM, `gmake test-vblank` passes with all of them on, and the user has confirmed the look in a MAME window.
Report as "n of 17".

Hardest finding first: **the wish list does not fit as CPU-driven effects.** The measured headroom is about 40 busy
scanlines on the worst stress frame (section 3). The plan fits only because the large, visible things are moved onto
hardware that costs no 68000 time: auto-animation, sticky sprite chains, shrink constants, hidden twin strips, and
palette RAM. Per-line heat haze and software particles are the things that get cut (decision D6).

## Sources and what "verified" means here

- Frame cost: `thoughts/spot/2026-11-10-vblank-overrun.md`, newest section "Engine cuts (2026-11-10, option C,
  uncommitted)". **Numbers used in this plan: busy lines median 152, p95 194, max 220 of 264, miss threshold about
  260, measured in the stress phase with 32 pool objects.** The older 176 / 223 / 270 are superseded. The cuts are
  uncommitted in `src/core/game.c` and `src/core/vram_queue.c`; if they are not landed, headroom is negative and
  nothing below may start.
- Source reads: `src/sprite_slots.h`, `src/vram_layout.h`, `src/gfx.h`, `src/gfx.c`, `src/bg.c`,
  `src/core/vram_queue.h`, `src/core/obj_pool.h`, `src/core/stage.c`, `src/core/tuning.h`, `Makefile`, `rom.mk`,
  `build/gen/*_sprites.h`, `build/rom/`.
- ngdevkit on this machine: `/opt/homebrew/Cellar/ngdevkit/0.5+202611061802-1/`. Its headers
  (`m68k-neogeo-elf/include/ngdevkit/registers.h`) define register and VRAM block addresses only: `ADDR_SCB1..4`,
  `ADDR_FIXMAP`, `REG_LSPCMODE`, `REG_TIMERHIGH/LOW`, `REG_IRQACK`, `REG_TIMERSTOP`, `REG_SHADOW/NOSHADOW`,
  `REG_PALBANK0/1`, `MMAP_PALBANK1`. No bit layouts, no limits, and no example programs are installed. So a
  register's existence is VERIFIED, every bit meaning and every limit below is marked UNVERIFIED unless the game
  source already depends on it and its tests pass (marked "verified by use").
- Also checked locally: `ngdevkit-crt0.o` has the symbols `rom_callback_Timer`, `rom_handler_Timer` and
  `rom_handler_Timer_default` (nm), so a timer interrupt hook exists in the runtime. The nullbios `000-lo.lo`
  (shrink lookup ROM) in `share/ngdevkit/neogeo.zip` is populated (130,594 of 131,072 bytes non-zero, row 255 is
  0..15), so vertical shrink can be tested under nullbios. MAME's software list
  (`/opt/homebrew/share/mame/hash/neogeo.xml`) has sprite data areas up to 64 MiB.
- No network was used.

## 1. Hardware budget

| Resource | Limit | Source of the limit | Used today | Source of the usage |
|---|---|---|---|---|
| Sprites total | 381 | `VQ_SPRITES 381` in vram_queue.h and sprite_slots.h; UNVERIFIED against hardware docs | 188 slots owned: 0..88 background (89), 96..191 pool (96), 192..194 hero (3). Free: 89..95 (7) and 195..380 (186) | `src/sprite_slots.h` |
| Sprites per scanline | 96 | project docs; UNVERIFIED locally. Which sprites vanish on overflow is UNVERIFIED (assumed: the highest indices, which here are the fliers) | Worst background line 42 (far 21 + mid 21, y 96..159); roof 21 on y 176..223; stars up to 16 and sky objects up to 10 on y 30..108 | ring tops 64 / 96 / 176 in `src/bg.c` RINGS, counts in sprite_slots.h |
| Sprite size | 16 px wide, up to 32 tiles (512 px) tall (height field in SCB3 low bits) | verified by use: `gfx_scb3_word(rows, top)`; 32-tile maximum UNVERIFIED | tallest today 6 tiles (far ring) | city background plan section 1 |
| Chaining | SCB3 bit 6 "sticky": sprite follows the previous one 16 px to the right, shares its y and height | verified by use (`1 << 6` in gfx.c, bg.c; test-scroll passes) | rings are two chains each; pool objects are chains of `POOL_COLS 3` | bg.c header comment, obj_pool.h |
| Shrink | SCB2: bits 11..8 horizontal (15 = full, 16 steps), bits 7..0 vertical (255 = full). Shrink only, never enlarge. A sticky sprite keeps its own horizontal shrink and takes the vertical shrink of its chain head | full value `0xFFF` verified by use; step counts and sticky inheritance UNVERIFIED | never shrunk (always 0xFFF) | grep SCB2 in src |
| Auto-animation | SCB1 attribute word bit 2 = 4-frame, bit 3 = 8-frame: the hardware replaces the low 2 or 3 bits of the tile number with a global frame counter. One counter and one speed for the whole screen: `REG_LSPCMODE` bits 15..8 = video frames per step, bit 3 = disable. Reading `REG_LSPCMODE` returns the counter in bits 2..0 and the raster line in bits 15..7 | VERIFIED IN MAME 2026-11-10 (`test-autoanim`, findings `thoughts/spot/2026-11-10-g1-g2-autoanim.md`), not on hardware: SCB1 bit 3 = 8-frame; read bits 2..0 = 3-bit counter; speed field bits 15..8 = frames per step minus 1; tile base must be 8-aligned; BIOS does not overwrite while PLAYING. Bit 2 (4-frame), bit 3 disable, raster line read: still UNVERIFIED | used since G2: star twinkle (`src/bg_stars.h`); `REG_LSPCMODE` written only by `gfx_flush` inside vblank | `test-autoanim` |
| Palettes | 256 palettes of 16 entries (entry 0 transparent) per bank, two banks (`REG_PALBANK0/1`). Backdrop colour is entry 4095 | backdrop verified by snapshot (city plan B2); palette index in SCB1 attribute bits 15..8 verified by use; bank count from register names | 9 palettes: fix 0..1, obstacles 1, city 4, Sootling 2 | vram_layout.h, build/gen headers |
| Palette RAM writes | Any time; one queued write costs 18 us of the 2000 us vblank flush (`VQ_US_PAL`, `GFX_FLUSH_BUDGET_US`) | vram_queue.h, gfx.h (measured by the project) | lamp blink: 4 words on a state flip every 18 to 30 frames | bg.c lamp_set |
| Fix layer | 40 x 32 cells of 8 x 8, always in front, no scroll, 16 colours per cell; fix cells can use palettes 0..15 only (UNVERIFIED); S ROM 131,072 bytes = 4096 tiles | cell grid verified by use (`VQ_FIX_COLS/ROWS`); S ROM size from `build/rom/roofline-s1.s1` | HUD text, 2 palettes | vram_layout.h |
| Timer interrupt | 32-bit reload in pixel clocks (`REG_TIMERHIGH/LOW`; 384 clocks per line, 264 lines per frame), enable and reload modes in `REG_LSPCMODE` bits 4..7, acknowledged through `REG_IRQACK` bit 1, level 2 on cartridge systems (above vblank) | registers and the crt0 hook VERIFIED; bits, units and level UNVERIFIED | not used | grep |
| Screen dim | `REG_SHADOW` / `REG_NOSHADOW`: darkens the whole video output | registers VERIFIED; effect UNVERIFIED | not used | grep |
| C ROM, this build | 2 x 2,097,152 bytes = 32,768 tiles (128 bytes per tile over the pair) | `rom.mk` CROMSIZE, `build/rom/roofline-c1.c1` size | 511 tiles (logo 256, obstacles 30, city 206, Sootling 19) = 1.6 percent. (`build/gen/heat_sprites.h` and `hero_sprites.h` are stale leftovers, not in `CROM_SETS`) | Makefile line 90, build/gen headers |
| C ROM, MVS cartridge | 20-bit tile number = 1,048,576 tiles = 128 MiB (UNVERIFIED); MAME's list has sets up to 64 MiB (VERIFIED locally) | SCB1 attribute bits 7..4 as tile high bits UNVERIFIED | 4 MiB pair | |
| C ROM, MiSTer core | UNVERIFIED. From memory: the 32 MB SDRAM module limits the total romset, 128 MB removes the limit. This plan needs under 1 MiB of tiles, so it stays inside the present 4 MiB pair and the question does not arise | | | |

Consequences that shape the plan:

1. Sprite slots are plentiful (193 free) but the free ones are in the wrong place: only 7 lie behind the pool. The
   slot map must be re-laid (G1) so that background layers sit below the pool and the hazard and foreground above the
   hero.
2. The scanline limit is the real design constraint. Reserve for gameplay on any one line: 7 fliers plus up to 7
   wrap-seam copies (14), two 64 px islands at the same height (8), effects (8) = **30**. That leaves **66** for
   scenery and foreground per line.
3. C ROM and palettes are effectively free. Spend them: more frames, more palettes, never more CPU.

## 2. Technique catalogue

Cost units: tiles in C ROM; palettes; sprites per scanline (of the 66 available); 68000 time in busy scanlines per
frame (one line = 768 cycles = 64 us) or "zero, hardware"; vblank flush time in us where it matters. CPU figures are
estimates from the measured queue costs (about 200 cycles per queued SCB word, `vblank-overrun.md`), not measured.

Common test pattern (T): headless MAME as in RULES.md (`SDL_VIDEODRIVER=dummy -video none -sound none -window
-nomaximize`), a Lua script that drives coin and start, keeps a shadow of LSPC VRAM writes (as `scroll_check.lua`
does), reads sentinels through `nm` addresses, saves snapshots to `build/test-snap/`, and a `python3.14 -I` Pillow
check on palette-exclusive colours (as `check_bg_pixels.py`). Each new test gets its own make target and is added to
`make test`.

### 2.1 Multi-layer parallax from sprite strips

- In this game: clouds, far skyline, mid skyline and near rooftops as separate planes that shift against each other.
  The arena does not scroll (test-scroll asserts `g_bg_scroll_px` is constant in play), so motion comes from a slow
  "orbit sway" (decision D1): the near plane and the islands stand still, the mid plane swings plus or minus 8 px,
  the far plane plus or minus 16 px, clouds drift with the wind. That is what a camera circling a fixed arena shows.
- Mechanism: one sticky chain of 22 sprites per plane (352 px, covers the screen at any offset within 16 px). Moving
  a plane is one SCB4 word on the chain head. No ring, no tile strip writes in play. The existing ring code
  (`src/bg.c`) stays for the attract or title pan.
- How many layers fit: 66 sprites per line minus nothing else = three full-width planes on one line, or two planes
  (44) plus 22 sparse sprites. By cropping each plane where the one in front hides it, no line carries more than two
  full planes, and the screen still shows seven depth planes (section 4).
- Cost: tiles see section 4; 22 sprites per line per plane; CPU about 0.3 line per moved plane and only on frames
  where its pixel offset changes (sway of 16 px over 10 s changes about every 20 frames); flush 15 us per word.
  Removes today's `bg_update` cost (6 median, 14 max lines) because nothing is recomputed per frame.
- Risk: scanline overflow drops sprites (assumed the fliers). Guarded by a host test over the layout tables
  (maximum sprites per line at most 90) in G1.
- Test: T with sentinel `g_bg_sway_px[]`; column histogram shift of each plane's exclusive colours between two
  snapshots equals the sentinel delta; VRAM shadow shows zero SCB1 words in play.

### 2.2 Per-scanline effects with the timer interrupt

- In this game: (a) sky colour bands: the backdrop colour (entry 4095) is rewritten at 5 to 7 chosen lines, giving
  a hand-picked banded dusk or dawn sky with zero sprites; cloud silhouettes break the straight edges. (b) Optional
  heat haze over fire and lava: the head x of the mid and near planes is nudged by 1 px on alternate lines in a
  40-line band above the hazard. (c) Optional water line wobble on the hazard strip.
- Mechanism: timer interrupt reloaded per event, a short assembly `rom_handler_Timer` that writes one palette word
  or one or two VRAM words from a precomputed table and re-arms the timer. All LSPC writes in play happen in the
  vblank flush, and timer events are placed in visible lines only, so the two never race for `REG_VRAMADDR`.
- Cost: (a) 0 tiles, 0 sprites, about 0.25 line per interrupt (estimate 190 cycles with a hand-written handler),
  7 interrupts = 2 lines. (b) 20 interrupts with two words each = about 6 lines. (c) 16 interrupts = 4 lines.
- Risk: every bit of the timer set-up is UNVERIFIED; mid-frame sprite x changes on MAME and the MiSTer core are
  UNVERIFIED; the banded sky conflicts with an earlier rejection (a 4-band sky was the rejected draft in the city
  plan) and with the no-ramp rule unless the bands are few, hand-coloured and broken by clouds: decision D2.
  (b) and (c) are the first cuts (D6).
- Test: T with sentinel `g_raster_irqs` (exactly K per frame, every frame of a 600-frame run); snapshot rows show
  the band colours at the table lines; `gmake test-vblank` and `test-unibios` still pass.

### 2.3 Hardware auto-animation

- In this game: everything that loops and does not need to react: the hazard strip, chimney smoke, rooftop fans,
  flags and laundry, neon tube chase, window television flicker, star twinkle, rain streaks, bird flock wing beat,
  airship propeller and running lights, hazard spray and embers.
- Mechanism: tiles laid out in aligned groups of 4 or 8 consecutive tile numbers, attribute bit 2 or 3 set, speed
  written once to `REG_LSPCMODE`. After the tile strip is written once, the 68000 does nothing.
- 16-frame hazard loops on 8-frame hardware: two strips of 20 sprites at the same place, bank A (frames 0..7) and
  bank B (frames 8..15). Only one is shown; the other has height 0, which takes it off every scanline. When the
  hardware counter wraps, the vblank callback swaps them with two SCB3 words. Cost of the 16-frame loop: 2 words
  every 8 animation steps.
- Global speed: one speed for the whole screen. The hazard frame times are 4, 4, 6, 8 video frames (hazards v3
  README), so the speed follows the match hazard and background loops run between 0.75 and 1.5 times their drawn
  pace (decision D5).
- Cost: tiles = spatial tiles x 8 per group (no deduplication inside a group); 0 palettes extra; sprites as the
  static art would need; CPU zero, hardware. Versus software tile swap: the hazard strip alone would be 20 strips
  per frame change = about 13 lines of CPU and 640 us of flush every 4 to 8 frames (from the measured 0.6 line per
  strip), which is a third of the whole headroom.
- Risk: attribute bits, speed field and the readable counter are all UNVERIFIED locally; G2 is the proof item and
  everything in this section waits for it. If the counter cannot be read, the bank swap is timed from a frame count
  started at the `REG_LSPCMODE` write (drift shows as one repeated frame, caught by the test).
- Test: T with snapshots one animation step apart: the animated cell changes and repeats with period 8 x speed
  frames; the VRAM shadow shows no SCB1 write between them (proves hardware). Hazard: for 2 full loops the pair
  (visible bank, counter) runs 0..15 in order with no repeat or skip.

### 2.4 Palette cycling and palette-driven light

- In this game: neon signs chase and buzz; lit windows switch on and off in groups; water glints travel; lava
  cracks pulse; searchlight beam sweeps (beam drawn as several index bands, one lit at a time); **hazard cast light**
  on the near buildings and island undersides; lightning in the rain mood; per-match time of day (mood palettes).
- Mechanism: a table-driven cycler writes palette words through `gfx_pal`. Art reserves fixed index ranges for
  cycling (section 5). Cast light uses the fact that the hazard tile is 64 px wide = 4 columns: near-plane and
  island tiles in the lit band use four palettes by screen column modulo 4, lit pixels are three reserved indices,
  and the level table from the draft script (4 columns x 16 frames) says which of the 12 words change on a step.
  This keeps the per-column flicker of the draft without rewriting a single tile strip. It requires the lit plane
  to stand still relative to the hazard, which the orbit sway gives (D1).
- Cost: 0 tiles; about 6 palettes for cycling plus 4 per mood for cast light; 0 sprites; CPU about 0.2 line and
  18 us of flush per word. Budget: at most 8 palette words per frame (1.6 lines, 144 us), enforced by the cycler
  (round-robin, a late step shows one frame later).
- Risk: palette word count creeping up; a real BIOS clears palette RAM on coin re-entry (already handled by
  `bg_load_palettes`; cycler state must reload the same way, test-unibios covers it).
- Test: T: palette RAM read from Lua at the table frames equals the table; sentinel `g_pal_words_frame_max` at
  most 8; snapshot shows the lit colour in columns whose level is above 0 and not in the others.

### 2.5 Sprite shrink for depth and impact

- In this game: title logo zooms in from a point (drawn at full size, shrunk to nothing, then released to full);
  bubble pop puff that bursts outward and a new bubble that inflates on respawn; island debris and bubblegum blobs
  that shrink as they fall "into" the screen; distant decorative Sootlings floating far behind the arena at half
  size with a dark palette (same tiles as the fliers, zero ROM); the airship growing as it approaches in the intro.
- Mechanism: SCB2 per sprite. Horizontal shrink is per column, vertical is per chain.
- Cost: 0 tiles; 1 or 2 palettes (distance tint); sprites as unshrunk; CPU about 0.3 line per shrunk object per
  frame while it changes; constants (far Sootlings) are zero. Title zoom is 15 words in one run on a screen with no
  gameplay load.
- Risk: shrink steps are coarse horizontally (16 steps), so shrink reads best on fast effects and round shapes;
  pool objects need a shrink field (engine change in `obj_pool`, owned by the engine session).
- Test: T: bounding box of the object's exclusive colour at three frames follows the shrink table within 1 px.

### 2.6 Big multi-sprite set pieces

- In this game: a low moon or sun disc (64 x 64) behind the skyline; a patched cargo airship (96 x 48) that crosses
  between the far and mid planes every 40 s with auto-animated propeller and running lights; one giant rooftop
  sign on the near plane (64 x 48) with palette-cycled tubes.
- Mechanism: one sticky chain each; movement is one SCB4 word.
- Cost: moon 16 tiles, airship 18 static + 32 animated, sign 12; 1 palette each; 4 + 6 + 0 extra sprites per line
  (the sign is part of the near plane); CPU under 0.3 line when it moves.
- Risk: none beyond the scanline count.
- Test: T: exclusive colours inside the expected box; airship x follows `g_ship_x`.

### 2.7 Foreground overlap layer

- In this game: the hazard strip itself is drawn in front of the fliers so they sink into it; spray, splashes and
  embers rise in front of the lower islands; a cable with hanging lamps or a pole and banner frames the left and
  right screen edges in front of everything but the HUD.
- Mechanism: sprite indices above the hero (195 and up).
- Cost: edge dressing about 40 tiles, 1 palette, 2 to 4 sprites per line; spray is auto-animated, CPU zero.
- Risk: hides fliers at the wrap seam. Keep edge dressing thinner than 8 px in the flight band, or only above the
  ceiling line and below y 176.
- Test: T: a flier parked behind the dressing shows the dressing's colours in its box (priority proven).

### 2.8 Weather and particles

- In this game: rain mood: 10 full-height sprite columns of baked streaks, auto-animated, in front of the scene,
  with 8-frame splash crowns on island tops; dusk mood: slow embers or pollen as an auto-animated sparse column
  set; dawn mood: a bird flock crossing as one 2-sprite chain.
- Mechanism: auto-animated columns standing still; no per-particle objects. A wind gust shifts all columns with one
  strided run.
- Cost: rain 32 tiles + 16 splash; 1 palette; 10 sprites per line; CPU zero (hardware), gust under 0.5 line.
  Software particles through the pool would cost about 3 lines per 8 particles and pool slots: cut (D6).
- Risk: 10 sprites per line is the largest sparse user of the scanline reserve; rain runs only in moods whose
  set-piece count leaves room (section 4 table).
- Test: T: streak colour present in at least N columns; no SCB writes for them between snapshots.

### 2.9 Shadows and highlights with spare palettes

- In this game: every material gets a lit and a shaded palette instead of drawn-in transparency: islands under the
  moon side versus the hazard side, fliers that pass in front of the big sign take a rim-lit palette for those
  frames, a hard-edged cel shadow blob under a standing flier (solid dark colour, 1 sprite, hidden in flight).
- Mechanism: palette choice per sprite in SCB1 (already how player and computer fliers differ).
- Cost: 0 tiles for palette variants, about 8 tiles for the shadow blob; 6 to 10 palettes; CPU: a palette change
  on a flier is one strip rewrite (about 0.6 line) on the frame it changes.
- Risk: none.
- Test: T: flier box shows the rim palette's exclusive colour when its x is inside the sign zone.

### 2.10 Screen shake and flash

- In this game: stomp and pop give a 4-frame vertical shake of the scenery planes (2 px, 1 px); a match win gives
  a white flash; lightning gives two bright frames.
- Mechanism: shake adds an offset to each plane's chain head y (one SCB3 word per plane, 4 or 5 planes) for a few
  frames; islands and fliers are not shaken (collision stays readable) and the fix-layer HUD cannot move. Flash:
  backdrop word plus up to 8 palette words, or `REG_NOSHADOW`/`REG_SHADOW` for a whole-screen dim pulse at the
  cost of one register write (effect UNVERIFIED).
- Cost: 0 tiles; CPU about 1.5 lines on shake frames only.
- Risk: flash at 60 Hz on a cabinet CRT: keep flashes at most 2 frames and at most one per second.
- Test: T: SCB3 shadow of the plane heads follows the shake table after a forced stomp; backdrop entry equals the
  flash colour on the flash frames.

### 2.11 Fake transparency

- Options: (a) alternate-frame flicker (30 Hz): cheap, blends on a CRT, flickers visibly on a flat panel and in
  recordings; (b) checker mesh: a dither field, which the art rules forbid; (c) no transparency: solid cel shapes
  with lit and shaded palettes (2.4, 2.9).
- Plan: (c) everywhere. Flicker only for the invulnerability blink of a respawned flier (already a game
  convention). Mesh is not used. Using mesh for rain sheets, smoke or shadows would need the user to lift the
  no-dither rule for those cases: decision D3.
- Cost: none beyond 2.4 and 2.9.

### 2.12 Fix layer HUD polish

- In this game: a custom two-tone font with a hard drop shadow; 16 x 16 score digits built from four fix cells;
  bubble icons for remaining bubbles per flier; a player colour chip per score; a thin drawn frame under the two
  HUD rows so the HUD reads as a marquee; "Insert Coin" pulsing by palette.
- Mechanism: S ROM tiles and fix palettes; the fix diff in `vq_fix_commit` already sends only changed cells.
- Cost: about 300 fix tiles of 4096; 4 fix palettes; 0 sprites; CPU unchanged (cells change only on score events).
- Risk: fix cells limited to palettes 0..15 (UNVERIFIED) and today's palette slots 0..1 are fix: reserve 0..7.
- Test: T: fix map shadow holds the big-digit cells for the score sentinel; snapshot colours in the HUD rows.

## 3. Frame budget

Base, stress phase with 32 pool objects (newest numbers): median 152, p95 194, max 220 busy lines; a frame is lost
at about 260. Headroom on the worst frame: about 40 lines. The stress turn-on frame (303 lines) already overruns and
is the one miss the test allows; graphics must not add a second kind of burst.

Second limit: the vblank flush, 2000 us. The stress p95 flush was 27 lines (1728 us) before the cuts and was not
re-reported after them. Graphics writes must stay small and even.

| Technique | 68000 per frame | Flush per frame | Class |
|---|---|---|---|
| Static layered scene, cropped planes | 0 | 0 | free |
| Auto-animation (hazard, life, rain, stars, spray) | 0 | 0 | free |
| Hazard 16-frame bank swap | 2 words per 32 to 64 frames | 30 us on that frame | free in practice |
| Shrink constants, set pieces standing still, foreground | 0 | 0 | free |
| Mood palettes loaded at match start | outside the frame loop | drained before play | free |
| Orbit sway (3 planes) + clouds + airship + far Sootlings | 1 line average, 2 worst | one run, about 50 us | CPU, small |
| Palette cycler incl. cast light, cap 8 words | 1.6 lines worst | 144 us | CPU, small |
| Sky bands, 7 timer interrupts | 2 lines | 0 | CPU, small |
| Shake (on event frames) | 1.5 lines | 75 us | CPU, small, rare |
| Shrink effects on pool objects (2 at once) | 0.6 line | 30 us | CPU, small |
| Removed: per-frame `bg_update` ring maths | minus 6 median, minus 14 worst | | gain |
| Heat haze, 20 interrupts | 6 lines | 0 | CPU, cut first |
| Water line wobble, 16 interrupts | 4 lines | 0 | CPU, cut first |
| Software weather particles (8) | 3 lines + pool slots | 100 us | CPU, cut |
| Software hazard tile swap (fallback if 2.3 fails) | 13 lines on swap frames | 640 us | CPU, burst: avoid |

Proposed allowance for graphics: **at most 8 lines of 68000 time on any frame and at most 300 us of flush**, sum of
the "CPU, small" rows (1 to 2 + 1.6 + 2 + 1.5 + 0.6 = about 7.7 lines worst, all at once). Against that the plan
removes `bg_update` (6 to 14 lines), so the expected net change is zero or a small gain, and the worst stress frame
stays near 220 of 260. Each build item re-runs `gmake test-vblank` (reason for the run: the change touches the frame
loop) and records busy-line median, p95 and max in this file; an item that pushes the max above 235 is not landed.

Plain statement: with heat haze, water wobble and software particles the worst frame would reach about 241 lines
and leave under 20 lines for everything gameplay still wants (hazard objects, pickups, more effects). They are out
unless the user decides otherwise (D6). If auto-animation cannot be proven (G2 fails), the hazard strip falls back
to software swaps and the palette cycler and sky bands must be cut to pay for it; the plan would then be reported as
not fitting.

## 4. Scene concept: the arena over the city

Seven depth planes, at most two full-width planes on any scanline. Tile counts are estimates before deduplication;
a plane is 22 columns.

| # | Plane (far to near) | Content | y range | Motion | Sprites per line | Palettes | Tiles |
|---|---|---|---|---|---|---|---|
| 0 | Sky | backdrop colour; 5 to 7 bands by raster if D2 allows | 0..223 | mood colour, lightning flash | 0 | 1 word | 0 |
| 1 | Sky objects | twinkling stars (auto-animation, 4 variants), moon or sun disc 64 x 64 | 16..96 | twinkle; disc stands | stars sparse up to 8, disc 4 | 2 | 32 + 16 |
| 2 | Cloud bank | two long flat-bottomed cel clouds with a lit rim | 40..88 | wind drift 1 px per 16 frames, wraps | 8 | 1 per mood | 48 |
| 3 | Far skyline | silhouette towers, aerials with beacons (auto-animated blink), far haze colour, cropped where plane 5 hides it | 72..135 | sway plus or minus 16 px | 22 | 1 | 120 |
| 4 | Airship | patched cargo airship, propeller and lights auto-animated; far Sootlings (half size) drifting near it | 80..128 | crosses in 40 s, then pauses | 6 + 3 | 2 | 50 |
| 5 | Mid skyline | buildings with window groups (palette cycled), two chimney smoke plumes (2 x 3 tiles x 8 frames each), flags, a water tower | 96..175 | sway plus or minus 8 px | 22 | 3 (walls, windows, smoke) | 240 |
| 6 | Near rooftops | rooftop edge with fans (auto-animated), laundry line, the giant sign (palette-cycled tubes), pipes; receives hazard cast light in its bottom 3 rows through 4 column palettes | 136..191 | stands still | 22 | 2 + 4 lit | 240 |
| G | Gameplay | 8 islands (redrawn as floating rooftop chunks with roots of pipe and cable, lit undersides near the hazard), fliers, effects | 16..200 | game | 30 reserved | islands 2 + 4 lit, fliers 2 to 7 | 100 |
| 7 | Hazard strip | one of water, fire, lava, spikes: 64 x 32 tile x 5, 16 frames, bank A and B; in front of the fliers | 192..223 | auto-animation + bank swap | 20 | 1 | 4 x 128 = 512, + 64 lava bubble variant |
| 8 | Foreground | hazard spray or embers (auto-animated), rain columns (rain mood), edge cable with lamps | 0..223 | hardware; gust shift | 10 rain or 4 spray, + 2 edge | 2 | 90 |

Worst scanlines (scenery + 30 gameplay reserve, limit 96, target at most 90):

| Lines | Scenery | Total with gameplay |
|---|---|---|
| 40..71 | clouds 8, stars 8, disc 4, rain 10, edge 2 = 32 | 62 |
| 72..95 | far 22, clouds 8, disc 4, airship 9, rain 10, edge 2 = 55 | 85 |
| 96..135 | far 22, mid 22, airship 9, edge 2 = 55; with rain 65 | 85; rain mood 95: **over target**, so in the rain mood the airship and far Sootlings are absent (56, total 86) |
| 136..175 | mid 22, near 22, rain 10, edge 2 = 56 | 86 |
| 176..191 | near 22, rain 10, spray 4, edge 2 = 38 | 68 |
| 192..223 | hazard 20, spray 4, rain 10 = 34 | 64 |

Tile total: about 1,500 new tiles (192 KiB of the 4 MiB pair, with today's 511 that is 6 percent). Room is left to
double every animated loop if a draft needs it.

Stage moods (decision D4). Same tiles, different palette sets (about 14 palettes each, loaded at match start, not
in the frame budget), one mood-specific extra each:

| Mood | Sky and light | Extra | Hazard pairing by default |
|---|---|---|---|
| Dusk | magenta to amber sky bands, low sun disc, warm rim light from the left, long cool shadows | embers or pollen rising, airship | lava, fire |
| Night rain | deep blue-violet, moon behind cloud, neon at full strength, wet rooftop highlights (palette), lightning every 10 to 20 s | rain columns, splash crowns, no airship | water, spikes |
| Dawn | teal to peach bands, pale disc, cool rim light from the right, mist colour on the far plane | bird flock, airship | any |

The budget allows three moods because moods cost ROM and palettes only. An in-match time-of-day shift is not
planned: it would cost 15 palette words per frame during the shift, twice the cycler cap.

## 5. Art production pipeline

1. Draft: one Python script per subject under `thoughts/shared/drafts/<date>-<subject>/` (as
   `draw_hazards_v3.py`), deterministic, simulation-baked for fluids (smoke, rain, spray, flags as cloth), drawing
   at 1x in the final palette. Outputs: `frames_<name>_1x.png` (frames in one row, RGBA, index 0 transparent),
   scene mock PNG at 3x, animated GIF at real frame timing, and an `index.html` gallery. Shown in the browser,
   never with `open` on a PNG. The user picks; the pick is recorded in the draft README.
2. Import: the picked `frames_*_1x.png` and a JSON sidecar (frame count, frame time, palette list in index order,
   cycle ranges, auto-animation flag, plane and crop rows) are copied to `assets/<set>/`. No hand edits after
   import; a change goes back through the script.
3. Build: `tools/sprite_pipeline.py` (the existing generic converter with deduplication and round-trip verify;
   extend it, do not write a second one) gains:
   - auto-animation groups: frames of one spatial tile are placed at 4 or 8 consecutive tile numbers on an aligned
     base, the group is deduplicated only as a whole, and the header carries the attribute bit;
   - bank split for 16-frame loops (frames 0..7 and 8..15 as two groups with the same spatial order);
   - palette sets: one tile set, N named palettes (moods, lit levels), emitted as tables;
   - checks that fail the build: more than 15 colours in a palette; a cycling or lit index used outside its range;
     any 2 x 2 checker of two colours repeated over more than 8 x 8 px (mechanical guard for the no-dither rule);
     more than 7 shades of one material ramp as declared in the sidecar; the scanline table (sprites per line from
     the plane rows) above 90.
4. Palette order rules (so palette effects are table-driven and art cannot break them):
   - index 0 transparent; index 1 the outline or darkest shade; then each material ramp dark to light, contiguous;
   - cycling ranges contiguous and declared in the sidecar (neon 3 to 4 entries, windows 3 groups, water glint 3);
   - cast-light indices fixed at 13, 14, 15 (face, rim dim, rim hot) in every palette of a lit plane; they hold the
     unlit colours at level 0;
   - a colour that a pixel test relies on is exclusive to its plane (as `check_bg_pixels.py` already requires).
5. C ROM order: append new sets to `CROM_SETS` (Makefile line 90) in plane order; bases stay derived in
   `src/vram_layout.h` from the generated headers. `test-crom` (exists) guards the order.
6. Deduplication: static tiles deduplicate across a set (existing); horizontal flip matching may be switched on for
   symmetrical set pieces; animated groups never deduplicate internally.
7. One test per technique, listed with each build item below; mutation check once per item (switch the feature off,
   see its test fail, switch it back).

## 6. Ordered build list

Order is visual gain per cost, after the two items everything depends on. "Draft" means a visual draft round and a
user pick come first. Every test is headless MAME through the real ROM (pattern T in section 2) and every item
re-runs `gmake test-vblank`.

| ID | Item | Reachability test | Depends on | Draft first |
|---|---|---|---|---|
| G1 | Budget guards: new sprite slot map (planes 0..6 below the pool, hazard and foreground above the hero), host test for sprites per line at most 90 from the layout tables, sentinel `g_pal_words_frame_max` | `test-scroll`, `test-flier` still pass on the new map; snapshot proves hero in front of planes and behind slot 195+ test sprite | engine cuts landed | no |
| G2 | Auto-animation proof: write `REG_LSPCMODE` speed, pipeline group layout, star twinkle moved from software swap to hardware | new `test-autoanim`: star cell changes with period 8 x speed, zero SCB1 writes in the VRAM shadow, counter readable (records the answer to the UNVERIFIED bits) | G1 | no |
| G3 | Hazard strip in the ROM: picked hazard, 16 frames as bank A and B with the hidden twin strip, in front of the fliers | `test-hazard`: visible frame runs 0..15 in order for 2 loops, hazard colours in y 192..223, a drowning flier is covered by the strip | G2, the user's hazard pick from drafts v3 | pick pending |
| G4 | Scene draft round: full 320 x 224 scene mock for the three moods with all planes, islands and one hazard, animated GIF with sway and life | none (draft); output is the pick written into this plan | D1, D2, D4 | yes |
| G5 | Layered city: planes 3, 5, 6 and clouds as sticky chains with cropping, orbit sway, `bg_update` ring maths off in the arena | `test-parallax`: histogram shift per plane equals `g_bg_sway_px`, zero SCB1 writes in play, busy lines not above the G1 baseline | G1, G4 | by G4 |
| G6 | Background life by auto-animation: smoke, fans, flags, beacons, sign frame | `test-autoanim` extended: each listed cell animates, no VRAM writes | G2, G5 | by G4 (smoke and cloth baked from simulation) |
| G7 | Island redraw as floating rooftop chunks, shaded and lit palettes | `test-flier` pixel box updated; island exclusive colours at the 8 platform rectangles | G4 | by G4 |
| G8 | Palette cycler (cap 8 words per frame): neon, window groups, water glint, lava pulse | `test-palcycle`: palette RAM equals the table at the table frames, cap sentinel at most 8 | G5 | no |
| G9 | Hazard cast light: 4 column palettes on plane 6 and island undersides, level table from the hazard script | `test-castlight`: lit colour present only in columns whose level is above 0, follows the 16-frame table | G3, G7, G8 | draft exists (v3 item 5); re-check on the G4 scene |
| G10 | Set pieces: moon or sun disc, airship crossing with far Sootlings (shrink constant) | `test-setpiece`: disc colours in its box, airship x equals `g_ship_x`, far Sootling box is half size | G5 | by G4 |
| G11 | Mood rotation: three palette sets, chosen per match, hazard pairing table | `test-mood`: three matches in a row show three backdrop and plane colour sets; `test-unibios` re-entry keeps the mood palettes | G5, G8 | by G4 |
| G12 | Weather: rain columns and splash crowns (night rain), bird flock (dawn), embers (dusk), lightning flash | `test-weather`: streak colour in at least 8 columns in the rain mood only, zero SCB writes for them, flash frames at most 2 | G2, G11 | yes (rain and splash simulation) |
| G13 | Sky bands by timer interrupt | `test-raster`: `g_raster_irqs` exactly K per frame for 600 frames, band colours at the table rows, `test-unibios` passes | D2, G11 | by G4 |
| G14 | Foreground: hazard spray or embers in front of the low islands, edge cable with lamps | `test-foreground`: a flier parked behind the dressing is covered | G3, G5 | yes (spray simulation) |
| G15 | Shrink effects: title zoom, bubble pop and inflate, falling debris | `test-shrink`: bounding box follows the shrink table at three frames | G1, pool shrink field from the engine session | yes (pop frames) |
| G16 | Shake and flash on stomp, pop and match win | `test-shake`: plane head SCB3 follows the shake table after a forced stomp; islands and fliers unchanged | G5 | no |
| G17 | Fix layer HUD: font, big digits, bubble icons, marquee frame | `test-hud`: fix map shadow holds the big-digit cells for the score sentinel | none | yes |

Not on the list (cut, D6): heat haze, water line wobble, software particles.

Human checks, each asked with the window named in chat (`make run`, LOCAL): after G3, G5, G9, G12 and at the end.
PASS is judged against the user's words: not flat, alive everywhere, reads as 16-bit depth.

## 7. Decisions for the user

- **D1 Background motion in the still arena.** (a) Orbit sway (Recommended): near plane and islands still, mid and
  far swing a few pixels, clouds and airship drift; true parallax, near-zero cost, cast light stays per column.
  (b) Continuous drift of all city planes behind the islands: stronger motion, but the arena reads as moving, costs
  ring updates, and cast light falls back to whole-screen flicker. (c) No plane motion: cheapest, least depth.
- **D2 Sky.** (a) 5 to 7 hand-coloured flat bands through the backdrop colour, edges broken by clouds
  (Recommended): rich sky for zero sprites and about 2 lines; this is close to the 4-band sky rejected earlier and
  must not look like a ramp. (b) One flat sky colour per mood: safe against the no-ramp rule, flatter. (c) A drawn
  sky plane of tiles: full control of shapes, costs 22 sprites per line and removes one skyline plane.
- **D3 Transparency.** (a) None: solid cel shapes, lit and shaded palettes, flicker only for the invulnerability
  blink (Recommended): keeps the no-dither rule intact. (b) Allow checker mesh for rain sheets, smoke and shadows:
  softer look, breaks the rule for those cases. (c) 30 Hz flicker for larger effects: blends on the cabinet CRT,
  flickers on flat panels and in recordings.
- **D4 Moods.** (a) Three moods rotating per match, palette sets plus one extra each (Recommended): large variety
  for ROM and palettes only; triples the palette drafting work. (b) One mood finished first, the others after the
  cabinet test: fastest route to a polished screen. (c) In-match time-of-day shift: does not fit the palette cap.
- **D5 Auto-animation speed.** (a) Follows the match hazard's frame time, background loops run 0.75 to 1.5 times
  their drawn pace (Recommended): the hazard costs no CPU. (b) One fixed speed, hazards redrawn to one frame time:
  even background pace, hazard timing from the drafts changes. (c) Fixed speed and software hazard swaps: exact
  timing everywhere, costs about 13 lines and 640 us on swap frames and forces cuts elsewhere.
- **D6 What is cut to fit the frame.** (a) Heat haze, water line wobble and software particles are out; rain,
  spray and embers are hardware columns (Recommended): keeps about 40 lines of headroom for gameplay. (b) Keep heat
  haze for fire and lava only: about 6 lines on those matches. (c) Keep all three: worst frame near 241 of 260,
  under 20 lines left for hazard objects and pickups.

### User answers (2026-11-10, through the question tool)

- **D1: (a) Orbit sway.** Near plane and islands still, mid and far planes swing a few pixels, clouds and airship
  drift. Cast light stays per column.
- **D2: (c) Drawn sky plane of tiles** (the user chose this over the plan's recommended colour bands). Cost
  accepted: 22 sprites per scanline and one skyline plane, so the city has 6 depth planes, not 7. Sections 2 and 4
  must be read with this change; the backdrop colour band technique is not used for the sky.
- **D3: (b) Checker mesh** for rain sheets, smoke and shadows.
- **CORRECTION, 2026-11-10: there is no "no-dither rule".** The user: "the no dither rule i never asked for". The
  rule was the assistant's wrong reading of the feedback about generated-looking gradients. Every mention of a
  no-dither rule in this plan (section intro, 2.x transparency, the section 5 pipeline guard that rejects 2 x 2
  checkers over 8 x 8 px, D3 text) is void. Dithering is allowed and wanted; the style comes from the user's pick
  of the dither variant drafts (`thoughts/shared/drafts/2026-11-10-dither-variants/`). The pipeline guard is
  removed or rewritten after that pick.
- **D4: (a) Three moods rotating per match** in the first build. Palette drafting is tripled; every background
  draft round shows all three moods.
- **D5: (a) Auto-animation speed follows the match hazard's frame time**; background loops run 0.75 to 1.5
  times their drawn pace.
- **D6: "lets test to not cut first"** (user's words). Nothing is cut up front: heat haze, water line wobble and
  software particles are built behind knobs, then measured with `gmake test-vblank` in the stress phase. A cut is
  decided from the measured numbers (the plan estimate for keeping all three is a worst frame near 241 of 260
  lines). Build order consequence: each of the three effects lands as its own step with its own measurement, so one
  can be removed without touching the others.

## Risks and unverified

- UNVERIFIED hardware claims (no local source beyond register names): 381 sprites and 96 per line; which sprites
  drop on overflow; 32-tile sprite height; shrink step counts and sticky inheritance; auto-animation attribute
  bits, speed field, disable bit and readable counter; timer reload units, mode bits, acknowledge bit and
  interrupt level; mid-frame backdrop and sprite x changes in MAME and on the MiSTer core; `REG_SHADOW` effect;
  fix layer palette range; 128 MiB cartridge limit; MiSTer core C ROM limit; whether MAME enforces the 96 per line
  limit (if it does not, only the host test protects the cabinet).
- G2 is the gate for sections 2.3, 2.8 and the hazard. Its test records the real answers; update this file then.
- CPU and flush costs of new techniques are estimates from the measured per-word queue cost, not measurements.
- The engine cuts that give the 152 / 194 / 220 baseline are uncommitted.
- Stale files `build/gen/heat_sprites.h` and `build/gen/hero_sprites.h` are not part of the ROM; ignore them when
  counting tiles.
- Nothing here was checked on the cabinet.

### Dither decision (user, 2026-11-10)

Style: S6 "mixed by material" from `thoughts/shared/drafts/2026-11-10-dither-variants/`: sparse transition on steel, crust and rock; ripple dashes on water; checker blend on melt and glow; graded 25/50/75 pattern on sky; foam stays hard. Strength is not fixed yet: the user asked for a stronger pass first (`thoughts/shared/drafts/2026-11-10-dither-s6-strong/`). The pipeline guard that rejects 2x2 checkers is to be removed. Tile reuse on static repeating background tiles must be measured once dither is on them.

Strength (user, 2026-11-10): sky H (full band, eighth steps), spikes H, water M (half band, quarter steps), lava M with the H fade on the cast light. Sky dither is hand-clustered (irregular clusters, cloud-shaped breaks), not the ordered 4x4 grid, on the 5-shade ramp up to violet (54,40,108). Reference: `thoughts/shared/drafts/2026-11-10-dither-s6-strong/`. Open: sky +2 colours not yet checked against the backdrop palette split.

### Dither decision, final (user, 2026-11-10, after the visible pass)

Supersedes the strength block above. Drafts: `thoughts/shared/drafts/2026-11-10-dither-visible/`.

- Rule: the two colours of every dither pattern are at least 28 of 255 apart in luminance; ramps use fewer, further-apart shades and dither supplies the in-between tones. Draft and pipeline scripts print dither pixel count and median pair step.
- Sky: V1 (pair step about 30, 4 colours), clusters from hand-drawn shapes, not a seeded generator.
- Lava: V1 (step about 31), cast light fade kept, crust grid anchor kept.
- Water: V2 (step about 42), full band.
- Spikes: no dither. Use the undithered v4 spikes.
- Fire: dither test still open (V1 step).
- Fire (user, 2026-11-10): dithered v6 with retuned palette accepted (pair step median 33.4). Hazard art is final: `thoughts/shared/drafts/2026-11-10-hazards-final/`. Water there uses a 1 px checker thinned along ripple order, full band.

## Update 2026-11-10: D1 orbit sway replaced

User decision (question tool): the arena becomes 384 px wide with a camera that follows
the human players. Camera parallax replaces the orbit sway for the city planes (far,
midA, midB, near); `g_bg_sway_px` goes away. Sky objects (airship, clouds, far Sootlings)
keep their own drift. Every "orbit sway" in this plan (D1, G4, G5, plane table, cost
table) reads as camera parallax. Details and checklist C1..C13:
`thoughts/shared/plans/2026-11-10-wide-arena-camera.md`.

Fliers: art grows to 32x48 (2 sprite columns per flier), same hit box; bubble design B
(one double-lobed membrane). Per-line budget proof required.
