/*
 * obj_pool.h - fixed-size pool of free-moving objects (engine layer for the flier gameplay,
 * thoughts/shared/plans/2026-11-09-flier-gameplay-design.md section 5). Pure C, host tested
 * (tests/host/test_obj_pool.c); the Neo Geo view glue in src/main.c turns objects into sprites.
 *
 * - Position and velocity are int32_t 16.16 fixed point (design 1.2): pixel = v >> 16.
 * - Alloc and free are O(1) through a free list; no malloc. A full pool fails quietly (POOL_NONE).
 * - Hardware sprites: object i owns the contiguous run base + i * POOL_COLS .. + POOL_COLS - 1 for its whole
 *   life. The run is a function of the index, so it never fragments and a spawn never fails for lack of
 *   sprites. A freed object is flagged in `hide`; the view hides its run once (obj_pool_take_hidden).
 * - No 32-bit `/` or `%` anywhere (68000 libgcc calls); per-frame paths are add, compare, shift.
 */
#ifndef ROOFLINE_OBJ_POOL_H
#define ROOFLINE_OBJ_POOL_H

#include <stdint.h>

#define POOL_MAX 32      /* design 5.1: 2 players + 6 fliers + 8 hazards + 10 pickups + 8 effects = 34, rounded to 32 */
#define POOL_COLS 3      /* hardware sprites per object: widest frame in tiles (obstacle art is 3 columns) */
#define POOL_SPRITES (POOL_MAX * POOL_COLS)
#define POOL_NONE 0xFF

#define POOL_F_LIVE 0x01 /* slot in use */
/* bits 0x02..0x80 free for the game (kind specific) */

typedef struct {
    int32_t x, y;        /* anchor in screen pixels, 16.16; the kind defines the point (obstacles: hit box left, bottom) */
    int32_t vx, vy;      /* pixels per frame, 16.16 */
    uint8_t type;        /* game kind */
    uint8_t flags;       /* POOL_F_* */
    uint8_t anim;        /* animation frame index */
    uint8_t anim_tick;   /* frames shown of the current animation frame */
} PoolObj;

typedef struct {
    PoolObj obj[POOL_MAX];
    uint8_t next_free[POOL_MAX]; /* free list links */
    uint8_t free_head;           /* first free index, POOL_NONE when full */
    uint8_t live;                /* live object count */
    uint8_t peak;                /* highest live count since init */
    uint32_t hide;               /* bit i: object i was freed, its sprite run is still shown */
    uint16_t sprite_base;        /* first hardware sprite of the pool range */
} ObjPool;

void obj_pool_init(ObjPool *p, uint16_t sprite_base);
/* Index of a new live object (zeroed, then the given fields), or POOL_NONE when the pool is full. */
uint8_t obj_pool_alloc(ObjPool *p, uint8_t type, int32_t x, int32_t y, int32_t vx, int32_t vy);
/* Frees a live object; a dead or out-of-range index is ignored. */
void obj_pool_free(ObjPool *p, uint8_t i);
/* One frame of free motion for every live object: x += vx, y += vy. */
void obj_pool_step(ObjPool *p);
/* Advances an object's animation: `ticks` frames per animation frame, `count` frames, wraps to 0. ticks 0 holds. */
/* Inline: the pool view calls it for every live object every frame (POOL_MAX of them under the stress hook). */
static inline void obj_pool_anim(PoolObj *o, uint8_t ticks, uint8_t count) {
    if (ticks == 0 || count == 0) { o->anim = 0; o->anim_tick = 0; return; }
    if (o->anim >= count) o->anim = 0; /* count changed under it (type change) */
    if (++o->anim_tick < ticks) return;
    o->anim_tick = 0;
    if (++o->anim >= count) o->anim = 0;
}
/* Returns the freed-object mask the view must hide (bit i = sprites of object i) and clears it. */
uint32_t obj_pool_take_hidden(ObjPool *p);

static inline int obj_pool_is_live(const ObjPool *p, uint8_t i) {
    return i < POOL_MAX && (p->obj[i].flags & POOL_F_LIVE);
}
/* First hardware sprite of object i's run (16-bit multiply only). */
static inline uint16_t obj_pool_sprite(const ObjPool *p, uint8_t i) {
    return (uint16_t)(p->sprite_base + (uint16_t)i * POOL_COLS);
}
static inline int16_t obj_pool_px(int32_t v) { return (int16_t)(v >> 16); }
static inline int32_t obj_pool_fp(int16_t px) { return (int32_t)px * 65536; }

#endif
