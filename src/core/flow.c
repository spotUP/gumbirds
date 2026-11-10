#include "flow.h"

static void enter(Flow *f, FlowState s)
{
    f->state = (uint8_t)s;
    f->timer = 0;
    f->reset_hold = 0;
    f->reset_fired = 0;
}

static void start_game(Flow *f, uint32_t seed, int demo)
{
    game_reset(&f->game, seed);
    f->demo = (uint8_t)demo;
    f->highlight = -1;
    f->new_row = -1;
    f->reset_flash = 0;
    enter(f, demo ? FLOW_ATTRACT_DEMO : FLOW_PLAYING);
}

void flow_init(Flow *f, const uint8_t *image, size_t len)
{
    f->dirty = 0;
    f->highlight = -1;
    f->new_row = -1;
    f->demo = 0;
    f->reset_flash = 0;
    f->reset_hold = 0;
    f->reset_fired = 0;
    f->last_score = 0;
    if (image) {
        hiscore_load(&f->table, image, len);
    } else {
        hiscore_defaults(&f->table);
    }
    game_reset(&f->game, 1);
    nameentry_init(&f->entry);
    enter(f, FLOW_ATTRACT_TITLE);
}

/* Would this score make the table? Tries the insert on a copy so the ranking rule
 * (ties rank below, zero never ranks) lives only in hiscore_insert. */
static int ranks(const Flow *f, uint32_t score)
{
    HiscoreTable t = f->table;
    return hiscore_insert(&t, "", score) >= 0;
}

/* Scripted demo input: hover. Flap (press edge: release the frame after a press) whenever the flier is
 * below DEMO_HOVER_Y, sweep right and left, switching every DEMO_SWEEP_FRAMES frames of the demo. */
static uint8_t demo_input(Flow *f)
{
    const Flier *fl = &f->game.flier;
    uint8_t in = 0;
    if (!fl->flap_prev && fl->y > FL_PX(DEMO_HOVER_Y)) {
        in |= IN_A;
    }
    in |= ((f->timer / DEMO_SWEEP_FRAMES) & 1u) ? IN_LEFT : IN_RIGHT;
    return in;
}

static void title_reset_combo(Flow *f, uint8_t input)
{
    if ((input & FLOW_RESET_COMBO) == FLOW_RESET_COMBO) {
        if (f->reset_hold < 0xFFFFu) {
            f->reset_hold++;
        }
        if (!f->reset_fired && f->reset_hold >= RESET_HOLD_FRAMES) {
            hiscore_defaults(&f->table);
            f->dirty = 1;
            f->reset_fired = 1;
            f->reset_flash = 1;
        }
    } else {
        f->reset_hold = 0;
        f->reset_fired = 0;
    }
}

void flow_step(Flow *f, uint8_t input, uint8_t start_pressed, uint32_t frame_counter)
{
    if (f->timer < 0xFFFFu) {
        f->timer++;
    }
    switch (f->state) {
    case FLOW_ATTRACT_TITLE:
        title_reset_combo(f, input);
        if (start_pressed && (input & FLOW_RESET_COMBO) != FLOW_RESET_COMBO) {
            start_game(f, frame_counter, 0);
        } else if (f->timer >= ATTRACT_TITLE_FRAMES) {
            f->reset_flash = 0;
            enter(f, FLOW_ATTRACT_TABLE);
        }
        break;
    case FLOW_ATTRACT_TABLE:
        if (start_pressed) {
            start_game(f, frame_counter, 0);
        } else if (f->timer >= ATTRACT_TABLE_FRAMES) {
            f->highlight = -1;
            start_game(f, frame_counter, 1);
        }
        break;
    case FLOW_ATTRACT_DEMO:
        if (start_pressed) {
            start_game(f, frame_counter, 0);
        } else {
            game_step_arena(&f->game, demo_input(f));
            /* The demo never scores into the table: it only ever returns to the title. */
            if (f->game.over || f->timer >= ATTRACT_DEMO_FRAMES) {
                f->demo = 0;
                enter(f, FLOW_ATTRACT_TITLE);
            }
        }
        break;
    case FLOW_PLAYING:
        game_step_arena(&f->game, input);
        if (f->game.over) {
            f->last_score = f->game.score;
            enter(f, FLOW_GAME_OVER);
        }
        break;
    case FLOW_GAME_OVER:
        if (f->timer >= GAMEOVER_FRAMES) {
            if (ranks(f, f->last_score)) {
                nameentry_init(&f->entry);
                enter(f, FLOW_NAME_ENTRY);
            } else {
                enter(f, FLOW_ATTRACT_TITLE);
            }
        }
        break;
    case FLOW_NAME_ENTRY:
        nameentry_step(&f->entry, input);
        if (f->entry.done) {
            f->new_row = (int8_t)hiscore_insert(&f->table, f->entry.name, f->last_score);
            f->highlight = f->new_row;
            f->dirty = 1;
            enter(f, FLOW_SAVE_REMINDER);
        }
        break;
    case FLOW_SAVE_REMINDER:
        if (f->timer >= REMINDER_FRAMES) {
            enter(f, FLOW_ATTRACT_TABLE); /* highlight stays until the table screen ends */
        }
        break;
    }
}

void flow_view(const Flow *f, FlowView *v)
{
    v->state = (FlowState)f->state;
    v->timer = f->timer;
    v->table = &f->table;
    v->highlight = f->highlight;
    v->game = &f->game;
    v->entry = &f->entry;
    v->score = f->last_score;
    v->reset_progress = f->reset_hold >= RESET_HOLD_FRAMES
                            ? 100
                            : (int)(((uint32_t)f->reset_hold * 100u) / RESET_HOLD_FRAMES);
    v->reset_flash = f->reset_flash;
}
