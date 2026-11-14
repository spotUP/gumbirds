/* Arcade bonus stage result screen: state and timing only (pure, host-testable). Order after the stage ends, in frames:
 * wait 20, popped count; wait 20, points each; balloons vanish (event), wait 2, total; wait 20; perfect: ticket and jingle;
 * wait 120; tally (100 points per 2 frames, the total counts down while the score rises, one tick event per step); wait 10;
 * perfect: bonus added at once (event), wait 20; then the screen holds until the player presses (A or Start), no timeout:
 * the attract demo never reaches a bonus stage. Spec: thoughts/spot/2026-11-13-bonus-ref.md section 6.
 * The score is added only by the tally and the perfect bonus, through the points res_step returns. Drawing: result_view.h. */
#ifndef CORE_RESULT_H
#define CORE_RESULT_H
#include <stdint.h>

#define RES_SLOTS 20

#define RES_EV_VANISH 1  /* balloons vanish */
#define RES_EV_TICK 2    /* one tally step */
#define RES_EV_JINGLE 4  /* the perfect box appears */
#define RES_EV_BONUS 8   /* the perfect bonus is added */

#define RES_SHOW_POPPED 1
#define RES_SHOW_EACH 2
#define RES_SHOW_TOTAL 4

#define RES_DIRTY_POPPED 1  /* the popped / each line */
#define RES_DIRTY_CAGE 2     /* unused: the cage is sprites now */
#define RES_DIRTY_MACHINE 4
#define RES_DIRTY_SCORE 8
#define RES_DIRTY_TICKET 16
#define RES_DIRTY_ALL 31

typedef struct {
    uint8_t active;
    uint8_t phase;
    uint8_t wait;
    uint8_t caught, perfect, show, vanished;
    uint8_t ticket;        /* 0 none, 1 PERFECT box, 2 bonus added */
    uint8_t events;        /* RES_EV_* of the last step, kept for the sound code (game.c sets it) */
    uint8_t dirty;         /* RES_DIRTY_* regions changed since the view last cleared them */
    uint16_t each;         /* points per popped bubble */
    uint32_t bonus;        /* perfect bonus, 0 when not perfect */
    uint32_t total_left;   /* tally still to add; shown as the total */
    uint32_t score_shown;
    /* Moving parts (sprites, main.c draw_result_fx). All of it follows the fields above; none of it changes the timing. */
    uint16_t t;            /* frames since the start */
    uint8_t pop[RES_SLOTS]; /* per bubble: 0 whole, 1..6 popping, 7 gone */
    uint8_t pop_cur;       /* bubbles popped so far (pop order: resp_order, top of the pile first) */
    uint16_t pop_acc;      /* tally points not yet paid for with a popped bubble */
    uint8_t digit[5];      /* decimal digits of total_left, most significant first */
    uint8_t wheel[5];      /* counter wheel positions, 16 per digit, 0..159 */
    uint8_t crank;         /* crank frame 0..7, one step per tally tick */
    uint8_t ticket_out;    /* pixels the ticket has slid out, 0..40 */
    uint8_t lines;         /* ticket text lines printed: 1 PERFECT, 2 the line under it */
} Result;

void res_start(Result *r, int caught, int number, int perfect, uint32_t score);
/* One frame. Returns RES_EV_* bits; *add gets the points to add to the score this frame (multiple of 100, usually 0).
 * press: a new A or Start press this frame (an edge, so a button held from the tally does not skip the hold). */
uint8_t res_step(Result *r, uint32_t *add, uint8_t press);
/* Bubble i this frame: 0 hidden, else 1 + sprite frame (0 whole, 1..3 pop); *x, *y = centre in cage window pixels. */
uint8_t res_bubble(const Result *r, int i, int *x, int *y);

#endif
