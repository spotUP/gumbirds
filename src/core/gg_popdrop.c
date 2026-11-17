#include "gg_popdrop.h"
#include "arena.h"
#include "game.h"       /* IN_C */
#include "nameentry.h"  /* IN_LEFT, IN_RIGHT */

static void place(GgPop *p, Flier *hero, Flier *target)
{
    int dir = (p->drop & 1u) ? -1 : 1;                 /* odd drops come from the right and drift left */
    flier_init(hero, GP_HERO_X, GP_HERO_Y, 0, 1);
    hero->state = FLIER_PARACHUTE;
    flier_init(target, arena_wrap_x(GP_HERO_X - dir * FL_PX(GP_START_DX)), GP_TARGET_Y, 1, 0);
    target->rival = 1;
    target->vx = dir * GP_DRIFT;
    p->phase = GP_HANG; p->timer = 0;
}

void gp_init(GgPop *p, Flier *hero, Flier *target)
{
    p->drop = 0; p->pops = 0; p->prev_in = 0; p->done = 0; p->end_t = 0;
    p->last_pop = 0; p->last_off = 0; p->total = 0; p->last_score = 0;
    place(p, hero, target);
}

static void drop_end(GgPop *p, int popped, int off)
{
    p->last_pop = (uint8_t)popped;
    p->last_off = (uint8_t)off;
    p->last_score = popped ? (uint16_t)(off < GP_RING ? GP_RING - off : 1) : 0;
    p->total = (uint16_t)(p->total + p->last_score);
    p->pops = (uint8_t)(p->pops + popped);
    p->phase = GP_PAUSE; p->timer = 0;
}

int gp_step(GgPop *p, Flier *hero, Flier *target, uint8_t in)
{
    FlierInput fi;
    uint8_t edge = (uint8_t)(in & ~p->prev_in);
    p->prev_in = in;
    fi.dir = (int8_t)(((in & IN_RIGHT) ? 1 : 0) - ((in & IN_LEFT) ? 1 : 0));
    fi.flap = 0;
    if (p->phase == GP_RESULT) { if (++p->end_t >= GP_RESULT_FRAMES) p->done = 1; return 0; }
    if (target->state == FLIER_ALIVE) target->x = arena_wrap_x(target->x + target->vx);   /* fixed drift, no physics */
    else flier_step(target, &fi, FLIER_NO_FLOOR);                                          /* popped: it falls */
    if (p->phase == GP_HANG) {
        flier_step(hero, &fi, FLIER_NO_FLOOR);                                             /* parachute sway; the stick steers the chute */
        if ((edge & IN_C) || ++p->timer >= GP_HANG_MAX) {                                  /* cut: a plain fall, sway velocity dropped */
            hero->state = FLIER_ALIVE; hero->has_parachute = 0; hero->vy = 0; hero->vx = 0;
            p->phase = GP_FALL;
        }
    } else if (p->phase == GP_FALL) {
        hero->vx = fi.dir * GP_NUDGE;
        flier_step(hero, &fi, FLIER_NO_FLOOR);
        if (flier_stomp(hero, target)) {
            int32_t dx = arena_near_x(target->x, hero->x) - target->x;
            drop_end(p, 1, (int)((dx < 0 ? -dx : dx) >> 16));
        } else if (hero->y >= GP_MISS_Y) {
            drop_end(p, 0, 0);
        }
    } else if (++p->timer >= GP_PAUSE_FRAMES) {
        if (++p->drop >= GP_DROPS) { p->phase = GP_RESULT; p->end_t = 0; return 1; }
        place(p, hero, target);
    }
    return 0;
}
