#ifndef SOUND_EVENTS_H
#define SOUND_EVENTS_H
/*
 * Turns the game state (read only FlowView) into sound events by edge detection, so main.c needs one call
 * per frame and the rules are host-tested. Events only fire in a real run (FLOW_PLAYING); the attract
 * demo is silent. The coin blip is not a flow event: the BIOS coin vector counts coins and coin_drain turns them into blips.
 * SE_FLAP fires on every flap press edge (Game.flaps), reusing the jump sample.
 */
#include <stdint.h>
#include "flow.h"
#include "hazard_kind.h"

#define SE_FLAP      0x01   /* flap press edge: plays the jump sample */
#define SE_HIT       0x02   /* Gum Trip hit (hazard or wall kill): plays the hit sample; fires on each frame Game.trip_events has TRIP_EV_HIT */
#define SE_START     0x08   /* run begins: music start (the coin blip plays on the coin, not here) */
#define SE_GAME_OVER 0x10   /* run ends: music stop and jingle */
#define SE_DIE       0x04   /* a flier lost its last balloon (stomp, body kill) and not to a hazard: plays die, once per flier */
#define SE_FALL      0x20   /* a flier starts to fall (FLIER_FALLING): plays fall, once per flier */
#define SE_SPLOSH    0x40   /* a live flier crossed the kill line of water or lava: plays splosh */
#define SE_SPIKE     0x80   /* a live flier crossed the spike kill line: plays spike */
#define SE_SIZZLE    0x100  /* a live flier crossed the fire kill line: plays sizzle (the mask is 16 bits: the low byte is full) */

/* Fliers watched: the player, the arena computer fliers, the Gum Trip rivals (sharing the cpu slots' space is not needed: one mode at a time). */
#define SE_WATCHED (1 + STAGE_SPAWN_COUNT + TRIP_RIVAL_MAX)
#define SE_UNSEEN  0xFF
#define SE_UNSEEN_GUM 0xFFFF

typedef struct {
    uint8_t prev_state, primed;
    uint32_t prev_flaps;
    uint8_t seen_state[SE_WATCHED];     /* last FlierState per watched flier, SE_UNSEEN when it was not live last frame */
    uint8_t seen_balloons[SE_WATCHED];
    /* Counts of the last se_step (a mask bit says "at least one"; several fliers can die in one frame, each is one sound). */
    uint8_t n_die, n_fall, n_splosh, n_spike, n_pop;   /* n_pop: a balloon burst (any flier) or the Trip gum reaching 0; no mask bit is left, read the count */
    int32_t splosh_x;                   /* world x in pixels of the last flier to cross a liquid line (valid while n_splosh > 0); the splash starts there */
    uint16_t prev_gum;                  /* player gum last frame in Gum Trip, SE_UNSEEN_GUM otherwise */
} SoundEvents;

void se_init(SoundEvents *e);
uint16_t se_step(SoundEvents *e, const FlowView *v);   /* returns SE_* mask for this frame */
uint8_t coin_drain(uint8_t *pending);                  /* takes one pending coin: returns 1 (play one blip) or 0 */

#endif
