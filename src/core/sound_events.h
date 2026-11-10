#ifndef SOUND_EVENTS_H
#define SOUND_EVENTS_H
/*
 * Turns the game state (read only FlowView) into sound events by edge detection, so main.c needs one call
 * per frame and the rules are host-tested. Events only fire in a real run (FLOW_PLAYING); the attract
 * demo is silent. There is no coin event in the flow, so SE_START (entering PLAYING) carries the coin blip.
 * SE_FLAP fires on every flap press edge (Game.flaps), reusing the jump sample.
 */
#include <stdint.h>
#include "flow.h"

#define SE_FLAP      0x01   /* flap press edge: plays the jump sample */
#define SE_START     0x08   /* run begins: coin blip and music start */
#define SE_GAME_OVER 0x10   /* run ends: music stop and jingle */

typedef struct {
    uint8_t prev_state, primed;
    uint32_t prev_flaps;
} SoundEvents;

void se_init(SoundEvents *e);
uint8_t se_step(SoundEvents *e, const FlowView *v);   /* returns SE_* mask for this frame */

#endif
