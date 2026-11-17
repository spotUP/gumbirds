#include "gg_fling.h"
#include "game.h"

static void begin(GgFling *f)
{
    f->phase = GF_WINDUP; f->prev_in = 0; f->power = 0; f->deg = 0; f->foul = 0;
    f->clock = GF_WINDUP_FRAMES; f->t = 0;
    gg_mash_reset(&f->mash);
    f->hold.charge = 0;
    f->vx = f->vy = f->h = 0; f->x = 0; f->dist = 0;
}

void gumfling_init(GgFling *f)
{
    gg_seq_start(&f->seq, GG_FLING, 1);
    f->seq.tickets[0] = GF_ATTEMPTS;
    begin(f);
}

uint8_t gumfling_deg(uint16_t charge)
{
    uint16_t a = charge > GF_AIM_CAP ? GF_AIM_CAP >> 1 : charge >> 1;          /* 0..64 on the 256-step angle circle */
    return (uint8_t)(a + (a >> 2) + (a >> 3) + (a >> 5));   /* a * 1.41 = degrees */
}

/* End of an attempt: score it and show the result. */
static void finish(GgFling *f, uint32_t dist)
{
    f->dist = dist;
    gg_seq_attempt(&f->seq, dist, (uint8_t)(dist >> 5), dist >= GF_MARK_PX);
    f->phase = GF_LANDED; f->t = 0;
}

int gumfling_step(GgFling *f, uint8_t in)
{
    uint8_t prev = f->prev_in;
    f->prev_in = in;
    switch (f->phase) {
    case GF_WINDUP:
        if (gg_mash_step(&f->mash, in, prev) && f->power < GF_POWER_MAX) f->power++;
        if (in & IN_C) { f->phase = GF_AIM; f->hold.charge = 0; }
        else if (--f->clock == 0) { f->foul = 1; finish(f, 0); }
        break;
    case GF_AIM: {
        uint16_t c = gg_hold_step(&f->hold, in, GF_AIM_CAP);
        f->deg = gumfling_deg(f->hold.charge);
        if (c) {
            uint8_t a = (uint8_t)(c >> 1 > 64 ? 64 : c >> 1);
            int32_t v0 = (int32_t)GF_V0_BASE + (int32_t)f->power * GF_V0_PER_PRESS;
            f->deg = gumfling_deg(c);
            if (f->deg < GF_DEG_MIN || f->deg > GF_DEG_MAX) { f->foul = 1; finish(f, 0); break; }
            f->vx = (int32_t)(((int64_t)(v0 >> 3) * flier_cos(a)) >> 12);
            f->vy = (int32_t)(((int64_t)(v0 >> 3) * flier_sin(a)) >> 12);
            if (f->vx > GF_MAX_VX) f->vx = GF_MAX_VX;
            f->h = 0; f->x = 0; f->phase = GF_FLIGHT;
            return GF_EV_LAUNCH;
        }
        break;
    }
    case GF_LANDED:
        if (++f->t >= (f->foul ? GF_FOUL_FRAMES : GF_SHOW_FRAMES)) {
            if (f->seq.tickets[0]) { begin(f); return GF_EV_NEXT; }
            f->phase = GF_END;
        }
        break;
    default:
        break;
    }
    return GF_EV_NONE;
}

int gumfling_fly(GgFling *f)
{
    if (f->phase != GF_FLIGHT) return GF_EV_NONE;
    f->x += (uint32_t)f->vx;
    f->h += f->vy;
    f->vy -= GF_GRAVITY;
    if (f->h <= 0) {
        f->h = 0;
        finish(f, f->x >> 16);
        return GF_EV_LANDED;
    }
    return GF_EV_NONE;
}

int32_t gumfling_scroll(const GgFling *f)
{
    return f->vx;
}
