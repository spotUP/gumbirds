#ifndef SPLASH_H
#define SPLASH_H
/* The splash of a flier falling into water or lava: one 3 column sprite (slots SPLASH_SPRITE..+SPLASH_COUNT-1), drawn behind the liquid. */
#include <stdint.h>
#include <ngdevkit/types.h>

extern volatile u16 g_splash_draws;  /* frames the splash was placed: the test's proof the code ran */

void splash_load_palettes(void);
/* Per frame. active 0 (not playing) hides it. start 1: a flier crossed a liquid line of hazard kind at world x (restarts a running splash).
 * cam_px is the wrapped camera x. */
void splash_update(int active, int start, uint8_t kind, int32_t x, int cam_px);
#endif
