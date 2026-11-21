#include "gg_tug.h"
#include "game.h"

/* Knot sign: negative = towards team 0 (left). Team 0 pulling moves it negative; a team wins by dragging the knot over its own line. */
static void round_reset(GgTug *t)
{
    t->phase = GTG_PLAY; t->t = 0; t->knot = 0;
    for (int i = 0; i < 2; i++) { t->press_pose[i] = t->slide[i] = t->stumble[i] = 0; t->since_pull[i] = 255; t->cool[i] = 0; }
}

/* Rival press gap in frames: one frame shorter for every round the rival has lost, never below GTG_CPU_GAP_FLOOR. */
static uint8_t cpu_gap(GgTug *t)
{
    uint8_t m = t->wins[0] >= GTG_CPU_GAP_MIN - GTG_CPU_GAP_FLOOR ? GTG_CPU_GAP_FLOOR : (uint8_t)(GTG_CPU_GAP_MIN - t->wins[0]);
    return (uint8_t)(m + rng_range(&t->rng, GTG_CPU_GAP_SPAN));
}

void gg_tug_start(GgTug *t, uint32_t seed, uint8_t humans)
{
    uint8_t *z = (uint8_t *)t;
    for (unsigned i = 0; i < sizeof(*t); i++) z[i] = 0;
    rng_seed(&t->rng, seed);
    t->humans = humans == 2 ? 2 : 1;
    t->cpu_gap = cpu_gap(t);
    round_reset(t);
}

static void dec(uint8_t *v) { if (*v) (*v)--; }

static void play(GgTug *t, const uint8_t pull[2], const uint8_t letgo[2])
{
    int16_t move = 0;
    for (int p = 0; p < 2; p++) {
        dec(&t->press_pose[p]); dec(&t->slide[p]); dec(&t->stumble[p]); dec(&t->cool[p]);
        if (t->since_pull[p] < 255) t->since_pull[p]++;
    }
    for (int p = 0; p < 2; p++) {
        int o = 1 - p;
        if (!letgo[p]) continue;
        t->slide[p] = GTG_SLIDE_FRAMES;
        move = (int16_t)(move + (p ? -GTG_LETGO_Q : GTG_LETGO_Q));   /* the knot goes to the rival's side */
        t->sfx |= GTG_SFX_LETGO;
        if (t->since_pull[o] <= GTG_LETGO_WINDOW) t->stumble[o] = GTG_STUMBLE_FRAMES;
    }
    for (int p = 0; p < 2; p++) {
        if (!pull[p]) continue;
        t->press_pose[p] = GTG_PRESS_POSE_FRAMES;
        t->press_n[p]++;
        if (t->cool[p]) continue;   /* faster than one pull per cooldown: the press shows but adds no force */
        t->cool[p] = GTG_PULL_COOLDOWN;
        t->since_pull[p] = 0;
        if (t->stumble[p]) continue;   /* a stumbling team's pulls count for nothing */
        move = (int16_t)(move + (p ? GTG_PULL_Q : -GTG_PULL_Q));
        t->sfx |= GTG_SFX_PULL;
    }
    t->knot = (int16_t)(t->knot + move);
    if (t->knot <= -GTG_WIN_Q || t->knot >= GTG_WIN_Q) {
        t->round_winner = t->knot < 0 ? 0 : 1;
        t->wins[t->round_winner]++;
        t->phase = GTG_SNAP; t->t = 0; t->sfx |= GTG_SFX_SNAP;
    }
}

void gg_tug_step(GgTug *t, uint8_t in1, uint8_t in2)
{
    uint8_t in[2], edge, pull[2], letgo[2];
    in[0] = in1; in[1] = t->humans == 2 ? in2 : 0;
    for (int p = 0; p < 2; p++) {
        edge = (uint8_t)(in[p] & ~t->prev[p]);
        t->prev[p] = in[p];
        pull[p] = (edge & (IN_A | IN_B | IN_C)) != 0;
        letgo[p] = (edge & IN_D) != 0;
    }
    switch (t->phase) {
    case GTG_PLAY:
        dec(&t->cpu_letgo_cd);
        if (t->humans == 1 && --t->cpu_gap == 0) {   /* the computer rival mashes at a steady rate; it lets go to stumble a human who is winning */
            if (!t->cpu_letgo_cd && t->knot < 0 && t->since_pull[0] <= GTG_LETGO_WINDOW && rng_range(&t->rng, 4) == 0) {
                letgo[1] = 1; t->cpu_letgo_cd = GTG_CPU_LETGO_CD;
            } else pull[1] = 1;
            t->cpu_gap = cpu_gap(t);
        }
        play(t, pull, letgo);
        break;
    case GTG_SNAP:
        if (++t->t >= GTG_SNAP_FRAMES) {
            if (t->wins[t->round_winner] >= GTG_ROUNDS_TO_WIN) { t->phase = GTG_RESULT; t->t = 0; t->sfx |= GTG_SFX_WIN; }
            else round_reset(t);
        }
        break;
    case GTG_RESULT:
        if (++t->t >= GTG_RESULT_FRAMES) t->phase = GTG_END;
        break;
    default: break;
    }
}

int gg_tug_pose(const GgTug *t, uint8_t seat)
{
    int team = seat >> 1, partner = seat & 1;
    if (t->phase >= GTG_SNAP) {
        if (team != t->round_winner) return GTG_POSE_SLAPPED;
        return t->phase == GTG_SNAP && t->t < 40 ? GTG_POSE_IDLE : ((t->t >> 4) & 1) ? GTG_POSE_CHEER1 : GTG_POSE_CHEER0;
    }
    if (t->stumble[team]) return partner ? GTG_POSE_STRAIN : GTG_POSE_STUMBLE;
    if (t->slide[team]) return GTG_POSE_SLIDE;
    if (t->press_pose[team]) return GTG_POSE_PULL0 + (t->press_n[team] % 3);
    if (team ? t->knot < -8 : t->knot > 8) return GTG_POSE_STRAIN;   /* being pulled over */
    return GTG_POSE_IDLE;
}
