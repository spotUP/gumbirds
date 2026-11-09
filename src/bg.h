#ifndef BG_H
#define BG_H
/* City parallax background: Neo Geo hardware side (palettes, sprite columns). Scroll math is src/core/bg_scroll.c. */
#include <ngdevkit/types.h>

/* Sentinels for the headless test (addresses from the ELF map). */
extern volatile u32 g_bg_scroll_px[3];   /* scroll in px as last drawn: far, mid, roof */
extern volatile u32 g_bg_column_writes;  /* SCB1 column strips written since boot */

void bg_load_palettes(void);             /* palettes + backdrop colour; call from video_init() */
void bg_init(void);                      /* static sprites, forces a full redraw on the next update */
void bg_update(u32 distance, u32 frame); /* distance: 8.8 px of the running game, 0 outside a run */

#endif
