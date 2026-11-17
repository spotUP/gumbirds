#include "gumgames.h"
#include "game.h"

void gg_mash_reset(GgMash *m) { m->last = 0; m->count = 0; }

int gg_mash_step(GgMash *m, uint8_t in, uint8_t prev)
{
    uint8_t press = (uint8_t)(in & ~prev & (IN_A | IN_B));
    if (press == IN_A || press == IN_B) {          /* both at once = ambiguous, not counted */
        if (press != m->last) {
            m->last = press;
            m->count++;
            return 1;
        }
    }
    return 0;
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
        if (gg_mash_step(&b->mash, in, b->prev)) b->size = (uint8_t)(b->size + GG_BLOW_PER_PRESS);
        if (b->size >= GG_BLOW_MAX) { b->size = GG_BLOW_MAX; blow_attempt(b, b->size, 1); break; }
        if ((b->clock & GG_BLOW_LEAK_MASK) == 0 && b->size) b->size--;
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
