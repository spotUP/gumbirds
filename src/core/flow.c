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
    if (demo) {
        game_set_mode(&f->game, f->demo_mode); /* each demo plays the next mode; the title highlight (f->mode) is untouched */
        f->demo_mode = (uint8_t)(f->demo_mode == GAME_MODE_ARCADE ? GAME_MODE_ARENA : f->demo_mode + 1); /* count and wrap, no % */
    } else {
        game_set_mode(&f->game, f->mode);
    }
    f->demo = (uint8_t)demo;
    f->demo_in = 0;
    attract_overlay_reset(&f->ov);
    f->game.rounds = (uint8_t)(!demo && f->mode != GAME_MODE_TRIP); /* real arena games get the round end and round start phases */
    f->highlight = -1;
    f->new_row = -1;
    f->reset_flash = 0;
    f->select_open = 0;
    enter(f, demo ? FLOW_ATTRACT_DEMO : FLOW_PLAYING);
}

void flow_init(Flow *f, const uint8_t *image, size_t len)
{
    f->dirty = 0;
    f->highlight = -1;
    f->new_row = -1;
    f->demo = 0;
    f->demo_mode = GAME_MODE_ARENA;
    f->demo_in = 0;
    attract_overlay_reset(&f->ov);
    f->select_open = 0;
    f->mode = GAME_MODE_ARENA;
    f->input_prev = 0;
    f->reset_flash = 0;
    f->reset_hold = 0;
    f->reset_fired = 0;
    f->last_score = 0;
    f->last_mode = GAME_MODE_ARENA;
    /* a version 1 image (arena only) loads with the trip table at defaults; dirty stays 0 so the version 2 image is
     * written back on the first new entry, not at boot (user 2026-11-11) */
    if (!image || !score_load(&f->tables, image, len)) {
        score_tables_defaults(&f->tables);
    }
    game_reset(&f->game, 1);
    nameentry_init(&f->entry);
    enter(f, FLOW_ATTRACT_TITLE);
}

/* Would this score make the table? Tries the insert on a copy so the ranking rule
 * (ties rank below, zero never ranks) lives only in hiscore_insert, reached through score_qualifies. */
static int ranks(const Flow *f, uint32_t score)
{
    return score_qualifies(&f->tables, f->last_mode, score);
}

/* Scripted demo input: hover. Flap (press edge: release the frame after a press; and the flap cooldown is over) whenever the flier is
 * below DEMO_HOVER_Y, sweep right and left, switching every DEMO_SWEEP_FRAMES frames of the demo. */
static uint8_t demo_input(Flow *f)
{
    const Flier *fl = &f->game.flier;
    uint8_t in = 0;
    if (!fl->flap_prev && fl->flap_cd == 0 && fl->y > FL_PX(DEMO_HOVER_Y)) {
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
            score_tables_defaults(&f->tables); /* wipes both tables */
            f->dirty = 1;
            f->reset_fired = 1;
            f->reset_flash = 1;
        }
    } else {
        f->reset_hold = 0;
        f->reset_fired = 0;
    }
}

/* Title mode select: a press edge steps through Arena, Gum Trip, Arcade: Down forward, Up back, both wrap (both on one frame: forward). A held stick does not repeat. */
static void title_mode_select(Flow *f, uint8_t input)
{
    uint8_t edge = (uint8_t)(input & ~f->input_prev & (IN_UP | IN_DOWN));
    if (edge) {
        if (edge & IN_DOWN) f->mode = f->mode == GAME_MODE_ARCADE ? GAME_MODE_ARENA : (uint8_t)(f->mode + 1);
        else f->mode = f->mode == GAME_MODE_ARENA ? GAME_MODE_ARCADE : (uint8_t)(f->mode - 1);
    }
}

/* A coin in any attract phase jumps to the title with the mode list open (the logo and the press start prompt). */
void flow_coin(Flow *f)
{
    if (f->state > FLOW_ATTRACT_DEMO) return;
    f->demo = 0;
    f->highlight = -1;
    f->select_open = 1;
    if (f->state != FLOW_ATTRACT_TITLE) enter(f, FLOW_ATTRACT_TITLE);
    else f->timer = 0;
}

