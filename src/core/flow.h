/*
 * flow.h - top-level screen flow for Bubblegum Brawl. Portable C99, no libc, no drawing.
 *
 * States: attract (title, high score table, demo play) cycling by knob durations; PLAYING;
 * GAME_OVER; NAME_ENTRY (only when the score ranks); SAVE_REMINDER (open the MiSTer menu
 * before power-off); then the table with the new row highlighted.
 *
 * Coins, credits and the start button are handled by the Neo Geo BIOS, so the caller passes
 * a start_pressed event (1 for one frame when a credited start happens) and a free running
 * frame counter, which seeds the game and the demo.
 *
 * Saving: the flow never touches backup RAM. It sets f->dirty to 1 whenever the table changed
 * (new entry, operator reset). The platform layer serialises f->tables with score_serialise,
 * writes it, and clears f->dirty. flow_init takes the backup RAM image (or NULL / bad image
 * for the defaults).
 *
 * Operator reset: on the title screen, hold A+B+C+D together for RESET_HOLD_FRAMES (3 s).
 * The table goes back to the factory defaults and dirty is set. The combo must be released
 * before it can fire again. Start presses are ignored while all four are held.
 *
 * Renderer: read flow_view(). Everything is read only; the renderer must not modify it.
 */
#ifndef BRAWL_FLOW_H
#define BRAWL_FLOW_H

#include <stdint.h>
#include <stddef.h>
#include "tuning.h"
#include "rng.h"
#include "game.h"
#include "hiscore.h"
#include "score_table.h"
#include "nameentry.h"

typedef enum {
    FLOW_ATTRACT_TITLE = 0,
    FLOW_ATTRACT_TABLE,
    FLOW_ATTRACT_DEMO,
    FLOW_PLAYING,
    FLOW_GAME_OVER,
    FLOW_NAME_ENTRY,
    FLOW_SAVE_REMINDER
} FlowState;

#define FLOW_RESET_COMBO (IN_A | IN_B | IN_C | IN_D)

typedef struct {
    uint8_t state;           /* FlowState */
    uint16_t timer;          /* frames spent in this state (saturates at 65535) */
    uint8_t dirty;           /* 1 = table changed, platform must write backup RAM and clear */
    int8_t highlight;        /* table row to highlight, -1 for none */
    int8_t new_row;          /* row of the entry made this run, -1 for none */
    uint8_t mode;            /* GameMode picked on the title (up or down edge toggles); default arena; kept across runs */
    uint8_t input_prev;      /* held input last frame, for the title edge */
    uint8_t select_open;     /* 1 after the first start press: mode select is open, the next start on the title begins the game */
    uint8_t demo;            /* 1 when game is the attract demo */
    uint8_t reset_flash;     /* 1 for the frames after an operator reset (draw a message) */
    uint16_t reset_hold;     /* frames the reset combo has been held */
    uint8_t reset_fired;     /* combo already fired, wait for release */
    uint32_t last_score;     /* score of the last real run */
    uint8_t last_mode;       /* GameMode of the last real run: its table is scored and shown after the run */
    ScoreTables tables;      /* one table per GameMode (score_table.h) */
    Game game;
    NameEntry entry;
} Flow;

typedef struct {
    FlowState state;
    uint16_t timer;
    const HiscoreTable *table;  /* the table to draw: tables.t[table_mode] */
    uint8_t table_mode;      /* GameMode of *table (title: picked mode; attract table: alternates; else the run) */
    int highlight;           /* -1 unless table_mode is the mode of the run that made the entry */
    const Game *game;        /* valid in PLAYING, GAME_OVER and ATTRACT_DEMO */
    const NameEntry *entry;  /* valid in NAME_ENTRY: name, pos, sym[] */
    uint32_t score;          /* score to show on game over / name entry / reminder */
    int reset_progress;      /* 0..100 percent of the reset hold, for a progress bar */
    int reset_flash;
    uint8_t mode;            /* GameMode highlighted on the title */
    uint8_t select_open;     /* title: mode select opened by a start press */
} FlowView;

/* Start in ATTRACT_TITLE. image/len is the backup RAM content (NULL allowed: defaults). */
void flow_init(Flow *f, const uint8_t *image, size_t len);

/* One frame. input is the raw held bits (IN_A..IN_D, IN_UP..IN_RIGHT). start_pressed is 1
 * on the frame a credited start happens. frame_counter is a free running counter. */
void flow_step(Flow *f, uint8_t input, uint8_t start_pressed, uint32_t frame_counter);

void flow_view(const Flow *f, FlowView *v);

#endif
