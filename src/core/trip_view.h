/*
 * trip_view.h - Gum Trip view maths (plan T-B9, step V0): screen positions, gum meter cells, sprites per scanline.
 *
 * Pure functions, no hardware access, no malloc, no division or modulo and no 64-bit arithmetic in the functions the
 * 68000 runs per frame (shifts and compares only). trip_view_line_sprites is a host measuring tool (plan section 2):
 * it counts the 16 px sprite columns that the trip objects put on one screen line, to check the 96 per line limit.
 */
#ifndef BRAWL_TRIP_VIEW_H
#define BRAWL_TRIP_VIEW_H

#include <stdint.h>
#include "trip_gen.h"

#define TRIP_VIEW_SCREEN_W      320
#define TRIP_VIEW_STRIP_COLS    22   /* sprite columns of one kill strip ring (plan V2) */
#define TRIP_VIEW_RIM_LINES     16   /* rim row: the tile row next to the window */
#define TRIP_VIEW_PICKUP_COLS   2
#define TRIP_VIEW_PICKUP_H      24   /* art height */
#define TRIP_VIEW_PICKUP_SPRITE_H 32 /* sprite height: 2 tiles; the 24 x 24 art sits 4 px from the left and 8 px from the top */
#define TRIP_VIEW_PICKUP_LEFT_OFF 16 /* sprite left = pickup centre x - 16 */
#define TRIP_VIEW_PICKUP_TOP_OFF  20 /* sprite top = pickup centre y - 20 */
#define TRIP_VIEW_PICKUP_FRAMES   16 /* idle animation frames */
#define TRIP_VIEW_PICKUP_BOB_MIN  (-2) /* idle bob extremes in lines (draft table), added to the sprite top */
#define TRIP_VIEW_PICKUP_BOB_MAX  3
#define TRIP_VIEW_COLLECT_FRAMES  8  /* collect effect frames (32 x 32, 2 x 2 tiles), 4 steps each */
#define TRIP_VIEW_COLLECT_TOP_OFF 16 /* collect sprite top = pickup centre y - 16 (the art is the whole 32 x 32 box) */
#define TRIP_VIEW_ISLAND_H      16
#define TRIP_VIEW_GUM_MAX       1024
#define TRIP_VIEW_METER_CELLS   4    /* 4 cells of 2 steps */

/* Sprite columns per line by part. strip is the full strip (every line above win_top and from win_bottom down);
 * strip_rim counts only the 16 lines next to the window. sum uses strip, sum_rim uses strip_rim. */
typedef struct {
    int haz, pickup, island, strip, strip_rim;
    int sum, sum_rim;
} TripViewLine;

/* Screen x of a world x: wx - scroll_px as a signed value, no wrap. */
int trip_view_screen_x(uint32_t wx, uint32_t scroll_px);

/* Hazard i of the chunk: screen x of its centre and its centre y at frame steps (trip_hit_haz_y). */
void trip_view_haz_xy(const TripChunk *c, int i, uint32_t scroll_px, uint32_t steps, int *x, int *y);

/* Gum meter: step = ceil(gum / 128), 0 only at gum 0, 8 at TRIP_VIEW_GUM_MAX. Cell c (0..3) holds 0..2 of the steps. */
int trip_view_meter_step(int gum);
int trip_view_meter_cell(int step, int c);
/* 1 when the meter is down to two steps or less (blink). */
int trip_view_warning(int step);

/* Sprite columns that trip objects put on screen line y (0..179): hazards (cloud 3 columns 48 tall, vent 2 columns 48
 * tall, coal 2 columns 32 tall, centred on the swept position), pickups (2 columns, 24 tall), islands (width / 16
 * columns rounded up, 16 tall from the top edge), kill strips (22 columns). Only columns on screen (x 0..319) count. */
TripViewLine trip_view_line_sprites(const TripGen *g, uint32_t scroll_px, uint32_t steps, int y);

/* Pickup view (step V3). Sprite left of the pickup of chunk c at scroll px (2 sprite columns of 16 px start there), or
 * CAMERA_COL_HIDDEN when the chunk has no pickup (never made, or collected) or the sprite is off screen (left <= -32 or >= 320). */
int trip_view_pickup_left(const TripChunk *c, uint32_t scroll_px);
/* Screen y of the first line of the pickup sprite. */
int trip_view_pickup_top(const TripChunk *c);
/* Idle bob in lines for idle frame f (0..15), cosmetic only: added to the sprite top, never to the hit box. Range BOB_MIN..BOB_MAX. */
int trip_view_pickup_bob(int frame);
/* Idle frame at trip step count steps: 4 steps per frame, 16 frames. */
int trip_view_pickup_frame(uint32_t steps);

