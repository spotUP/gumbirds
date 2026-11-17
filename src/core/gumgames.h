#ifndef GUMGAMES_H
#define GUMGAMES_H
#include <stdint.h>

/* Gum Games event framework (pure logic, no hardware): shared by Big Blow, Burst Race and Bubble Gather. */

#define GG_EVENTS 3u          /* Big Blow, Burst Race, Bubble Gather (record slots 0..2, 3..5 are spare) */
#define GG_ATTEMPTS 3u        /* retry tickets per player per event */
#define GG_QUALIFY_POINTS 500u
#define GG_STAGE_POINTS 100u

enum { GG_BIG_BLOW, GG_BURST_RACE, GG_BUBBLE_GATHER };

/* Alternate A/B mash counter: a press counts only when it is the other button than the last counted one. */
typedef struct { uint8_t last; uint16_t count; } GgMash;
void gg_mash_reset(GgMash *m);
/* in = input byte this frame, prev = last frame. Returns 1 when this frame counted a press. */
int gg_mash_step(GgMash *m, uint8_t in, uint8_t prev);

/* Hold-release on C: charge grows while C is held; releasing returns the charge (0 until released). */
typedef struct { uint16_t charge; } GgHold;
uint16_t gg_hold_step(GgHold *h, uint8_t in, uint16_t cap);

/* Fix-layer power bar: writes only the cells that change. Each out entry = cell index, bit 7 set = filled. */
typedef struct { uint8_t width, filled; } GgBar;
int gg_bar_set(GgBar *b, uint8_t filled, uint8_t *out, int max);

/* Event sequencing for one event: marks, retry tickets, points, whose turn it is. */
typedef struct {
    uint8_t event, players;
    uint8_t turn;                       /* 0 = P1, 1 = P2 (alternates after each attempt) */
    uint8_t tickets[2];                 /* attempts left per player */
    uint8_t qualified[2];               /* qualifying mark per player */
    uint32_t points[2];
    uint32_t best[2];                   /* best result so far per player (event meaning: size, time...) */
} GgSeq;
void gg_seq_start(GgSeq *s, uint8_t event, uint8_t players);
uint32_t gg_points(uint8_t stage, int qualified);
/* End of an attempt by the player whose turn it is: records best, marks, points, spends a ticket, hands the turn over.
 * Returns 1 while attempts remain for someone, 0 when the event is over. */
int gg_seq_attempt(GgSeq *s, uint32_t result, uint8_t stage, int qualified);
/* Input byte of the player whose turn it is (P2 reads input2 only in a 2P game). */
uint8_t gg_seq_input(const GgSeq *s, uint8_t in1, uint8_t in2);
#endif
