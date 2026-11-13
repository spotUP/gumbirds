#include "sprite_budget.h"
#include "../sprite_slots.h"
#include "bg_scroll.h"
#include "stage.h"
#include "gen/city_tables.h"
#include "gen/island_tables.h"
#include "gen/logo_sprites.h"

/* Per sprite slot of the planes (plane order: table index = slot - BG_SKY_SPRITE): first tile row and tile rows drawn. */
static const unsigned char COL_ROW0[] = CITY_TABLE_COL_ROW0;
static const unsigned char COL_ROWS[] = CITY_TABLE_COL_ROWS;
static const unsigned char PLANE_TOP[] = CITY_TABLE_PLANE_TOP;
/* C99 build (host tests): a compile-time check as a constant division, zero when the sizes differ. */
enum { SB_CHECK_TABLE = 1 / (sizeof COL_ROWS == BG_SPRITE_TOTAL && sizeof COL_ROW0 == BG_SPRITE_TOTAL) }; /* one table row per background sprite */

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
    /* island sprites sit 4 lines above the platform top and are 16 high (ISLAND_LINE_ROW): lines 68-4 .. 164+12. The bands of the 4 islands
       are disjoint, so one line meets one island at most; the widest island (112 px) has 7 columns. */
    { "islands",     ISLAND_SPRITE,       ISLAND_COUNT,        32, 176, 7, SB_ISLANDS },
    /* The player's gum bubble (full size in the arena, the gum meter in Gum Trip): 2 columns; the bird (and so the bubble) may be on any line. */
    { "gum bubble",  GUM_SPRITE,          GUM_COUNT,            0, 224, GUM_COUNT, SB_ALWAYS },
    /* The splash cell is 48 x 48 at screen lines 160..207 (water 162, lava 160 to 209): 3 columns on those lines only. */
    { "splash",      SPLASH_SPRITE,       SPLASH_COUNT,       160, 210, SPLASH_COUNT, SB_ALWAYS },
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

/* Columns of the plane entry that cover screen line y; none for a plane Gum Trip hides. */
static int columns_on_line(const SpriteBudgetEntry *e, int y, int trip) {
    int plane = 0, n = 0;
    while (PLANE_FIRST[plane] != e->first) plane++;
    if (trip && (BG_TRIP_HIDDEN_MASK >> plane & 1)) return 0;
    for (int c = 0; c < e->count; c++) {
        int slot = e->first + c - BG_SKY_SPRITE, top = PLANE_TOP[plane] + 16 * COL_ROW0[slot];
        if (COL_ROWS[slot] && y >= top && y < top + 16 * COL_ROWS[slot]) n++;
    }
    return n;
}

/* Island columns of the arena stage on screen line y: the platforms whose one tile row high band starts ISLAND_LINE_ROW above the top. */
static int platform_columns_on_line(int y) {
    int n = 0;
    for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) {
        int top = stage_platforms[i].y - ISLAND_LINE_ROW;
        if (y >= top && y < top + 16) n += stage_platforms[i].w / ISLAND_PIECE_W;
    }
    return n;
}

int sprite_budget_line(int y, int rain, int trip) {
    int total = 0;
    for (int i = 0; i < SPRITE_BUDGET_COUNT; i++) {
        const SpriteBudgetEntry *e = &SPRITE_BUDGET[i];
        if (y < e->y0 || y >= e->y1) continue;
        if (e->mood == SB_NOT_RAIN && rain) continue;
        if (e->mood == SB_RAIN_ONLY && !rain) continue;
        if (e->mood == SB_TRIP_ONLY && !trip) continue;
        total += e->mood == SB_COLUMNS ? columns_on_line(e, y, trip) : e->mood == SB_ISLANDS && !trip ? platform_columns_on_line(y) : e->per_line;
    }
    return total;
}

static const unsigned char LOGO_STRIP_Y_TAB[] = LOGO_TABLE_STRIP_Y;
static const unsigned char LOGO_STRIP_H_TAB[] = LOGO_TABLE_STRIP_H;
static const unsigned char LOGO_PIECE_FIRST_TAB[] = LOGO_TABLE_PIECE_FIRST;
static const unsigned char LOGO_PIECE_Y_TAB[] = LOGO_TABLE_PIECE_Y;

/* Logo sprites on screen line y in animation frame f: every strip that covers the line plus the frame's free pieces (16 px high). */
static int logo_frame_on_line(int f, int y) {
    int n = 0;
    for (int i = 0; i < LOGO_STRIP_COUNT; i++)
        if (y >= LOGO_STRIP_Y_TAB[i] && y < LOGO_STRIP_Y_TAB[i] + 16 * LOGO_STRIP_H_TAB[i]) n++;
    for (int i = LOGO_PIECE_FIRST_TAB[f]; i < LOGO_PIECE_FIRST_TAB[f + 1]; i++)
        if (y >= LOGO_PIECE_Y_TAB[i] && y < LOGO_PIECE_Y_TAB[i] + 16) n++;
    return n;
}

static int logo_on_line(int y) {
    int worst = 0;
    for (int f = 0; f < LOGO_FRAME_COUNT; f++) {
        int n = logo_frame_on_line(f, y);
        if (n > worst) worst = n;
    }
    return worst;
}

int sprite_budget_logo_worst(void) {
    int worst = 0;
    for (int y = 0; y < SB_LINES; y++) {
        int n = logo_on_line(y);
        if (n > worst) worst = n;
    }
    return worst;
}

/* Title: the moon planes (outside Gum Trip), the logo's worst frame, two title Sootlings (2 columns each, y 108..180 with the bob) and the gum bubble's 2 sprites kept on every line. Nothing from play is shown. */
int sprite_budget_title_line(int y) {
    int total = 2 + logo_on_line(y);
    for (int i = 0; i < SPRITE_BUDGET_COUNT; i++)
        if (SPRITE_BUDGET[i].mood == SB_COLUMNS && y >= SPRITE_BUDGET[i].y0 && y < SPRITE_BUDGET[i].y1) total += columns_on_line(&SPRITE_BUDGET[i], y, 0);
    if (y >= 108 && y < 180) total += 4;
    return total;
}
