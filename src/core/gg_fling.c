#include "gg_fling.h"
#include "game.h"

static void begin(GgFling *f)
{
    f->phase = GF_WINDUP; f->prev_in = 0; f->thrower = f->seq.turn; f->power = 0; f->drain_t = 0; f->deg = 0; f->foul = 0;
    f->clock = GF_WINDUP_FRAMES; f->t = 0;
    f->hold.charge = 0;
    f->vx = f->vy = f->h = 0; f->x = 0; f->dist = 0;
}

void gumfling_init(GgFling *f)
{
    gg_seq_start(&f->seq, GG_FLING, 1);
    f->seq.tickets[0] = GF_ATTEMPTS;
    f->sfx = 0;
    begin(f);
}

void gumfling_add_p2(GgFling *f)
{
    f->seq.players = 2;
    f->seq.tickets[1] = GF_ATTEMPTS;
}

uint8_t gumfling_winner(const GgFling *f)
{
    return f->seq.best[0] == f->seq.best[1] ? 2 : f->seq.best[1] > f->seq.best[0];
}

uint8_t gumfling_deg(uint16_t charge)
{
    uint16_t a = charge > GF_AIM_CAP ? GF_AIM_CAP >> 1 : charge >> 1;          /* 0..64 on the 256-step angle circle */
    return (uint8_t)(a + (a >> 2) + (a >> 3) + (a >> 5));   /* a * 1.41 = degrees */
}

/* Launch velocity of a throw: run-up power and the frames of B held in the aim (charge). Shared by the launch and the aim preview. */
static void launch_vel(uint8_t power, uint16_t charge, int32_t *vx, int32_t *vy)
{
    uint8_t a = (uint8_t)(charge >> 1 > 64 ? 64 : charge >> 1);
    int32_t v0 = (int32_t)GF_V0_BASE + (int32_t)power * GF_V0_PER_PRESS;
    *vx = (int32_t)(((int64_t)(v0 >> 3) * flier_cos(a)) >> 12);
    *vy = (int32_t)(((int64_t)(v0 >> 3) * flier_sin(a)) >> 12);
    if (*vx > GF_MAX_VX) *vx = GF_MAX_VX;
}

/* One flight frame on the position and the vertical speed. Returns 1 on the touch-down frame (h clamped to 0). */
static int fly_frame(uint32_t *x, int32_t *h, int32_t *vy, int32_t vx)
{
    *x += (uint32_t)vx;
    *h += *vy;
    *vy -= GF_GRAVITY;
    if (*h > 0) return 0;
    *h = 0;
    return 1;
}

int gumfling_path(uint8_t power, uint16_t charge, int16_t *dx, int16_t *dy, int n)
{
    int32_t vx, vy, h = 0;
    uint32_t x = 0;
    int frames = 0, i, t = 0, landed = 0;
    launch_vel(power, charge, &vx, &vy);
    {   /* flight time first, so the dots spread over the whole throw */
        int32_t vy2 = vy;
        while (frames < 4000) { frames++; if (fly_frame(&x, &h, &vy2, vx)) break; }
    }
    x = 0; h = 0;
    for (i = 0; i < n; i++) {
        int target = frames * (i + 1) / n;
        while (t < target && !landed) { t++; landed = fly_frame(&x, &h, &vy, vx); }
        dx[i] = (int16_t)(x >> 16);
        dy[i] = (int16_t)(h >> 16);
    }
    return frames;
}

/* End of an attempt: score it and show the result. */
static void finish(GgFling *f, uint32_t dist)
{
    f->dist = dist;
    f->thrower = f->seq.turn;
    f->more = (uint8_t)gg_seq_attempt(&f->seq, dist, (uint8_t)(dist >> 5), dist >= GF_MARK_PX);
    f->sfx |= f->foul ? GF_SFX_FOUL : GF_SFX_LAND;
    f->phase = GF_LANDED; f->t = 0;
}

int gumfling_step(GgFling *f, uint8_t in)
{
    uint8_t prev = f->prev_in;
    f->prev_in = in;
    switch (f->phase) {
    case GF_WINDUP:
        if ((in & IN_A) && !(prev & IN_A) && f->power < GF_POWER_MAX) f->power++;
        if (++f->drain_t >= GF_POWER_DRAIN_FRAMES) { f->drain_t = 0; if (f->power) f->power--; }
        if (in & IN_B) { f->phase = GF_AIM; f->hold.charge = 0; f->t = 0; }   /* B ends the run-up and starts the needle */
        else if (--f->clock == 0) { f->foul = 1; finish(f, 0); }
        else if (f->clock % 60 == 0) f->sfx |= GF_SFX_TICK;
        break;
    case GF_AIM: {
        uint16_t c = 0;
        if (in & IN_B) { if (f->hold.charge < GF_AIM_CAP) f->hold.charge++; }
        else { c = f->hold.charge ? f->hold.charge : 1; f->hold.charge = 0; }
        f->deg = gumfling_deg(f->hold.charge);
        if (c) {
            f->deg = gumfling_deg(c);
            if (f->deg < GF_DEG_MIN || f->deg > GF_DEG_MAX) { f->foul = 1; finish(f, 0); break; }
            launch_vel(f->power, c, &f->vx, &f->vy);
            f->h = 0; f->x = 0; f->phase = GF_FLIGHT;
            f->sfx |= GF_SFX_THROW;
            return GF_EV_LAUNCH;
        }
        break;
    }
    case GF_LANDED:
        if (++f->t >= (f->foul ? GF_FOUL_FRAMES : GF_SHOW_FRAMES)) {
            if (f->more) { begin(f); return GF_EV_NEXT; }
            f->phase = GF_RESULT; f->t = 0;
            f->sfx |= (f->seq.players == 2 || f->seq.qualified[0]) ? GF_SFX_WIN : GF_SFX_LOSE;
        }
        break;
    case GF_RESULT:
        if (++f->t >= GF_RESULT_FRAMES) f->phase = GF_END;
        break;
    default:
        break;
    }
    return GF_EV_NONE;
}

int gumfling_fly(GgFling *f)
{
    if (f->phase != GF_FLIGHT) return GF_EV_NONE;
    if (fly_frame(&f->x, &f->h, &f->vy, f->vx)) {
        finish(f, f->x >> 16);
        return GF_EV_LANDED;
    }
    return GF_EV_NONE;
}

int32_t gumfling_scroll(const GgFling *f)
{
    return f->vx;
}
