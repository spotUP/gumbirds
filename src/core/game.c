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

#define SPAWN_W_TOTAL (SPAWN_W_VENT + SPAWN_W_CABLE + SPAWN_W_DRONE + SPAWN_W_BOT)

static int32_t speed_for(uint32_t distance)
{
    uint32_t px = distance >> 8;
    uint32_t add = px / SPEED_RAMP_PX;
    uint32_t sp = (uint32_t)SPEED_BASE + add;
    if (sp > (uint32_t)SPEED_MAX) {
        sp = (uint32_t)SPEED_MAX;
    }
    return (int32_t)sp;
}

static uint16_t gap_for(Game *g)
{
    uint32_t px = g->distance >> 8;
    uint32_t cut = px / GAP_RAMP_PX;
    uint32_t base = (uint32_t)GAP_START;
    if (cut >= base || base - cut < (uint32_t)GAP_END) {
        base = (uint32_t)GAP_END;
    } else {
        base -= cut;
    }
    return (uint16_t)(base + rng_range(&g->rng, GAP_JITTER));
}

void game_reset(Game *g, uint32_t seed)
{
    zero(g, sizeof(*g));
    rng_seed(&g->rng, seed);
    g->lives = LIVES_START;
    g->speed = speed_for(0);
    g->next_gap = gap_for(g);
    flier_init(&g->flier, FL_PX(FLIER_START_X), FL_PX(FLIER_START_Y), FLIER_START_BALLOONS, 0);
}

void game_step_arena(Game *g, uint8_t input)
{
    FlierInput in;
    if (g->over) {
        return;
    }
    g->frame++;
    in.flap = (input & IN_A) ? 1 : 0;
    in.dir = (int8_t)(((input & IN_RIGHT) ? 1 : 0) - ((input & IN_LEFT) ? 1 : 0));
    if (in.flap && !g->flier.flap_prev && g->flier.state < FLIER_DROWNED) {
        g->flaps++;
    }
    flier_step(&g->flier, &in, stage_floor_y(g->flier.x, g->flier.y + flier_half_h(&g->flier)));
    g->flier_steps++;
    if (g->flier.state >= FLIER_DROWNED) {
        g->over = 1;
    } else {
        g->distance += SPEED_BASE;
    }
    g->score = (g->distance >> (8 + DIST_SHIFT)) + g->bonus;
}

void game_hero_box(const Game *g, int *x, int *y, int *w, int *h)
{
    int bh = g->ducking ? HERO_DUCK_H : HERO_H;
    *x = HERO_X;
    *w = HERO_W;
    *h = bh;
    *y = GROUND_Y - (int)(g->hero_h >> 8) - bh;
}

uint32_t game_multiplier(const Game *g)
{
    uint32_t m = 1u;
    if (g->chain_timer > 0) {
        m = 1u + g->chain;
    }
    return m > (uint32_t)CHAIN_MAX ? (uint32_t)CHAIN_MAX : m;
}

static int overlap(int ax, int ay, int aw, int ah, int bx, int by, int bw, int bh)
{
    return ax < bx + bw && bx < ax + aw && ay < by + bh && by < ay + ah;
}

static void spawn(Game *g)
{
    int i;
    uint32_t r;
    Obstacle *o = 0;
    for (i = 0; i < MAX_OBSTACLES; i++) {
        if (!g->obs[i].active) {
            o = &g->obs[i];
            break;
        }
    }
    r = rng_range(&g->rng, SPAWN_W_TOTAL);
    if (!o) {
        return; /* pool full: skip this spawn */
    }
    zero(o, sizeof(*o));
    o->active = 1;
    o->x = (int32_t)SCREEN_W << 8;
    if (r < (uint32_t)SPAWN_W_VENT) {
        o->type = OB_VENT; o->w = VENT_W; o->h = VENT_H; o->y = GROUND_Y - VENT_H;
    } else if (r < (uint32_t)(SPAWN_W_VENT + SPAWN_W_CABLE)) {
        o->type = OB_CABLE; o->w = CABLE_W; o->h = CABLE_H; o->y = GROUND_Y - CABLE_BOTTOM - CABLE_H;
    } else if (r < (uint32_t)(SPAWN_W_VENT + SPAWN_W_CABLE + SPAWN_W_DRONE)) {
        o->type = OB_DRONE; o->w = DRONE_W; o->h = DRONE_H; o->y = GROUND_Y - DRONE_BOTTOM - DRONE_H;
    } else {
        o->type = OB_BOT; o->w = BOT_W; o->h = BOT_H; o->y = GROUND_Y - BOT_H;
    }
    g->spawned++;
}

static void fire(Game *g)
{
    int i, hx, hy, hw, hh;
    for (i = 0; i < MAX_BOLTS; i++) {
        if (!g->bolts[i].active) {
            game_hero_box(g, &hx, &hy, &hw, &hh);
            g->bolts[i].active = 1;
            g->bolts[i].x = (int32_t)(hx + hw) << 8;
            g->bolts[i].y = (int16_t)(hy + LASER_Y_OFFSET);
            g->shots++;
            g->heat += HEAT_PER_SHOT;
            g->fire_cd = LASER_FIRE_INTERVAL;
            if (g->heat >= HEAT_MAX) {
                g->heat = HEAT_MAX;
                g->lockout = LOCKOUT_FRAMES;
                g->overheats++;
            }
            return;
        }
    }
    /* Pool full: no shot, no heat. */
}

