#ifndef SOUND_EVENTS_H
#define SOUND_EVENTS_H
/*
 * Turns the game state (read only FlowView) into sound events by edge detection, so main.c needs one call
 * per frame and the rules are host-tested. Events only fire in a real run (FLOW_PLAYING); the attract
 * demo is silent. The coin blip is not a flow event: the BIOS coin vector counts coins and coin_drain turns them into blips.
 * SE_FLAP fires on every flap press edge (Game.flaps[0]).
 */
#include <stdint.h>
#include "flow.h"
#include "hazard_kind.h"

#define SE_FLAP      0x01   /* flap press edge: plays the jump sample */
#define SE_HIT       0x02   /* Gum Trip hit (hazard or wall kill): plays the hit sample; fires on each frame Game.trip_events has TRIP_EV_HIT */
#define SE_START     0x08   /* run begins: music start (the coin blip plays on the coin, not here) */
#define SE_GAME_OVER 0x10   /* run ends: music stop and jingle */
#define SE_DIE       0x04   /* a flier lost its last balloon (stomp, body kill) and not to a hazard: plays die, once per flier */
#define SE_FALL      0x20   /* a flier starts to fall: FLIER_FALLING, or a balloon-less walker dropping off an edge (SE_DROP_VY); plays fall, once per fall */
#define SE_SPLOSH    0x40   /* a live flier crossed the kill line of water or lava: plays splosh */
#define SE_SPIKE     0x80   /* a live flier crossed the spike kill line: plays spike */
#define SE_SIZZLE    0x100  /* a live flier crossed the fire kill line: plays sizzle (the mask is 16 bits: the low byte is full) */
#define SE_TITLE     0x200  /* the flow entered the title/table/demo screens (also the first frame): title music */
#define SE_ROUND     0x400  /* matches_won rose while playing: round clear jingle */

/* Cues: one bit each in SoundEvents.cues (a bit, not a count: three rivals pumping in one frame make one sound).
   sound.c maps the bit index to a sample. Edges of Game state, same priming rule as the mask: nothing on the first playing frame. */
enum {
    SC_GO, SC_BANNER,                       /* round_start became RS_GO / RS_ROUND (not the first banner: the start sample owns that frame) */
    SC_PUMP_A, SC_PUMP_B, SC_RIVAL_LAUNCH, SC_DEFEAT,   /* arcade rival: pump progress rose (odd A, even B), PUMPING to FLYING, to DEFEATED */
    SC_BUMP,                                /* Game.bounces rose */
    SC_CHUTE,                               /* a flier went ALIVE to PARACHUTE */
    SC_VENT_WARN, SC_VENT_BURST,            /* vent timer reached ARC_VENT_TELEGRAPH / ARC_VENT_LAUNCH */
    SC_FLIPPER, SC_GRATE,                   /* the player started to touch a flipper / entered a grate draft */
    SC_GRAB_RISE, SC_GRAB_BITE,             /* grabber left hidden / reached art frame ARC_GRAB_HIT_FIRST */
    SC_BUBBLE_PUFF,                         /* bonus stage: a bubble left a nozzle */
    SC_PICKUP, SC_PICKUP_STREAK,            /* Gum Trip pickup; streak of SE_STREAK_MIN or more */
    SC_RIVAL_WARN,                          /* Gum Trip rival entered */
    SC_GUM_LOW,                             /* Gum Trip gum fell below SE_GUM_LOW (not to 0: that is the pop) */
    SC_LIFE_LOST, SC_CONTINUE_TICK, SC_CONTINUE_YES,   /* arcade lives fell; continue digit changed; continue taken */
    SC_NE_MOVE, SC_NE_CONFIRM, SC_NE_DONE,  /* name entry: symbol or cursor back, cursor forward, finished */
    SC_COUNT
};
#define SE_STREAK_MIN 3
#define SE_GUM_LOW (GUM_MAX / 4)
/* A balloon-less ALIVE flier in the air falling faster than this is falling off an edge: a ground jump comes back down at
   2 * FLIER_FLAP_IMPULSE plus at most one gravity step, so a jump on level ground stays under it. */
#define SE_DROP_VY (2 * FLIER_FLAP_IMPULSE + 2 * FLIER_GRAVITY_NO_BALLOON)

/* Fliers watched: the humans, the arena computer fliers, the Gum Trip rivals (sharing the cpu slots' space is not needed: one mode at a time). */
#define SE_WATCHED (HUMANS + STAGE_SPAWN_COUNT + TRIP_RIVAL_MAX)
#define SE_UNSEEN  0xFF
#define SE_UNSEEN_GUM 0xFFFF

typedef struct {
    uint8_t prev_state, primed;
    uint32_t prev_matches;              /* Game.matches_won last frame while playing */
    uint32_t prev_flaps[HUMANS];
    uint8_t seen_state[SE_WATCHED];     /* last FlierState per watched flier, SE_UNSEEN when it was not live last frame */
    uint8_t seen_balloons[SE_WATCHED];
    /* Counts of the last se_step (a mask bit says "at least one"; several fliers can die in one frame, each is one sound). */
    uint8_t n_die, n_fall, n_splosh, n_spike, n_pop;   /* n_pop: a balloon burst (any flier) or the Trip gum reaching 0; no mask bit is left, read the count */
    int32_t splosh_x;                   /* world x in pixels of the last flier to cross a liquid line (valid while n_splosh > 0); the splash starts there */
    uint16_t prev_gum;                  /* player gum last frame in Gum Trip, SE_UNSEEN_GUM otherwise */
    uint32_t cues;                      /* SC_* bits of the last se_step */
    uint8_t drop[SE_WATCHED];           /* 1 while a balloon-less walker's drop has made its fall sound; cleared on the ground */
    /* last frame's values for the cue edges */
    uint8_t prev_round_start, prev_pump[STAGE_SPAWN_COUNT] /* state << 4 | progress */, prev_touch /* bit 0 flipper, bit 1 grate */;
    uint8_t prev_life_state[HUMANS], prev_seconds[HUMANS], ne_seen, ne_pos, ne_sym, ne_done;
    uint16_t prev_el[ARC_ELEM_MAX];
    uint32_t prev_bounces;
    int prev_lives[HUMANS], prev_spawned, prev_caught;
} SoundEvents;

void se_init(SoundEvents *e);
uint16_t se_step(SoundEvents *e, const FlowView *v);   /* returns SE_* mask for this frame */
uint8_t coin_drain(uint8_t *pending);                  /* takes one pending coin: returns 1 (play one blip) or 0 */

#endif
