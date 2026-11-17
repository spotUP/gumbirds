#ifndef GG_POPDROP_H
#define GG_POPDROP_H
#include <stdint.h>
#include "flier.h"
#include "gumgames.h"

/* Gum Games event Pop Drop (pure logic): the bird hangs under a parachute over a rival balloon drifting sideways. C cuts the chute, the bird falls
 * (the stick nudges it sideways) and a stomp pops the balloon. Drop score = GD_POP_RING minus the pixels the feet land off the balloon centre.
 * Five drops; the event record is the best total of the five drop scores (higher is better, 0 = none). */
#define GP_DROPS 5u
#define GP_QUALIFY 3u                 /* pops out of 5 */
#define GP_RING 12                    /* drop score of a dead-centre pop; a pop further off than this still scores 1 */
#define GP_HERO_X FL_PX(192)
#define GP_HERO_Y FL_PX(24)
#define GP_TARGET_Y FL_PX(120)        /* balloon rival centre; its gum is what the stomp hits */
#define GP_MISS_Y FL_PX(140)          /* hero centre below this without a pop: the drop is missed */
#define GP_DRIFT 32768                /* target sideways drift: 0.5 px per frame, alternating direction each drop */
#define GP_START_DX 110               /* the target starts this many px beside the hero */
#define GP_NUDGE 24000                /* stick nudge in the fall: about 0.37 px per frame, not steering */
#define GP_HANG_MAX 900u              /* an idle bird cuts itself loose after 15 s */
#define GP_PAUSE_FRAMES 60u           /* after a pop or a miss, before the next drop */
#define GP_RESULT_FRAMES 150u
enum { GP_HANG, GP_FALL, GP_PAUSE, GP_RESULT };

typedef struct {
    uint8_t phase, drop, pops, last_pop, prev_in, done, end_t;   /* drop: 0-based index of the current drop; last_pop: 1 when the drop just ended popped */
    uint8_t last_off;                                            /* pixels off centre of the last pop */
    uint16_t timer;
    uint16_t total;                                              /* sum of the drop scores */
    uint16_t last_score;                                         /* drop score of the drop just ended (0 = miss) */
} GgPop;

/* Clear the event and place the first drop: hero on its parachute, target beside it. */
void gp_init(GgPop *p, Flier *hero, Flier *target);
/* One frame. Returns 1 on the frame the fifth drop ends (the points are then gg_points(pops, pops >= GP_QUALIFY)). */
int gp_step(GgPop *p, Flier *hero, Flier *target, uint8_t in);
#endif
