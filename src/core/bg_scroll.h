#ifndef BG_SCROLL_H
#define BG_SCROLL_H
/*
 * Parallax background math (pure, host tested). The background is BG_PLANE_COUNT planes, each one row of 16 px column sprites,
 * every plane a seamless loop of its own width. A plane with factor k (sixteenths, per plane table in assets/city/city_sheet.json,
 * generated as CITY_TABLE_PLANE_K) follows the unwrapped camera at k / 16 of its speed: k 0 never moves (sky), k 16 moves with the
 * world like the hazard strip (near). Factors are art ratios, not gameplay knobs, so they live in the asset table and not in tuning.h.
 */
#include <stdint.h>
#include "vram_queue.h"

#define BG_PLANE_COUNT 5
#define BG_COL_PX 16
#define BG_PLANE_FAR 1
#define BG_PLANE_NEAR 4
/* Planes Gum Trip does not show (bit = plane index: sky 0, far 1, mid A 2, mid B 3, near 4): they cost the per-line sprite budget. */
#define BG_TRIP_HIDDEN_MASK ((1u << BG_PLANE_FAR) | (1u << BG_PLANE_NEAR))
#define BG_K_ONE 16  /* factor denominator: k 16 = full camera speed */

/* Looping planes. u = camera_unwrapped_px (continuous; it drops by CAM_LAP_PERIOD_PX once per lap, a multiple of every plane period at its
 * factor, so no plane moves at the drop), k = factor (a multiple of 4: shifts and adds, no multiply), period = plane width in px
 * (generated CITY_TABLE_PLANE_PERIOD_PX). Offset into the art: floor(u * k / 16) mod period, u at most CAM_LAP_PERIOD_PX + 383. */
uint32_t bg_loop_offset(uint32_t u, uint32_t k, uint32_t period);
/* Screen x of art column c (16 px) of a plane whose offset is off: 16c - off, moved one period right once it has left the screen. */
int bg_column_x(uint32_t off, uint32_t c, uint32_t period);

/* The SCB4 words of all `cols` columns of a plane (period = 16 * cols) at offset off, as two ramps for VQ_RAMP: columns [0, split) hold
 * v1, v1 + VQ_SCB4_COL, ... and columns [split, cols) hold v2, v2 + VQ_SCB4_COL, ... Equal word for word to VQ_SCB4_X(bg_column_x(off, c,
 * period)) for off < period: with off = 16 split + r (r < 16) exactly the first `split` columns have wrapped one period right. O(1) in cols. */
typedef struct { uint16_t v1, v2; uint8_t split; } BgRamp;
void bg_ramp(uint32_t off, uint32_t period, BgRamp *out);

#endif
