#include "game.h"
#include "stage.h"
#include "nameentry.h"
#include "arena.h"
#include "hazard_kind.h"
#include "banner.h"

/* Broad phase reach in half pixels: the widest pair contact (two wide gums, flier.h FLIER_PAIR_REACH_HALF). */
#define BROAD_REACH_HALF FLIER_PAIR_REACH_HALF

/* Zero a struct without libc. Byte loop; the compiler may turn it into a memset call, which
 * the ngdevkit libc provides. */
static void zero(void *p, size_t n)
{
    uint8_t *b = (uint8_t *)p;
    while (n--) {
        *b++ = 0;
    }
}

/* The hazard of a kind on one flier: the kill line, and whether it is spike tips a dead body bounces on (arena only). */
static void flier_set_hazard(Flier *f, uint8_t kind)
{
    f->kill_y = FL_PX(hazard_kill_px(kind));
    f->solid_kill = (uint8_t)(kind == HZ_SPIKES);
}

/* The player at the spawn point with the start values. Used for a new game and for every rematch, so
 * nothing of the last match (position, speed, facing, invincibility, lost balloons) carries over. */
static void player_spawn(Game *g)
{
    flier_init(&g->flier, FL_PX(FLIER_START_X), FL_PX(FLIER_START_Y), FLIER_START_BALLOONS, 0);
    flier_spawn_protect(&g->flier);
    flier_set_hazard(&g->flier, g->hazard_kind);
}

void game_set_hazard(Game *g, uint8_t kind)
{
    int i;
    g->hazard_kind = kind;
    flier_set_hazard(&g->flier, kind);
    for (i = 0; i < STAGE_SPAWN_COUNT; i++) {
        flier_set_hazard(&g->cpu[i], kind);
    }
}

void game_reset(Game *g, uint32_t seed)
{
    zero(g, sizeof(*g));
    rng_seed(&g->rng, seed);
    camera_init(&g->camera);
    trip_init(&g->trip);
    stage_select(0);
    stage_set_level(0);
    player_spawn(g);
}

void game_set_mode(Game *g, uint8_t mode)
{
    g->mode = mode == GAME_MODE_TRIP || mode == GAME_MODE_ARCADE ? mode : GAME_MODE_ARENA;
    if (g->mode == GAME_MODE_ARCADE) {
        arc_start(&g->arc);
        arc_lives_start(&g->lives); /* the arena step builds stage 1 at its first frame (match_start) */
    }
    if (g->mode == GAME_MODE_TRIP) {
        flier_init(&g->flier, FL_PX(TRIP_START_X), FL_PX(TRIP_START_Y), 2, 0);
        flier_spawn_protect(&g->flier);
        flier_set_hazard(&g->flier, g->hazard_kind);
        g->flier.solid_kill = 0; /* Gum Trip draws no spike strip: the dead body just falls */
        g->flier.no_wrap = 1;
        trip_init(&g->trip);
        tripgen_init(&g->trip_gen, rng_next(&g->rng)); /* course seed: next draw of the run's seed (game_reset(seed) at Start) */
        trip_rivals_init(&g->trip_rivals, &g->trip, rng_next(&g->rng)); /* rival seed: the draw after the course seed */
        g->trip_events = 0;
        g->trip_rival_events = 0;
        g->trip_hold = 0;
        camera_init(&g->camera);
        g->camera.cam = 0; /* the view starts at the scroll origin: camera == trip distance mod ARENA_W */
    }
}

void game_step(Game *g, uint8_t input)
{
    if (g->mode == GAME_MODE_TRIP) {
        game_step_trip(g, input);
    } else {
        game_step_arena(g, input); /* ARENA and ARCADE share the arena step; the arcade differences are branches inside it */
    }
}

/* Fighter i: 0 is the player, 1..cpu_count the computer fliers. */
static Flier *fighter(Game *g, int i)
{
    return i == 0 ? &g->flier : &g->cpu[i - 1];
}

