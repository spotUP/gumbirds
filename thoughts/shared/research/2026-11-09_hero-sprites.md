---
date: 2026-11-09
topic: P2.5 hero sprite pipeline - guard_sheet.png to Neo Geo C-ROM tiles, palettes, C table
tags: [neogeo, sprites, crom, palette, hero, p2.5, tiletool]
status: pipeline-done-not-integrated
---

# Pipeline

`assets/hero/guard_sheet.png` + `guard_sheet.json` -> `tools/build_hero_sprites.py` -> `build/gen/` (generated, not committed):

- `hero.c1`, `hero.c2`: C-ROM tile pair, 64 bytes per 16x16 tile per file. Made by the stock `tiletool.py --sprite -c` on a 1-row palette-indexed atlas (index 0 = transparent), exactly the rule in ngdevkit build.mk (`%.c1 %.c2: %.gif`).
- `hero_sprites.c` / `hero_sprites.h`: `hero_palettes[2][16]` (DRGB words), `hero_tile_index[]`, `hero_frames[34]` (HeroFrame), `hero_anims[16]` (HeroAnim), `HERO_ANIM_*` ids, `HERO_TILE_COUNT`.
- `hero_atlas.png`: intermediate atlas.

Command (PYTHON from config.mk, Pillow needed; `-I` ok):

    /opt/homebrew/bin/python3.14 -I tools/build_hero_sprites.py [--out build/gen] [--scratch DIR] [--no-verify]

Exit non-zero with `[ERROR]` on: partial alpha, colour that is not a 5-bit expanded value, more than 15 colours in an animation or a tile, tile file size mismatch, any round-trip pixel difference.

# Decisions

- Pattern copied from ngdevkit: `tiletool.py --sprite -c` for tiles; palette word layout as paltool.py (bit 15 dark, bits 14-12 = LSB of R,G,B, nibbles above). paltool.py itself is NOT used: it truncates to 6 bits and derives the dark bit from the LSBs, which is not exact for this art. We emit dark bit 0 and the exact 5-bit channel (hi 4 bits + LSB); colour 0 = 0x8000 (transparent).
- Frame box: ceil(w/16) x ceil(h/16) tiles. Art is centred horizontally (pad_left = (box-w)/2, so hflip pivots on the sprite centre) and bottom aligned (pad_top; feet = bottom edge of the box). Hero frames are 34 px wide -> 3 tiles wide, 2 or 3 tiles tall.
- One palette per animation; an animation joins an existing palette only if its colours are a subset (no growth). Result: palette 0 = hero body (14 colours + transparent, shared by all 14 body animations), palette 1 = effects (laser, hit_flash; 3 colours + transparent).
- Tiles are deduplicated across frames (tile 0 = blank). Index lists are column-major, top tile first (Neo Geo sprite = vertical strip of tiles).
- Colours in the sheet differ from the `palette` map in the json (json holds the pre-rounding values); the sheet is the source of truth.

# Result

    [OK] frames=34 palettes=2 tiles=102 (unique, incl. 1 blank) tile-refs=267
         palette 0: 14 colours + transparent; anims: run, run_shoot, run_recoil, aim_forward, aim_forward_recoil, duck, duck_recoil, jump, jump_recoil, hit, aim_diag_up, aim_up, aim_diag_down, aim_down
         palette 1: 3 colours + transparent; anims: laser, hit_flash
    [OK] round-trip: 34 frames, 68352 pixels compared, 0 mismatches

Round-trip decodes the shipped `hero.c1/c2` with `tiletool.py --sprite -x`, parses palette words and tables back out of the generated `hero_sprites.c` (2-D palette words reconverted to RGB), rebuilds each frame and compares every pixel including transparency to the sheet. Negative check: flipping one byte of hero.c1 made it fail with pixel mismatches (verified once, not a committed test). Limit: encode and decode both come from tiletool, so a tiletool bit-order bug would cancel; the layout was read in tiletool source, final proof is MAME showing the sprite.

hero.c1/c2 are 6528 bytes each (102 tiles x 64).

# Integration notes (not applied)

