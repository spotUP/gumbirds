#include "sprite_budget.h"
#include "../sprite_slots.h"
#include "gen/city_tables.h"

/* Per sprite slot of the planes (plane order, so the index is the slot): first tile row and tile rows drawn. */
static const unsigned char COL_ROW0[] = CITY_TABLE_COL_ROW0;
static const unsigned char COL_ROWS[] = CITY_TABLE_COL_ROWS;
static const unsigned char PLANE_TOP[] = CITY_TABLE_PLANE_TOP;
/* C99 build (host tests): a compile-time check as a constant division, zero when the sizes differ. */
enum { SB_CHECK_TABLE = 1 / (sizeof COL_ROWS == BG_SPRITE_END && sizeof COL_ROW0 == BG_SPRITE_END) }; /* one table row per background sprite */

/* y ranges and counts per line: the drawn art (the parallax planes: counts and y ranges in src/sprite_slots.h,
 * checked against the sheet in src/bg.c). Plane entries (SB_COLUMNS) count column by column from the generated table. */
const SpriteBudgetEntry SPRITE_BUDGET[] = {
    { "sky plane",   BG_SKY_SPRITE,       BG_SKY_COUNT, BG_SKY_Y0, BG_SKY_Y1, BG_SKY_COUNT, SB_COLUMNS },
    { "far plane",   BG_FAR_SPRITE,       BG_FAR_COUNT, BG_FAR_Y0, BG_FAR_Y1, BG_FAR_COUNT, SB_COLUMNS },
    { "mid A plane", BG_MIDA_SPRITE,      BG_MIDA_COUNT, BG_MIDA_Y0, BG_MIDA_Y1, BG_MIDA_COUNT, SB_COLUMNS },
    { "mid B plane", BG_MIDB_SPRITE,      BG_MIDB_COUNT, BG_MIDB_Y0, BG_MIDB_Y1, BG_MIDB_COUNT, SB_COLUMNS },
    { "near plane",  BG_NEAR_SPRITE,      BG_NEAR_COUNT, BG_NEAR_Y0, BG_NEAR_Y1, BG_NEAR_COUNT, SB_COLUMNS },
    { "gameplay",    POOL_SPRITE_BASE,    HERO_SPRITE + HERO_SPRITE_COUNT - POOL_SPRITE_BASE,
                                                                0, 224, SB_GAMEPLAY_PER_LINE, SB_ALWAYS },
    /* 24 columns, not the 21 visible at a camera offset: the LSPC picks sprites per line by Y only, so columns with X off screen still count. */
    { "hazard",      HAZARD_SPRITE,       HAZARD_COUNT,       192, 224, 24, SB_ALWAYS },
    { "rain",        FG_RAIN_SPRITE,      FG_RAIN_COUNT,        0, 224, 10, SB_RAIN_ONLY },
    { "spray",       FG_SPRAY_SPRITE,     FG_SPRAY_COUNT,     176, 224,  4, SB_ALWAYS },
};
const int SPRITE_BUDGET_COUNT = (int)(sizeof SPRITE_BUDGET / sizeof SPRITE_BUDGET[0]);

const SpriteBudgetMood SPRITE_BUDGET_MOODS[] = {
    { "moon",  1, 0 },   /* clear night: built, no rain */
    { "dusk",  0, 0 },   /* not built (BG-2) */
    { "storm", 0, 1 },   /* not built (BG-2): the only mood with rain columns */
};
const int SPRITE_BUDGET_MOOD_COUNT = (int)(sizeof SPRITE_BUDGET_MOODS / sizeof SPRITE_BUDGET_MOODS[0]);

/* First sprite slot of each plane, in plane order (the order of CITY_TABLE_PLANE_TOP). */
static const unsigned char PLANE_FIRST[] = { BG_SKY_SPRITE, BG_FAR_SPRITE, BG_MIDA_SPRITE, BG_MIDB_SPRITE, BG_NEAR_SPRITE };
enum { SB_CHECK_PLANES = 1 / (sizeof PLANE_FIRST == sizeof PLANE_TOP) }; /* one slot range per plane */

/* Columns of the plane entry that cover screen line y. */
static int columns_on_line(const SpriteBudgetEntry *e, int y) {
    int plane = 0, n = 0;
    while (PLANE_FIRST[plane] != e->first) plane++;
    for (int c = 0; c < e->count; c++) {
        int slot = e->first + c, top = PLANE_TOP[plane] + 16 * COL_ROW0[slot];
        if (COL_ROWS[slot] && y >= top && y < top + 16 * COL_ROWS[slot]) n++;
    }
    return n;
}

int sprite_budget_line(int y, int rain) {
    int total = 0;
    for (int i = 0; i < SPRITE_BUDGET_COUNT; i++) {
        const SpriteBudgetEntry *e = &SPRITE_BUDGET[i];
        if (y < e->y0 || y >= e->y1) continue;
        if (e->mood == SB_NOT_RAIN && rain) continue;
        if (e->mood == SB_RAIN_ONLY && !rain) continue;
        total += e->mood == SB_COLUMNS ? columns_on_line(e, y) : e->per_line;
    }
    return total;
}
