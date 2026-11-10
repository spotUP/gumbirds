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

/* Kind of match number n (0 for the first match). */
static inline uint8_t hazard_kind_for_match(uint16_t n) { return (uint8_t)(n % HAZARD_KINDS); }

/* Kill line of a kind in whole world pixels (index = hazard kind). */
static inline int hazard_kill_px(uint8_t kind)
{
    static const int line[HAZARD_KINDS] = { HAZARD_KILL_SPIKES, HAZARD_KILL_FIRE, HAZARD_KILL_WATER, HAZARD_KILL_LAVA };
    return line[kind % HAZARD_KINDS];
}
#endif
