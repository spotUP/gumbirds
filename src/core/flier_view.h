/*
 * flier_view.h - which Sootling frame a flier shows. Pure, host tested (tests/host/test_flier_view.c); the Neo Geo
 * glue in src/main.c turns the frame into sprite registers. The sheet is a set of clips (assets/flier/sootling_sheet.json,
 * imported from the draft frames.json by tools/import_flier_sheet.py; the build writes the clip table and the per frame
 * ticks to build/gen/sootling_tables.h, src/main.c passes them in as FlierClips, so no timing number lives in C):
 *   flap2 / flap1  steady clips for 2 / 1 balloons, advance while the flier is in the air, rest on frame 0 on the ground
 *   idle           no balloons (also on a parachute)         fall   dead and falling
 *   pop2 / pop1    one shot, played when the 2nd / last balloon pops (a pop from 2 to 0 plays pop1)
 *   inflate        one shot, played when a balloon is gained and when a flier first shows (not with 0 balloons)
 * A one shot plays to its end, then the steady clip of the moment takes over; falling cuts an inflate short.
 * Each frame lasts its number of 60 Hz ticks. The sprite is mirrored when the flier faces left.
 */
#ifndef BRAWL_FLIER_VIEW_H
#define BRAWL_FLIER_VIEW_H

#include "flier.h"

typedef struct {
    const uint8_t *first, *count, *loop; /* per clip: first sheet frame, frames, 1 if it loops */
    const uint8_t *ticks;                /* per sheet frame: 60 Hz ticks it is shown */
    uint8_t flap2, flap1, pop2, pop1, inflate, fall, idle; /* clip numbers */
} FlierClips;

typedef struct {
    uint8_t clip, frame, tick; /* clip playing, frame within it, ticks spent on that frame */
    uint8_t balloons;          /* balloons seen last step */
    uint8_t started;
} FlierAnim;

void flier_anim_init(FlierAnim *a);
/* One video frame for flier f. Returns the sheet frame to draw; *flip is 1 when it must be mirrored (facing left). */
uint8_t flier_anim_step(FlierAnim *a, const Flier *f, const FlierClips *c, int *flip);

#endif
