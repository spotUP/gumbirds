#include "gum_view.h"

/* GUM_MAX / 16 as a shift: the per frame mapping needs no division. */
#define STEP_SHIFT 6
typedef char gum_view_max_is_16_steps[((GUM_MAX >> STEP_SHIFT) == GUM_VIEW_LEVELS && (GUM_MAX & ((1 << STEP_SHIFT) - 1)) == 0) ? 1 : -1];

uint8_t gum_view_level(uint16_t gum)
{
    uint32_t level = ((uint32_t)gum + ((1u << STEP_SHIFT) - 1)) >> STEP_SHIFT; /* ceil */
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
