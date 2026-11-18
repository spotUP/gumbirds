#include "gumgames.h"
#include "game.h"

void gg_mash_reset(GgMash *m) { m->count = 0; }

int gg_mash_step(GgMash *m, uint8_t in, uint8_t prev)
{
    if (!(in & ~prev & (IN_A | IN_B))) return 0;   /* a new press of A or B counts once, A and B on the same frame too */
    m->count++;
    return 1;
}

uint16_t gg_hold_step(GgHold *h, uint8_t in, uint16_t cap)
{
    if (in & IN_C) {
        if (h->charge < cap) h->charge++;
        return 0;
    }
    {
        uint16_t c = h->charge;
        h->charge = 0;
        return c;
    }
}

int gg_bar_set(GgBar *b, uint8_t filled, uint8_t *out, int max)
{
    int n = 0;
    uint8_t i, lo, hi;
    if (filled > b->width) filled = b->width;
    if (filled == b->filled) return 0;
    lo = filled < b->filled ? filled : b->filled;
    hi = filled < b->filled ? b->filled : filled;
    for (i = lo; i < hi && n < max; i++) out[n++] = (uint8_t)(i | (filled > b->filled ? 0x80 : 0));
    b->filled = filled;
    return n;
}

void gg_seq_start(GgSeq *s, uint8_t event, uint8_t players)
{
    uint8_t i;
    s->event = event;
    s->players = players > 1 ? 2 : 1;
    s->turn = 0;
    for (i = 0; i < 2; i++) {
        s->tickets[i] = i < s->players ? GG_ATTEMPTS : 0;
        s->qualified[i] = 0;
        s->points[i] = 0;
        s->best[i] = 0;
    }
}

uint32_t gg_points(uint8_t stage, int qualified)
{
    return (uint32_t)stage * GG_STAGE_POINTS + (qualified ? GG_QUALIFY_POINTS : 0u);
}

int gg_seq_attempt(GgSeq *s, uint32_t result, uint8_t stage, int qualified)
{
    uint8_t t = s->turn;
    uint32_t p = gg_points(stage, qualified);
    if (s->tickets[t]) s->tickets[t]--;
    if (result > s->best[t]) s->best[t] = result;
    if (qualified) s->qualified[t] = 1;
    if (p > s->points[t]) s->points[t] = p;       /* best attempt counts, as the record does */
    if (s->players == 2 && s->tickets[1 - t]) s->turn = (uint8_t)(1 - t);
    return s->tickets[0] || s->tickets[1];
}

uint8_t gg_seq_input(const GgSeq *s, uint8_t in1, uint8_t in2)
{
    return (s->players == 2 && s->turn == 1) ? in2 : in1;
}

/* The Big Blow pump, shared with Burst Race: a counted A/B press adds GG_BLOW_PER_PRESS, then the leak takes 1 on every 8th tick. */
static void pump_press(GgMash *m, uint8_t *size, uint8_t in, uint8_t prev)
{
    if (gg_mash_step(m, in, prev)) *size = (uint8_t)(*size + GG_BLOW_PER_PRESS);
}
static void pump_leak(uint8_t *size, uint16_t tick)
{
    if ((tick & GG_BLOW_LEAK_MASK) == 0 && *size) (*size)--;
}

void gg_blow_start(GgBlow *b, uint8_t players)
{
    uint8_t *z = (uint8_t *)b;
    for (unsigned i = 0; i < sizeof(*b); i++) z[i] = 0;
    gg_seq_start(&b->seq, GG_BIG_BLOW, players);
    b->phase = GG_BLOW_INTRO;
}

static void blow_attempt(GgBlow *b, uint8_t size, int burst)
{
    uint8_t stage = burst ? 0 : (uint8_t)(size / GG_BLOW_STAGE);
    int ok = !burst && stage >= GG_BLOW_QUALIFY_STAGE;
    b->last_size = burst ? 0 : size;
    b->last_stage = stage;
    b->last_qualified = (uint8_t)ok;
    b->burst = (uint8_t)burst;
    b->last_points = gg_points(stage, ok);
    b->more = (uint8_t)gg_seq_attempt(&b->seq, b->last_size, stage, ok);
    b->timer = 0;
    b->phase = burst ? GG_BLOW_BURST : GG_BLOW_RESULT;
}