static void step_laser(Game *g, uint8_t input)
{
    int i;
    if (g->lockout > 0) {
        g->lockout--;
        if (g->lockout == 0) {
            g->heat = 0;
        }
    } else {
        g->heat = g->heat > HEAT_COOL ? (uint16_t)(g->heat - HEAT_COOL) : 0;
    }
    if (g->fire_cd > 0) {
        g->fire_cd--;
    }
    if ((input & IN_A) && g->lockout == 0 && g->fire_cd == 0) {
        fire(g);
    }
    for (i = 0; i < MAX_BOLTS; i++) {
        Bolt *b = &g->bolts[i];
        if (b->active) {
            b->x += LASER_SPEED;
            if ((b->x >> 8) >= SCREEN_W) {
                b->active = 0;
            }
        }
    }
    if (g->chain_timer > 0) {
        g->chain_timer--;
        if (g->chain_timer == 0) {
            g->chain = 0;
        }
    }
}

static void kill_enemy(Game *g)
{
    if (g->chain_timer > 0) {
        if (g->chain < 255) {
            g->chain++;
        }
    } else {
        g->chain = 0;
    }
    g->bonus += (uint32_t)KILL_SCORE * game_multiplier(g);
    g->chain_timer = CHAIN_WINDOW;
    g->kills++;
}

void game_step(Game *g, uint8_t input)
{
    int i, j, hx, hy, hw, hh;
    uint8_t pressed;

    if (g->over) {
        return;
    }
    g->frame++;
    pressed = (uint8_t)(input & (uint8_t)~g->prev_in);
    g->prev_in = input;

    /* Hero: jump on B press from the floor, duck on C held while on the floor. */
    if (g->hero_h == 0 && g->hero_vy == 0) {
        g->ducking = (input & IN_C) ? 1 : 0;
        if ((pressed & IN_B) && !g->ducking) {
            g->hero_vy = JUMP_VEL;
        }
    }
    if (g->hero_vy != 0 || g->hero_h > 0) {
        g->hero_h += g->hero_vy;
        g->hero_vy -= GRAVITY;
        if (g->hero_h <= 0) {
            g->hero_h = 0;
            g->hero_vy = 0;
        }
    }
    if (g->invuln > 0) {
        g->invuln--;
    }

    /* Difficulty ramp and scrolling. */
    g->speed = speed_for(g->distance);
    g->distance += (uint32_t)g->speed;
    g->spawn_acc += (uint32_t)g->speed;
    if (g->spawn_acc >= ((uint32_t)g->next_gap << 8)) {
        g->spawn_acc -= (uint32_t)g->next_gap << 8;
        spawn(g);
        g->next_gap = gap_for(g);
    }
    for (i = 0; i < MAX_OBSTACLES; i++) {
        Obstacle *o = &g->obs[i];
        if (!o->active) {
            continue;
        }
        o->x -= g->speed;
        if (o->type == OB_DRONE || o->type == OB_BOT) {
            o->x -= ENEMY_EXTRA_SPEED;
        }
        if ((o->x >> 8) + o->w < 0) {
            o->active = 0;
        }
    }

    step_laser(g, input);

    /* Bolts against enemies. Vents and cables do not stop bolts. */
    for (i = 0; i < MAX_BOLTS; i++) {
        Bolt *b = &g->bolts[i];
        if (!b->active) {
            continue;
        }
        for (j = 0; j < MAX_OBSTACLES; j++) {
            Obstacle *o = &g->obs[j];
            if (o->active && (o->type == OB_DRONE || o->type == OB_BOT) &&
                overlap(b->x >> 8, b->y, LASER_W, LASER_H, o->x >> 8, o->y, o->w, o->h)) {
                o->active = 0;
                b->active = 0;
                g->kill_x = (int16_t)((o->x >> 8) + o->w / 2);
                g->kill_y = (int16_t)(o->y + o->h / 2);
                g->kill_frame = g->frame;
                kill_enemy(g);
                break;
            }
        }
    }

    /* Hero against obstacles, then near-miss bookkeeping. */
    game_hero_box(g, &hx, &hy, &hw, &hh);
    for (i = 0; i < MAX_OBSTACLES; i++) {
        Obstacle *o = &g->obs[i];
        int ox, touching;
        if (!o->active) {
            continue;
        }
        ox = o->x >> 8;
        touching = overlap(hx, hy, hw, hh, ox, o->y, o->w, o->h);
        if (touching) {
            if (g->invuln > 0) {
                o->tainted = 1;
            } else {
                o->active = 0;
                g->hits++;
                g->chain = 0;
                g->chain_timer = 0;
                if (g->lives > 0) {
                    g->lives--;
                }
                if (g->lives == 0) {
                    g->over = 1;
                    break;
                }
                g->invuln = INVULN_FRAMES;
            }
            continue;
        }
        if (overlap(hx, hy, hw, hh, ox - NEAR_MISS_PX + 1, o->y - NEAR_MISS_PX + 1,
                    o->w + 2 * (NEAR_MISS_PX - 1), o->h + 2 * (NEAR_MISS_PX - 1))) {
            o->near = 1;
        }
        if (ox + o->w <= hx) {
            /* Fully behind the hero: dodged. */
            if (o->near && !o->tainted && g->invuln == 0) {
                g->bonus += NEAR_MISS_BONUS;
                g->near_misses++;
            }
            o->active = 0;
        }
    }

    g->score = (g->distance >> (8 + DIST_SHIFT)) + g->bonus;
}
