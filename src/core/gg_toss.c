#include "gg_toss.h"
#include "game.h"

uint16_t gg_toss_fuse(uint8_t round)
{
    uint32_t cut = (uint32_t)GT_FUSE_STEP * round;
    return cut >= GT_FUSE_BASE - GT_FUSE_MIN ? GT_FUSE_MIN : (uint16_t)(GT_FUSE_BASE - cut);
}

uint8_t gg_toss_seat_of(uint8_t p) { return p ? 2 : 0; }

uint8_t gg_toss_count(const GgToss *t)
{
    uint8_t n = 0;
    for (uint8_t s = 0; s < GT_SEATS; s++) n = (uint8_t)(n + ((t->alive >> s) & 1));
    return n;
}

uint8_t gg_toss_target(uint8_t from, uint8_t alive, uint8_t k)
{
    uint8_t o[GT_SEATS], n = 0;
    for (uint8_t d = 1; d < GT_SEATS; d++) {
        uint8_t s = (uint8_t)((from + d) % GT_SEATS);
        if ((alive >> s) & 1) o[n++] = s;
    }
    return n ? o[k * n / 3] : 0xFF;
}

static void take_gum(GgToss *t, uint8_t seat)
{
    t->carrier = seat;
    t->phase = GT_HOLD;
    t->fuse = (uint16_t)(gg_toss_fuse(t->round) + rng_range(&t->rng, GT_FUSE_JITTER));
    t->think = (uint16_t)(GT_THINK_MIN + rng_range(&t->rng, GT_THINK_SPAN));
    t->lead = GT_LEAD_FRAMES;
}

static uint8_t random_survivor(GgToss *t)
{
    uint32_t pick = rng_range(&t->rng, gg_toss_count(t));
    for (uint8_t s = 0; s < GT_SEATS; s++)
        if (((t->alive >> s) & 1) && pick-- == 0) return s;
    return 0;
}

void gg_toss_start(GgToss *t, uint32_t seed, uint8_t humans)
{
    uint8_t *z = (uint8_t *)t;
    for (unsigned i = 0; i < sizeof(*t); i++) z[i] = 0;
    rng_seed(&t->rng, seed);
    t->humans = humans == 2 ? 2 : 1;
    t->alive = 0x0F;
    take_gum(t, random_survivor(t));
}

static int is_human(const GgToss *t, uint8_t seat) { return seat == 0 || (seat == 2 && t->humans == 2); }

static void toss_to(GgToss *t, uint8_t to)
{
    t->target = to;
    t->phase = GT_FLIGHT;
    t->t = 0;
    t->sfx |= GT_SFX_TOSS;
}

void gg_toss_step(GgToss *t, uint8_t in1, uint8_t in2)
{
    uint8_t in[2], edge[2];
    in[0] = in1; in[1] = t->humans == 2 ? in2 : 0;
    edge[0] = (uint8_t)(in[0] & ~t->prev[0]); edge[1] = (uint8_t)(in[1] & ~t->prev[1]);
    t->prev[0] = in[0]; t->prev[1] = in[1];
    switch (t->phase) {
    case GT_HOLD: {
        uint8_t c = t->carrier;
        if (t->lead) t->lead--;
        if (t->fuse && --t->fuse == 0) {
            t->alive = (uint8_t)(t->alive & ~(1u << c));
            t->round++;
            t->phase = GT_BURST; t->t = 0; t->sfx |= GT_SFX_BURST;
            break;
        }
        if (t->lead) break;
        if (is_human(t, c)) {
            uint8_t e = edge[c == 2];
            uint8_t k = (e & IN_A) ? 0 : (e & IN_B) ? 1 : (e & IN_C) ? 2 : 0xFF;
            if (k != 0xFF) toss_to(t, gg_toss_target(c, t->alive, k));
        } else if (t->think && --t->think == 0) {
            toss_to(t, gg_toss_target(c, t->alive, (uint8_t)rng_range(&t->rng, 3)));
        }
        break;
    }
    case GT_FLIGHT:
        if (++t->t >= GT_FLIGHT_FRAMES) {
            uint16_t fuse = t->fuse;
            take_gum(t, t->target);
            t->fuse = fuse;            /* the fuse keeps what is left of it */
        }
        break;
    case GT_BURST:
        if (++t->t >= GT_BURST_FRAMES) {
            if (gg_toss_count(t) <= 1) {
                for (uint8_t s = 0; s < GT_SEATS; s++) if ((t->alive >> s) & 1) t->winner = s;
                t->phase = GT_RESULT; t->t = 0; t->sfx |= GT_SFX_WIN;
            } else take_gum(t, random_survivor(t));
        }
        break;
    case GT_RESULT:
        if (++t->t >= GT_RESULT_FRAMES) t->phase = GT_END;
        break;
    default: break;
    }
}

int gg_toss_pose(const GgToss *t, uint8_t seat)
{
    if (t->phase == GT_HOLD && seat == t->carrier)
        return t->lead > GT_LEAD_FRAMES - 9 ? GT_POSE_ABSORB : t->lead > GT_LEAD_FRAMES - 18 ? GT_POSE_RECOIL : GT_POSE_CARRY;
    if (t->phase != GT_FLIGHT) return -1;
    if (seat == t->carrier) return t->t < 6 ? GT_POSE_WINDUP : t->t < GT_RELEASE_FRAME ? GT_POSE_RELEASE : t->t < 16 ? GT_POSE_FOLLOW : -1;
    if (seat == t->target) return t->t >= 22 ? GT_POSE_CATCH : t->t >= 12 ? GT_POSE_REACH : -1;
    return -1;
}
