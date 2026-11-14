#ifndef BG_H
#define BG_H
/* Parallax background (moon and dusk moods): hardware side (palettes, one sprite per column). The math is src/core/bg_scroll.c. */
#include <ngdevkit/types.h>

/* Sentinels for the headless test (addresses from the ELF map). */
extern volatile s16 g_bg_plane_x[5];  /* screen x each plane's first column last got: sky, far, mid A, mid B, near */
extern volatile u32 g_bg_x_writes;    /* plane SCB4 runs (one per plane, all its columns) sent since boot: only camera-move frames add any */

void bg_load_palettes(void);          /* palettes + backdrop colour; call from video_init() */
void bg_init(void);                   /* tiles, tops and heights of every column, written once; forces the x words on the next update */
void bg_trip_planes(u8 trip);          /* 1 hides the planes Gum Trip drops (BG_TRIP_HIDDEN_MASK: far, near), 0 shows them again; also the backdrop colour: sky colour in trip, dark otherwise; words go out only on a change */
void bg_set_mood(u8 mood);            /* GAME_MOOD_*: hides the planes now, rewrites their strips over the next bg_update calls, then shows them; no-op for the mood shown or asked */
extern volatile u8 g_bg_mood;         /* mood on screen (test sentinel) */
extern volatile u8 g_bg_mood_busy;    /* 1 while a mood change runs */
extern volatile u16 g_bg_mood_changes; /* mood changes finished since boot (test sentinel) */
void bg_update(s32 unwrapped_px);     /* each frame, camera_unwrapped_px: plane offset = (px * k / 16) mod plane width; returns at once when the camera did not move, words go out only for a plane whose offset changed */

#endif
