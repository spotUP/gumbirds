#ifndef LOGO_H
#define LOGO_H
/* The title logo: 20 strips + up to 8 free pieces (slots LOGO_SPRITE..+LOGO_COUNT-1, shared with the Gum Trip kill strips,
 * see src/sprite_slots.h). Animated from the generated frame table. */
#include <stdint.h>
#include <ngdevkit/types.h>

extern volatile u16 g_logo_draws;  /* frames the logo was placed: the test's proof the code ran */
extern volatile u16 g_logo_frame;  /* animation frame shown */

void logo_load_palettes(void);
/* The video hardware was reset (video_init): forget what was sent. */
void logo_reset(void);
/* Per video frame. active 0 (not the title) hides every logo sprite and restarts the animation. */
void logo_step(int active);
/* Number of animation frame advances since the title opened; the blinking plate line keys on it. */
uint16_t logo_ticks(void);
#endif
