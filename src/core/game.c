#include "game.h"
#include "stage.h"
#include "nameentry.h"
#include "arena.h"
#include "hazard_kind.h"

/* Broad phase reach in half pixels: the larger of the stomp reach (feet + gum boxes, flier.h) and body contact
   (2 * FLIER_HALF_W whole pixels apart = 4 px; body_overlap rounds half pixel positions up to 9). */
#define BODY_REACH_HALF (4 * FLIER_HALF_W + 1)
#define BROAD_REACH_HALF (FLIER_STOMP_REACH_HALF > BODY_REACH_HALF ? FLIER_STOMP_REACH_HALF : BODY_REACH_HALF)

/* Zero a struct without libc. Byte loop; the compiler may turn it into a memset call, which
 * the ngdevkit libc provides. */
static void zero(void *p, size_t n)
{
    uint8_t *b = (uint8_t *)p;
    while (n--) {
        *b++ = 0;
    }
}

/* The player at the spawn point with the start values. Used for a new game and for every rematch, so
 * nothing of the last match (position, speed, facing, invincibility, lost balloons) carries over. */
static void player_spawn(Game *g)
{
    flier_init(&g->flier, FL_PX(FLIER_START_X), FL_PX(FLIER_START_Y), FLIER_START_BALLOONS, 0);
    g->flier.kill_y = FL_PX(hazard_kill_px(g->hazard_kind));
}

void game_set_hazard(Game *g, uint8_t kind)
{
    int i;
    int32_t line;
    g->hazard_kind = kind;
    line = FL_PX(hazard_kill_px(kind));
    g->flier.kill_y = line;
    for (i = 0; i < STAGE_SPAWN_COUNT; i++) {
        g->cpu[i].kill_y = line;
    }
}

void game_reset(Game *g, uint32_t seed)
{
    zero(g, sizeof(*g));
    rng_seed(&g->rng, seed);
    camera_init(&g->camera);
    player_spawn(g);
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
        g->cpu[i].kill_y = FL_PX(hazard_kill_px(g->hazard_kind));
    }
}

/* The camera follows the living human fliers. Only the player exists today; a second human adds an entry here. */
static void camera_follow(Game *g)
{
    int32_t humans[1];
    int n = 0;
    if (g->flier.state < FLIER_DROWNED) {
        humans[n++] = g->flier.x;
    }
    camera_step(&g->camera, humans, n);
}

int game_camera_px(const Game *g)
{
    return camera_px(&g->camera);
}

void game_step_arena(Game *g, uint8_t input)
{
    FlierInput in;
    int i, j, n;
    if (g->over) {
        camera_follow(g);
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
    /* Every flier can stomp and touch every other. The three pair passes below are O(n^2) and were a large part
       of the frame with seven fliers, so a horizontal broad phase skips pairs that cannot touch. It is exact, not
       an approximation: a stomp needs the attacker's feet box to overlap the victim's body box, which in half
       pixels (x >> 15, the units of flier_feet_hit) means |ax - vx| < FLIER_STOMP_REACH_HALF (feet half width plus
       the wider gum half width, both from flier.h); body contact needs whole-pixel
       centres at most 2 * FLIER_HALF_W = 4 px apart (body_overlap), which implies at most 9 half pixels. A pair
       further apart than FLIER_STOMP_REACH_HALF half pixels makes flier_stomp return 0 and further apart than 9 makes
       flier_body_bounce and flier_body_kill return 0, all without touching either flier, so skipping it changes
       nothing. Two masks keep the cheap body passes on the narrow reach: near (stomp) and touch (body). None of the three passes moves a flier
       horizontally (they change velocities, state and at most y), so the near set computed here holds for all
       three, and the passes keep their order and their (i, j) order. Distances are measured across the arena seam
       (arena_dx_half): fliers wrap at 384 px, so x 382 and x 2 are 4 px apart. Positions stay in 0..384 px, far
       inside the int16 range that flier_feet_hit casts to. */
    n = g->cpu_count + 1;
    {
        Flier *f[CPU_MAX + 1];
        int32_t hx[CPU_MAX + 1];
        uint8_t near[CPU_MAX + 1];      /* pairs within stomp reach */
        uint8_t touch[CPU_MAX + 1];     /* pairs within body contact reach (a subset of near) */
        for (i = 0; i < n; i++) {
            f[i] = fighter(g, i);
            hx[i] = f[i]->x >> 15;
            near[i] = 0;
            touch[i] = 0;
        }
        for (i = 0; i < n; i++) {
            for (j = i + 1; j < n; j++) {
                int32_t d = arena_dx_half(hx[i], hx[j]);
                if (d <= BROAD_REACH_HALF && d >= -BROAD_REACH_HALF) {
                    near[i] = (uint8_t)(near[i] | (1u << j));
                    near[j] = (uint8_t)(near[j] | (1u << i));
                    if (d <= BODY_REACH_HALF && d >= -BODY_REACH_HALF) {
                        touch[i] = (uint8_t)(touch[i] | (1u << j));
                        touch[j] = (uint8_t)(touch[j] | (1u << i));
                    }
                }
            }
        }
        for (i = 0; i < n; i++) {
            for (j = 0; j < n; j++) {
                if (near[i] & (1u << j)) {
                    Flier *v = f[j];
                    uint8_t was_up = v->state <= FLIER_PARACHUTE;
                    int popped = flier_stomp(f[i], v);
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
                if (touch[i] & (1u << j)) {
                    g->bounces += (uint32_t)flier_body_bounce(f[i], f[j]);
                }
            }
        }
        for (i = 0; i < n; i++) {
            for (j = 0; j < n; j++) {
                if (touch[i] & (1u << j)) {
                    int killed = flier_body_kill(f[i], f[j]);
                    if (killed && j == 0 && i > 0) {
                        g->score += SCORE_CPU_DEFEAT; /* the player's body touched a balloon-less computer flier */
                    }
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
            player_spawn(g); /* rematch = fresh match (design N1a): every flier starts on its spawn point */
            match_start(g);
        }
    }
    camera_follow(g);
}
