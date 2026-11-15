#ifndef WORLD_H
#define WORLD_H
/*
 * Worlds (WORLD-1, owner decisions 2026-11-14): the one place that decides sky mood, island look and hazard per round.
 *  - Arcade: one linked world per block of WORLD_BLOCK_STAGES stages, not random: stages 1-4 moon, 5-8 dusk, 9-12 storm.
 *    The loop restart (ARC_LOOP_STAGE) and the bonus stage follow the table through the stage number (the bonus stage keeps
 *    the world of the stage it follows).
 *  - Arena: each part varies on its own per round, never the same value twice in a row: mood by game_next_mood, look by
 *    stage_look_for_level(matches_won) (period 3), hazard by HAZARD_ROUND_ORDER_LIST (period 8, each kind once on even and
 *    once on odd rounds, so the 2-mood alternation meets every kind). 24 rounds show all 2 x 3 x 4 combinations.
 * Picked once per round or stage start (game.c match_start, main.c hazard restart); never per frame.
 */
#include "game.h"
#include "stage.h"
#include "hazard_kind.h"

#define WORLD_BLOCK_STAGES 4
enum { WORLD_MOON, WORLD_DUSK, WORLD_STORM, WORLD_COUNT };

typedef struct {
    uint8_t mood, look, hazard;
} World;

static inline const World *world_get(int w)
{
    static const World table[WORLD_COUNT] = {
        { GAME_MOOD_MOON, STAGE_LOOK_ROOF, HZ_WATER },
        { GAME_MOOD_DUSK, STAGE_LOOK_GARDEN, HZ_LAVA },
        { GAME_MOOD_STORM, STAGE_LOOK_DECK, HZ_SPIKES },
    };
    return &table[w < 0 ? 0 : w >= WORLD_COUNT ? WORLD_COUNT - 1 : w];
}

/* World of arcade stage 1..ARC_STAGE_COUNT. Subtraction, not '/': runs once per stage. */
static inline int world_of_stage(int stage)
{
    int w = 0;
    while (stage > WORLD_BLOCK_STAGES && w < WORLD_COUNT - 1) {
        stage -= WORLD_BLOCK_STAGES;
        w++;
    }
    return w;
}

/* Hazard of the round the game is entering (main.c reads it when the round number changes): arena = round order by
 * matches won; arcade = world of the stage that plays next (during CLEAR before a plain stage: the next stage; CLEAR before
 * a bonus and the bonus itself: the stage just cleared). */
static inline uint8_t world_hazard(const Game *g)
{
    int s;
    if (g->mode != GAME_MODE_ARCADE) {
        return hazard_kind_for_round((uint16_t)g->matches_won);
    }
    s = g->arc.stage;
    if (g->arc.state == ARC_CLEAR && s % ARC_BONUS_EVERY != 0) {
        s = arc_next_stage(s);
    }
    return world_get(world_of_stage(s))->hazard;
}
#endif
