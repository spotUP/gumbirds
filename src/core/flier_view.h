/*
 * flier_view.h - which Sootling frame a flier shows. Pure, host tested (tests/host/test_flier_view.c); the Neo Geo
 * glue in src/main.c turns the frame into sprite registers. The sheet is a set of clips (assets/flier/sootling_sheet.json,
 * imported from the draft frames.json by tools/import_flier_sheet.py; the build writes the clip table and the per frame
 * ticks to build/gen/sootling_tables.h, src/main.c passes them in as FlierClips, so no timing number lives in C):
 *   flap2 / flap1  steady clips for 2 / 1 balloons in the air: played once per flap press (Flier.flapped), a press while
 *                  it plays restarts it, between presses the flier holds the rest frame (the clip's first frame)
 *   walk / land / breathe  ground clips, one per balloon count 0, 1, 2 (arrays indexed by balloons): walk while the flier
 *                  moves, breathe while it stands, land is a one shot started when it touches the ground
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
    uint8_t walk[3], land[3], breathe[3];                  /* ground clip numbers, indexed by balloon count 0, 1, 2 */
} FlierClips;

typedef struct {
    uint8_t clip, frame, tick; /* clip playing, frame within it, ticks spent on that frame */
    uint8_t balloons;          /* balloons seen last step */
    uint8_t started;
    uint8_t prev_ground;       /* grounded last step (the 0 -> 1 edge starts the landing clip) */
    uint8_t flapping;          /* 1 while a flap clip plays, 0 = parked on its first frame */
} FlierAnim;

void flier_anim_init(FlierAnim *a);
/* One video frame for flier f. Returns the sheet frame to draw; *flip is 1 when it must be mirrored (facing left). */
uint8_t flier_anim_step(FlierAnim *a, const Flier *f, const FlierClips *c, int *flip);

/* Blink while protected (invincible or spawn_inv): 1 when the flier is drawn on this frame. A protected ALIVE or PARACHUTE flier
 * is shown FLIER_BLINK_HALF_PERIOD frames, then hidden as many; FALLING and later, and an unprotected flier, are always shown.
 * Pure; the glue passes Game.frame (advanced by game_step_arena and game_step_trip) and keeps stepping the animation while hidden. */
int flier_view_visible(const Flier *f, uint32_t frame);

/* Body drawing rules for a dead flier (state >= FLIER_FALLING). flier_body_visible: any part of the sprite is still on
 * the screen, so the glue keeps drawing it (it falls behind the hazard art until the sprite is fully off screen).
 * flier_body_front: a body that bounced on spikes draws in front of the spike art (dead body slots, sprite_slots.h). */
int flier_body_visible(const Flier *f);
int flier_body_front(const Flier *f);

#endif