/* Hazard view (step V4). Hazard i (0..TRIP_GEN_MAX_HAZ-1) of the chunk held in ring slot r draws as pool object r * 3 + i. The art
 * is a cell of whole 16 px tiles; its hit box (sheet json) is centred on the gameplay centre (trip_view_haz_xy), so the art left and
 * top are the centre minus the hit box centre offset inside the cell (cloud 25,20; vent 16,13; coal 13,18). */
#define TRIP_VIEW_HAZ_PER_CHUNK 3
#define TRIP_VIEW_HAZ_OBJECTS   (TRIP_GEN_RING * TRIP_VIEW_HAZ_PER_CHUNK)
#define TRIP_VIEW_HAZ_TICKS_SHIFT 2  /* 4 steps per animation frame */
typedef struct { int left, top, cols, rows, frame, kind; } TripViewHaz;
/* Fills *out and returns 1 when hazard i of chunk c is shown (it exists and its sprite columns touch the screen), else 0. */
int trip_view_haz_art(const TripChunk *c, int i, uint32_t scroll_px, uint32_t steps, TripViewHaz *out);
/* Animation frame of hazard kind at trip step count steps; 24 frames for cloud and coal, 16 for vent. */
int trip_view_haz_frame(int kind, uint32_t steps);
int trip_view_haz_frame_count(int kind);
/* Island view (step V1). A held chunk r (0..TRIP_GEN_RING-1, its slot in TripGen.ring) draws its island in a fixed block of
 * TRIP_VIEW_ISLAND_BLOCK sprite columns, so a chunk keeps its sprites while it lives. */
#define TRIP_VIEW_ISLAND_BLOCK  6    /* 96 px / 16 */

/* Sprite columns of a generated island of width w px: 4, 5 or 6 for 64, 80, 96. */
int trip_view_island_cols(int w);
/* The chunk held in ring slot r, or 0 when the slot is not live or ready is 0 (nothing may read chunks before
 * game_trip_ready). Live slots are the count slots from head, wrapping. */
const TripChunk *trip_view_ring_chunk(const TripGen *g, int r, int ready);
/* Screen x of column col (0..cols-1) of the island of chunk c, or CAMERA_COL_HIDDEN when it is off screen
 * (x <= -16 or x >= 320) or the chunk has no island. No wrap. */
int trip_view_island_col_x(const TripChunk *c, int col, uint32_t scroll_px);

/* Kill strip view (step V2). A ring of TRIP_VIEW_STRIP_COLS columns of 16 px per strip (floor and ceiling) follows the camera; a
 * column holds world column j = world x / 16. The art is a vertical sequence of cells: a rim cell next to the window, fill beyond.
 * The rim repeats every 4 columns (64 px): roles A B B A with horizontal flips 0 1 0 1; the ceiling is the floor flipped vertically.
 * Fill cells flip horizontally in a checkerboard of (column + row). Floor strips run from win_bottom to the screen bottom
 * (TRIP_VIEW_STRIP_BOTTOM), ceiling strips from the screen top to win_top. */
#define TRIP_VIEW_STRIP_BOTTOM   224
#define TRIP_VIEW_STRIP_MAX_ROWS 14   /* 224 / 16 */
#define TRIP_STRIP_FILL 0
#define TRIP_STRIP_RIM_A 1
#define TRIP_STRIP_RIM_B 2
#define TRIP_STRIP_HFLIP 1
#define TRIP_STRIP_VFLIP 2
typedef struct { uint8_t role, flip; } TripStripCell;

/* The chunk that holds world column j (wx <= 16 j < wx + TRIP_CHUNK_PX) among the live ring slots, or 0 (not live, not ready). */
const TripChunk *trip_view_strip_chunk(const TripGen *g, uint32_t j, int ready);
/* Cells of column j of the floor (ceiling 0) or ceiling (1) strip of chunk c, top row first. Returns the row count (0 hides the
 * column) and sets *top to the screen y of the first row (may be negative). */
int trip_view_strip_column(const TripChunk *c, uint32_t j, int ceiling, TripStripCell *cells, int *top);

/* Ring slots: column j0 + k (k 0..TRIP_VIEW_STRIP_COLS-1) sits in slot (s0 + k) mod 22, so a column keeps its slot while it
 * scrolls. advance moves the ring to first column j0 by repeated steps (no division) and returns 1 when the ring jumped
 * (first call, backwards, or more than 22 columns): every slot is then unknown. */
typedef struct { uint32_t j0; uint8_t s0, valid; } TripStripRing;
int trip_view_strip_advance(TripStripRing *r, uint32_t j0);
int trip_view_strip_slot(const TripStripRing *r, int k);

#endif
