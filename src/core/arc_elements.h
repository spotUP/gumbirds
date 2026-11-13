/*
 * arc_elements.h - arcade stage elements: smog vent, gum flipper, drain grabber, updraft grate.
 * Pure logic, C99, no malloc, no float, no RNG. Positions are whole pixels, flier velocities are 16.16 (flier.h).
 * Art numbers come from thoughts/spot/2026-11-12-arcade-art-final.md; every other number is an own first value (marked VETO).
 * Stage index is the 0 based position in the proposed arcade order: R01 R02 N05 N03 N06 N04 N08 N02 N09 R10 R07 R12b.
 */
#ifndef BRAWL_ARC_ELEMENTS_H
#define BRAWL_ARC_ELEMENTS_H

#include <stdint.h>

#define ARC_ELEM_MAX 5          /* elements per stage */

/* ---- smog vent (art: loop 336 ticks, idle 0..143, telegraph 144..215, launch at 216) ---- */
#define ARC_VENT_LOOP 336
#define ARC_VENT_LAUNCH 216
#define ARC_VENT_BURST_TICKS 40 /* VETO: plume hurts this long from launch (spark rises 2.6 px per tick) */
#define ARC_VENT_HALF_W 10      /* VETO: plume half width, px */
#define ARC_VENT_PLUME_H 48     /* VETO: plume height above the vent top, px */

/* ---- gum flipper (art: hit box 28 x 28 centred, set A) ---- */
#define ARC_FLIP_HALF 14
#define ARC_FLIP_SPEED 98304    /* VETO: speed given to each axis on a bounce, 16.16 (1.5 px per tick) */

/* ---- drain grabber (art: 12 frames, grab frames 5..7, hit x 12..28 y 6..44 of a 40 x 44 frame) ---- */
#define ARC_GRAB_FRAMES 12
#define ARC_GRAB_HIT_FIRST 5
#define ARC_GRAB_HIT_LAST 7
#define ARC_GRAB_HALF_W 8
#define ARC_GRAB_HIT_H 38       /* rows 6..44 */
/* Trigger rule (thoughts/spot/2026-11-13-grabber-trigger.md, own numbers): the hand waits hidden (timer 0) and patrols its x range;
   it rises (timer 1..) only while a flier with balloons is low over the water at its x, bites only if a low flier is still at its x when the
   rise ends, retreats at once (straight to the sink frames) if none is, and follows the target x while rising. */
#define ARC_GRAB_LOOP 71        /* active ticks: sum of the 12 art frame ticks (test_arc_elements asserts it) */
#define ARC_GRAB_RISE 29        /* ticks of art frames 0..4: the hand comes up; the bite (frames 5..7, 20 ticks) follows */
#define ARC_GRAB_SINK_AT 50     /* timer value of art frame 8, the sink; a retreat jumps here */
#define ARC_GRAB_LOW_DY 18      /* VETO: a flier is low when its centre is this far above the water line: feet about 12 px over the surface (reference rule: the hand only answers fliers skimming the water; was 42, which raised it under fliers in mid air) */
#define ARC_GRAB_PATROL 1       /* px per tick the hidden hand moves, wrapping from the right end to the left end */
#define ARC_GRAB_TRIG_DX 6      /* VETO: a low flier within this many px of the hidden hand's x starts the rise */
#define ARC_GRAB_TRACK_DX 16    /* VETO: a rising hand keeps a target within this many px; the hand slides to its x */
#define ARC_GRAB_FOLLOW 4       /* VETO: max px per tick the rising hand slides toward the target */

/* ---- updraft grate (art: zone 32 wide, 48 above the hatch top) ---- */
#define ARC_GRATE_HALF_W 16
#define ARC_GRATE_H 48
#define ARC_GRATE_LIFT 3000     /* VETO: vy delta per tick while inside, 16.16 (about 0.046 px/tick^2, steeper than gravity 2048) */

typedef enum { ARC_EL_NONE = 0, ARC_EL_VENT, ARC_EL_FLIPPER, ARC_EL_GRABBER, ARC_EL_GRATE } ArcElKind;

typedef struct {
    uint8_t kind;      /* ArcElKind */
    int16_t x, y;      /* vent/grate: centre x, top y. flipper: centre. grabber: x set by step, y = water line */
    uint16_t timer;    /* ticks into the cycle */
    int16_t param;     /* grabber: right end of its x range (x is the left end until step moves it); else 0 */
    int16_t x0;        /* grabber: left end of its x range */
    uint16_t cycle;    /* grabber: rises started so far */
} ArcElement;

/* ---- rival avoidance (src/core/game.c steers a rival away from an element that would hurt it) ---- */
#define ARC_VENT_TELEGRAPH 144  /* art: telegraph 144..215 */
#define ARC_AVOID_PAD 8         /* VETO: px added to each kill box half extent for rival avoidance */
#define ARC_AVOID_LOOK 40       /* VETO: sideways px a rival looks ahead of a vent plume; air steering is one flap thrust per flap, so a reversal needs about 30 frames and 40 px */
#define ARC_AVOID_AHEAD 16      /* VETO: ticks of current vx added to the flier x before picking the escape side (damps overshoot) */
#define ARC_AVOID_REACH (ARC_VENT_HALF_W + 2 + ARC_AVOID_PAD)   /* 20: vent half width + flier half width (2) + pad; the spawn rule uses it */

#define ARC_LOW_MAX 8           /* fliers noted per tick (player + rivals) */
typedef struct {
    ArcElement el[ARC_ELEM_MAX]; uint8_t n;
    uint8_t nlow; int16_t low_x[ARC_LOW_MAX], low_y[ARC_LOW_MAX];   /* fliers with balloons noted this tick (arc_elements_note_low), cleared by step */
} ArcElements;

/* stage_index out of 0..11 gives an empty table. */
void arc_elements_init(ArcElements *a, int stage_index);
/* One tick. Call arc_elements_note_low for every living flier with balloons first; the grabber reads them. */
void arc_elements_step(ArcElements *a);
void arc_elements_note_low(ArcElements *a, int cx, int cy);
/* Rival steering: -1 / +1 = the way out of the nearest threatening element (vent telegraphing or bursting, grabber hand while the box
   is low over the water near it), 0 = none. Threat boxes are arc_elements_kill's grown by ARC_AVOID_PAD (vent: ARC_AVOID_LOOK sideways);
   nearest and side are judged at x + vx * ARC_AVOID_AHEAD (vx 16.16). */
int arc_elements_avoid_dir(const ArcElements *a, int cx, int cy, int hw, int hh, int32_t vx);

/* A flier box is centre (cx, cy) and half extents (hw, hh) in whole pixels. Edges inclusive (trip_hit.h convention). */
int arc_elements_kill(const ArcElements *a, int cx, int cy, int hw, int hh);   /* vent plume active or grabber hand closed */
/* Flipper: if the box touches one, set *vx / *vy (16.16) to ARC_FLIP_SPEED away from its centre and return 1. */
int arc_elements_bounce(const ArcElements *a, int cx, int cy, int hw, int hh, int32_t *vx, int32_t *vy);
int32_t arc_elements_lift(const ArcElements *a, int cx, int cy, int hw, int hh);   /* summed vy delta (negative is up), 0 outside */
int arc_elements_grab_frame(uint16_t timer);   /* grabber frame 0..ARC_GRAB_FRAMES-1 for its timer, -1 while hidden (timer 0) (used by arc_view) */

#endif
