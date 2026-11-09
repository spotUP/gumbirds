---
date: 2026-11-09
topic: Obstacle sprites (vent, cable, drone, bot) drawn from game state
tags: [art, sprites, pipeline, neo-geo, tests, reachability]
status: done
---

# Obstacle sprites

## Result

- Original art (no external source): tools/draw_obstacle_sheet.py -> assets/obstacles/obstacle_sheet.png + .json. Sizes match the hit boxes: vent 32x24 (2 frames), cable 48x16 (3), drone 28x20 (4), bot 28x28 (2). One palette, 14 colours + transparent, 30 unique tiles, 11 frames.
- Pipeline unified: tools/sprite_pipeline.py is the hero pipeline made generic (`main(name, sheet, meta)`); hero and obstacle wrappers are a few lines. Hero C-ROM output is byte-identical to before. New palette policy "merge" (grow an existing palette while the union fits 15 colours). Generated header has `<N>_MAX_COLUMNS`. Round-trip verifier runs for both sets (obstacles: 11 frames, 10496 pixels, 0 mismatches).
- C-ROM order: logo, hero, obstacles. Tile base, palette slot (after hero palettes 2,3) derive from generated headers. Palettes load in video_init(). Animation index equals ObstacleType, enforced by _Static_assert.
- Frame choice is the pure helper src/core/obstacle_view.[ch] (host tested). main.c only writes registers.
- Sprite slots: OBSTACLE_SPRITE_BASE 128 (64 slots, 8 obstacles x 3 columns) in src/sprite_slots.h, per coordinator: background reserves 0..88, hero moves to 192 later (HERO_SPRITE untouched). Unused columns and inactive obstacles are hidden every frame (height 0, non-sticky).

## Reachability proof

- tests/mame/boot_check.lua reads the active obstacles from RAM (offsets from tests/mame/layout_probe.c, compiled for the 68000) and snapshots obstacles.png at the first frame with an obstacle fully on screen. tests/mame/check_obstacle_pixels.py counts obstacle-only colours in each obstacle box (min 30, none before start). First run: a bot, 554 px.
- Disabled the obs_show call: check failed (0 px, min 30). Restored: pass.
- check_hero_pixels.py now counts only hero colours no obstacle palette uses (16 hero-only colours), so the checks are independent.
- make test and make test-unibios both pass.

## Found

- First obstacle appears after frame ~380 and depends on the seed, so the Lua script polls instead of using a fixed frame.
- Layout offsets must come from the 68000 compiler: m68k aligns int32 to 2 bytes, host gcc gives other offsets.
