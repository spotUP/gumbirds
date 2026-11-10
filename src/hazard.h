#ifndef HAZARD_H
#define HAZARD_H
/*
 * Hazard strip along the bottom of the screen (build plan G3, visual only: no rule reads it). One hazard per
 * match, rotating spikes, fire, water, lava. Each hazard has 16 frames: the LSPC auto-animation steps through 8
 * tile numbers by itself (SCB1 attribute bit 3), and two strips of 20 sprites hold frames 0..7 (bank 0) and 8..15
 * (bank 1). gfx_flush shows one bank and hides the other each time the animation counter wraps, so after the
 * match start the CPU writes no SCB1 word and no per frame word at all (tests/mame/hazard_check.lua).
 * The animation speed is the hazard's frames per step; the star twinkle shares the one counter and follows it.
 */
#include <ngdevkit/types.h>

#define HAZARD_KINDS 4
#define HAZARD_STRIP_COLS 20 /* 320 px = 5 variants of 4 sprite columns */
#define HAZARD_STRIP_ROWS 2  /* 32 px, screen lines 192..223 */
#define HAZARD_STRIP_Y 192

/* Kind of match number n (0 for the first match). */
static inline u8 hazard_kind_for_match(u16 n) { return (u8)(n % HAZARD_KINDS); }

void hazard_load_palettes(void);
void hazard_init(void);               /* hide both banks; the hardware state is unknown (video_init) */
void hazard_step(u8 match_running);   /* per frame: starts the strip on the rise of match_running, hides it on the fall */

extern volatile u8 g_hazard_kind;     /* 0xFF while no strip is shown (test sentinel) */
extern volatile u16 g_hazard_matches; /* strips started since boot (test sentinel) */
#endif
