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

typedef enum { VQ_WORD, VQ_STRIP, VQ_PAL } VqKind;

typedef struct {
    const u16 *tiles;   /* VQ_STRIP: `rows` tile numbers, table value + base */
    u16 a;              /* WORD: VRAM address; STRIP: sprite; PAL: palette RAM index */
    u16 b;              /* WORD/PAL: value; STRIP: tile base */
    u16 c;              /* STRIP: attribute word */
    u8 kind;
    u8 rows;
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
int vq_vram_word(VramQueue *q, u16 addr, u16 val);  /* unshadowed single word (e.g. a star tile) */
int vq_strip(VramQueue *q, u16 sprite, const u16 *tiles, u16 base, u8 rows, u16 attr);
int vq_pal(VramQueue *q, u16 idx, u16 val);
void vq_fix_put(VramQueue *q, u8 x, u8 y, u16 cell);
void vq_fix_fill(VramQueue *q, u16 cell);
int vq_fix_commit(VramQueue *q);           /* queue the changed fix cells; 0 when the queue filled up (call again) */
/* The consumer side is inline: gfx_flush runs it in vblank, where a call per op cost more than the op's writes. */
static inline const VqOp *vq_peek(const VramQueue *q) { return q->count ? &q->ops[q->head] : 0; }

static inline void vq_pop(VramQueue *q) {
    if (!q->count) return;
    q->head = (u16)(q->head + 1 == VQ_CAP ? 0 : q->head + 1);  /* no `%`: see push() in vram_queue.c */
    q->count--;
}

/* Flush time of one op in microseconds, worst case (address set + data + the loop's per-op overhead), measured in
 * MAME on the gfx_flush loop (thoughts/shared/research/2026-11-09_vblank-writes.md): a word or palette op costs about
 * 29 us plus 5 us for an address set, a strip about 50 us plus 5 us per row (two data writes). The per-op overhead,
 * not the register write, dominates: budgeting by register writes let a flush of single words run past vblank. */
#define VQ_US_OP 34u
#define VQ_US_STRIP 50u
#define VQ_US_ROW 5u
static inline u16 vq_cost(const VqOp *op) {
    return op->kind == VQ_STRIP ? (u16)(VQ_US_STRIP + VQ_US_ROW * op->rows) : (u16)VQ_US_OP;
}

#endif