/* Score add: the arcade clamps at SCORE_CAP (FQ10), the other modes add as before. */
static void score_add(Game *g, uint32_t pts)
{
    g->score = g->mode == GAME_MODE_ARCADE ? arc_score_add(g->score, pts) : g->score + pts;
}

/* ArcPump of fighter index i (0 is the player, which never pumps: a window-less static). */
static const ArcPump *pump_of(const Game *g, int i)
{
    static const ArcPump none = { ARC_PUMP_IDLE, 1, 0 };
    return i > 0 ? &g->pump[i - 1] : &none;
}

/* The player touched a pumping rival: pop it at once (all gum, even through the pop protection) and pay its window defeat. */
static void pump_defeat(Game *g, Flier *v, ArcPump *p)
{
    uint32_t win = arc_pump_resolve(p);
    v->invincible = 0;
    v->spawn_inv = 0;
    while (flier_lose_balloon(v)) {
        v->invincible = 0;
    }
    g->stomps++;
    score_add(g, g->mode == GAME_MODE_ARCADE ? win : SCORE_CPU_DEFEAT);
}

static void match_start(Game *g)
{
    int arcade = g->mode == GAME_MODE_ARCADE;
    int rank = arcade ? arc_rank_for(g->arc.stage, g->arc.loops) : 1;
    int n = CPU_START_COUNT + (int)g->matches_won;
    int i;
    if (n > CPU_MAX) {
        n = CPU_MAX;
    }
    if (arcade) {
        stage_select(arc_stage_layout(g->arc.stage));
        stage_set_level(g->arc.stage - 1);
        n = stage_rival_count(); /* the layout's own rival count (ROT3b) */
        arc_elements_init(&g->elems, g->arc.stage - 1);
    } else if (g->rounds) {
        stage_select((int)(g->matches_won % (uint32_t)stage_layout_count())); /* round start: the pan has ended, the screen is frozen under ROUND nn */
        stage_set_level((int)g->matches_won);
    }
    g->cpu_count = (uint8_t)n;
    g->cpu_alive = (uint8_t)n;
    for (i = 0; i < STAGE_SPAWN_COUNT; i++) {
        if (i < n) {
            flier_init(&g->cpu[i], FL_PX(stage_spawns[i].x), FL_PX(stage_spawns[i].y), FLIER_START_BALLOONS, 0);
            g->cpu[i].rival = 1;
            ai_init(&g->ai[i], &g->rng, rank);
            arc_pump_start(&g->pump[i], rank, 1); /* every layout spawn stands just above a platform top */
        } else {
            flier_init(&g->cpu[i], 0, 0, 0, 0);
            g->cpu[i].state = FLIER_GONE;
        }
        flier_set_hazard(&g->cpu[i], g->hazard_kind);
    }
    if (g->rounds) {
        g->round_start = RS_ROUND; /* round 1 and every round after the pan: ROUND nn, GO!, all frozen */
        g->round_start_timer = 0;
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

/* Arena and arcade share the round phases (pan, ROUND/STAGE banner, frozen hazards). */
static int has_rounds(const Game *g)
{
    return g->mode == GAME_MODE_ARENA || g->mode == GAME_MODE_ARCADE;
}

int game_flier_visible(const Game *g)
{
    return !(has_rounds(g) && g->round_end == RE_PAN);
}

int game_round_start_phase(const Game *g)
{
    return has_rounds(g) ? g->round_start : RS_NONE;
}

int game_round_number(const Game *g)
{
    if (g->mode != GAME_MODE_ARCADE) {
        return (int)g->matches_won + 1;
    }
    /* arcade: the stage that starts next; the bonus number during a bonus stage and the clear before it */
    if (g->arc.state == ARC_CLEAR && g->arc.stage % ARC_BONUS_EVERY == 0) {
        return g->arc.bonus_no + 1;
    }
    return g->arc.state == ARC_BONUS ? g->arc.bonus_no : g->arc.state == ARC_CLEAR ? arc_next_stage(g->arc.stage) : g->arc.stage;
}

int game_banner_flags(const Game *g)
{
    if (g->mode != GAME_MODE_ARCADE) {
        return 0;
    }
    return (g->arc.state == ARC_BONUS || (g->arc.state == ARC_CLEAR && g->arc.stage % ARC_BONUS_EVERY == 0)) ? BANNER_BONUS : BANNER_STAGE;
}

const char *game_round_start_text(const Game *g, int line)
{
    if (g->mode != GAME_MODE_ARCADE || g->arc.state != ARC_BONUS) {
        return 0;
    }
    return line == 0 ? "BONUS STAGE" : line == 1 ? "POP THE BUBBLES" : 0;
}

int game_hazards_frozen(const Game *g)
{
    return has_rounds(g) && (g->round_start != RS_NONE || g->round_end != RE_NONE);
}

int game_camera_px(const Game *g)
{
    return camera_px(&g->camera);
}

int game_flier_cam_px(const Game *g)
{
    /* The trip flier lives in screen space (x 0..319): the view places it with camera 0. */
    return g->mode == GAME_MODE_TRIP ? 0 : camera_px(&g->camera);
}

/* One arena step for any flier: the floor line, then the solid island bodies (pre-step position kept for the push-out). */
/* Gum posts of the arcade stages (gen3.py post lists): hang 'down' from the underside of a layout platform or stand 'up' on its top. */
typedef struct { uint8_t layout, plat; int16_t x; uint8_t len, up; } ArcPost;
#define ARC_POST_W 16
#define ARC_POSTS_MAX 3
/* Catcher box around the player in the bonus stage, px. Reference pop test: |dx| < 16 and |dy| < 24 between centres. Our test is box overlap
 * with the 16 px bubble box (half 8), so the catcher half sizes are 16 - 8 = 8 wide and 24 - 8 = 16 high: the same distances. */
#define ARC_BONUS_CATCH_HALF_W 8
#define ARC_BONUS_CATCH_HALF_H 16
static const ArcPost arc_posts[] = {
    { 14, 2, 144, 40, 0 }, { 14, 3, 232, 40, 0 }, { 14, 4, 320, 40, 0 }, /* N05 */
    { 17, 2, 176, 40, 1 },                                             /* N04 */
    { 23, 2, 132, 32, 1 }, { 23, 2, 212, 32, 1 },                      /* R12b */
};

/* Appends the posts of the current layout as solid boxes (copy nearest x16); returns the new count. */
static int add_post_solids(int32_t x16, FlierSolid *so, int n)
{
    unsigned i;
    for (i = 0; i < sizeof(arc_posts) / sizeof(arc_posts[0]); i++) {
        const ArcPost *p = &arc_posts[i];
        const StagePlatform *pl = &stage_platforms[p->plat];
        if (p->layout != stage_layout_index()) continue;
        so[n].x16 = arena_near_x(x16, FL_PX(p->x + ARC_POST_W / 2)) - FL_PX(ARC_POST_W / 2);
        so[n].y16 = FL_PX(p->up ? pl->y - p->len : pl->y + STAGE_PLATFORM_H);
        so[n].w16 = FL_PX(ARC_POST_W);
        so[n].h16 = FL_PX(p->len);
        n++;
    }
    return n;
}

static void arena_flier_step(const Game *g, Flier *f, const FlierInput *in) {
    int32_t px = f->x, py = f->y;
    FlierSolid so[STAGE_SOLIDS_MAX + ARC_POSTS_MAX];
    int n;
    flier_step(f, in, stage_floor_y(f->x, f->y + flier_half_h(f)));
    n = stage_solids_near(f->x, so, STAGE_SOLIDS_MAX);
    if (g->mode == GAME_MODE_ARCADE) n = add_post_solids(f->x, so, n);
    flier_collide_solids(f, px, py, so, n);
}

/* Stage elements act on one live flier: a kill drowns it like the hazard line, a flipper sets its speed, a grate lifts it. */
static void arc_element_apply(const ArcElements *a, Flier *f)
{
    int cx = (int)(f->x >> 16), cy = (int)(f->y >> 16), hh = (int)(flier_half_h(f) >> 16);
    if (f->state >= FLIER_FALLING) return;
    if (arc_elements_kill(a, cx, cy, FLIER_HALF_W, hh)) {
        f->state = FLIER_DROWNED;
        f->vx = 0;
        if (f->vy < 0) f->vy = 0;
        return;
    }
    arc_elements_bounce(a, cx, cy, FLIER_HALF_W, hh, &f->vx, &f->vy);
    f->vy += arc_elements_lift(a, cx, cy, FLIER_HALF_W, hh);
    if (f->vy < -FLIER_RISE_MAX) f->vy = -FLIER_RISE_MAX;
}

/* The grabber rises for a flier with balloons low in the air over the water (one standing on an island is out of reach): tell the elements where every such flier is. */
static void arc_note_low_fliers(Game *g)
{
    int i;
    if (g->flier.state == FLIER_ALIVE && g->flier.balloons && !g->flier.on_ground) arc_elements_note_low(&g->elems, (int)(g->flier.x >> 16), (int)(g->flier.y >> 16));
    for (i = 0; i < g->cpu_count; i++) {
        const Flier *c = &g->cpu[i];
        if (c->state == FLIER_ALIVE && c->balloons && !c->on_ground) arc_elements_note_low(&g->elems, (int)(c->x >> 16), (int)(c->y >> 16));
    }
}

/* A solid island between two fliers blocks their contact (pop, bounce, body kill). The solids come from the pair midpoint so
   a platform at the seam is found from both sides. Only called for pairs that already touch. */
static int arena_pair_blocked(const Flier *a, const Flier *b)
{
    FlierSolid so[STAGE_SOLIDS_MAX];
    int32_t mid = arena_wrap_x(a->x + ((arena_near_x(a->x, b->x) - a->x) >> 1));
    return flier_pair_blocked(a, b, so, stage_solids_near(mid, so, STAGE_SOLIDS_MAX), 1);
}

/* Round end and round start phases of a real game. Returns 1 when the frame is spent (the caller returns). Game.frame
 * keeps counting; the flier, the computer fliers and the pair passes do not run; the camera follows. */
static int round_phase_step(Game *g)
{
    if (g->round_end != RE_NONE) {
        g->frame++;
        if (g->round_end == RE_HOLD) {
            if (g->round_timer > 0) {
                g->round_timer--;
            }
            if (g->round_timer == 0) {
                g->round_end = RE_PAN;
                player_spawn(g); /* hidden (game_flier_visible) at the spawn: the camera slides to it */
            }
        } else {
            int32_t humans[1];
            humans[0] = g->flier.x;
            if (camera_arrived(&g->camera, humans, 1)) {
                g->round_end = RE_NONE;
                match_start(g);
            }
        }
        camera_follow(g);
        return 1;
    }
    if (g->round_start != RS_NONE) {
        g->frame++;
        g->round_start_timer++;
        if (g->round_start == RS_ROUND && g->round_start_timer >= ROUND_START_TEXT_FRAMES) {
            g->round_start = RS_GO;
            g->round_start_timer = 0;
        } else if (g->round_start == RS_GO && g->round_start_timer >= ROUND_GO_TEXT_FRAMES) {
            g->round_start = RS_NONE;
        }
        camera_follow(g);
        return 1;
    }
    return 0;
}

/* A new arcade stage begins: the player returns to the spawn, then the camera pan (real game) or at once. */
static void arc_enter_stage(Game *g)
{
    player_spawn(g);
    if (g->rounds) {
        g->round_end = RE_PAN;
    } else {
        match_start(g);
    }
}

/* Arcade between stages: the CLEAR frames, the BONUS banner hold, the bonus stage (the player flies, its box catches bubbles).
 * Returns 1 when the frame is spent. The next stage starts like a round end: spawn, then the pan (real game) or match_start. */
static int arc_interlude(Game *g, uint8_t input)
{
    FlierInput in;
    if (g->mode != GAME_MODE_ARCADE || g->arc.state == ARC_PLAY) {
        return 0;
    }
    g->frame++;
    if (g->arc.state == ARC_CLEAR) {
        int started = arc_step(&g->arc);
        g->round_timer = (uint16_t)g->arc.timer;
        if (g->arc.state == ARC_BONUS) {
            arc_bonus_init(&g->bonus, g->arc.bonus_no, rng_next(&g->rng));
            stage_select(ARC_LAYOUT_BONUS); /* floor strip and nozzle tops; arc_enter_stage / match_start selects the next stage's layout */
            g->round_end = RE_NONE; /* ALL POPPED showed once; the bonus is announced by the round-start phase (BONUS STAGE, then GO) */
            if (g->rounds) {
                g->round_start = RS_ROUND;
                g->round_start_timer = 0;
            }
        } else if (started) {
            arc_enter_stage(g);
        }
    } else if (round_phase_step(g)) {
        return 1; /* the bonus announcement: everything frozen */
    } else {
        int cx = (int)(g->flier.x >> 16), cy = (int)(g->flier.y >> 16);
        in.flap = (input & IN_A) ? 1 : 0;
        in.dir = (int8_t)(((input & IN_RIGHT) ? 1 : 0) - ((input & IN_LEFT) ? 1 : 0));
        arena_flier_step(g, &g->flier, &in);
        arc_bonus_step(&g->bonus, g->flier.state == FLIER_ALIVE && g->flier.balloons > 0, cx - ARC_BONUS_CATCH_HALF_W, cy - ARC_BONUS_CATCH_HALF_H, 2 * ARC_BONUS_CATCH_HALF_W, 2 * ARC_BONUS_CATCH_HALF_H);
        if (g->flier.state == FLIER_GONE) {
            player_spawn(g); /* a bonus stage costs no life */
        }
        if (g->bonus.over) {
            /* stand-in: result screen tally replaces this */
            score_add(g, (uint32_t)g->bonus.caught * (uint32_t)arc_bonus_value(g->bonus.number) + (g->bonus.perfect ? (uint32_t)arc_bonus_perfect(g->bonus.number) : 0u));
            arc_bonus_done(&g->arc);
            arc_enter_stage(g);
        }
    }
    camera_follow(g);
    return 1;
}

void game_step_arena(Game *g, uint8_t input)
{
    FlierInput in;
    int i, j, n;
    uint8_t bodies;
    uint8_t a_edge = (uint8_t)((input & IN_A) && !g->cont_a);
    g->cont_a = (input & IN_A) ? 1 : 0;
    if (g->over) {
        camera_follow(g);
        return;
    }
    if (g->mode == GAME_MODE_ARCADE && g->lives.state == ARC_LIFE_CONTINUE) {
        /* Continue screen: the world is frozen. A press continues; credits are a constant 1 here (shortcut: the real credit
         * path is a later task); the countdown running out ends the run. */
        if (arc_continue_step(&g->lives, a_edge, 1)) {
            g->score = g->lives.score;
            player_spawn(g);
        } else if (g->lives.state == ARC_LIFE_ENDED) {
            g->over = 1;
        }
        camera_follow(g);
        return;
    }
    if (g->cpu_count == 0) {
        match_start(g);
    }
    if (arc_interlude(g, input) || round_phase_step(g)) {
        return;
    }
    g->frame++;
    if (g->mode == GAME_MODE_ARCADE) {
        arc_note_low_fliers(g);
        arc_elements_step(&g->elems);
    }
    in.flap = (input & IN_A) ? 1 : 0;
    in.dir = (int8_t)(((input & IN_RIGHT) ? 1 : 0) - ((input & IN_LEFT) ? 1 : 0));
    if (in.flap && !g->flier.flap_prev && g->flier.state < FLIER_DROWNED) {
        g->flaps++;
    }
    arena_flier_step(g, &g->flier, &in);
    g->flier_steps++;
    if (g->mode == GAME_MODE_ARCADE) arc_element_apply(&g->elems, &g->flier);
    for (i = 0; i < g->cpu_count; i++) {
        Flier *c = &g->cpu[i];
        FlierInput ci;
        uint8_t was = c->state;
        int pumping;
        if (c->state == FLIER_GONE) {
            continue;
        }
        pumping = arc_pump_in_window(&g->pump[i]);
        arc_pump_step(&g->pump[i]);
        if (pumping) {
            ci.dir = 0; /* sits and pumps: no AI, no input until the window ends */
            ci.flap = 0;
        } else if (c->state <= FLIER_PARACHUTE) {
            ai_step(&g->ai[i], &g->rng, c, ai_nearest(c, &g->flier, g->cpu, g->cpu_count), &ci);
            if (g->mode == GAME_MODE_ARCADE) {
                int away = arc_elements_avoid_dir(&g->elems, (int)(c->x >> 16), (int)(c->y >> 16), FLIER_HALF_W, (int)(flier_half_h(c) >> 16), c->vx);
                if (away) {
                    ci.dir = (int8_t)away;   /* a burst kills, an island underside only bumps: overrides the overhead-edge steer in ai.c */
                    /* Air steering only acts on a flap and the AI flaps only toward a target above, so a rival drifted into the plume
                       at constant vx: flap on every allowed press while threatened (sideways thrust away, and lift above the plume). */
                    if (!c->on_ground && c->flap_cd == 0 && !c->flap_prev) ci.flap = 1;
                }
            }
        } else {
            ci.dir = 0;
            ci.flap = 0;
        }
        arena_flier_step(g, c, &ci);
        if (g->mode == GAME_MODE_ARCADE) arc_element_apply(&g->elems, c);
        if (pumping && !arc_pump_in_window(&g->pump[i])) {
            c->vy = FLIER_GROUND_JUMP_VY; /* lift-off: one upward impulse, no sideways speed */
            c->vx = 0;
            c->on_ground = 0;
        }
        if (c->state == FLIER_DROWNED && was != FLIER_DROWNED) {
            /* A living computer flier reached the hazard (scored once, on entry; it sinks or bounces on from here). A defeated one (FALLING) passes through the water and
               leaves as GONE: its defeat already paid SCORE_CPU_DEFEAT, so it scores nothing more
               (user decision 2026-11-10). */
            score_add(g, SCORE_CPU_DROWN);
        }
    }
    /* Every flier can pop and touch every other (flier_pair decides gum against gum, body against gum, body against body);
       a solid island between the two blocks the contact (arena_pair_blocked: no pop, bounce or body kill).
       The pair passes are O(n^2) and were a large part of the frame with seven fliers, so a horizontal broad phase skips
       pairs that cannot touch. It is exact, not an approximation: no pair contact reaches further than
       FLIER_PAIR_REACH_HALF half pixels (x >> 15, the unit flier_pair compares in), and a pair further apart makes
       flier_pair and flier_body_kill return 0 without touching either flier, so skipping it changes nothing. The pair
       passes do not move a flier horizontally (they change velocities, state and at most y), so the near set computed
       here holds for both, and they keep the (i, j) order. Distances are measured across the arena seam (arena_dx_half):
       fliers wrap at 384 px, so x 382 and x 2 are 4 px apart. */
    n = g->cpu_count + 1;
    {
        Flier *f[STAGE_SPAWN_COUNT + 1];
        int32_t hx[STAGE_SPAWN_COUNT + 1];
        uint8_t near[STAGE_SPAWN_COUNT + 1];      /* pairs within contact reach */
        for (i = 0; i < n; i++) {
            f[i] = fighter(g, i);
            hx[i] = f[i]->x >> 15;
            near[i] = 0;
        }
        for (i = 0; i < n; i++) {
            for (j = i + 1; j < n; j++) {
                int32_t d = arena_dx_half(hx[i], hx[j]);
                if (d <= BROAD_REACH_HALF && d >= -BROAD_REACH_HALF) {
                    near[i] = (uint8_t)(near[i] | (1u << j));
                    near[j] = (uint8_t)(near[j] | (1u << i));
                }
            }
        }
        /* One decision per unordered pair; a bounce reflects both fliers (a balloon-less one is left to flier_body_kill). */
        for (i = 0; i < n; i++) {
            for (j = i + 1; j < n; j++) {
                if (near[i] & (1u << j)) {
                    FlierPairAct act = flier_pair(f[i], f[j]);
                    int popper = act == FLP_POP_B ? i : j;
                    int popped_idx = act == FLP_POP_B ? j : i;
                    Flier *v = f[popped_idx];
                    uint8_t was_up = v->state <= FLIER_PARACHUTE;
                    if (act == FLP_NONE || arena_pair_blocked(f[i], f[j])) continue;
                    /* A pumping rival is harmless and still: the player's contact (any height) defeats it, nothing bounces or pops. */
                    if (arc_pump_in_window(pump_of(g, i)) || arc_pump_in_window(pump_of(g, j))) {
                        if (i == 0) {
                            pump_defeat(g, f[j], &g->pump[j - 1]);
                        }
                        continue;
                    }
                    /* Computer fliers never pop each other (BR-D3): a gum-on-gum contact between two of them is a bounce.
                       flier_pair stays pure; the rule lives here, where the indices say who is the player. (In Gum Trip
                       the rivals never meet each other, so this is arena only.) */
                    if (i > 0 && j > 0 && (act == FLP_POP_A || act == FLP_POP_B)) act = FLP_BOUNCE;
                    if (act == FLP_BOUNCE) {
                        flier_pair_apply(f[i], f[j], act);
                        g->bounces++;
                        continue;
                    }
                    if (flier_pair_apply(f[i], f[j], act)) {
                        g->stomps++;
                        if (popper == 0) {
                            /* Points only for the player's own pops on a computer flier (design 3.3). */
                            if (g->mode == GAME_MODE_ARCADE) {
                                const ArcRank *rk = arc_rank(g->pump[popped_idx - 1].rank);
                                score_add(g, rk->pop_score + ((was_up && v->state > FLIER_PARACHUTE) ? rk->defeat_score : 0));
                            } else {
                                score_add(g, SCORE_STOMP_POP);
                                score_add(g, (was_up && v->state > FLIER_PARACHUTE) ? SCORE_CPU_DEFEAT : 0);
                            }
                        }
                    }
                }
            }
        }
        for (i = 0; i < n; i++) {
            for (j = 0; j < n; j++) {
                if (near[i] & (1u << j)) {
                    int killed = flier_body_touching(f[i], f[j]) && !arena_pair_blocked(f[i], f[j]) && flier_body_kill(f[i], f[j]);
                    if (killed && j == 0 && i > 0) {
                        score_add(g, g->mode == GAME_MODE_ARCADE ? arc_rank(g->pump[i - 1].rank)->defeat_score : SCORE_CPU_DEFEAT); /* the player's body touched a balloon-less computer flier */
                    }
                }
            }
        }
    }
    g->cpu_alive = 0;
    bodies = 0;
    for (i = 0; i < g->cpu_count; i++) {
        g->cpu_alive = (uint8_t)(g->cpu_alive + (g->cpu[i].state < FLIER_DROWNED ? 1 : 0));
        bodies = (uint8_t)(bodies + (g->cpu[i].state == FLIER_DROWNED ? 1 : 0));
    }
    if (g->flier.state == FLIER_GONE) {
        if (g->mode == GAME_MODE_ARCADE) {
            arc_lose_life(&g->lives);
            if (g->lives.state == ARC_LIFE_PLAY) {
                player_spawn(g); /* next life on the same stage */
            }   /* else the continue screen runs from the next step (top of this function) */
        } else {
            g->over = 1; /* the dead hero has left the screen: the run ends now, not at the kill */
        }
    } else {
        g->distance += SPEED_BASE;
        /* the match is won when no computer flier lives and the last hazard body has left the screen (cpu_alive counts FALLING bodies as alive) */
        if (g->cpu_alive == 0 && bodies == 0 && g->flier.state < FLIER_FALLING) {
            g->matches_won++;
            if (g->mode == GAME_MODE_ARCADE) {
                arc_stage_cleared(&g->arc); /* arc_interlude runs the CLEAR frames and the bonus stage from the next frame */
            }
            score_add(g, SCORE_MATCH_WIN);
            if (g->flier.balloons >= FLIER_START_BALLOONS) {
                score_add(g, SCORE_MATCH_CLEAN); /* no balloon lost in the match: the player cannot gain any in play */
            }
            if (g->rounds) {
                g->round_end = RE_HOLD; /* banner, then the camera slide, then the next round (round_phase_step) */
                g->round_timer = MATCH_END_FRAMES;
            } else if (g->mode != GAME_MODE_ARCADE) { /* arcade: arc_interlude starts the next stage */
                player_spawn(g); /* rematch = fresh match (design N1a): every flier starts on its spawn point */
                match_start(g);
            }
        }
    }
    camera_follow(g);
}

int game_trip_ready(const Game *g)
{
    return tripgen_covers(&g->trip_gen, g->trip.px);
}

void game_step_trip(Game *g, uint8_t input)
{
    FlierInput in;
    uint32_t step;
    if (g->over) {
        g->trip_events = 0; /* no stale TRIP_EV_HIT for the sound edge */
        return;
    }
    if (!tripgen_covers(&g->trip_gen, g->trip.px)) {
        /* run start: build the first screen one chunk per step, nothing else moves. game_step runs from the frame after
         * game_reset + game_set_mode (flow_step enters PLAYING without stepping), so this never shares their frame. */
        tripgen_advance(&g->trip_gen, g->trip.px);
        g->trip_hold++;
        return;
    }
    g->frame++;
    in.flap = (input & IN_A) ? 1 : 0;
    in.dir = (int8_t)(((input & IN_RIGHT) ? 1 : 0) - ((input & IN_LEFT) ? 1 : 0));
    if (in.flap && !g->flier.flap_prev && g->flier.state < FLIER_DROWNED) {
        g->flaps++;
    }
    g->flier.no_wrap = 1;
    {
        int32_t px = g->flier.x, py = g->flier.y;
        FlierSolid so[TRIP_SOLIDS_MAX];
        flier_step(&g->flier, &in, trip_hit_floor_y(&g->trip, &g->trip_gen, &g->flier));
        flier_collide_solids(&g->flier, px, py, so, trip_hit_solids(&g->trip, &g->trip_gen, &g->flier, so, TRIP_SOLIDS_MAX));
    }
    g->flier_steps++;
    step = g->trip.speed; /* the step trip_step scrolls by this frame */
    trip_step(&g->trip, &g->flier);
    tripgen_advance(&g->trip_gen, g->trip.px);
    /* Walls first (hero: bottom rock kills, top rock bounces without gum loss), so the strip hit test below never sees the hero
     * inside the rock; then the hazard hit (gum loss, cooldown), the push-out and bounce off the hazard, and the walls again
     * (a push into the rock is a wall touch). TRIP_EV_HIT from a wall kill plays the hit sound like a hazard hit. */
    {
        unsigned ev = trip_hit_hero_walls(&g->trip, &g->trip_gen, &g->flier);
        ev |= trip_collide(&g->trip, &g->trip_gen, &g->flier);
        trip_hit_haz_bounce(&g->trip, &g->trip_gen, &g->flier);
        ev |= trip_hit_hero_walls(&g->trip, &g->trip_gen, &g->flier);
        g->trip_events = (uint8_t)ev;
    }
    g->trip_rival_events = (uint8_t)trip_rivals_step(&g->trip_rivals, &g->trip, &g->trip_gen, &g->flier);
    camera_scroll(&g->camera, step);
    g->distance = g->trip.px;
    g->score = trip_score(&g->trip);
    g->over = (uint8_t)trip_over(&g->flier);
}
