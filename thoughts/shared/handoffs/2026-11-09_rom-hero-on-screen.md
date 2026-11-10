---
date: 2026-11-09
topic: Bubblegum Brawl ROM with core logic and hero sprite on screen
tags: [handoff, neogeo, ngdevkit, brawl]
status: final
---

# Handoff: ROM runs core, hero on screen

## Tasks
Bubblegum Brawl Neo Geo MVS endless runner. This session: art lock (v9), game core + flow (host tests), P0 toolchain and ROM, BIOS USER re-entry fix, hero sprite pipeline and display.

## Critical references
- Plan: /Users/spot/.claude/plans/buzzing-kindling-heron.md
- Ledger (order of remaining work): thoughts/spot/todos.md
- thoughts/shared/research/2026-11-09_p0-toolchain.md (sections "P0 step 3", "BIOS USER re-entry")
- thoughts/shared/research/2026-11-09_hero-sprites.md (section "Hero on screen")
- thoughts/shared/research/2026-11-09_art-direction.md (locked v9), design/brawl-test-v5.html
- thoughts/shared/research/2026-11-09_game-core.md, 2026-11-09_flow-nameentry.md, 2026-11-09_game-design-shooting.md

## Recent changes
- src/main.c: glue loop, rom_game/rom_title hooks (no C runtime re-init on coin), bios_user_mode 2 in PLAYING, hero 3-sprite draw, fix-layer text.
- Makefile: core + hero_sprites linked, C-ROM = logo (256 tiles) + hero; make run windowed 960x672; make test = host tests + boot_check.lua + check_hero_pixels.py.
- src/core/nameentry.c: stuck-button timeout fix + regression test.
- tools/build_hero_sprites.py.

## Learnings
- ngdevkit default rom_game/rom_title re-run init_c_runtime then main: define them in the game.
- SCB sprite pattern: ngdevkit-examples 03-sprite-animation/main.c:54-84; bios_user_mode: 07-attract-and-game/main.c.
- Hero palettes slots 2,3 (fix layer uses 0,1). HERO_TILE_BASE 256.
- Black-screen report from user: earlier MAME ran fullscreen with only small debug text. Now windowed.

## Next steps
See ledger "Open, in order". Start with enemies/obstacles sprites.

## Other notes
- Not a git repo yet; nothing committed. Ask user before git init/commit.
- DEViLBOX preset fix prompt: ~/Code/DEViLBOX/thoughts/spot/next-session-neogeo-presets.md.
