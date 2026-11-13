/*
 * arcade.h - arcade mode core: stage loop, rival ranks, gum carry-over, bonus stage, score clamp.
 * Pure logic. Portable C99, no malloc, no float, no globals but const tables. The numbers live here until the wiring step moves them to tuning.h.
 */
#ifndef BRAWL_ARCADE_H
#define BRAWL_ARCADE_H

#include <stdint.h>
#include "rng.h"
#include "tuning.h" /* ARC_LIVES_START */

/* ---- numbers (own first values, tuned in play) ---- */
#define ARC_STAGE_COUNT 12            /* stages in one pass */
#define ARC_LOOP_STAGE 4              /* after stage 12 and its bonus the run restarts here (1 based) */
#define ARC_BONUS_EVERY 3             /* a bonus stage follows every third stage */
#define ARC_CLEAR_FRAMES 120          /* CLEAR interstitial */
#define ARC_GUM_HEAL 2                /* gum after a bonus stage or on a new life */
#define ARC_GUM_MAX 2
#define ARC_RANK_MAX 3
#define ARC_BONUS_BUBBLES 20
/* Pool of live bubbles; a spawn is skipped when all are live. The reference has 10 slots, but at its pace no more than 8 are ever alive:
 * a 9th needs 8 spawn gaps of 40+ frames (320) while the longest rise (lowest nozzle top to 16 px past the top at 0.5 px/frame) is
 * 312 frames, so 8 slots play exactly the same. tests/host/test_arcade.c checks the bound; 10 live measured logic end 219..222 with
 * missed frames (make test-arcade-bonus stress fill), 8 live max 214. */
#define ARC_BONUS_LIVE_MAX 8
#define ARC_BONUS_SPAWN_MIN 40        /* spawn timer reload = MIN + (random & MASK) frames: 40..103 (reference) */
#define ARC_BONUS_SPAWN_MASK 63
#define ARC_BONUS_PUFF_FRAMES 16      /* frames the nozzle mouth puffs when a bubble leaves (4 art frames, 4 each) */
#define ARC_BONUS_STRAIGHT 40         /* px a bubble rises straight above its nozzle top before it starts to sway */
#define ARC_NOZZLE_COUNT 4
#define ARC_NOZZLE_W 32               /* nozzle art width, px */
#define ARC_FLOOR_Y 164               /* top of the bonus floor strip, px */
#define ARC_LAYOUT_BONUS 24           /* stage.c layout of the bonus stage: floor strip and nozzle tops, no islands */
#define ARC_BONUS_BOX 16              /* bubble box, px */
#define ARC_BONUS_WORLD_W 384
#define ARC_LAYOUT_NONE (-1)
#define ARC_LAYOUT_BASE 12 /* arcade stage n plays stage.c layout ARC_LAYOUT_BASE + n - 1 (the arena layouts 0..11 stay untouched) */
#define ARC_PUMP_STAGES 4             /* blow-up animation steps: progress runs 0..ARC_PUMP_STAGES */
#define ARC_CONTINUE_SECONDS 10       /* continue countdown at 60 Hz (own first value) */
#define ARC_CONTINUE_FRAMES (ARC_CONTINUE_SECONDS * 60)
#define ARC_BONUS_MIN_VISIBLE 290     /* reach rule: even the fastest bubble (bonus 5, reference pace 0.65625 px/frame) stays inside the 0..FLIER_WORLD_H screen rows at least this many frames (298 measured; was 300 at the old own speeds) */

typedef enum { ARC_PLAY = 0, ARC_CLEAR, ARC_BONUS, ARC_OVER } ArcState;

typedef struct {
    int16_t pump_frames;   /* grounded rival blows up gum this long; air spawns skip it */
    uint16_t pop_score;
    uint16_t defeat_score; /* also paid by a parachute finish */
} ArcRank;

typedef struct {
    int stage;             /* 1 based, 1..ARC_STAGE_COUNT */
    int loops;             /* completed passes */
    int bonus_no;          /* number of the bonus stage being played or last played; 0 before the first */
    ArcState state;
    int timer;             /* CLEAR countdown */
    int gum;               /* carried gum count */
} ArcRun;

typedef struct {
    int32_t y16;           /* top of the bubble, 16.16 px */
    int16_t x;             /* left, px */
    uint8_t live;          /* 0 free pool slot, 1 rising */
    uint8_t nozzle;        /* nozzle it came out of */
    int16_t x0;            /* left of the rising line, px; x = x0 + sway */
    uint16_t age;          /* frames since it left the nozzle */
    uint8_t ph;            /* sway sine index 0..24 */
    uint8_t amp;           /* sway amplitude 1..16 px */
} ArcBubble;

