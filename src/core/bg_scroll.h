#ifndef BG_SCROLL_H
#define BG_SCROLL_H
/*
 * Parallax background math (pure, host tested). The background is BG_PLANE_COUNT planes, each one row of 16 px column sprites
 * wide enough to cover the 320 px screen at every camera x. A plane with factor k (sixteenths, per plane table in
 * assets/city/city_sheet.json, generated as CITY_TABLE_PLANE_K) sits at screen x = -(cam_px * k / 16): k 0 never moves
 * (sky), k 16 moves with the world like the hazard strip (near). A plane is 320 + 64 * k / 16 px wide, so its right
 * edge reaches the screen edge exactly at the camera limit of 64 px (ARENA_CAM_MAX).
 * Factors are art ratios, not gameplay knobs, so they live in the asset table and not in tuning.h.
 */
#include <stdint.h>

#define BG_PLANE_COUNT 5
#define BG_COL_PX 16
#define BG_K_ONE 16  /* factor denominator: k 16 = full camera speed */

/* Whole pixels the plane has moved left at camera x cam_px: cam_px * k / 16, rounded down (shift, no divide). */
uint32_t bg_plane_offset(uint32_t cam_px, uint32_t k);
/* Screen x of the plane's left edge (the SCB4 value of its head sprite): -bg_plane_offset. */
int bg_plane_x(uint32_t cam_px, uint32_t k);

#endif
