#ifndef VRAM_QUEUE_H
#define VRAM_QUEUE_H
/*
 * Pure model of the video memory write path. Game logic and view code only touch this RAM structure;
 * gfx.c (the single owner of the LSPC registers and palette RAM) pops the queued operations right
 * after vblank starts and writes them. Dedup happens here, on enqueue, against what the hardware will
 * hold once the queue is flushed:
 *   - fix layer: a wanted-tile buffer (text and clears write it freely), vq_fix_commit diffs it
 *     against the hardware shadow and queues only changed cells;
 *   - SCB2/SCB3/SCB4 words: shadowed, an unchanged word queues nothing;
 *   - SCB1 strips (tile column of a sprite): the descriptor (tile table pointer, base, attr, rows)
 *     is remembered per sprite, an identical strip queues nothing;
 *   - palette words and single SCB1 words are queued as given (callers write them on state change).
 * vq_invalidate forgets the hardware state (boot, BIOS resume) so the next writes all go out.
 */
#include <stdint.h>

typedef uint8_t u8;
typedef uint16_t u16;

#define VQ_CAP 384
#define VQ_FIX_COLS 40
#define VQ_FIX_ROWS 32
#define VQ_FIX_BASE 0x7000u
#define VQ_SCB_BASE 0x8000u   /* SCB2, SCB3, SCB4 */
#define VQ_SCB_WORDS 0x600u
#define VQ_SPRITES 381

typedef enum { VQ_WORD, VQ_STRIP, VQ_PAL, VQ_RUN, VQ_STRIP_ATTR } VqKind;

/* VQ_RUN: `rows` words at VRAM a, a + b, a + 2b, ... (REG_VRAMMOD = b), read at flush time from the SCB shadow
 * (tiles = &scb_hw[a - VQ_SCB_BASE], same stride). One op for a strided run of SCB words, e.g. the x of every pool
 * object: the per-op flush overhead is paid once. Reading the shadow at flush time is safe: the shadow is what the
 * hardware holds once the queue is flushed, so a word changed again before the flush is written with its final
 * value (and again by its own later op). */
typedef struct {
    const u16 *tiles;   /* VQ_STRIP: `rows` tile numbers, table value + base; VQ_STRIP_ATTR: `rows` pairs {tile, attribute}; VQ_RUN: first source word */
    u16 a;              /* WORD/RUN: VRAM address; STRIP/STRIP_ATTR: sprite; PAL: palette RAM index */
    u16 b;              /* WORD/PAL: value; STRIP/STRIP_ATTR: tile base; RUN: address stride (REG_VRAMMOD) */
    u16 c;              /* STRIP: attribute word */
    u8 kind;
    u8 rows;            /* STRIP: tile rows; RUN: words */
    u16 cost;           /* flush time in us (vq_cost), set on enqueue so the vblank loop does no arithmetic for it */
} VqOp;

typedef struct {
    const u16 *tiles;
    u16 base, attr;
    u8 rows;
} VqStripKey;

typedef struct {
    VqOp ops[VQ_CAP];
    u16 head, count;
    u16 fix_want[VQ_FIX_COLS * VQ_FIX_ROWS];
    u16 fix_hw[VQ_FIX_COLS * VQ_FIX_ROWS];
    u8 fix_dirty[VQ_FIX_COLS];
    u16 scb_hw[VQ_SCB_WORDS];
    u8 scb_valid[VQ_SCB_WORDS / 8];
    VqStripKey strip[VQ_SPRITES];
} VramQueue;

void vq_init(VramQueue *q);
void vq_invalidate(VramQueue *q);          /* hardware content unknown: drop pending ops and all shadows */
u16 vq_pending(const VramQueue *q);
/* Each enqueue returns 1 when queued or deduplicated away, 0 when the queue is full (nothing changed). */
int vq_scb_word_push(VramQueue *q, u16 addr, u16 val);   /* vq_scb_word without the dedupe test */
/* addr in SCB2..SCB4. Inline dedupe: most per-frame sprite words are unchanged, and a call per word was a large
 * part of the frame (PC profile, thoughts/shared/research/2026-11-09_test-laser-hit-fix.md). */
