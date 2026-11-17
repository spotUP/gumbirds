#ifndef GG_COUNTDOWN_H
#define GG_COUNTDOWN_H
#include <stdint.h>

/* GET SET / GO! before every Gum Games event. Game.cd_t counts frames since the countdown began (game.c cd_tick): GET SET for the
 * first GGCD_SET_FRAMES, then GO! for GGCD_GO_FRAMES while play runs. GGCD_END = done / not running. Dash, Pop Drop, Fling and Gather
 * freeze their event step while cd_t < GGCD_SET_FRAMES; Big Blow and Burst Race start it GGCD_SET_FRAMES before the intro ends. */
#define GGCD_SET_FRAMES 60u
#define GGCD_GO_FRAMES 30u
#define GGCD_END (GGCD_SET_FRAMES + GGCD_GO_FRAMES + 1u)
enum { GGCD_WORD_NONE, GGCD_WORD_SET, GGCD_WORD_GO };
#define GGCD_EV_TICK 1u /* GET SET appears: tick beep */
#define GGCD_EV_GO 2u   /* GO! appears: higher beep */

static inline uint8_t ggcd_events(uint16_t t) { return t == 0 ? GGCD_EV_TICK : t == GGCD_SET_FRAMES ? GGCD_EV_GO : 0; }
static inline uint8_t ggcd_word(uint16_t t) { return t == 0 ? GGCD_WORD_NONE : t <= GGCD_SET_FRAMES ? GGCD_WORD_SET : t <= GGCD_SET_FRAMES + GGCD_GO_FRAMES ? GGCD_WORD_GO : GGCD_WORD_NONE; }
#endif