void gg_blow_step(GgBlow *b, uint8_t in1, uint8_t in2)
{
    uint8_t in = gg_seq_input(&b->seq, in1, in2);
    switch (b->phase) {
    case GG_BLOW_INTRO:
        if (++b->timer >= GG_BLOW_INTRO_FRAMES) {
            b->phase = GG_BLOW_PLAY; b->timer = 0; b->size = 0; b->clock = GG_BLOW_CLOCK;
            gg_mash_reset(&b->mash);
        }
        break;
    case GG_BLOW_PLAY:
        pump_press(&b->mash, &b->size, in, b->prev);
        if (b->size >= GG_BLOW_MAX) { b->size = GG_BLOW_MAX; blow_attempt(b, b->size, 1); break; }
        pump_leak(&b->size, b->clock);
        if (--b->clock == 0) blow_attempt(b, b->size, 0);
        break;
    case GG_BLOW_BURST:
    case GG_BLOW_RESULT:
        if (++b->timer >= (b->phase == GG_BLOW_BURST ? GG_BLOW_BURST_FRAMES : GG_BLOW_RESULT_FRAMES)) {
            b->timer = 0;
            b->phase = b->more ? GG_BLOW_INTRO : GG_BLOW_END;
        }
        break;
    default: break;
    }
    b->prev = in;
}

void gg_race_start(GgRace *r, uint8_t players)
{
    uint8_t *z = (uint8_t *)r;
    for (unsigned i = 0; i < sizeof(*r); i++) z[i] = 0;
    gg_seq_start(&r->seq, GG_BURST_RACE, 1);
    r->seq.tickets[0] = 1;                            /* retry-free heat */
    r->players = players == 2 ? 2 : 1;
    r->phase = GG_RACE_INTRO;
}

static void race_finish(GgRace *r, uint8_t winner)
{
    int p1 = winner == 0;
    uint8_t stage = p1 ? (uint8_t)(GG_BLOW_MAX / GG_BLOW_STAGE) : 0;
    r->winner = winner;
    r->last_points = gg_points(stage, p1);
    gg_seq_attempt(&r->seq, p1 ? r->frames : 0, stage, p1);
    r->timer = 0;
    r->phase = GG_RACE_RESULT;
}

void gg_race_step(GgRace *r, uint8_t in1, uint8_t in2)
{
    switch (r->phase) {
    case GG_RACE_INTRO:
        if (++r->timer >= GG_RACE_INTRO_FRAMES) { r->phase = GG_RACE_PLAY; r->timer = 0; }
        break;
    case GG_RACE_PLAY: {
        uint8_t in[2];
        in[0] = in1;
        /* the computer bird pumps, one press every GG_RACE_CPU_PERIOD frames */
        in[1] = r->players == 2 ? in2 : (uint8_t)(r->frames % GG_RACE_CPU_PERIOD == 0 ? (((r->frames / GG_RACE_CPU_PERIOD) & 1) ? IN_A : IN_B) : 0);
        r->frames++;
        for (int s = 0; s < 2; s++) { pump_press(&r->mash[s], &r->size[s], in[s], r->prev[s]); r->prev[s] = in[s]; }
        if (r->size[0] >= GG_BLOW_MAX || r->size[1] >= GG_BLOW_MAX) {
            for (int s = 0; s < 2; s++) if (r->size[s] > GG_BLOW_MAX) r->size[s] = GG_BLOW_MAX;
            race_finish(r, (uint8_t)(r->size[0] >= GG_BLOW_MAX ? 0 : 1));    /* both on one frame: P1 */
            break;
        }
        for (int s = 0; s < 2; s++) pump_leak(&r->size[s], (uint16_t)r->frames);
        if (r->frames >= GG_RACE_CLOCK) race_finish(r, (uint8_t)(r->size[0] >= r->size[1] ? 0 : 1));
        break;
    }
    case GG_RACE_RESULT:
        if (++r->timer >= GG_RACE_RESULT_FRAMES) r->phase = GG_RACE_END;
        break;
    default: break;
    }
}

int gg_race_bursts(const GgRace *r, int side) { return r->phase >= GG_RACE_RESULT && r->winner == side; }
