#include "gg_flapdash.h"
#include "arena.h"
#include "game.h"

void gumdash_init(GgDash *d, Flier *hero)
{
    d->mash.last = 0; d->mash.count = 0;
    d->prev_in = 0; d->laps = 0; d->done = 0; d->frames = 0; d->lap_dist = 0;
    flier_init(hero, 0, GD_FLOOR_Y, 2, 0);
    hero->y = GD_FLOOR_Y - FL_PX(16);
}

int gumdash_step(GgDash *d, Flier *hero, uint8_t in)
{
    FlierInput fi;
    int32_t step;
    if (d->done) return 0;
    fi.dir = 1;                                   /* the thrust needs a direction held (tuning.h); the dash runs rightward only */
    fi.flap = (uint8_t)gg_mash_step(&d->mash, in, d->prev_in);
    d->prev_in = in;
    flier_step(hero, &fi, GD_FLOOR_Y);
    if (hero->vx > GD_MAX_VX) {                   /* undo the excess so x and vx agree on the clamped speed */
        hero->x = arena_wrap_x(hero->x - (hero->vx - GD_MAX_VX));
        hero->vx = GD_MAX_VX;
    }
    d->frames++;
    step = hero->vx > 0 ? hero->vx : 0;
    d->lap_dist += step;
    if (d->lap_dist >= ARENA_W16) {
        d->lap_dist -= ARENA_W16;
        if (++d->laps >= GD_LAPS) { d->done = 1; return 1; }
    }
    return 0;
}

uint32_t gumdash_mark(uint32_t loop)
{
    uint32_t m = GD_MARK_FRAMES;
    while (loop-- && m > GD_MARK_MIN) m = (m * 243u) >> 8;
    return m > GD_MARK_MIN ? m : GD_MARK_MIN;
}
