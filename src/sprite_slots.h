#ifndef SPRITE_SLOTS_H
#define SPRITE_SLOTS_H

/*
 * Hardware sprite slot map (381 sprites). Single place that says who owns which range.
 * A lower index draws behind a higher one. Overlap is rejected by the static asserts in main.c, bg.c and the
 * host test tests/host/test_sprite_budget.c (which also checks the sprites per scanline from src/core/sprite_budget.c).
 * Plan: thoughts/shared/plans/2026-11-10-neo-geo-graphics-max.md, G1. The background sits below the pool, the
 * hazard strip and the foreground above the hero.
 *   0        reserved, never a visible sprite (SPRITE_RESERVED, SCB3 height 0 from boot). Measured 2026-11-11: sprite 0 draws
 *            IN FRONT of every other sprite in screen x 0..15 (believed cause, unverified: unused entries of the per-line
 *            sprite list hold index 0, so it is drawn again after all others), which hid the ceiling, hero and islands there
 *   1..110   parallax background planes, one sprite per 16 px column, back to front (BG_*_SPRITE, widths from
 *            CITY_TABLE_PLANE_COLS): sky 20, far 21, mid A 22, mid B 23, near 24 sprites
 *   111..112 the player's gum bubble (Gum Trip only, GUM_SPRITE, src/gum.c): 2 columns, drawn over the planes, under the islands
 *   113..115 the splash of a flier falling into water or lava (SPLASH_SPRITE, src/splash.c): 3 columns, drawn BEHIND the islands, pool and
 *            the hazard strip, so the liquid covers the splash base
 *   116..119 free (clouds and airship drift, BG-2)
 *   120..160 floating islands (ISLAND_COUNT 41 = room for the stage platform columns, 22 in stage 1, and the Gum Trip islands): one sprite per column of each platform in
 *            stage table order, drawn by src/island.c; they sit below the pool so fliers draw in front
 *   161..256 object pool (POOL_SPRITE_COUNT = POOL_MAX x POOL_COLS, src/core/obj_pool.h): object i owns
 *            POOL_SPRITE_BASE + i * POOL_COLS; computer fliers draw through it
 *   257..259 hero (HERO_SPRITE_COUNT)
 *   261..308 plane 7 hazard strip: two banks of 24 sprites (bank 0 at 261, bank 1 at 285), one visible at a time
 *   309..318 plane 8 rain columns (reserved), 319..322 spray
 */
#define SPRITE_RESERVED 0 /* never visible: see the map above */
#define BG_SKY_SPRITE (SPRITE_RESERVED + 1)
#define BG_SKY_COUNT 20
#define BG_SKY_Y0 0
#define BG_SKY_Y1 112
#define BG_FAR_SPRITE (BG_SKY_SPRITE + BG_SKY_COUNT)
#define BG_FAR_COUNT 21
#define BG_FAR_Y0 48
#define BG_FAR_Y1 128
#define BG_MIDA_SPRITE (BG_FAR_SPRITE + BG_FAR_COUNT)
#define BG_MIDA_COUNT 22
#define BG_MIDA_Y0 80
#define BG_MIDA_Y1 144
#define BG_MIDB_SPRITE (BG_MIDA_SPRITE + BG_MIDA_COUNT)
#define BG_MIDB_COUNT 23
#define BG_MIDB_Y0 112
#define BG_MIDB_Y1 176
#define BG_NEAR_SPRITE (BG_MIDB_SPRITE + BG_MIDB_COUNT)
#define BG_NEAR_COUNT 24
#define BG_NEAR_Y0 128
#define BG_NEAR_Y1 224
#define BG_SPRITE_END (BG_NEAR_SPRITE + BG_NEAR_COUNT)
#define BG_SPRITE_TOTAL (BG_SPRITE_END - BG_SKY_SPRITE) /* rows of the generated column tables; table index = slot - BG_SKY_SPRITE */
#define GUM_SPRITE 111
#define GUM_COUNT 2
#define SPLASH_SPRITE 113
#define SPLASH_COUNT 3
#define ISLAND_SPRITE 120
#define ISLAND_COUNT 41
#define POOL_SPRITE_BASE 161
#define POOL_SPRITE_COUNT 96
#define HERO_SPRITE 257
#define HERO_SPRITE_COUNT 3
#define HAZARD_SPRITE 261
#define HAZARD_COUNT 48
#define FG_RAIN_SPRITE 309
#define FG_RAIN_COUNT 10
#define FG_SPRAY_SPRITE 319
#define FG_SPRAY_COUNT 4
/* Arcade stage elements (src/core/arc_view.h): drawn in arcade mode only, in the rain and spray slots, which no code draws (the rain mood is
   not built). The planned 261..308 is the hazard strip. 14 columns: the worst stage (R10) needs 13 for bodies; smoke and air particles are not drawn. */
#define ARC_ELEM_SPRITE FG_RAIN_SPRITE
#define ARC_ELEM_COUNT (FG_RAIN_COUNT + FG_SPRAY_COUNT)
#define TRIP_STRIP_SPRITE 323 /* Gum Trip kill strips: 22 floor columns, then 22 ceiling columns (step V2) */
#define TRIP_STRIP_COUNT 44
/* The title shares the Gum Trip kill strip range: no strip is drawn on the title, and trip_strip_step rewrites every column's tiles,
 * SCB3 and SCB4 on each Gum Trip entry (after its hide_all: g_key and g_x forgotten), so the logo leaves nothing stale. Asserted in
 * src/logo.c; the title hides these slots (logo_hide) on every other state. 20 strips + up to 8 free pieces, then 2 title Sootlings x 2 columns. */
#define LOGO_SPRITE TRIP_STRIP_SPRITE
/* The arcade bonus stage bubbles share the range too (no Gum Trip strip is drawn in the arcade): 2 sprite columns per bubble, bubble i at
 * ARC_BONUS_SPRITE + 2 * i. They are hidden (arcade_bonus_step in main.c) once when the bonus ends; Gum Trip entry rewrites every strip slot. */
#define ARC_BONUS_SPRITE TRIP_STRIP_SPRITE
#define ARC_BONUS_COUNT 40
#define LOGO_COUNT 28
#define TITLE_SOOT_SPRITE (LOGO_SPRITE + LOGO_COUNT)
#define TITLE_SOOT_COUNT 4
#define TRIP_PICKUP_SPRITE 367 /* Gum Trip pickups: 2 sprite columns per ring slot, 5 slots (step V3) */
#define TRIP_PICKUP_COUNT 10
#define SPRITE_SLOT_END 377
/* Dead bodies in front of the spike art (dead flier hazard hunt, DF3): the last 4 hardware sprites, above every other
 * range, so a body that bounced on the spikes draws over the strip. 2 sprite columns per body, so 2 bodies; a third
 * simultaneous spike death stays in its normal slot (behind the spikes). Only the arena uses them (the Gum Trip kill
 * strips and pickups below are not covered by a front body). SPRITE_SLOT_END above is the end of the fixed ranges. */
#define DEAD_BODY_SPRITE 377
#define DEAD_BODY_COUNT 4
#define DEAD_BODY_COLUMNS 2 /* sprite columns of one body (main.c asserts it equals SOOT_COLUMNS) */
#endif
