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

/* Big Blow (event 1): mash A and B to inflate the bubble, stop before it bursts. Size 0..GG_BLOW_MAX, stage = size / GG_BLOW_STAGE. */
#define GG_BLOW_MAX 64u
#define GG_BLOW_STAGE 16u
#define GG_BLOW_PER_PRESS 3u
#define GG_BLOW_LEAK_MASK 7u           /* size drops by 1 every 8th frame */
#define GG_BLOW_QUALIFY_STAGE 3u       /* size 48 or more */
#define GG_BLOW_CLOCK 480u
#define GG_BLOW_INTRO_FRAMES 150u
#define GG_BLOW_BURST_FRAMES 60u
#define GG_BLOW_RESULT_FRAMES 150u
enum { GG_BLOW_INTRO, GG_BLOW_PLAY, GG_BLOW_BURST, GG_BLOW_RESULT, GG_BLOW_END };
typedef struct {
    GgSeq seq;
    GgMash mash;
    uint8_t phase, size, prev, more, burst;
    uint16_t timer, clock;
    uint8_t last_size, last_stage, last_qualified;   /* the attempt just played, shown on the result screen */
    uint32_t last_points;
} GgBlow;
void gg_blow_start(GgBlow *b, uint8_t players);
/* One frame; in1/in2 = the two players' input bytes (the turn picks one). */
void gg_blow_step(GgBlow *b, uint8_t in1, uint8_t in2);
#endif
