/* Test input for the arena: put the player's feet in the balloon box of the first computer flier that still has
 * balloons, so the next game_step_arena runs a real stomp (flier_stomp inside game_step_arena, score added there).
 * Returns 1 if a target was found. The feet must sit in the gum band, ay in (vy-31, vy-22) pixels above the target's feet (both fliers with balloons, flier.h gum box,
 * body 7 plus gum 9 reach sideways); vy-26 is the middle. */
#ifndef BRAWL_TEST_STOMP_ASSIST_H
#define BRAWL_TEST_STOMP_ASSIST_H
#include "../../src/core/game.h"

static int stomp_assist(Game *g)
{
    int i;
    for (i = 0; i < g->cpu_count; i++) {
        const Flier *c = &g->cpu[i];
        if (c->state <= FLIER_PARACHUTE && c->balloons > 0) {
            g->flier.x = c->x;
            g->flier.y = c->y - FL_PX(26);
            g->flier.vx = 0;
            g->flier.vy = FL_PX(1); /* falling onto the target: a pop needs the pair to close */
            return 1;
        }
    }
    return 0;
}
#endif
