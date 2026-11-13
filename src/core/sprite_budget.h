#ifndef SPRITE_BUDGET_H
#define SPRITE_BUDGET_H
/*
 * Sprite budget per scanline (plan 2026-11-10-neo-geo-graphics-max.md, G1). The hardware draws at most 96 sprites on
 * one line and drops the rest; the target is 90. Each entry of SPRITE_BUDGET names a slot range of
 * src/sprite_slots.h, the screen lines it covers and how many of its sprites meet one line there. Gameplay (fliers,
 * islands, effects) is one entry that reserves SB_GAMEPLAY_PER_LINE for the whole screen. An entry with a mood flag
 * counts only in that mood: rain mood has no airship; rain columns exist only in the rain mood.
 * Pure C, no hardware: tests/host/test_sprite_budget.c sums it, so a layout change that overfills a line fails there.
 */
#include <stdint.h>

#define SB_LINES 224
#define SB_LIMIT 90
#define SB_GAMEPLAY_PER_LINE 14 /* fliers only (platforms left the pool for the island row). CPU_MAX 3: arena 4 fliers x 2 strips, measured peak 8 (gmake test-sprite-peak, 2026-11-13); arcade at most 4 rivals + hero = 10; Gum Trip pool + hero measured 4 (trip_check.lua). Lowered 18 -> 14 so arcade stage elements fit SB_LIMIT (thoughts/spot/2026-11-13-budget-e.md); was 24 with platforms in the pool */
/* SB_COLUMNS: a parallax plane. Every column is its own sprite with its own top and height (generated table
 * CITY_TABLE_COL_ROW0 / COL_ROWS, indexed by sprite slot - BG_SKY_SPRITE), so a column counts only on the lines it spans. */
enum { SB_ALWAYS = 0, SB_NOT_RAIN = 1, SB_RAIN_ONLY = 2, SB_COLUMNS = 3, SB_TRIP_ONLY = 4, SB_ISLANDS = 5 };
/* SB_ISLANDS: the islands. Gum Trip counts the flat per_line (its generated islands are not on a fixed table); the arena counts per line the columns of the stage platforms whose band (platform top - ISLAND_LINE_ROW, one tile row high) meets the line (stage_platforms, src/core/stage.c). SB_TRIP_ONLY: counts only in Gum Trip. SB_COLUMNS planes in BG_TRIP_HIDDEN_MASK (src/core/bg_scroll.h) count only outside it. */

typedef struct {
    const char *name;
    uint16_t first, count;   /* sprite slots */
    uint16_t y0, y1;         /* screen lines y0..y1-1 */
    uint8_t per_line;        /* sprites of this range on one line inside y0..y1-1 (SB_COLUMNS: the most one line can have) */
    uint8_t mood;
} SpriteBudgetEntry;

extern const SpriteBudgetEntry SPRITE_BUDGET[];
extern const int SPRITE_BUDGET_COUNT;
/* Moods: the game ships one at a time. A mood that is not built yet has no art to count, so tests must not pass it. */
typedef struct { const char *name; uint8_t built, rain; } SpriteBudgetMood;
extern const SpriteBudgetMood SPRITE_BUDGET_MOODS[];
extern const int SPRITE_BUDGET_MOOD_COUNT;
/* Sprites on screen line y in the rain mood (rain != 0) or the other moods, in Gum Trip (trip != 0) or the arena; includes the gameplay reserve. */
int sprite_budget_line(int y, int rain, int trip);
/* Title screen: sprites on line y (planes, logo worst frame, title Sootlings, bubble). sprite_budget_logo_worst is the logo alone, recomputed from the generated tables. */
int sprite_budget_title_line(int y);
int sprite_budget_logo_worst(void);
#endif