void flow_step(Flow *f, uint8_t input, uint8_t start_pressed, uint32_t frame_counter)
{
    if (f->timer < 0xFFFFu) {
        f->timer++;
    }
    /* MB1/MB2: A is a second Start on the attract screens, B goes back to the title (press edges) */
    uint8_t a_edge = (uint8_t)(input & ~f->input_prev & IN_A);
    uint8_t b_edge = (uint8_t)(input & ~f->input_prev & IN_B);
    switch (f->state) {
    case FLOW_ATTRACT_TITLE:
        title_reset_combo(f, input);
        title_mode_select(f, input);
        if (start_pressed && (input & FLOW_RESET_COMBO) != FLOW_RESET_COMBO) {
            /* start_pressed means a credit was taken: it always becomes a game, in the highlighted mode */
            start_game(f, frame_counter, 0);
        } else if (a_edge && (input & FLOW_RESET_COMBO) != FLOW_RESET_COMBO) {
            if (!f->select_open) { f->select_open = 1; f->timer = 0; } /* A without a credit only opens the select */
        } else if (f->timer >= ATTRACT_TITLE_FRAMES) {
            f->reset_flash = 0;
            f->select_open = 0;
            f->highlight = -1; /* the saved row was shown on the title, the table that follows is plain */
            enter(f, FLOW_ATTRACT_TABLE);
        }
        break;
    case FLOW_ATTRACT_TABLE:
        if (start_pressed) {
            f->highlight = -1;
            start_game(f, frame_counter, 0);
        } else if (a_edge || b_edge) {
            f->highlight = -1;
            enter(f, FLOW_ATTRACT_TITLE);
            f->select_open = !b_edge || a_edge;
        } else if (f->timer >= ATTRACT_TABLE_FRAMES) {
            f->highlight = -1;
            start_game(f, frame_counter, 1);
        }
        break;
    case FLOW_ATTRACT_DEMO:
        if (start_pressed) {
            start_game(f, frame_counter, 0);
        } else if (a_edge || b_edge) {
            f->demo = 0;
            enter(f, FLOW_ATTRACT_TITLE);
            f->select_open = !b_edge || a_edge;
        } else {
            f->demo_in = demo_input(f);
            attract_overlay_step(&f->ov, f->demo_in);
            game_step(&f->game, f->demo_in);
            /* The demo never scores into the table: it only ever returns to the title. */
            if (f->game.over || f->timer >= ATTRACT_DEMO_FRAMES) {
                f->demo = 0;
                enter(f, FLOW_ATTRACT_TITLE);
            }
        }
        break;
    case FLOW_PLAYING:
        game_step(&f->game, input);
        if (f->game.over) {
            f->last_score = f->game.score;
            f->last_mode = f->game.mode;
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
        nameentry_step(&f->entry, start_pressed ? (uint8_t)(input | IN_A) : input); /* NE1: Start confirms a letter like A */
        if (f->entry.done) {
            f->new_row = (int8_t)score_insert(&f->tables, f->last_mode, f->entry.name, f->last_score);
            f->highlight = f->new_row;
            f->dirty = 1;
            enter(f, FLOW_SAVE_REMINDER);
        }
        break;
    case FLOW_SAVE_REMINDER:
        if (f->timer >= REMINDER_FRAMES) {
            enter(f, FLOW_ATTRACT_TITLE); /* BG1: straight to the title; the highlight stays until the title times out */
        }
        break;
    }
    f->input_prev = input;
}

void flow_view(const Flow *f, FlowView *v)
{
    v->state = (FlowState)f->state;
    v->timer = f->timer;
    v->table_mode = (uint8_t)score_shown_mode(f->state, f->mode, f->last_mode, f->timer, SCORE_TABLE_SWAP_FRAMES);
    v->table = &f->tables.t[v->table_mode];
    v->highlight = v->table_mode == f->last_mode ? f->highlight : -1;
    v->game = &f->game;
    v->entry = &f->entry;
    v->score = f->last_score;
    v->reset_progress = f->reset_hold >= RESET_HOLD_FRAMES
                            ? 100
                            : (int)(((uint32_t)f->reset_hold * 100u) / RESET_HOLD_FRAMES);
    v->reset_flash = f->reset_flash;
    v->mode = f->mode;
    v->select_open = f->select_open;
    v->ov_key = f->ov.key;
}
