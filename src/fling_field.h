#ifndef FLING_FIELD_H
#define FLING_FIELD_H
/* Gum Fling grass field (owner 2026-11-18: one field for the whole event, no scene cut): turf ring, foul line and distance boards, landing puff. */
#include <ngdevkit/types.h>
#include "core/gg_fling.h"

/* Per frame. on 0 hides the field (and hands the island slots back); on 1 loads it hidden, show 1 reveals it once every tile is loaded. tug 1 paints the Tug Gum chalk lines into three turf columns. */
void fling_field_step(const GgFling *f, u8 mood, int on, int show, int markers, int tug);
u8 fling_field_loaded(void); /* every tile is loaded (the entry hold may end) */
#endif
