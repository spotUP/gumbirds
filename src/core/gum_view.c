#include "gum_view.h"

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

/* Per bird frame (sootling_anims[PLAYER], Sootling E): bubble bob and whether the frame carries a string. Generated from
 * thoughts/spot/drafts/2026-11-12-degummed-sootling-r2/bubble_motion.json (subtle.dy.player, shows_bubble.player). */
typedef struct { int8_t dy; uint8_t show; } BirdBob;
static const BirdBob bobs[GUM_VIEW_BIRD_FRAMES] = {
    {4, 1}, {4, 1}, {2, 1}, {0, 1}, {0, 1}, {1, 1}, {2, 1},
    {3, 1}, {4, 1}, {4, 1}, {2, 1}, {0, 1}, {0, 1}, {1, 1},
    {2, 1}, {3, 1}, {2, 1}, {3, 1}, {4, 1}, {4, 1}, {4, 1},
    {2, 1}, {2, 1}, {2, 1}, {2, 1}, {3, 1}, {3, 1}, {4, 1},
    {2, 1}, {3, 0}, {4, 0}, {3, 0}, {3, 0}, {1, 0}, {0, 0},
    {0, 0}, {0, 0}, {0, 0}, {2, 0}, {3, 0}, {5, 0}, {5, 0},
    {5, 0}, {4, 1}, {2, 1}, {2, 1}, {2, 1}, {1, 1}, {1, 1},
    {1, 1}, {2, 1}, {3, 1}, {0, 0}, {1, 0}, {0, 0}, {-1, 0},
    {0, 0}, {0, 0}, {1, 0}, {0, 0}, {-1, 0}, {0, 0}, {3, 0},
    {2, 0}, {1, 0}, {0, 0}, {0, 0}, {2, 0}, {1, 0}, {0, 0},
    {0, 0}, {3, 0}, {3, 0}, {3, 0}, {2, 0}, {1, 0}, {2, 0},
    {2, 1}, {1, 1}, {1, 1}, {1, 1}, {2, 1}, {1, 1}, {1, 1},
    {1, 1}, {3, 1}, {3, 1}, {3, 1}, {2, 1}, {1, 1}, {2, 1},
    {2, 1}, {1, 1}, {1, 1}, {1, 1}, {2, 1}, {1, 1}, {1, 1},
    {1, 1}, {3, 1}, {3, 1}, {3, 1}, {2, 1}, {1, 1}, {2, 1},
};

GumOffset gum_view_offset(uint8_t bird_frame, int flip)
{
    GumOffset o = { 0, 0, 0 };
    if (bird_frame >= GUM_VIEW_BIRD_FRAMES) return o;
    o.dx = (int8_t)(flip ? GUM_BIRD_DX_FLIP : GUM_BIRD_DX);
    o.dy = (int8_t)(GUM_BIRD_ROW + bobs[bird_frame].dy);
    o.show = bobs[bird_frame].show;
    return o;
}
