#include "result.h"
#include "arcade.h"

enum { P_POPPED, P_EACH, P_VANISH, P_TOTAL, P_HOLD, P_TALLY, P_POST, P_END };

void res_start(Result *r, int caught, int number, int perfect, uint32_t score)
{
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
}

uint8_t res_step(Result *r, uint32_t *add)
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
            r->dirty |= RES_DIRTY_TICKET | RES_DIRTY_CAGE;
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
            r->dirty |= RES_DIRTY_MACHINE | RES_DIRTY_SCORE;
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
            r->active = 0;
            return ev;
        }
        break;
    default:
        r->active = 0;
        return ev;
    }
    r->phase++;
    return ev;
}
