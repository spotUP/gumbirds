/* rain.h - storm rain on the fix layer (owner-approved draft v3, thoughts/shared/drafts/2026-11-20-rain-v3) and its lightning timer.
 * Zero sprites: drops are 8 x 8 fix tiles (build/gen/rain_tiles.h) written only into cells that are blank, so text and the HUD win.
 * Portable C99, no hardware access: the caller loads the palette words and feeds the flash to the planes. */
#ifndef BRAWL_RAIN_H
#define BRAWL_RAIN_H
#include <stdint.h>
#include "vram_queue.h"

#define RAIN_MAX_DROPS 96
#define RAIN_COLS 40
#define RAIN_ROWS 28
#define RAIN_MODE_ARENA 0 /* arena, arcade, Gum Games gather and dash */
#define RAIN_MODE_TRIP 1
#define RAIN_MODE_STADIUM 2
#define RAIN_BURST_FRAMES 48 /* the burst rain lasts this many frames from the flash start */
#define RAIN_BURST_PAL_FRAMES 32 /* the rain palette stays pale storm blue this long */
#define RAIN_FLASH_FRAMES 24 /* flash length: levels at 0-3, 4-7, 16-19, 20-23 (none 8-15) */

typedef struct { int16_t px, py; uint8_t kind, end_row; int16_t acc; } RainDrop;

typedef struct {
    RainDrop drop[RAIN_MAX_DROPS];
    uint8_t n;
    uint8_t own[RAIN_COLS * RAIN_ROWS];  /* tile id + 1 this module wrote into each cell, 0 none */
    uint16_t list[RAIN_MAX_DROPS * 3];   /* cells set in own[] (col * RAIN_ROWS + row) */
    uint16_t n_list;
    uint8_t now[RAIN_COLS * RAIN_ROWS];
    uint16_t frame;                      /* frames the rain has been active */
    uint16_t timer;                      /* frames to the next flash */
    uint8_t gap;                         /* index into the gap list */
    uint8_t flash_t;                     /* 0 none, else flash frame + 1 */
    uint8_t was_active, pal;
    uint8_t burst_n;                     /* burst drops spawned this flash */
    uint32_t rng;
} Rain;

/* pal_slot: the fix palette slot (RAIN_PAL_SLOT in src/vram_layout.h) the tiles are drawn with. */
void rain_init(Rain *r, uint8_t pal_slot);
/* One frame. active 0: every cell it owns is blanked and the state restarts. mode: RAIN_MODE_*. scroll_px: Gum Trip camera
 * movement this frame in pixels (rain scrolls with the scene), else 0. q receives the fix writes. */
void rain_step(Rain *r, VramQueue *q, uint8_t active, uint8_t mode, int16_t scroll_px);
/* 0 no flash, 1..4 the planes' flash level index (rain_flash_color). */
uint8_t rain_flash_index(const Rain *r);
/* 1 while the rain palette is the burst colour. */
uint8_t rain_burst_active(const Rain *r);
/* Pale flash: colour c brightened toward white by level idx (1..4), NG 16-bit colour word. idx 0 returns c. */
uint16_t rain_flash_color(uint16_t c, uint8_t idx);
/* Seconds between flashes: the typed list walked in order. */
uint16_t rain_gap_frames(uint8_t i);
#endif
