#ifndef HAZARD_H
#define HAZARD_H
/*
 * Hazard strip along the bottom of the screen (build plan G3, visual only: no rule reads it). One hazard per
 * match, rotating spikes, fire, water, lava. Each hazard has 16 frames: the LSPC auto-animation steps through 8
 * tile numbers by itself (SCB1 attribute bit 3), and two strips of 24 sprites hold frames 0..7 (bank 0) and 8..15
 * (bank 1). gfx_flush shows one bank and hides the other each time the animation counter wraps, so after the
 * match start the CPU writes no SCB1 word and no per frame word at all (tests/mame/hazard_check.lua).
 * The animation speed is the hazard's frames per step; the star twinkle shares the one counter and follows it.
 */
#include <ngdevkit/types.h>
#include "core/hazard_kind.h" /* kinds, strip top line, kill lines (shared with the core) */

#define HAZARD_STRIP_COLS 24 /* 384 px = the arena: 6 groups of 4 sprite columns, variants repeat A B C A B C (nv 1, 2, 3 all divide 6, so the wrap seam is a tile boundary) */
#define HAZARD_STRIP_ROWS 2  /* 32 px, screen lines 192..223 */

/* Kind the core must use now: the shown strip, or the one the next strip will show (demo, title, a play starting this frame). */
u8 hazard_kind_now(void);

void hazard_load_palettes(void);
void hazard_init(void);               /* hide both banks; the hardware state is unknown (video_init) */
void hazard_step(u8 match_running, int cam_px); /* per frame: starts the strip on the rise of match_running, hides it on the fall; the strip scrolls with the world: head x = -cam_px, written (SCB4, both banks) only when it changed */

extern volatile s16 g_hazard_x;       /* head x last sent (test sentinel, 0x7FFF before the first strip) */
extern volatile u8 g_hazard_kind;     /* 0xFF while no strip is shown (test sentinel) */
extern volatile u16 g_hazard_matches; /* strips started since boot (test sentinel) */
#endif
