#ifndef BG_H
#define BG_H
/* Parallax background (moon mood): hardware side (palettes, one sprite per column). The math is src/core/bg_scroll.c. */
#include <ngdevkit/types.h>

/* Sentinels for the headless test (addresses from the ELF map). */
extern volatile s16 g_bg_plane_x[5];  /* screen x each plane's first column last got: sky, far, mid A, mid B, near */
extern volatile u32 g_bg_x_writes;    /* plane SCB4 runs (one per plane, all its columns) sent since boot: only camera-move frames add any */

void bg_load_palettes(void);          /* palettes + backdrop colour; call from video_init() */
void bg_init(void);                   /* tiles, tops and heights of every column, written once; forces the x words on the next update */
void bg_update(u8 cam_px);            /* each frame: plane x = -(cam_px * k / 16); a word goes out only when it changed */

#endif
