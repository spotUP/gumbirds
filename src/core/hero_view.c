#include "hero_view.h"
#include "tuning.h"

HeroLook hero_view_look(const Game *g, int *visible)
{
    uint32_t since;
    *visible = 1;
    if (g->invuln == 0) {
        return HV_LOOK_NORMAL;
    }
    since = (uint32_t)(INVULN_FRAMES - g->invuln); /* frames since the hit, 0 on the frame it happened */
    if (since < HIT_POSE_FRAMES) {
        return HV_LOOK_HIT;
    }
    *visible = (int)(((since - HIT_POSE_FRAMES) / HIT_BLINK_FRAMES) & 1u) == 0;
    return HV_LOOK_NORMAL;
}