Existing C-ROM: `build/assets/base-crom-logo.c1/.c2` are 16384 bytes = 256 tiles (ngdevkit logo, padded). CROM1/CROM2 are built by `echo $^ | xargs cat` then truncated to CROMSIZE (2 MB), so appended files land after the logo.

1. Makefile (other agent owns it; line near existing `$(CROM1): $(BUILDDIR)/assets/base-crom-logo.c1`):

        $(CROM1): $(BUILDDIR)/assets/base-crom-logo.c1 $(BUILDDIR)/gen/hero.c1
        $(CROM2): $(BUILDDIR)/assets/base-crom-logo.c2 $(BUILDDIR)/gen/hero.c2
        $(BUILDDIR)/gen/hero.c1 $(BUILDDIR)/gen/hero.c2 $(BUILDDIR)/gen/hero_sprites.c $(BUILDDIR)/gen/hero_sprites.h: assets/hero/guard_sheet.png assets/hero/guard_sheet.json tools/build_hero_sprites.py
        	$(PYTHON) -I tools/build_hero_sprites.py --out $(BUILDDIR)/gen

   Order of prerequisites matters (cat order): logo first. Add `$(BUILDDIR)/gen/hero_sprites.c` to the 68k objects and `-I$(BUILDDIR)/gen` to CFLAGS (check how SRCDIRS/objects are derived in the Makefile; the pattern rule may need a vpath for build/gen).
2. Tile base: `#define HERO_TILE_BASE 256` (logo size) in main.c. If the logo is dropped from the C-ROM later, base becomes 0; keep the macro single-sourced.
3. Palettes (in main.c, glue only): the fix layer already uses palette bank slots 0 and 1 (`MMAP_PALBANK1[0..2]`, `[16..18]`). Sprites share the same palette RAM, so load hero palettes at slots 2 and 3:

        for (p = 0; p < HERO_PALETTE_COUNT; p++)
            for (i = 0; i < 16; i++) MMAP_PALBANK1[(2 + p) * 16 + i] = hero_palettes[p][i];

4. Show frame 0 of `run` (HERO_ANIM_RUN, hero_frames[0]) as hardware sprite number S (e.g. 1), at (x, y) in pixels. For each of `tiles_w` columns c use SCB1 (VRAM 0 + S*64), rows 0..tiles_h-1 (32 entries of 2 words per sprite): word0 = tile & 0xFFFF; word1 = (palette_slot << 8) | ((tile >> 16) & 0xF) << 4 (flips are bits 0,1, auto-animation bits 2,3). Because a sprite is one strip, a 3-wide hero needs 3 hardware sprites (S, S+1, S+2), one per column; chain them via SCB2 sticky bit (bit 6 of SCB3-level word: sticky sprites follow the previous one) or position each explicitly. Steps with registers.h: `*REG_VRAMMOD = 1; *REG_VRAMADDR = ADDR_SCB1 + S*64; *REG_VRAMRW = word...` ; SCB2 at `ADDR_SCB2 + S` = 0x0FFF (no shrink); SCB3 at `ADDR_SCB3 + S` = (Y_value << 7) | height_in_tiles (Y = 496 - screen_y, wraps; check ngdevkit example 02/04 `sprite` code for the sign convention before trusting this note); SCB4 at `ADDR_SCB4 + S` = x << 7. Register layout from the Neo Geo programming docs, UNVERIFIED against this ngdevkit version; the ngdevkit-examples sprite example (not installed locally; `mdfind -name ngdevkit-examples` found nothing) is the reference to copy.
5. Reachability test (rule in RULES.md): headless MAME Lua check that the screen shows hero colours: the palette 0 colours (e.g. 0x8CADF7 family; read distinct colours via `screens[":screen"]:pixels()` as in the p0 doc) appear after boot, plus a sentinel set by the show-hero call. Palette RAM reads are not usable as proof (p0 doc).
6. `make clean` should leave build/gen regenerable; build/gen is already under ignored build/.

# Open items

