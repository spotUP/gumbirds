#ifndef HAZARD_KIND_H
#define HAZARD_KIND_H
/*
 * Hazard kinds and where each one kills. Pure C, shared by the view (src/hazard.c) and the core (game.c, flier.c),
 * so the drawn strip and the death line cannot drift apart.
 *
 * Kill line = strip top + measured surface row + dip, in world pixels (world y = screen y). The surface rows are
 * the topmost opaque pixel of the drawn art, median over all columns, frames and variants (spikes: the tip row 0),
 * measured in thoughts/spot/2026-11-10-hazard-surface-rows.md. The feet may dip HAZARD_DIP px into water, lava
 * and fire before the flier dies; spikes kill at the tip row. A flier dies when its y (centre) + half height
 * (= feet bottom) reaches the line (flier_step).
 */
#include <stdint.h>

#define HZ_SPIKES 0
#define HZ_FIRE 1
#define HZ_WATER 2
#define HZ_LAVA 3
#define HAZARD_KINDS 4

#define HAZARD_STRIP_TOP_Y 192 /* first screen line of the strip */
#define HAZARD_DIP 4           /* feet depth below the surface at death (liquids and fire) */

#define HAZARD_KILL_SPIKES (HAZARD_STRIP_TOP_Y + 0)
#define HAZARD_KILL_FIRE (HAZARD_STRIP_TOP_Y + 18 + HAZARD_DIP)
#define HAZARD_KILL_WATER (HAZARD_STRIP_TOP_Y + 12 + HAZARD_DIP)
#define HAZARD_KILL_LAVA (HAZARD_STRIP_TOP_Y + 10 + HAZARD_DIP)

/* Order of the kinds by round (0 for the first round of a game): water, spikes, lava, fire, then again. */
#define HAZARD_ROUND_ORDER_LIST HZ_WATER, HZ_SPIKES, HZ_LAVA, HZ_FIRE

/* Kind of round number n (0 for the first round of a game). */
static inline uint8_t hazard_kind_for_round(uint16_t n)
{
    static const uint8_t order[HAZARD_KINDS] = { HAZARD_ROUND_ORDER_LIST };
    return order[n % HAZARD_KINDS];
}

/* Kill line of a kind in whole world pixels (index = hazard kind). */
static inline int hazard_kill_px(uint8_t kind)
{
    static const int line[HAZARD_KINDS] = { HAZARD_KILL_SPIKES, HAZARD_KILL_FIRE, HAZARD_KILL_WATER, HAZARD_KILL_LAVA };
    return line[kind % HAZARD_KINDS];
}
#endif
