#include "game.h"
#include "stage.h"
#include "nameentry.h"

/* Zero a struct without libc. Byte loop; the compiler may turn it into a memset call, which
 * the ngdevkit libc provides. */
static void zero(void *p, size_t n)
{
    uint8_t *b = (uint8_t *)p;
    while (n--) {
        *b++ = 0;
    }
}

void game_reset(Game *g, uint32_t seed)
{
    zero(g, sizeof(*g));
    rng_seed(&g->rng, seed);
    flier_init(&g->flier, FL_PX(FLIER_START_X), FL_PX(FLIER_START_Y), FLIER_START_BALLOONS, 0);
}

/* Fighter i: 0 is the player, 1..cpu_count the computer fliers. */
static Flier *fighter(Game *g, int i)
{
    return i == 0 ? &g->flier : &g->cpu[i - 1];
}

static void match_start(Game *g)
{
    int n = CPU_START_COUNT + (int)g->matches_won;
    int i;
    if (n > CPU_MAX) {
        n = CPU_MAX;
    }
    g->cpu_count = (uint8_t)n;
    g->cpu_alive = (uint8_t)n;
    for (i = 0; i < STAGE_SPAWN_COUNT; i++) {
        if (i < n) {
            flier_init(&g->cpu[i], FL_PX(stage_spawns[i].x), FL_PX(stage_spawns[i].y), FLIER_START_BALLOONS, 0);
            ai_init(&g->ai[i], &g->rng);
        } else {
            flier_init(&g->cpu[i], 0, 0, 0, 0);
            g->cpu[i].state = FLIER_GONE;
        }
    }
    while (g->flier.balloons < FLIER_START_BALLOONS && flier_add_balloon(&g->flier)) {
    }
}

void game_step_arena(Game *g, uint8_t input)
{
    FlierInput in;
    int i, j, n;
    if (g->over) {
        return;
    }
    if (g->cpu_count == 0) {
        match_start(g);
    }
    g->frame++;
    in.flap = (input & IN_A) ? 1 : 0;
    in.dir = (int8_t)(((input & IN_RIGHT) ? 1 : 0) - ((input & IN_LEFT) ? 1 : 0));
    if (in.flap && !g->flier.flap_prev && g->flier.state < FLIER_DROWNED) {
        g->flaps++;
    }
    flier_step(&g->flier, &in, stage_floor_y(g->flier.x, g->flier.y + flier_half_h(&g->flier)));
    g->flier_steps++;
    for (i = 0; i < g->cpu_count; i++) {
        Flier *c = &g->cpu[i];
        FlierInput ci;
        if (c->state >= FLIER_DROWNED) {
            continue;
        }
        if (c->state <= FLIER_PARACHUTE) {
            ai_step(&g->ai[i], &g->rng, c, ai_nearest(c, &g->flier, g->cpu, g->cpu_count), &ci);
        } else {
            ci.dir = 0;
            ci.flap = 0;
        }
        flier_step(c, &ci, stage_floor_y(c->x, c->y + flier_half_h(c)));
        if (c->state == FLIER_DROWNED) {
            /* A living computer flier reached the water. A defeated one (FALLING) passes through the water and
               leaves as GONE: its defeat already paid SCORE_CPU_DEFEAT, so it scores nothing more
               (user decision 2026-11-10). */
            g->score += SCORE_CPU_DROWN;
        }
    }
    /* Every flier can stomp and touch every other. */
    n = g->cpu_count + 1;
    for (i = 0; i < n; i++) {
        for (j = 0; j < n; j++) {
            if (i != j) {
                Flier *v = fighter(g, j);
                uint8_t was_up = v->state <= FLIER_PARACHUTE;
                int popped = flier_stomp(fighter(g, i), v);
                g->stomps += (uint32_t)popped;
                if (i == 0 && j > 0) {
                    /* Points only for the player's own stomps on a computer flier (design 3.3). */
                    g->score += popped ? SCORE_STOMP_POP : 0;
                    g->score += (was_up && v->state > FLIER_PARACHUTE) ? SCORE_CPU_DEFEAT : 0;
                }
            }
        }
    }
    /* Body contact reflects first (a balloon-less flier about to die gets none), then kills. */
    for (i = 0; i < n; i++) {
        for (j = 0; j < n; j++) {
            if (i != j) {
                g->bounces += (uint32_t)flier_body_bounce(fighter(g, i), fighter(g, j));
            }
        }
    }
    for (i = 0; i < n; i++) {
        for (j = 0; j < n; j++) {
            if (i != j) {
                int killed = flier_body_kill(fighter(g, i), fighter(g, j));
                if (killed && j == 0 && i > 0) {
                    g->score += SCORE_CPU_DEFEAT; /* the player's body touched a balloon-less computer flier */
                }
            }
        }
    }
    g->cpu_alive = 0;
    for (i = 0; i < g->cpu_count; i++) {
        g->cpu_alive = (uint8_t)(g->cpu_alive + (g->cpu[i].state < FLIER_DROWNED ? 1 : 0));
    }
    if (g->flier.state >= FLIER_DROWNED) {
        g->over = 1;
    } else {
        g->distance += SPEED_BASE;
        if (g->cpu_alive == 0 && g->flier.state < FLIER_FALLING) {
            g->matches_won++;
            g->score += SCORE_MATCH_WIN;
            if (g->flier.balloons >= FLIER_START_BALLOONS) {
                g->score += SCORE_MATCH_CLEAN; /* no balloon lost in the match: the player cannot gain any in play */
            }
            match_start(g);
        }
    }
}