- Not built into the ROM; nothing in src/ or Makefile touched. Sprite register sequence in note 4 is from memory, not from an ngdevkit source in this checkout: verify first.
- On-screen look unchecked (no screenshots per brief). Neo Geo sprite rows beyond 224 px and the 48 px aim_up frame (3 tiles tall) fit one strip (max 32 tiles).
- hit_flash is 13x13 and laser 24x5: each takes a 1x1 or 2x1 tile box, wasting space but fine.
- Hflip: box-centred, pivot is tile box centre (art centred), good for facing left; recoil/muzzle offsets are in json origin only.
- No dark-bit or shrink use; no auto-animation (run cycle must be driven by main.c switching hero_frames).

# Hero on screen

Changed
- Makefile: CROM1/CROM2 = logo then build/gen/hero.c1/.c2 (logo is 16384 bytes = 256 tiles, so HERO_TILE_BASE 256 verified); rule runs tools/build_hero_sprites.py into build/gen; build/gen/hero_sprites.o linked into the ELF; main.o depends on hero_sprites.h. Serial build kept.
- src/main.c (glue only): hero palettes to slots 2 and 3; each frame in PLAYING the hero is placed from game_hero_box (feet = hit box bottom, box left = HERO_X - 11) as 3 sticky hardware sprites (sprite 0..2), frame from state: invuln blink = hit, airborne = jump, ducking = duck, else run cycle (game frame / 4). Hidden (SCB3 height 0) outside PLAYING. BIOS_USER_MODE = 2 in PLAYING, 1 otherwise.
- tests/mame/boot_check.lua extended; tests/mame/check_hero_pixels.py new; RULES.md Commands updated.

Verified SCB pattern (resolves the open item in Integration note 4)
- Source: dciabrin/ngdevkit-examples 03-sprite-animation/main.c:54-84 (cloned, since deleted). SCB1 at ADDR_SCB1 + sprite*64, VRAMMOD 1, two words per tile row (tile low 16 bits, attr = palette<<8 | flips); then VRAMMOD 0x200 from ADDR_SCB2: word SCB2 = 0xFFF, SCB3 = (y<<7)|height, SCB4 = x<<7; follower sprites get SCB2 = 0xFFF and SCB3 = 1<<6 (sticky). Palette slot 0 fix text, slot 1 sprite (example 03:36-43). Example 03 puts hero-like tiles at 256 after the logo (main.c:119-120), same layout as here. Y convention: I use 496 - top; confirmed by screen pixels (feet at y=175).
- BIOS_USER_MODE: examples 07-attract-and-game/main.c:29-31, 90 (USER_MODE_DEMO 1, GAME 2; bios_user_mode).

Test result (gmake test)
    PASS counter 290 -> 421 over frames 290..420 (-> 701 at 700), state 0 -> 3, image unchanged, coin=true start=true, user_mode 2 playing, 2 after 2nd coin, state 3/3
    [OK] hero pixels in box (25, 116, 97, 188) (image (320, 224), 14 colours): before start 0 (max 5), playing 806 (min 200)
    [OK] make test passed
(host: test_core 3859, test_flow 36172, knobs 59, 0 failures.)

Snapshots for a later visual check (agent did not look at them)
- /private/tmp/claude-501/-Users-spot-Code-ArcadeGame/06a12133-dc4e-43e6-b08a-169b50911a0f/scratchpad/heroint/snaps/pre_start.png (attract, frame 350)
- /private/tmp/claude-501/-Users-spot-Code-ArcadeGame/06a12133-dc4e-43e6-b08a-169b50911a0f/scratchpad/heroint/snaps/playing.png (PLAYING, frame 450)
- latest run also in build/test-snap/

Open items
- Look at playing.png: pixel test proves hero colours at the expected box, not that tiles are arranged correctly (column order, tile seams) or look right.
- Run cycle speed (4 frames), hit blink, and the muzzle/laser frames (run_shoot, laser, hit_flash anims) are not wired; only run, jump, duck, hit.
- Second-coin check uses MAME coin input only; hardware credit behaviour with mode 2 unverified.
- A vitest run from another session (Jobb) was active when make test ran; I did not wait.
