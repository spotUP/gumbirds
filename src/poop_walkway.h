#ifndef POOP_WALKWAY_H
#define POOP_WALKWAY_H
/* Poop the Man pavement band (owner 2026-11-22, strip_2): 20 sprite columns over backdrop rows 160..223 and a dithered contact shadow under each walker. */
#include <ngdevkit/types.h>
#include "core/gg_poop.h"

/* Per frame. on 0 hides the band (and hands the island slots back); on 1 loads it hidden, show 1 reveals it once every tile is loaded. */
void poop_walkway_step(const GgPoop *p, u8 mood, int on, int show);
u8 poop_walkway_loaded(void); /* every column is loaded (the entry hold may end) */
#endif
