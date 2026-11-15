/* Gum Trip cave edges: which art piece a 16 px strip column shows and where its rock edge is (collision, rivals, strip view).
 * Pieces come from thoughts/shared/drafts/2026-11-15-trip-cave-v3 (owner decisions in thoughts/spot/2026-11-15-trip-cave-facts.md):
 * a flat column shows the rim (roof) or lip (floor) at the window edge; where an edge moves 16 or 32 px between chunks an eased
 * curve (S16 48x32, S32 48x48, 3 columns) is drawn on the side of the boundary whose window is narrower at that edge, so the
 * curve rock never reaches into a window. */
#ifndef BRAWL_TRIP_CAVE_H
#define BRAWL_TRIP_CAVE_H
#include "trip_gen.h"

#define TRIP_CAVE_FLAT 0
#define TRIP_CAVE_S16  1
#define TRIP_CAVE_S32  2
#define TRIP_CAVE_COLS (TRIP_CHUNK_PX / 16)
#define TRIP_CAVE_CURVE_COLS 3

typedef struct {
    uint8_t kind;    /* TRIP_CAVE_FLAT / S16 / S32 */
    uint8_t pcol;    /* tile column of the piece as drawn (0..2), before hflip */
    uint8_t hflip;   /* 1: piece mirrored (roof rising / floor falling to the right) */
    int16_t y0;      /* world y of the piece top row (flat roof: edge - 16, flat floor: edge) */
} TripCavePiece;

/* Piece of column k (0..TRIP_CAVE_COLS-1) of chunk c, roof (ceiling 1) or floor. */
void trip_cave_piece(const TripChunk *c, int k, int ceiling, TripCavePiece *p);
/* Rock edge of column k: roof = first open row below the rock, floor = first rock row. Per 16 px column, the furthest the
 * drawn rock reaches in that column (thoughts/shared/drafts/2026-11-15-trip-cave-v3/heights.json); flat = win_top / win_bottom. */
int trip_cave_edge(const TripChunk *c, int k, int ceiling);
/* Widens *top / narrows *bot to the rock edges of the columns that chunk-relative x0..x1 overlaps (clipped to the chunk). */
void trip_cave_span(const TripChunk *c, int x0, int x1, int *top, int *bot);
/* Rows of a piece (1 flat, 2 S16, 3 S32). */
int trip_cave_piece_rows(int kind);
#endif
