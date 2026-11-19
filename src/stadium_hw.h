#ifndef STADIUM_HW_H
#define STADIUM_HW_H
/* Stadium stands of the ground events (Big Blow, Burst Race, Gum Fling) as sprites: two merged groups of full-width columns
 * (tools/build_stadium_sprites.py, build/gen/stadium_layout.h) plus four tower columns, filled and animated through the vram queue.
 * The pure crowd logic is src/core/stadium.c; this file only places and writes it. */
#include <ngdevkit/types.h>

/* Per frame. on 0 hides the stands (and forgets the crowd); on 1 loads them hidden, show 1 reveals them once every strip, palette
 * and the first crowd pass are loaded. fling 1 = the Gum Fling plane (23 columns, follows the field at 1/4 speed by scroll px). */
void stadium_hw_step(int on, int show, u8 mood, int fling, int scroll);
u8 stadium_hw_loaded(void);                     /* everything is loaded (the entry hold may end) */
void stadium_hw_scores(u8 p1, u8 p2);           /* a rise cheers on that side, the scoreboard shows the scores */
void stadium_hw_finish(int winner);             /* 0 or 1 wins, -1 draw; call once at the result */
void stadium_hw_wave(void);                     /* both sides roll the wave once */
#endif
