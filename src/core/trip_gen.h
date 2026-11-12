/*
 * trip_gen.h - Gum Trip random layout generator (plan T-B5): islands, moving hazards, kill strips, pickups.
 *
 * Pure logic, no hardware, deterministic from a seed, fixed-size ring of chunks (no malloc). No division or modulo
 * and no 64-bit arithmetic in the code (only trip_density_at, called once per chunk, divides in trip.c).
 * The course is made of chunks of TRIP_CHUNK_PX world pixels, generated in order as the scroll passes. World y is
 * the screen y (0..FLIER_WORLD_H). Each chunk has one safe vertical window (kill strips above and below it), 0..3
 * moving hazards of one kind (kind by distance band), at most one island and at most one pickup. Output is data;
 * the view maps it later (plan T-B5, T-B9).
 *
 * Passability rule (tested exactly): for every chunk, the set of heights where a box TRIP_PASS_MIN tall is clear of
 * all solids of that chunk is one band; consecutive chunks' bands overlap by at least TRIP_PASS_MIN. A flier can
 * therefore fly a straight line over every chunk boundary and slide inside a band, so no chunk needs a climb.
 * Plan F1 (window >= TRIP_GAP_MIN) and F2 (window centres within the climb the flier can make) are kept as well.
 */
#ifndef BRAWL_TRIP_GEN_H
#define BRAWL_TRIP_GEN_H

#include <stdint.h>
#include "rng.h"

#include "tuning.h"

/* Slot width: one hazard or the pickup per slot, boxes lie inside their slot with TRIP_HAZ_X_GAP/2 clear each side.
 * 48 px fits the widest hit box (cloud A, 36 px) plus margin. Structural, not a tuning knob (see tuning.h Gum Trip
 * layout knobs): TRIP_CHUNK_PX must stay a multiple of it and the pickup spacing is counted in slots. */
#ifndef TRIP_SLOT_PX
#define TRIP_SLOT_PX 48
#endif

/* Not knobs: facts of the layout. */
#define TRIP_SLOTS         (TRIP_CHUNK_PX / TRIP_SLOT_PX)
#define TRIP_GEN_RING      5     /* chunks held: screen 320 + ahead 96 + two partial chunks fits 4; one spare */
#define TRIP_GEN_MAX_HAZ   3     /* hazards per chunk; TRIP_DENSITY_MAX must not exceed it and TRIP_SLOTS - 1 */
#define TRIP_GEN_WORLD_H   180   /* FLIER_WORLD_H */
#define TRIP_HAZ_X_GAP     8     /* clear px between a hazard box and its slot border pair (4 each side) */
#define TRIP_ISLAND_W_MIN  64    /* generated island widths are 64, 80, 96 (the art has 64/80/96/112) */
#define TRIP_PICKUP_HALF   12    /* pickup A 24 x 24 */
#define TRIP_PICKUP_CLEAR  6     /* clear px around a pickup box to the strips and the island floor */

typedef enum { TRIP_HAZ_COAL = 0, TRIP_HAZ_VENT = 1, TRIP_HAZ_CLOUD = 2 } TripHazKind;

typedef struct {
    uint8_t kind;        /* TripHazKind (plan C, B, A) */
    uint8_t hw, hh;      /* hit box half extents */
    uint8_t amp;         /* vertical sweep: the box centre moves between y - amp and y + amp */
    uint8_t phase;       /* start phase of the sweep, 0..255 */
    int16_t x;           /* centre x, relative to the chunk start */
    int16_t y;           /* centre y of the sweep, world */
} TripGenHazard;

typedef struct {
    uint8_t present;
    int16_t x;           /* left edge relative to the chunk start */
    int16_t y;           /* top edge, world */
    uint8_t w, h;
} TripGenIsland;

typedef struct {
    uint8_t present;
    int16_t x, y;        /* centre, x relative to the chunk start */
} TripGenPickup;

typedef struct {
    uint32_t index;      /* chunk number, 0 first */
    uint32_t wx;         /* world x of the chunk start = index * TRIP_CHUNK_PX */
    int16_t win_top, win_bottom;     /* safe window: strips fill 0..win_top and win_bottom..180 */
    int16_t band_top, band_bottom;   /* clear band beside hazards and island (see the passability rule) */
    uint8_t n_haz;       /* hazards actually placed */
    uint8_t n_req;       /* hazards the density asked for (differs only when dropped is set) */
    uint8_t dropped;     /* 1: no fair placement was found, hazards left out of this chunk */
    uint8_t haz_top;     /* 1: hazards hang from the window top, 0: stand on the window floor */
    TripGenHazard haz[TRIP_GEN_MAX_HAZ];
    TripGenIsland island;
    TripGenPickup pickup;
} TripChunk;

typedef struct {
    Rng rng;
    TripChunk ring[TRIP_GEN_RING];
    uint8_t head, count;             /* oldest chunk slot, chunks held */
    uint32_t next_index, next_wx;    /* the chunk generated next */
    uint32_t pk_chunk;               /* chunk of the next pickup */
    uint8_t pk_slot;                 /* slot of the next pickup */
    int16_t prev_band_top, prev_band_bottom, prev_centre;
    int16_t prev_isl_end, prev_isl_y;  /* island of the previous chunk: right edge relative to its chunk start (0 = none) and top edge */
    uint32_t overflow;               /* chunks that were needed but did not fit the ring (must stay 0) */
    uint32_t made;                   /* sentinel: chunks generated */
    uint32_t drops;                  /* chunks that dropped their hazards */
} TripGen;

/* Seed and build the chunks that cover the first screen, world x 0..319 (two at 192 px). Same seed, same course. */
void tripgen_init(TripGen *g, uint32_t seed);
/* 1 when the chunks covering world x [scroll_px, scroll_px + 320) are all built. */
int tripgen_covers(const TripGen *g, uint32_t scroll_px);
/* Retire chunks fully left of scroll_px and generate the next chunk when it starts before
 * scroll_px + 320 + TRIP_GEN_AHEAD_PX: AT MOST ONE chunk per call (frame time budget), so a caller scrolling by
 * more than a chunk per call falls behind; the game scrolls under 1 px per frame. */
void tripgen_advance(TripGen *g, uint32_t scroll_px);
/* Chunk by number, or 0 when it is not held. */
const TripChunk *tripgen_get(const TripGen *g, uint32_t index);
/* Hit box half extents and sweep of a kind (tables, exposed for tests and the view). */
uint8_t tripgen_haz_hw(uint8_t kind);
uint8_t tripgen_haz_hh(uint8_t kind);
uint8_t tripgen_haz_amp(uint8_t kind);

#endif
