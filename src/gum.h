#ifndef GUM_H
#define GUM_H
/* The player's gum bubble in Gum Trip: one 1 or 2 column sprite above the bird (slots GUM_SPRITE..+GUM_COUNT-1). */
#include <stdint.h>
#include <ngdevkit/types.h>

extern volatile u16 g_gum_draws;  /* frames the bubble was placed: the test's proof the code ran */
extern volatile u16 g_gum_loads;  /* tile loads queued (frame or size changed) */

void gum_load_palettes(void);
/* Per frame. active 0 (not in Gum Trip) hides the bubble and forgets the pop. gum is Trip.gum; frame is Game.frame (wobble
 * clock). drawn 0 (bird hidden) hides it; else cx is the bird sprite centre x and top its sprite top, in screen pixels,
 * and bird_frame the animation frame shown (selects the secondary motion offset). Level -> 0 plays one pop. */
void gum_step(int active, uint16_t gum, uint32_t frame, int drawn, uint8_t bird_frame, int flip, int cx, int top);
#endif