static inline int vq_scb_same(const VramQueue *q, u16 addr, u16 val) {
    u16 i = (u16)(addr - VQ_SCB_BASE);
    return i < VQ_SCB_WORDS && q->scb_hw[i] == val && (q->scb_valid[i >> 3] & (u8)(1u << (i & 7)));
}
static inline int vq_scb_word(VramQueue *q, u16 addr, u16 val) {
    return vq_scb_same(q, addr, val) ? 1 : vq_scb_word_push(q, addr, val);
}
/* Strided SCB run: vals[k] is the word for addr + k * mod (all inside SCB2..SCB4, n <= 255). Dedupes against the
 * shadow like vq_scb_word; the changed words (first to last changed, unchanged ones in between are rewritten with
 * the same value) go out as one VQ_RUN op. Returns 0 (nothing changed) when the queue is full or the run is out of
 * range. */
int vq_scb_run(VramQueue *q, u16 addr, u16 mod, const u16 *vals, u8 n);
int vq_vram_word(VramQueue *q, u16 addr, u16 val);  /* unshadowed single word (e.g. a star tile) */
int vq_strip(VramQueue *q, u16 sprite, const u16 *tiles, u16 base, u8 rows, u16 attr);
/* One column whose tiles carry their own attribute (palette): `pairs` holds `rows` {tile, attribute} pairs. For art
 * that uses several palettes in one column, written once at init, so there is no dedupe key. */
int vq_strip_attr(VramQueue *q, u16 sprite, const u16 *pairs, u16 base, u8 rows);
/* vq_strip for `cols` adjacent sprites from `first`, column c taking tiles[c * rows ..]: one call per sprite block
 * (the pool view redraws up to POOL_MAX blocks in one frame when their animations flip together). Returns the
 * columns done; fewer than `cols` when the queue filled (call again from there after a drain). */
u8 vq_strips(VramQueue *q, u16 first, u8 cols, u8 rows, const u16 *tiles, u16 base, u16 attr);
int vq_pal(VramQueue *q, u16 idx, u16 val);
void vq_fix_put(VramQueue *q, u8 x, u8 y, u16 cell);
/* vq_fix_put of cell hi | (base + c) for every char c of s from (x, y) to the right, clipped at the last column. One call
 * per string with an incremental cell index: the HUD text goes through it every frame. */
void vq_fix_text(VramQueue *q, u8 x, u8 y, u16 hi, u16 base, const char *s);
void vq_fix_fill(VramQueue *q, u16 cell);
int vq_fix_commit(VramQueue *q);           /* queue the changed fix cells; 0 when the queue filled up (call again) */
/* The consumer side is inline: gfx_flush runs it in vblank, where a call per op cost more than the op's writes. */
static inline const VqOp *vq_peek(const VramQueue *q) { return q->count ? &q->ops[q->head] : 0; }

static inline void vq_pop(VramQueue *q) {
    if (!q->count) return;
    q->head = (u16)(q->head + 1 == VQ_CAP ? 0 : q->head + 1);  /* no `%`: see push() in vram_queue.c */
    q->count--;
}

/* Flush time of one op in microseconds, worst case, from the cycle count of the gfx_flush loop (68000 at 12 MHz,
 * 12 cycles = 1 us; thoughts/shared/research/2026-11-09_object-pool.md, section Flush speed fix), rounded up with
 * margin. Before that loop was rewritten a word op cost about 31 us of bookkeeping; now a word op costs about 13 us
 * and a word inside a run 3.5 us. The cost is set on enqueue (op->cost). */
#define VQ_US_OP 15u          /* word op: about 158 cycles (13 us) */
#define VQ_US_PAL 18u         /* palette op: about 190 cycles (16 us) */
#define VQ_US_STRIP 22u       /* strip op overhead: about 230 cycles (19 us) */
#define VQ_US_ROW 5u          /* strip row, two data writes: 56 cycles (4.7 us) */
#define VQ_US_RUN 22u         /* run op overhead (address and stride set, stride restore): about 230 cycles (19 us) */
#define VQ_US_RUN_WORD 4u     /* run word: 42 cycles (3.5 us) */
static inline u16 vq_cost(const VqOp *op) { return op->cost; }

#endif
