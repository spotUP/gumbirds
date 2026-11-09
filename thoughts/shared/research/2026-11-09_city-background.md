---
date: 2026-11-09
topic: City parallax background implementation status
tags: [background, parallax, neo-geo, sprites, tests]
status: in-progress
---

# City background: status (12 of 14 done; B1 unverified, B14 human only)

Plan: thoughts/shared/plans/2026-11-09-city-background.md. Checklist B1..B14.

## Result
- B2 answer: backdrop colour is the last palette RAM entry, `MMAP_PALBANK1[4095]`, not entry 0. Verified by snapshot (0x0f00 there gave red). Loaded in `video_init()` through `bg_load_palettes()` because the real BIOS clears palette RAM on re-entry.
- B1: v9 equals v5 (Q1) stays unverified, as decided by the user.
- B14 open: human check on `make run`.

## Design as built
- Art: assets/city/draw_city.py (v5 port, 320 px torus, roof line y 176) -> city_sheet.png/json -> tools/build_city_sprites.py (generic tools/sprite_pipeline.py; `src_w/src_h` widened to u16 because 320 overflowed u8).
- Runtime: src/bg.c, three rings of 21 non-sticky sprites (far, mid, roof) + stars + moon/clouds. Scroll is a pure function of distance (src/core/bg_scroll.c): far = d>>10, mid = ((d>>4)*9)>>8, roof = d>>8 (d in 8.8 px). Entering column strip is rewritten when the first visible column advances.
- Lamps blink by palette swap; stars twinkle by tile swap.
- Sprite map: src/sprite_slots.h (bg 0..88, obstacles 128..191, hero 192). Tile map: src/vram_layout.h.

## Tests
- tests/host/test_bg.c: 117 checks.
- tests/mame/check_bg_pixels.py: backdrop share, layer colours in bands, measured shift equals exported scroll (far 15, mid 34, roof 60 px between snapshots), delta ratios 0.25 / 0.5625, strip write count equals column boundaries crossed.
- Far layer has only 1 layer-only colour, so its shift evidence is thin (24 of 43 pixels); it still matches exactly.
- Roof uses whole-pixel comparison: colour masks were ambiguous at a 4 column offset.
- Hero outline colour #21184a collided with the roof colour (within tolerance 12); roof colour `stv` moved to #4a2a30.
- unibios_check.lua: city palettes (weighted sum) and backdrop survive the coin re-entry.
- B13 mutation: `bg_update` call disabled -> 8 pixel checks failed; reverted.

## Human check (B14)
Run `make run` (MAME window): skyline visible, three speeds visible, lamps blink, hero in front, no 2 px slits, loop seam invisible after 320 px of roof travel.
