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
#define SB_GAMEPLAY_PER_LINE 24 /* measured peak 12, 20 with two-column fliers, 4 spare (thoughts/spot/2026-11-10-budget-c11.md) */
enum { SB_ALWAYS = 0, SB_NOT_RAIN = 1, SB_RAIN_ONLY = 2 };

typedef struct {
    const char *name;
    uint16_t first, count;   /* sprite slots */
    uint16_t y0, y1;         /* screen lines y0..y1-1 */
    uint8_t per_line;        /* sprites of this range on one line inside y0..y1-1 */
    uint8_t mood;
} SpriteBudgetEntry;

extern const SpriteBudgetEntry SPRITE_BUDGET[];
extern const int SPRITE_BUDGET_COUNT;
/* Sprites on screen line y in the rain mood (rain != 0) or the other moods; includes the gameplay reserve. */
int sprite_budget_line(int y, int rain);
#endif
