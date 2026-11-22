#include "result.h"
#include "arcade.h"
#include "gen/result_paths.h"

enum { P_POPPED, P_EACH, P_VANISH, P_TOTAL, P_HOLD, P_TALLY, P_POST, P_WAIT };

/* total_left as 5 digits, by subtraction (a 32-bit divide is a libgcc call on the 68000). */
static void set_digits(Result *r)
{
    static const uint16_t P[5] = { 10000, 1000, 100, 10, 1 };
    uint32_t v = r->total_left;
    uint8_t i;
    for (i = 0; i < 5; i++) {
        uint8_t d = 0;
        while (v >= P[i] && d < 9) { v -= P[i]; d++; }
        r->digit[i] = d;
    }
}

void res_start(Result *r, int caught, int number, int perfect, uint32_t score)
{
    uint8_t i;
    r->active = 1;
    r->phase = P_POPPED;
    r->wait = 20;
    r->caught = (uint8_t)caught;
    r->perfect = perfect ? 1 : 0;
    r->show = r->vanished = r->ticket = 0;
    r->dirty = RES_DIRTY_ALL;
    r->each = (uint16_t)arc_bonus_value(number);
    r->bonus = perfect ? (uint32_t)arc_bonus_perfect(number) : 0u;
    r->total_left = (uint32_t)caught * r->each;
    r->score_shown = score;
    r->two = 0;
    r->ev = 0;
    r->score2 = 0;
    r->t = 0;
    r->pop_cur = 0;
    r->pop_acc = 0;
    r->crank = r->ticket_out = r->lines = 0;
    for (i = 0; i < RES_SLOTS; i++) r->pop[i] = 0;
    for (i = 0; i < 5; i++) r->wheel[i] = 0;
    set_digits(r);
}

void res_start_event(Result *r, uint8_t ev, uint32_t score)
{
    res_start(r, 0, 1, 0, score);
    r->ev = ev;
    r->phase = P_WAIT;
    r->wait = RES_EVENT_SKIP;
}

/* One frame of the moving parts. ev and d are this frame's events and tally points. */
static void res_animate(Result *r, uint8_t ev, uint32_t d)
{
    uint8_t i;
    if (r->t < 0xFFFFu) r->t++;
    if (ev & RES_EV_TICK) {
        r->crank = (uint8_t)((r->crank + 1) & 7);
        r->pop_acc = (uint16_t)(r->pop_acc + d);
        while (r->pop_acc >= r->each && r->pop_cur < r->caught) { /* one bubble pops for each `each` points paid */
            r->pop_acc = (uint16_t)(r->pop_acc - r->each);
            r->pop[resp_order[RESP_RUN(r->caught) + r->pop_cur++]] = 1;
        }
        set_digits(r);
    }
    for (i = 0; i < RES_SLOTS; i++) if (r->pop[i] && r->pop[i] < 7) r->pop[i]++;
    for (i = 0; i < 5; i++) { /* wheels roll the short way round to their digit, 8 pixels a frame at most */
        uint8_t want = (r->show & RES_SHOW_TOTAL) ? (uint8_t)(r->digit[i] << 4) : 0;
        int diff = want - r->wheel[i], v = r->wheel[i];
        if (!diff) continue;
        if (diff < 0) diff += 160;
        if (diff <= 80) v += diff < 8 ? diff : 8;
        else v -= 160 - diff < 8 ? 160 - diff : 8;
        if (v < 0) v += 160;
        if (v >= 160) v -= 160;
        r->wheel[i] = (uint8_t)v;
    }
    if (r->ticket) {
        if (r->ticket_out < 40) r->ticket_out = (uint8_t)(r->ticket_out + 2);
        else if (r->lines < 2 && !(r->t & 7)) { r->lines++; r->dirty |= RES_DIRTY_TICKET; }
    }
}

uint8_t res_bubble(const Result *r, int i, int *x, int *y)
{
    uint16_t run, k, p;
    if (i >= r->caught || r->t < resp_start[i] || r->pop[i] == 7) return 0;
    run = (uint16_t)(RESP_RUN(r->caught) + i);
    k = (uint16_t)(r->t - resp_start[i]);
    if (k >= resp_len[run]) k = (uint16_t)(resp_len[run] - 1);
    p = (uint16_t)((resp_off[run] + k) << 1);
    *x = resp_xy[p];
    *y = resp_xy[p + 1];
    return r->pop[i] ? (uint8_t)(2 + ((r->pop[i] - 1) >> 1)) : 1;
}

static uint8_t res_phase(Result *r, uint32_t *add, uint8_t press)
{
    uint8_t ev = 0;
    *add = 0;
    if (!r->active) return 0;
    if (r->wait > 1) {
        r->wait--;
        return 0;
    }
    switch (r->phase) {
    case P_POPPED:
        r->show |= RES_SHOW_POPPED;
        r->dirty |= RES_DIRTY_POPPED;
        r->wait = 20;
        break;
    case P_EACH:
        r->show |= RES_SHOW_EACH;
        r->vanished = 1;
        r->dirty |= RES_DIRTY_POPPED | RES_DIRTY_CAGE;
        ev |= RES_EV_VANISH;
        r->wait = 2;
        break;
    case P_VANISH:
        r->show |= RES_SHOW_TOTAL;
        r->dirty |= RES_DIRTY_MACHINE;
        r->wait = 20;
        break;
    case P_TOTAL:
        if (r->perfect) {
            r->ticket = 1;
            r->dirty |= RES_DIRTY_TICKET;
            ev |= RES_EV_JINGLE;
        }
        r->wait = 120;
        break;
    case P_HOLD:
        r->wait = 1;
        break;
    case P_TALLY:
        if (r->total_left) {
            uint32_t d = r->total_left < 100u ? r->total_left : 100u;
            r->total_left -= d;
            r->score_shown += d;
            *add = d;
            r->dirty |= RES_DIRTY_SCORE; /* the total is on the counter wheels (sprites) */
            ev |= RES_EV_TICK;
            r->wait = 2;
            return ev;  /* stay in the tally */
        }
        r->wait = 10;
        break;
    case P_POST:
        if (r->perfect) {
            r->ticket = 2;
            r->score_shown += r->bonus;
            *add = r->bonus;
            r->dirty |= RES_DIRTY_TICKET | RES_DIRTY_SCORE;
            ev |= RES_EV_BONUS;
            r->wait = 20;
        } else {
            r->wait = 1;
        }
        break;
    default: /* P_WAIT: the totals stay up until the player presses */
        if (press) r->active = 0;
        return ev;
    }
    r->phase++;
    return ev;
}

uint8_t res_step(Result *r, uint32_t *add, uint8_t press)
{
    uint8_t ev;
    *add = 0;
    if (!r->active) return 0;
    ev = res_phase(r, add, press);
    res_animate(r, ev, *add);
    return ev;
}
