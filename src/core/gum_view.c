#include "gum_view.h"
#include "gen/sootling_tables.h"

typedef char gum_view_bird_frames_match_sheet[(GUM_VIEW_BIRD_FRAMES == SOOTLING_FRAMES) ? 1 : -1];

/* One level is GUM_MAX / 16 gum; a power of two keeps the per frame mapping division free on the 68000 (the compiler turns it into a shift). */
#define STEP (GUM_MAX / GUM_VIEW_LEVELS)
typedef char gum_view_max_is_16_steps[(STEP * GUM_VIEW_LEVELS == GUM_MAX) ? 1 : -1];
typedef char gum_view_step_is_power_of_two[(STEP > 0 && (STEP & (STEP - 1)) == 0) ? 1 : -1];

uint8_t gum_view_level(uint16_t gum)
{
    uint32_t level = ((uint32_t)gum + (STEP - 1)) / STEP; /* ceil */
    return level > GUM_VIEW_LEVELS ? GUM_VIEW_LEVELS : (uint8_t)level;
}

GumSize gum_view_size(uint8_t level)
{
    return level >= 13 ? GUM_SIZE_LARGE : level >= 8 ? GUM_SIZE_MEDIUM : level >= 5 ? GUM_SIZE_SMALL : GUM_SIZE_TINY;
}

GumPop gum_view_pop(uint8_t level)
{
    return level >= 8 ? GUM_POP_LARGE : GUM_POP_SMALL;
}

uint8_t gum_view_anim(uint8_t level, GumState state)
{
    uint8_t l = level < 1 ? 1 : level > GUM_VIEW_LEVELS ? GUM_VIEW_LEVELS : level;
    return state == GUM_STATE_POP ? (gum_view_pop(l) == GUM_POP_LARGE ? 16 : 17) : (uint8_t)(GUM_VIEW_LEVELS - l);
}

uint8_t gum_view_frame(GumState state, uint32_t t)
{
    if (state == GUM_STATE_WOBBLE) return (uint8_t)((t / GUM_WOBBLE_FRAMES) % GUM_VIEW_WOBBLE_SHEET);
    return gum_view_pop_done(t) ? GUM_VIEW_POP_SHEET - 1 : (uint8_t)(t / GUM_POP_FRAMES);
}

int gum_view_pop_done(uint32_t t) { return t >= (uint32_t)GUM_VIEW_POP_SHEET * GUM_POP_FRAMES; }

/* Per bird frame (the player animation of the Sootling sheet), from tools/import_gum_mouth_sheet.py through the build:
 * gum_dx = grip column - sprite centre column, gum_dy = rows the frame was shifted down to its feet relative to the hanging
 * poses (so the bubble keeps its place on the beak), gum_show = 0 in the pop poses (strain, burst), where the gum is gone;
 * the pop2 clip (2 balloons to 1) keeps the bubble and adds a pushed-in bob to gum_dy (GUM_BOB in the importer). */
static const int8_t k_gum_dx[GUM_VIEW_BIRD_FRAMES] = SOOTLING_TABLE_GUM_DX;
static const int8_t k_gum_dy[GUM_VIEW_BIRD_FRAMES] = SOOTLING_TABLE_GUM_DY;
static const uint8_t k_gum_show[GUM_VIEW_BIRD_FRAMES] = SOOTLING_TABLE_GUM_SHOW;

GumOffset gum_view_offset(uint8_t bird_frame, int flip)
{
    GumOffset o = { 0, 0, 0 };
    if (bird_frame >= GUM_VIEW_BIRD_FRAMES) return o;
    o.dx = (int8_t)(flip ? GUM_BIRD_DX_FLIP - k_gum_dx[bird_frame] : GUM_BIRD_DX + k_gum_dx[bird_frame]);
    o.dy = (int8_t)(GUM_BIRD_ROW + k_gum_dy[bird_frame]);
    o.show = k_gum_show[bird_frame];
    return o;
}

int gum_view_draws(int popping, uint8_t level, uint8_t show) { return popping || (level > 0 && show); }

int gum_view_leaks_balloons(uint8_t balloons) { return balloons == 1; }
int gum_view_leaks_gum(uint16_t gum) { return gum > 0 && gum < GUM_MAX / 2; }
uint8_t gum_view_leak_frame(uint32_t t) { return (uint8_t)((t / GUM_LEAK_TICK) % GUM_LEAK_FRAMES); }
uint32_t gum_view_wobble_clock(uint32_t t, int leaking) { return leaking ? t * 2 : t; }

uint8_t gum_view_pump_level(int elapsed, int pump_frames, int full_level) {
    /* No divides (libgcc calls on the 68000, per pumping flier per frame): growth and stroke phase by compares. */
    int g = 1, acc = pump_frames, t, lvl;
    if (elapsed >= pump_frames || pump_frames <= 0) return (uint8_t)full_level;
    if (elapsed < 0) elapsed = 0;
    t = elapsed * (full_level - 1);
    while (g < full_level && t >= acc) { g++; acc += pump_frames; }
    t = elapsed * GUM_PUMP_STROKES;
    while (t >= pump_frames) t -= pump_frames;   /* phase inside the stroke, 0..pump_frames - 1 */
    lvl = g + (t < (pump_frames >> 2) ? GUM_PUMP_SWELL : (t < (pump_frames >> 1) ? 1 : 0));
    return (uint8_t)(lvl > full_level ? full_level : lvl);
}
