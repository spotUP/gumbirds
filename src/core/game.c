#include "game.h"
#include "stage.h"
#include "nameentry.h"
#include "arena.h"
#include "hazard_kind.h"
#include "banner.h"
#include "world.h"

/* near[] holds one bit per fighter in a uint8_t */
typedef char near_mask_fits_uint8[(HUMANS + STAGE_SPAWN_COUNT <= 8) ? 1 : -1];

/* Broad phase reach in half pixels: the widest pair contact (two wide gums, flier.h FLIER_PAIR_REACH_HALF). */
#define BROAD_REACH_HALF FLIER_PAIR_REACH_HALF
#define PARTY_WIND_ACCEL 400  /* Windy twist: 16.16 vx added per frame to each airborne flier (0.006 px/frame^2) */
#define PARTY_SLOW_RANK -3    /* Slow Thinkers: ai rank below the arena value 1 (think period +24 frames) */
#define PARTY_QUICK_RANK 4    /* Quick Thinkers: arcade rank 4 (think period -18 frames) */

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
static void player_spawn_h(Game *g, int h)
{
    flier_init(&g->hero[h], FL_PX(FLIER_START_X + h * FLIER_START_GAP), FL_PX(FLIER_START_Y), FLIER_START_BALLOONS, 0);
    flier_spawn_protect(&g->hero[h]);
    flier_set_hazard(&g->hero[h], g->hazard_kind);
}

int game_lives_mode(const Game *g)
{
    return g->mode == GAME_MODE_ARCADE || (g->mode == GAME_MODE_ARENA && g->players == 2);
}

int game_banner_winner(const Game *g)
{
    if (g->mode == GAME_MODE_ARENA && (g->players == 2 || g->party_rule == PARTY_ROOST)) return g->round_winner;
    return g->players == 2 && g->last_popper == 1 ? BANNER_P2 : BANNER_P1;
}

/* Stage start and rematch: every human still in the run is back at the spawn (a player waiting on the continue screen stays out). */
static void player_spawn(Game *g)
{
    int h;
    for (h = 0; h < g->players; h++) {
        if (!game_lives_mode(g) || g->lives[h].state == ARC_LIFE_PLAY) {
            player_spawn_h(g, h);
            g->out_mask &= (uint8_t)~(1u << h);
        }
    }
}

void game_start_p2(Game *g)
{
    g->players = 2;
    arc_lives_start(&g->lives[1]);
    player_spawn_h(g, 1);
}

/* P2 may join now: arcade play with no round end pan, no result screen, no run over, and the P2 side free (never joined, or out of lives). */
int game_can_join_p2(const Game *g)
{
    if (g->mode == GAME_MODE_ARENA) { /* a join restarts the whole match (flow_join_p2) */
        return g->rounds && !g->over && g->cpu_count > 0 && (g->players == 1 || g->lives[1].state == ARC_LIFE_ENDED);
    }
    return g->mode == GAME_MODE_ARCADE && !g->over && g->round_end == RE_NONE && !g->res.active && g->arc.state == ARC_PLAY &&
           g->cpu_count > 0 && (g->players == 1 || g->lives[1].state == ARC_LIFE_ENDED);
}

/* A flier drops in on its parachute from the top at world x (the P2 join, and the Roost Rule respawn). It flies out on its first flap. */
static void chute_drop(Game *g, Flier *f, int32_t x)
{
    flier_init(f, x, FL_PX(FLIER_START_JOIN_Y), FLIER_START_BALLOONS, 1);
    f->state = FLIER_PARACHUTE;
    flier_spawn_protect(f);
    flier_set_hazard(f, g->hazard_kind);
}

/* World x of the screen centre, wrapped into the arena. */
static int32_t camera_centre_x(const Game *g)
{
    int32_t x = g->camera.cam + (int32_t)(SCREEN_W / 2) * 65536;
    while (x >= ARENA_W16) x -= ARENA_W16;
    return x;
}

/* P2 Start in play (a credit was taken): fresh lives, and hero[1] drops in on its parachute from the top at the camera centre.
 * Returns 0 when refused (the caller keeps the credit). */
int game_join_p2(Game *g)
{
    if (!game_can_join_p2(g)) return 0;
    if (g->mode == GAME_MODE_ARENA) return 0; /* Arena joins through flow_join_p2: a fresh match */
    g->players = 2;
    arc_lives_start(&g->lives[1]);
    chute_drop(g, &g->hero[1], camera_centre_x(g));
    return 1;
}

void game_set_hazard(Game *g, uint8_t kind)
{
    int i;
    g->hazard_kind = kind;
    for (i = 0; i < HUMANS; i++) {
        flier_set_hazard(&g->hero[i], kind);
    }
    for (i = 0; i < STAGE_SPAWN_COUNT; i++) {
        flier_set_hazard(&g->cpu[i], kind);
    }
}

void game_reset(Game *g, uint32_t seed)
{
    uint8_t mood = g->mood < GAME_MOOD_COUNT ? g->mood : GAME_MOOD_MOON; /* boot: the Game holds no valid mood yet */
    zero(g, sizeof(*g));
    g->mood = mood;
    rng_seed(&g->rng, seed);
    camera_init(&g->camera);
    trip_init(&g->trip);
    stage_select(0);
    stage_set_level(0);
    g->players = 1;
    flier_init(&g->hero[1], 0, 0, 0, 0); /* player 2 slot: GONE until a join (Phase 1 and later) */
    g->hero[1].state = FLIER_GONE;
    flier_set_hazard(&g->hero[1], g->hazard_kind);
    player_spawn(g);
}