typedef struct {
    ArcBubble b[ARC_BONUS_LIVE_MAX]; /* pool; the slot index is the bubble's sprite slot */
    Rng rng;
    int16_t timer;         /* frames to the next spawn */
    int spawned;           /* of ARC_BONUS_BUBBLES */
    int number;            /* bonus number, 1 based */
    int frame;
    int caught;
    int over;
    int perfect;
    int nlive;             /* bubbles alive now */
    uint8_t puff[ARC_NOZZLE_COUNT]; /* frames of mouth puff left per nozzle (drawn by main.c) */
} ArcBonus;

/* Stage table lookups, stage 1 based. Name is the draft id ("R01"); layout is the stage.c layout index (ARC_LAYOUT_NONE for a stage without a layout; all 12 are built). */
const char *arc_stage_name(int stage);
int arc_stage_layout(int stage);
int arc_rank_for(int stage, int loops);
const ArcRank *arc_rank(int rank);       /* rank 1..3, clamped */

void arc_start(ArcRun *r);
/* Call when every rival is defeated: stage-clear interstitial begins. */
void arc_stage_cleared(ArcRun *r);
/* One frame. After the CLEAR timer: a bonus stage (stage % 3 == 0) or the next stage. Returns 1 when the state changed to PLAY (new stage begins). */
int arc_step(ArcRun *r);
/* Call when the bonus stage has ended: moves to the next stage. */
void arc_bonus_done(ArcRun *r);
int arc_next_stage(int stage);           /* stage after the bonus: 12 -> 4 */

int arc_gum_after_stage(int gum);        /* carry: clamp 0..ARC_GUM_MAX */
int arc_gum_on_bonus(void);
int arc_gum_on_new_life(void);

uint32_t arc_score_add(uint32_t score, uint32_t points); /* clamps at SCORE_CAP, never wraps */

int32_t arc_bonus_speed16(int number);   /* 16.16 px per frame, bonus number 1 based (5 and up the same) */
int arc_bonus_value(int number);         /* points per popped bubble: 300 / 500 / 700 / 700 / 700 */
int arc_bonus_perfect(int number);       /* all 20 popped: 10000 / 15000 / 20000 / 25000 / 30000 */
int arc_nozzle_x(int i);                 /* left, px */
int arc_nozzle_top(int i);               /* top, px; the solid top of the stage.c bonus layout */
void arc_bonus_init(ArcBonus *b, int number, uint32_t seed);
/* One frame; when armed (the player still has a gum), the caller's rectangle (px) pops bubbles it overlaps. Returns bubbles popped this frame. No score is added. */
int arc_bonus_step(ArcBonus *b, int armed, int rx, int ry, int rw, int rh);


/* ---- rival pump-up (FQ4): one ArcPump per rival slot ---- */
typedef enum { ARC_PUMP_IDLE = 0, ARC_PUMP_PUMPING, ARC_PUMP_FLYING, ARC_PUMP_DEFEATED } ArcPumpState;
typedef struct { uint8_t state; uint8_t rank; int16_t frame; } ArcPump;
/* Grounded spawn blows up gum for the rank's pump_frames; an air spawn skips straight to FLYING. */
void arc_pump_start(ArcPump *p, int rank, int grounded);
void arc_pump_step(ArcPump *p);           /* one frame; PUMPING becomes FLYING when the window ends */
int arc_pump_in_window(const ArcPump *p); /* 1 while PUMPING */
/* A stomp or bump: inside the window the rival is defeated and the rank defeat score is returned; outside it returns 0 and changes nothing. */
uint32_t arc_pump_resolve(ArcPump *p);
int arc_pump_progress(const ArcPump *p);  /* 0..ARC_PUMP_STAGES from elapsed frames, monotonic; air spawns stay 0 */

/* ---- lives and continue ---- */
typedef enum { ARC_LIFE_PLAY = 0, ARC_LIFE_CONTINUE, ARC_LIFE_ENDED } ArcLifeState;
typedef struct { int lives; int gum; uint32_t score; int state; int countdown; } ArcLives;
void arc_lives_start(ArcLives *l);
/* The player lost a life: lives--, gum heals to ARC_GUM_HEAL for the next life; at 0 lives the continue countdown starts. */
void arc_lose_life(ArcLives *l);
/* One frame of the continue state. start_pressed with credits > 0 continues (full lives, score 0, gum healed, same stage: the caller keeps the stage) and returns 1 credit used; timeout ends the run. */
int arc_continue_step(ArcLives *l, int start_pressed, int credits);
int arc_continue_seconds(const ArcLives *l); /* digit to show, 10..0 */

#endif
