#include "nameentry.h"

char nameentry_symbol_char(uint8_t sym)
{
    if (sym < 26) {
        return (char)('A' + sym);
    }
    if (sym < 36) {
        return (char)('0' + (sym - 26));
    }
    if (sym == 36) {
        return ' ';
    }
    if (sym == 37) {
        return '.';
    }
    return 0; /* END */
}

void nameentry_init(NameEntry *e)
{
    int i;
    for (i = 0; i < NAME_LEN; i++) {
        e->name[i] = ' ';
        e->sym[i] = 0;
    }
    e->pos = 0;
    e->done = 0;
    e->prev_in = 0;
    e->held_dir = 0;
    e->held_frames = 0;
    e->idle = 0;
}

/* Pad everything from the cursor on with spaces and mark done. */
static void finish(NameEntry *e, uint8_t count)
{
    int i;
    if (count == 0) {
        for (i = 0; i < NAME_LEN; i++) {
            e->name[i] = NAME_ENTRY_DEFAULT[i];
        }
    } else {
        for (i = count; i < NAME_LEN; i++) {
            e->name[i] = ' ';
        }
    }
    e->done = 1;
}

static void cycle(NameEntry *e, int dir)
{
    int s = e->sym[e->pos] + dir;
    if (s < 0) {
        s = NAME_SYMBOLS - 1;
    } else if (s >= NAME_SYMBOLS) {
        s = 0;
    }
    e->sym[e->pos] = (uint8_t)s;
}

void nameentry_step(NameEntry *e, uint8_t input)
{
    uint8_t edge, dir;
    if (e->done) {
        return;
    }
    edge = (uint8_t)(input & (uint8_t)~e->prev_in);
    e->prev_in = input;

    /* Only a new press counts as activity. A held or stuck button must not keep
     * the entry open forever, or the cabinet hangs on this screen. */
    if (edge != 0) {
        e->idle = 0;
    } else if (++e->idle >= NAME_TIMEOUT_FRAMES) {
        finish(e, e->pos);
        return;
    }

    /* Up wins when both directions are held. */
    dir = (input & IN_UP) ? IN_UP : ((input & IN_DOWN) ? IN_DOWN : 0);
    if (dir != e->held_dir) {
        e->held_dir = dir;
        e->held_frames = 0;
        if (dir) {
            cycle(e, dir == IN_UP ? 1 : -1);
        }
    } else if (dir) {
        e->held_frames++;
        if (e->held_frames >= NAME_REPEAT_DELAY &&
            (uint16_t)(e->held_frames - NAME_REPEAT_DELAY) % NAME_REPEAT_RATE == 0) {
            cycle(e, dir == IN_UP ? 1 : -1);
        }
    }

    if (edge & IN_A) {
        if (e->sym[e->pos] == NAME_SYMBOL_END) {
            finish(e, e->pos);
        } else {
            e->name[e->pos] = nameentry_symbol_char(e->sym[e->pos]);
            e->pos++;
            if (e->pos >= NAME_LEN) {
                e->pos = NAME_LEN - 1;
                finish(e, NAME_LEN);
            }
        }
    } else if ((edge & IN_B) && e->pos > 0) {
        e->pos--;
        e->name[e->pos] = ' ';
    }
}

uint8_t nameentry_seconds_left(const NameEntry *e)
{
    uint16_t left;
    uint8_t s = 0;
    if (e->done || e->idle >= NAME_TIMEOUT_FRAMES) {
        return 0;
    }
    left = (uint16_t)(NAME_TIMEOUT_FRAMES - e->idle);
    while (left > 60u) {
        left = (uint16_t)(left - 60u);
        s++;
    }
    return (uint8_t)(s + 1u);
}
