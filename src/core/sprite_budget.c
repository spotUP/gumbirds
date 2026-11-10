#include "sprite_budget.h"
#include "../sprite_slots.h"

/* y ranges and counts per line: plan section 4 for the unbuilt planes, the drawn art for the existing ones
 * (stars y 30..92, moon y 32..80, left clouds y 48..64, far ring y 64..176, mid ring y 96..176, roof y 176..224). */
const SpriteBudgetEntry SPRITE_BUDGET[] = {
    { "stars",       BG_STAR_SPRITE,      BG_STAR_COUNT,       16,  96,  8, SB_ALWAYS },
    { "sky objects", BG_SKY_SPRITE,       BG_SKY_COUNT,        32,  80, 10, SB_ALWAYS },
    { "cloud bank",  BG_CLOUDBANK_SPRITE, BG_CLOUDBANK_COUNT,  40,  88,  8, SB_ALWAYS },
    { "far ring",    BG_FAR_SPRITE,       BG_RING_COUNT,       64, 176, BG_RING_COUNT, SB_ALWAYS },
    { "airship",     BG_AIRSHIP_SPRITE,   BG_AIRSHIP_COUNT,    80, 128,  9, SB_NOT_RAIN },
    { "mid ring",    BG_MID_SPRITE,       BG_RING_COUNT,       96, 176, BG_RING_COUNT, SB_ALWAYS },
    { "smoke",       BG_SMOKE_SPRITE,     BG_SMOKE_COUNT,      96, 136,  6, SB_ALWAYS },
    { "roof ring",   BG_ROOF_SPRITE,      BG_RING_COUNT,      176, 224, BG_RING_COUNT, SB_ALWAYS },
    { "gameplay",    POOL_SPRITE_BASE,    HERO_SPRITE + HERO_SPRITE_COUNT - POOL_SPRITE_BASE,
                                                                0, 224, SB_GAMEPLAY_PER_LINE, SB_ALWAYS },
    { "hazard",      HAZARD_SPRITE,       HAZARD_COUNT,       192, 224, 20, SB_ALWAYS },
    { "rain",        FG_RAIN_SPRITE,      FG_RAIN_COUNT,        0, 224, 10, SB_RAIN_ONLY },
    { "spray",       FG_SPRAY_SPRITE,     FG_SPRAY_COUNT,     176, 224,  4, SB_ALWAYS },
    { "edge cable",  FG_EDGE_SPRITE,      FG_EDGE_COUNT,        0, 224,  2, SB_ALWAYS },
};
const int SPRITE_BUDGET_COUNT = (int)(sizeof SPRITE_BUDGET / sizeof SPRITE_BUDGET[0]);

int sprite_budget_line(int y, int rain) {
    int total = 0;
    for (int i = 0; i < SPRITE_BUDGET_COUNT; i++) {
        const SpriteBudgetEntry *e = &SPRITE_BUDGET[i];
        if (y < e->y0 || y >= e->y1) continue;
        if (e->mood == SB_NOT_RAIN && rain) continue;
        if (e->mood == SB_RAIN_ONLY && !rain) continue;
        total += e->per_line;
    }
    return total;
}