void game_set_mode(Game *g, uint8_t mode)
{
    g->party_rule = PARTY_NONE;
    g->roost.last = 0xFF;
    g->mode = mode == GAME_MODE_TRIP || mode == GAME_MODE_ARCADE ? mode : GAME_MODE_ARENA;
    if (g->mode == GAME_MODE_ARCADE) {
        arc_start(&g->arc);
        arc_lives_start(&g->lives[0]); /* the arena step builds stage 1 at its first frame (match_start) */
        g->lives[1].state = ARC_LIFE_ENDED; /* player 2 is out until a join */
    }
    if (g->mode == GAME_MODE_TRIP) {
        flier_init(&g->hero[0], FL_PX(TRIP_START_X), FL_PX(TRIP_START_Y), 2, 0);
        flier_spawn_protect(&g->hero[0]);
        flier_set_hazard(&g->hero[0], g->hazard_kind);
        g->hero[0].solid_kill = 0; /* Gum Trip draws no spike strip: the dead body just falls */
        g->hero[0].no_wrap = 1;
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

static void match_start(Game *g);
int game_begin(Game *g)
{
    if (g->mode == GAME_MODE_TRIP || g->over || g->cpu_count) return 0;
    match_start(g);
    return 1;
}

/* Fighter i: 0..players-1 are the humans in play (a slot beyond players takes no part), then the computer fliers (cpu_count of them). */
static Flier *fighter(Game *g, int i)
{
    return i < g->players ? &g->hero[i] : &g->cpu[i - g->players];
}

/* Score add: the arcade clamps at SCORE_CAP (FQ10), the other modes add as before. */
static void score_add(Game *g, uint32_t pts)
{
    if (g->party_rule == PARTY_ROOST && !g->roost.paying) return; /* Roost Rule: only the roost ticks score */
    g->score = g->mode == GAME_MODE_ARCADE ? arc_score_add(g->score, pts) : g->score + pts;
}

/* Score of human h: player 1 keeps the Game total, player 2 its own lives[1].score (arcade only). */
static void score_add_h(Game *g, int h, uint32_t pts)
{
    if (h == 0) score_add(g, pts);
    else if (g->party_rule == PARTY_ROOST && !g->roost.paying) return;
    else g->lives[h].score = arc_score_add(g->lives[h].score, pts);
}

/* ArcPump of fighter index i (a human never pumps: a window-less static). */
static const ArcPump *pump_of(const Game *g, int i)
{
    static const ArcPump none = { ARC_PUMP_IDLE, 1, 0, 0 };
    return i >= g->players ? &g->pump[i - g->players] : &none;
}

/* Human h touched a pumping rival: pop it at once (all gum, even through the pop protection) and pay its window defeat to h. */
static void pump_defeat(Game *g, int h, Flier *v, ArcPump *p)
{
    uint32_t win = arc_pump_resolve(p);
    v->invincible = 0;
    v->spawn_inv = 0;
    v->has_parachute = 0; /* a window defeat is a defeat: no arcade parachute on the way down */
    while (flier_lose_balloon(v)) {
        v->invincible = 0;
    }
    if (v->state == FLIER_ALIVE) flier_start_falling(v); /* grounded: popping leaves it standing, and the body pass would pay the defeat twice */
    g->stomps++;
    g->last_popper = (uint8_t)h;
    score_add_h(g, h, g->mode == GAME_MODE_ARCADE ? win : SCORE_CPU_DEFEAT);
}

void game_next_mood(Game *g)
{
    uint32_t m = (uint32_t)g->mood + 1;
    if (GAME_MOOD_COUNT > 2) {
        m += rng_range(&g->rng, GAME_MOOD_COUNT - 1);
    }
    if (m >= GAME_MOOD_COUNT) { /* m < 2 * GAME_MOOD_COUNT: one subtract wraps, no % */
        m -= GAME_MOOD_COUNT;
    }
    g->mood = (uint8_t)m;
}

/* Rule of the Round: this round's twist, drawn from the game Rng and never the one just played. */
static void twist_draw(Game *g)
{
    int first = g->twist == TWIST_NONE; /* no previous twist: all TWIST_COUNT-1 are open, otherwise skip the previous one */
    uint8_t t = (uint8_t)(1 + rng_range(&g->rng, (uint32_t)(TWIST_COUNT - (first ? 1 : 2))));
    if (!first && t >= g->twist) t++;
    g->twist = t;
}

static void roost_pick(Game *g);
static void match_start(Game *g)
{
    int arcade = g->mode == GAME_MODE_ARCADE;
    int rank = arcade ? arc_rank_for(g->arc.stage, g->arc.loops) : 1;
    int ai_rank = rank;
    int h;
    int n = CPU_START_COUNT + (int)g->matches_won;
    int i;
    if (n > CPU_MAX) {
        n = CPU_MAX;
    }
    if (arcade) {
        stage_select(arc_stage_layout(g->arc.stage));
        stage_set_level(world_get(world_of_stage(g->arc.stage))->look); /* arcade: the stage block's world (world.h) */
        g->mood = world_get(world_of_stage(g->arc.stage))->mood;
        n = stage_rival_count(); /* the layout's own rival count (ROT3b) */
        arc_elements_init(&g->elems, g->arc.stage - 1);
    } else {
        if (g->rounds) {
            stage_select((int)(g->matches_won % (uint32_t)stage_layout_count())); /* round start: the pan has ended, the screen is frozen under ROUND nn */
            stage_set_level((int)g->matches_won);
        }
        game_next_mood(g); /* arena: each part varies on its own (world.h) */
    }
    if (g->party_rule == PARTY_ROUND) {
        twist_draw(g);
        if (g->twist == TWIST_CROWDED) n = CPU_MAX;
        if (g->twist == TWIST_SLOW) ai_rank = PARTY_SLOW_RANK;
        if (g->twist == TWIST_QUICK) ai_rank = PARTY_QUICK_RANK;
        for (h = 0; h < g->players; h++) {
            if (g->twist == TWIST_ONE_GUM && g->hero[h].state != FLIER_GONE) g->hero[h].balloons = 1;
        }
    }
    g->cpu_count = (uint8_t)n;
    g->cpu_alive = (uint8_t)n;
    for (i = 0; i < STAGE_SPAWN_COUNT; i++) {
        if (i < n) {
            flier_init(&g->cpu[i], FL_PX(stage_spawns[i].x), FL_PX(stage_spawns[i].y), g->twist == TWIST_ONE_GUM ? 1 : FLIER_START_BALLOONS, g->mode == GAME_MODE_ARCADE); /* arcade: the last gum lost in the air opens a parachute (re-pump rule) */
            g->cpu[i].rival = 1;
            ai_init(&g->ai[i], &g->rng, ai_rank);
            arc_pump_start(&g->pump[i], rank, 1); g->pump[i].two = (uint8_t)(g->players == 2); /* every layout spawn stands just above a platform top */
        } else {
            flier_init(&g->cpu[i], 0, 0, 0, 0);
            g->cpu[i].state = FLIER_GONE;
        }
        flier_set_hazard(&g->cpu[i], g->hazard_kind);
    }
    if (g->party_rule == PARTY_ROOST) {
        roost_pick(g);
        g->ai[0].hold = 1; /* the first computer flier contests the island; the others fight as usual */
    }
    if (g->rounds) {
        g->round_start = RS_ROUND; /* round 1 and every round after the pan: ROUND nn, GO!, all frozen */
        g->round_start_timer = 0;
    }
}

/* x of the living human fliers in play; returns how many. */
static int human_xs(const Game *g, int32_t *humans)
{
    int n = 0, i;
    for (i = 0; i < g->players; i++) {
        if (g->hero[i].state < FLIER_DROWNED) {
            humans[n++] = g->hero[i].x;
        }
    }
    return n;
}

/* Co-op soft wall: with two humans alive, neither leaves the screen margins; velocity into the edge is zeroed. This is what
 * keeps the pair within one screen, so camera_step's arc-switch (an arc over 272 px cannot fit) never happens in play. */
static void coop_wall(Game *g)
{
    int h, live = 0;
    int32_t cam = (int32_t)camera_px(&g->camera) * 65536, lo = (int32_t)CAM_EDGE_MARGIN_PX * 65536, hi = (int32_t)(SCREEN_W - CAM_EDGE_MARGIN_PX) * 65536;
    for (h = 0; h < g->players; h++) live += g->hero[h].state < FLIER_DROWNED;
    if (live < 2) return;
    for (h = 0; h < g->players; h++) {
        Flier *f = &g->hero[h];
        int32_t r;
        if (f->state >= FLIER_DROWNED) continue;
        r = arena_near_x(cam + (int32_t)(SCREEN_W / 2) * 65536, f->x) - cam;
        if (r < lo) { if (f->vx < 0) f->vx = 0; f->x = arena_wrap_x(f->x + (lo - r)); }
        else if (r > hi) { if (f->vx > 0) f->vx = 0; f->x = arena_wrap_x(f->x - (r - hi)); }
    }
}

static void camera_follow(Game *g)
{
    int32_t humans[HUMANS];
    int n = human_xs(g, humans);
    camera_step(&g->camera, humans, n);
    coop_wall(g);
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

/* The party rule table: name, goal line (owner-approved 2026-11-16). Index = PARTY_*; twist names index = TWIST_*. */
static const char *const party_names[PARTY_RULE_COUNT] = { "", "RULE OF THE ROUND", "ROOST RULE", "HOT GUM", "HAZARD ROULETTE" };
static const char *const party_goals[PARTY_RULE_COUNT] = {
    "", "A NEW TWIST EVERY ROUND", "STAND ON THE GLOWING ISLAND TO SCORE", "PASS THE HOT GUM BEFORE IT POPS", "NEW HAZARD EVERY ROUND"
};
static const char *const twist_names[TWIST_COUNT] = { "", "ONE GUM EACH", "CROWDED SKY", "SLOW THINKERS", "QUICK THINKERS", "MIRROR STICK", "WINDY" };
const char *game_party_name(uint8_t rule) { return rule < PARTY_RULE_COUNT ? party_names[rule] : ""; }
const char *game_party_goal(uint8_t rule) { return rule < PARTY_RULE_COUNT ? party_goals[rule] : ""; }
const char *game_twist_name(uint8_t twist) { return twist < TWIST_COUNT ? twist_names[twist] : ""; }

/* One explanation line per twist for the round banner (owner decision 2026-11-16; text awaits owner approval). Max PARTY_GOAL_W. */
static const char *const twist_lines[TWIST_COUNT] = {
    "", "EVERY BIRD STARTS WITH ONE GUM", "MORE COMPUTER BIRDS IN THE SKY", "COMPUTER BIRDS REACT SLOWLY",
    "COMPUTER BIRDS REACT FAST", "LEFT AND RIGHT ARE SWAPPED", "A WIND PUSHES EVERY BIRD SIDEWAYS"
};
/* How-to overlay before round 1 of a PARTY match: three lines per rule, index = PARTY_*. */
static const char *const party_howto[PARTY_RULE_COUNT][3] = {
    { "", "", "" },
    { "POP THE OTHER BIRDS' GUM BUBBLES", "THE LAST BIRD FLYING WINS THE ROUND", "EVERY ROUND HAS A NEW TWIST" },
    { "STAND ALONE ON THE GLOWING ISLAND", "TO EARN POINTS WHILE YOU HOLD IT", "POP RIVALS OFF THE ISLAND" },
    { "ONE BIRD CARRIES THE HOT GUM", "PASS IT ON BEFORE IT POPS", "TOUCH ANOTHER BIRD TO PASS IT" },
    { "A NEW HAZARD ARRIVES REGULARLY", "DODGE IT AND POP YOUR RIVALS", "THE LAST BIRD FLYING WINS" }
};
const char *game_party_howto(uint8_t rule, int line) { return rule < PARTY_RULE_COUNT && line >= 0 && line < 3 ? party_howto[rule][line] : ""; }

const char *game_round_start_text(const Game *g, int line)
{
    if (g->party_rule != PARTY_NONE && g->mode == GAME_MODE_ARENA) {
        if (line == 0) return g->party_rule == PARTY_ROUND ? game_twist_name(g->twist) : game_party_name(g->party_rule);
        if (line == 1 && g->party_rule == PARTY_ROUND && g->twist < TWIST_COUNT) return twist_lines[g->twist];
        return line == 1 ? game_party_goal(g->party_rule) : 0;
    }
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
    if (g->twist == TWIST_WINDY && f->state == FLIER_ALIVE && !f->on_ground) { /* one add per flier; the push stops at the air speed cap, no drag to bound it */
        int32_t w = (g->matches_won & 1) ? -PARTY_WIND_ACCEL : PARTY_WIND_ACCEL;
        if (w > 0 ? f->vx < FLIER_TOP_AIR_SPEED : f->vx > -FLIER_TOP_AIR_SPEED) f->vx += w;
    }
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
    for (i = 0; i < g->players; i++) {
        const Flier *h = &g->hero[i];
        if (h->state == FLIER_ALIVE && h->balloons && !h->on_ground) arc_elements_note_low(&g->elems, (int)(h->x >> 16), (int)(h->y >> 16));
    }
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
static int round_phase_step(Game *g, uint8_t skip)
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
            int32_t humans[HUMANS];
            int n = human_xs(g, humans);
            if (camera_arrived(&g->camera, humans, n)) {
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
        if (g->round_start == RS_ROUND && g->party_rule != PARTY_NONE && skip) g->round_start_timer = PARTY_ROUND_START_TEXT_FRAMES; /* A or Start skips the party hold */
        if (g->round_start == RS_ROUND && g->round_start_timer >= (g->party_rule != PARTY_NONE ? PARTY_ROUND_START_TEXT_FRAMES : ROUND_START_TEXT_FRAMES)) {
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
static int arc_interlude(Game *g, uint8_t input, uint8_t a_edge)
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
            g->bonus_caught[0] = g->bonus_caught[1] = 0;
            stage_select(ARC_LAYOUT_BONUS); /* floor strip and nozzle tops; arc_enter_stage / match_start selects the next stage's layout */
            g->round_end = RE_NONE; /* ALL POPPED showed once; the bonus is announced by the round-start phase (BONUS STAGE, then GO) */
            if (g->rounds) {
                g->round_start = RS_ROUND;
                g->round_start_timer = 0;
            }
        } else if (started) {
            arc_enter_stage(g);
        }
    } else if (round_phase_step(g, 0)) {
        return 1; /* the bonus announcement: everything frozen */
    } else if (g->res.active) {
        uint32_t add;
        g->res.events = res_step(&g->res, &add, a_edge); /* main.c folds a Start press into A on this screen */
        if (add) {
            score_add(g, add);
            g->res.score_shown = g->score;
        }
        if (!g->res.active) {
            arc_bonus_done(&g->arc);
            arc_enter_stage(g);
        }
    } else {
        int h;
        uint8_t ins[HUMANS];
        ins[0] = input;
        ins[1] = g->input2;
        for (h = 0; h < g->players; h++) {
            Flier *f = &g->hero[h];
            int cx, cy, armed, n;
            if (h > 0 && g->lives[h].state != ARC_LIFE_PLAY) continue; /* a player out of lives or on the continue screen sits the bonus out */
            cx = (int)(f->x >> 16);
            cy = (int)(f->y >> 16);
            in.flap = (ins[h] & IN_A) ? 1 : 0;
            in.dir = (int8_t)(((ins[h] & IN_RIGHT) ? 1 : 0) - ((ins[h] & IN_LEFT) ? 1 : 0));
            arena_flier_step(g, f, &in);
            armed = f->state == FLIER_ALIVE && f->balloons > 0;
            /* the first human steps the bubbles, the partner only tests its box on the moved bubbles; each box credits its own catcher */
            n = h == 0 ? arc_bonus_step(&g->bonus, armed, cx - ARC_BONUS_CATCH_HALF_W, cy - ARC_BONUS_CATCH_HALF_H, 2 * ARC_BONUS_CATCH_HALF_W, 2 * ARC_BONUS_CATCH_HALF_H)
                       : arc_bonus_catch(&g->bonus, armed, cx - ARC_BONUS_CATCH_HALF_W, cy - ARC_BONUS_CATCH_HALF_H, 2 * ARC_BONUS_CATCH_HALF_W, 2 * ARC_BONUS_CATCH_HALF_H);
            g->bonus_caught[h] = (uint8_t)(g->bonus_caught[h] + n);
            if (f->state == FLIER_GONE) {
                player_spawn_h(g, h); /* a bonus stage costs no life */
            }
        }
        if (g->bonus.over) {
            int caught0 = g->players > 1 ? g->bonus_caught[0] : g->bonus.caught;
            res_start(&g->res, caught0, g->bonus.number, g->bonus.perfect, g->score); /* the result screen adds the score */
            if (g->players > 1) { /* player 2 is paid at once and shown as a second total */
                uint32_t pay = (uint32_t)g->bonus_caught[1] * g->res.each + g->res.bonus;
                g->lives[1].score = arc_score_add(g->lives[1].score, pay);
                g->res.two = 1;
                g->res.score2 = g->lives[1].score;
            }
        }
    }
    camera_follow(g);
    return 1;
}

/* ---- Roost Rule (PARTY_ROOST) ---- */

static int roost_centre_px(const StagePlatform *p) { return p->x + p->w / 2; }

/* Pick this round's roost (never the previous one while another platform exists) and aim the AI target mark at it. */
static void roost_pick(Game *g)
{
    int ok[STAGE_PLATFORM_COUNT], n = 0, i;
    for (i = 0; i < STAGE_PLATFORM_COUNT; i++) if (stage_platforms[i].w > 0 && i != g->roost.last) ok[n++] = i;
    if (n == 0) for (i = 0; i < STAGE_PLATFORM_COUNT; i++) if (stage_platforms[i].w > 0) ok[n++] = i;
    g->roost.idx = (uint8_t)ok[n > 1 ? (int)rng_range(&g->rng, (uint32_t)n) : 0];
    g->roost.last = g->roost.idx;
    g->roost.timer = ROOST_ROUND_FRAMES;
    g->roost.acc = 0;
    g->roost.sole = 0xFF;
    g->roost.paying = 0;
    for (i = 0; i < ROOST_FIGHTERS; i++) g->roost.ticks[i] = 0;
    flier_init(&g->roost.mark, FL_PX(roost_centre_px(&stage_platforms[g->roost.idx])), 0, FLIER_START_BALLOONS, 0);
    g->roost.mark.y = FL_PX(stage_platforms[g->roost.idx].y) - flier_half_h(&g->roost.mark);
}

int game_roost_rect(const Game *g, int *x, int *top, int *w)
{
    const StagePlatform *p;
    if (g->party_rule != PARTY_ROOST || g->mode != GAME_MODE_ARENA) return 0;
    p = &stage_platforms[g->roost.idx];
    *x = p->x; *top = p->y; *w = p->w;
    return 1;
}

/* f stands on the roost: alive on the ground, balloons up, over the platform's span, feet on its top. */
static int roost_stands(const Game *g, const Flier *f)
{
    const StagePlatform *p = &stage_platforms[g->roost.idx];
    int32_t feet = f->y + flier_half_h(f) - FL_PX(p->y);
    int dx = arena_dx((int)(f->x >> 16), roost_centre_px(p));
    return f->state == FLIER_ALIVE && f->on_ground && f->balloons > 0 && dx >= -p->w / 2 && dx <= p->w / 2 && feet >= -FL_PX(2) && feet <= FL_PX(2);
}

/* A popped or fallen fighter comes back by parachute (humans at the screen centre, computer fliers over their spawn point). */
static void roost_respawn(Game *g)
{
    int h, i;
    for (h = 0; h < g->players; h++) if (g->hero[h].state == FLIER_GONE) chute_drop(g, &g->hero[h], camera_centre_x(g));
    for (i = 0; i < g->cpu_count; i++) {
        if (g->cpu[i].state != FLIER_GONE) continue;
        chute_drop(g, &g->cpu[i], FL_PX(stage_spawns[i].x));
        g->cpu[i].rival = 1;
    }
}

static void roost_end(Game *g)
{
    int i, best = 0, tied = 0;
    for (i = 1; i < ROOST_FIGHTERS; i++) {
        if (g->roost.ticks[i] > g->roost.ticks[best]) { best = i; tied = 0; }
        else if (g->roost.ticks[i] == g->roost.ticks[best]) tied = 1;
    }
    if (tied || g->roost.ticks[best] == 0) g->round_winner = BANNER_DRAW;
    else g->round_winner = (uint8_t)(best < HUMANS ? (best == 0 ? BANNER_P1 : BANNER_P2) : BANNER_CPU);
    g->matches_won++;
    if (g->rounds) { g->round_end = RE_HOLD; g->round_timer = MATCH_END_FRAMES; }
    else { player_spawn(g); match_start(g); }
}

/* One frame of the rule after the fliers moved: respawns, the sole-stander tick, and the round end. */
static void roost_step(Game *g)
{
    int i, n = g->players + g->cpu_count, who = -1, stand = 0;
    roost_respawn(g);
    for (i = 0; i < n; i++) {
        if (roost_stands(g, fighter(g, i))) { stand++; who = i; }
    }
    if (stand == 1 && who == g->roost.sole) {
        if (++g->roost.acc >= ROOST_TICK_FRAMES) {
            int slot = who < g->players ? who : HUMANS + (who - g->players);
            g->roost.acc = 0;
            g->roost.ticks[slot]++;
            if (who < g->players) { g->roost.paying = 1; score_add_h(g, who, SCORE_ROOST_TICK); g->roost.paying = 0; }
        }
    } else {
        g->roost.sole = (uint8_t)(stand == 1 ? who : 0xFF);
        g->roost.acc = 0;
    }
    if (g->roost.timer > 0) g->roost.timer--;
    for (i = 0; i < ROOST_FIGHTERS; i++) if (g->roost.ticks[i] >= ROOST_TARGET_TICKS) break;
    if (i < ROOST_FIGHTERS || g->roost.timer == 0) roost_end(g);
}

void game_step_arena(Game *g, uint8_t input)
{
    FlierInput in;
    int i, j, n, h;
    uint8_t bodies;
    uint8_t ins[HUMANS], a_edge_h[HUMANS], start_edge_h[HUMANS];
    uint8_t a_edge, skip;
    ins[0] = input;
    ins[1] = g->input2;
    for (h = 0; h < g->players; h++) {
        a_edge_h[h] = (uint8_t)((ins[h] & IN_A) && !g->cont_a[h]);
        g->cont_a[h] = (ins[h] & IN_A) ? 1 : 0;
        start_edge_h[h] = (uint8_t)(g->start_in[h] && !g->cont_start[h]);
        g->cont_start[h] = g->start_in[h];
    }
    a_edge = a_edge_h[0];
    if (g->over) {
        camera_follow(g);
        return;
    }
    if (game_lives_mode(g)) {
        int cont = 0, frozen = 1;
        for (h = 0; h < g->players; h++) {
            cont |= g->lives[h].state == ARC_LIFE_CONTINUE;
            if (g->lives[h].state == ARC_LIFE_PLAY) frozen = 0;
        }
        if (cont) {
            /* Continue screen of a player: with no one else playing the world is frozen; a partner still playing plays on.
             * Start continues (owner 2026-11-15); each A press drops the count by one;
             * a continue needs a banked credit (g->credits); the countdown running out ends that player. */
            int all_out = 1;
            for (h = 0; h < g->players; h++) {
                if (g->lives[h].state != ARC_LIFE_CONTINUE) continue;
                if (arc_continue_step(&g->lives[h], start_edge_h[h], g->credits)) {
                    g->credits_spent++;
                    if (h == 0) g->score = g->lives[0].score;
                    if (g->mode == GAME_MODE_ARCADE) player_spawn_h(g, h); /* Arena versus: back in at the next round */
                } else if (a_edge_h[h]) {
                    arc_continue_skip(&g->lives[h]);
                }
            }
            for (h = 0; h < g->players; h++) all_out &= g->lives[h].state == ARC_LIFE_ENDED;
            if (all_out) g->over = 1; /* the run ends when every player is out */
            if (frozen) {
                camera_follow(g);
                return;
            }
        }
    }
    if (g->cpu_count == 0) {
        match_start(g);
    }
    for (h = 0, skip = 0; h < g->players; h++) skip |= (uint8_t)(a_edge_h[h] | start_edge_h[h]);
    if (arc_interlude(g, input, a_edge) || round_phase_step(g, skip)) {
        return;
    }
    g->frame++;
    if (g->mode == GAME_MODE_ARCADE) {
        arc_note_low_fliers(g);
        arc_elements_step(&g->elems);
    }
    for (h = 0; h < g->players; h++) {
        Flier *hf = &g->hero[h];
        if (hf->state == FLIER_GONE) continue; /* out of lives or waiting on its continue screen */
        in.flap = (ins[h] & IN_A) ? 1 : 0;
        in.dir = (int8_t)(((ins[h] & IN_RIGHT) ? 1 : 0) - ((ins[h] & IN_LEFT) ? 1 : 0));
        if (g->twist == TWIST_MIRROR) in.dir = (int8_t)-in.dir; /* play input only: flow and name entry never reach here */
        if (in.flap && !hf->flap_prev && hf->state < FLIER_DROWNED) {
            g->flaps[h]++;
        }
        arena_flier_step(g, hf, &in);
        if (g->mode == GAME_MODE_ARCADE) arc_element_apply(&g->elems, hf);
    }
    g->flier_steps++;
    for (i = 0; i < g->cpu_count; i++) {
        Flier *c = &g->cpu[i];
        FlierInput ci;
        uint8_t was = c->state;
        int pumping, sitting;
        if (c->state == FLIER_GONE) {
            continue;
        }
        pumping = arc_pump_in_window(&g->pump[i]);
        sitting = g->pump[i].state == ARC_PUMP_STANDING;
        if (sitting && c->state != FLIER_ALIVE) g->pump[i].state = ARC_PUMP_FLYING; /* killed while standing: no pump */
        g->pump[i].two = (uint8_t)(g->players == 2); /* a P2 join mid-stage speeds the running windows */
        arc_pump_step(&g->pump[i]);
        if (arc_pump_in_window(&g->pump[i]) && c->balloons < FLIER_START_BALLOONS) {
            /* Re-pump window (user decision 2026-11-16): the gum grows with the pump stages, one gum inside the window, the second
               only at window end (a stage-start window always holds full gum, so it never takes this branch). */
            if (c->balloons == 0) flier_add_balloon(c); /* one gum (never none: the player's touch needs gum to pop through pump_defeat) */
        }
        sitting = sitting || pumping;
        if (sitting) {
            ci.dir = 0; /* stands, then sits and pumps: no AI, no input until the window ends */
            ci.flap = 0;
        } else if (c->state <= FLIER_PARACHUTE) {
            ai_step(&g->ai[i], &g->rng, c, g->ai[i].hold ? &g->roost.mark : ai_nearest(c, g->hero, g->players, g->cpu, g->cpu_count), &ci);
            if (g->mode == GAME_MODE_ARCADE) {
                int away = arc_elements_avoid_dir(&g->elems, (int)(c->x >> 16), (int)(c->y >> 16), FLIER_HALF_W, (int)(flier_half_h(c) >> 16), c->vx);
                if (away) {
                    ci.dir = (int8_t)away;   /* a burst kills, an island underside only bumps: overrides the overhead-edge steer in ai.c */
                    /* Air steering only acts on a flap and the AI flaps only toward a target above, so a rival drifted into the plume
                       at constant vx: flap on every allowed press while threatened (sideways thrust away, and lift above the plume). */
                    if (c->flap_cd == 0 && !c->flap_prev) ci.flap = 1;   /* grounded too: the jump lifts a rival standing beside the vent */
                }
            }
        } else {
            ci.dir = 0;
            ci.flap = 0;
        }
        arena_flier_step(g, c, &ci);
        if (g->mode == GAME_MODE_ARCADE) arc_element_apply(&g->elems, c);
        if (pumping && !arc_pump_in_window(&g->pump[i])) {
            while (c->balloons < FLIER_START_BALLOONS && flier_add_balloon(c)) {} /* full gum at window end */
            c->vy = FLIER_GROUND_JUMP_VY; /* lift-off: one upward impulse, no sideways speed */
            c->vx = 0;
            c->on_ground = 0;
        }
        /* Arcade re-pump (user decision 2026-11-16): a rival standing alive with no gum (landed on its parachute, or popped
           while standing) waits ARC_REPUMP_STAND_FRAMES, then pumps the stage-start window at the same rank. */
        if (g->mode == GAME_MODE_ARCADE && c->state == FLIER_ALIVE && c->on_ground && c->balloons == 0 && arc_pump_restand(&g->pump[i])) c->vx = 0; /* stands still */
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
    n = g->players + g->cpu_count;
    {
        Flier *f[HUMANS + STAGE_SPAWN_COUNT];
        int32_t hx[HUMANS + STAGE_SPAWN_COUNT];
        uint8_t near[HUMANS + STAGE_SPAWN_COUNT];      /* pairs within contact reach; one bit per fighter, so at most 8 */
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
                        if (i < g->players) {
                            pump_defeat(g, i, f[j], &g->pump[j - g->players]);
                        }
                        continue;
                    }
                    /* Computer fliers never pop each other (BR-D3): a gum-on-gum contact between two of them is a bounce.
                       flier_pair stays pure; the rule lives here, where the indices say who is the player. (In Gum Trip
                       the rivals never meet each other, so this is arena only.) */
                    if (i >= g->players && j >= g->players && (act == FLP_POP_A || act == FLP_POP_B)) act = FLP_BOUNCE;
                    if (act == FLP_BOUNCE) {
                        flier_pair_apply(f[i], f[j], act);
                        g->bounces++;
                        continue;
                    }
                    if (flier_pair_apply(f[i], f[j], act)) {
                        g->stomps++;
                        if (popper < g->players && popped_idx >= g->players) {
                            g->last_popper = (uint8_t)popper;
                            /* Points only for the player's own pops on a computer flier (design 3.3), to the popper's own score; a partner stomp pays nothing. */
                            if (g->mode == GAME_MODE_ARCADE) {
                                const ArcRank *rk = arc_rank(g->pump[popped_idx - g->players].rank);
                                score_add_h(g, popper, rk->pop_score + ((was_up && v->state > FLIER_PARACHUTE) ? rk->defeat_score : 0));
                            } else {
                                score_add_h(g, popper, SCORE_STOMP_POP);
                                score_add_h(g, popper, (was_up && v->state > FLIER_PARACHUTE) ? SCORE_CPU_DEFEAT : 0);
                            }
                        } else if (popper < g->players && g->mode == GAME_MODE_ARENA) { /* versus: a human stomp scores like a computer stomp */
                            g->last_popper = (uint8_t)popper;
                            score_add_h(g, popper, SCORE_STOMP_POP);
                            score_add_h(g, popper, (was_up && v->state > FLIER_PARACHUTE) ? SCORE_CPU_DEFEAT : 0);
                        }
                    }
                }
            }
        }
        for (i = 0; i < n; i++) {
            for (j = 0; j < n; j++) {
                if (near[i] & (1u << j)) {
                    int killed;
                    if (i < g->players && j < g->players) continue; /* partners never body-kill each other */
                    killed = flier_body_touching(f[i], f[j]) && !arena_pair_blocked(f[i], f[j]) && flier_body_kill(f[i], f[j]);
                    if (killed && j < g->players && i >= g->players) {
                        g->last_popper = (uint8_t)j;
                        score_add_h(g, j, g->mode == GAME_MODE_ARCADE ? arc_rank(g->pump[i - g->players].rank)->defeat_score : SCORE_CPU_DEFEAT); /* the player's body touched a balloon-less computer flier */
                    }
                }
            }
        }
    }
    if (g->party_rule == PARTY_ROOST) { roost_step(g); camera_follow(g); return; } /* Roost Rule: no lives, no last-flier win */
    g->cpu_alive = 0;
    bodies = 0;
    for (i = 0; i < g->cpu_count; i++) {
        g->cpu_alive = (uint8_t)(g->cpu_alive + (g->cpu[i].state < FLIER_DROWNED ? 1 : 0));
        bodies = (uint8_t)(bodies + (g->cpu[i].state == FLIER_DROWNED ? 1 : 0));
    }
    {
        int up = 0, alive = 0; /* humans on the stage before this frame's life loss handling */
        int versus = g->mode == GAME_MODE_ARENA && g->players == 2;
        int settled = 1, win = 0, cpu_up = 0;
        for (h = 0; h < g->players; h++) {
            if (g->hero[h].state != FLIER_GONE) {
                up++;
                alive += g->hero[h].state < FLIER_FALLING;
                if (g->hero[h].state >= FLIER_FALLING) settled = 0;
            }
        }
        for (h = 0; h < g->players; h++) {
            if (g->hero[h].state != FLIER_GONE) continue;
            if (g->mode == GAME_MODE_ARCADE) {
                arc_lose_life(&g->lives[h]); /* no-op for a player already out of play */
                if (g->lives[h].state == ARC_LIFE_PLAY) {
                    player_spawn_h(g, h); /* next life on the same stage */
                }   /* else the continue screen runs from the next step (top of this function) */
            } else if (versus) { /* one life per death; the human waits for the next round */
                if (!(g->out_mask & (1u << h))) { g->out_mask |= (uint8_t)(1u << h); arc_lose_life(&g->lives[h]); }
            } else {
                g->over = 1; /* the dead hero has left the screen: the run ends now, not at the kill */
            }
        }
        if (versus) { /* the round ends when one flier is left, computer fliers counted (or no human is left) */
            for (i = 0; i < g->cpu_count; i++) {
                cpu_up += g->cpu[i].state < FLIER_FALLING;
                if (g->cpu[i].state >= FLIER_FALLING && g->cpu[i].state < FLIER_DROWNED) settled = 0;
            }
            win = settled && bodies == 0 && (alive == 0 || alive + cpu_up <= 1);
            if (win) g->round_winner = (uint8_t)(alive == 0 ? (cpu_up ? BANNER_CPU : BANNER_DRAW) : cpu_up ? BANNER_CPU : (g->hero[0].state < FLIER_FALLING ? BANNER_P1 : BANNER_P2));
        }
        if (up > 0 || versus) { /* the partner of a lost player plays on */
            g->distance += SPEED_BASE;
            /* the match is won when no computer flier lives and the last hazard body has left the screen (cpu_alive counts FALLING bodies as alive) */
            if (versus ? win : (g->cpu_alive == 0 && bodies == 0 && alive > 0)) {
                g->matches_won++;
                if (g->mode == GAME_MODE_ARCADE) {
                    arc_stage_cleared(&g->arc); /* arc_interlude runs the CLEAR frames and the bonus stage from the next frame */
                }
                for (h = 0; h < g->players; h++) {
                    if (g->hero[h].state >= FLIER_FALLING) continue; /* only a human alive at the clear collects the match bonus */
                    score_add_h(g, h, SCORE_MATCH_WIN);
                    if (g->hero[h].balloons >= FLIER_START_BALLOONS) {
                        score_add_h(g, h, SCORE_MATCH_CLEAN); /* no balloon lost in the match: the player cannot gain any in play */
                    }
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
    int was_alive;
    if (g->over) {
        g->trip_events = 0; /* no stale TRIP_EV_HIT for the sound edge */
        g->trip_splat = 0;
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
    if (in.flap && !g->hero[0].flap_prev && g->hero[0].state < FLIER_DROWNED) {
        g->flaps[0]++;
    }
    g->hero[0].no_wrap = 1;
    was_alive = g->hero[0].state < FLIER_FALLING;
    {
        int32_t px = g->hero[0].x, py = g->hero[0].y;
        FlierSolid so[TRIP_SOLIDS_MAX];
        flier_step(&g->hero[0], &in, trip_hit_floor_y(&g->trip, &g->trip_gen, &g->hero[0]));
        flier_collide_solids(&g->hero[0], px, py, so, trip_hit_solids(&g->trip, &g->trip_gen, &g->hero[0], so, TRIP_SOLIDS_MAX));
    }
    g->flier_steps++;
    step = g->trip.speed; /* the step trip_step scrolls by this frame */
    trip_step(&g->trip, &g->hero[0]);
    tripgen_advance(&g->trip_gen, g->trip.px);
    /* Walls first (hero: the bottom and the top rock both kill), so the strip hit test below never sees the hero inside the
     * rock; then the hazard hit (gum loss, cooldown), the push-out and bounce off the hazard, and the walls again (a push into
     * the rock is a wall touch). A wall kill plays the hit sound like a hazard hit (TRIP_EV_HIT); only the bottom rock is a
     * floor death: a roof death splats when the falling body reaches the floor line (trip_roof_fall); a mid-air gum death
     * makes no splat. */
    {
        unsigned side = trip_hit_hero_walls(&g->trip, &g->trip_gen, &g->hero[0]);
        unsigned ev = side ? TRIP_EV_HIT : 0u;
        int floor_kill = side == TRIP_WALL_BOTTOM, roof_kill = side == TRIP_WALL_TOP;
        int32_t lo, hi;
        ev |= trip_collide(&g->trip, &g->trip_gen, &g->hero[0]);
        trip_hit_haz_bounce(&g->trip, &g->trip_gen, &g->hero[0]);
        side = trip_hit_hero_walls(&g->trip, &g->trip_gen, &g->hero[0]);
        if (side) ev |= TRIP_EV_HIT;
        floor_kill |= side == TRIP_WALL_BOTTOM;
        roof_kill |= side == TRIP_WALL_TOP;
        g->trip_events = (uint8_t)ev;
        /* a death at the floor: the bottom rock, or the kill line reached alive (DROWNED); a mid-air gum death falls on and makes no splat */
        g->trip_splat = (uint8_t)(was_alive && g->hero[0].state >= FLIER_FALLING && (floor_kill || g->hero[0].state == FLIER_DROWNED));
        if (was_alive && g->hero[0].state == FLIER_FALLING && roof_kill && !floor_kill) {
            g->trip_roof_fall = 1;   /* a roof death splats later, where the falling body reaches the floor line (owner 2026-11-15) */
        } else if (g->trip_roof_fall) {
            /* the floor line is the floor-death line (window hi): the first frame below it is the landing, splat placed as a floor death */
            if (g->hero[0].state != FLIER_FALLING) g->trip_roof_fall = 0;
            else if (trip_hit_window(&g->trip, &g->trip_gen, &g->hero[0], &lo, &hi) && g->hero[0].y > hi) g->trip_splat = 1, g->trip_roof_fall = 0;
        }
        g->trip_splat_y = (int16_t)((g->hero[0].y + flier_half_h(&g->hero[0])) >> 16);
    }
    g->trip_rival_events = (uint8_t)trip_rivals_step(&g->trip_rivals, &g->trip, &g->trip_gen, &g->hero[0]);
    camera_scroll(&g->camera, step);
    g->distance = g->trip.px;
    g->score = trip_score(&g->trip);
    g->over = (uint8_t)trip_over(&g->hero[0]);
}
