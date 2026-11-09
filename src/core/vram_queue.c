#include "vram_queue.h"

/* Ring index wrap by compare, never `%`: the 68000 has no 32-bit divide, so `% VQ_CAP` on the int-promoted
 * index is a libgcc __modsi3 call (__divsi3 + __mulsi3), about 1700 cycles per pop in MAME. In gfx_flush that
 * made each queued op cost 2.3 scanlines and pushed the flush 100+ lines past vblank (make test-vblank). */
static int push(VramQueue *q, const VqOp *op) {
    if (q->count >= VQ_CAP) return 0;
    u16 tail = (u16)(q->head + q->count);
    if (tail >= VQ_CAP) tail = (u16)(tail - VQ_CAP);
    q->ops[tail] = *op;
    q->count++;
    return 1;
}

void vq_invalidate(VramQueue *q) {
    q->head = q->count = 0;
    for (u16 i = 0; i < VQ_FIX_COLS * VQ_FIX_ROWS; i++) { q->fix_hw[i] = 0xFFFF; q->fix_want[i] = 0xFFFF; }
    for (u16 i = 0; i < VQ_FIX_COLS; i++) q->fix_dirty[i] = 0;
    for (u16 i = 0; i < VQ_SCB_WORDS / 8; i++) q->scb_valid[i] = 0;
    for (u16 i = 0; i < VQ_SPRITES; i++) q->strip[i].tiles = 0;
}

void vq_init(VramQueue *q) { vq_invalidate(q); }

u16 vq_pending(const VramQueue *q) { return q->count; }

int vq_scb_word_push(VramQueue *q, u16 addr, u16 val) {
    u16 i = (u16)(addr - VQ_SCB_BASE);
    if (i >= VQ_SCB_WORDS) return 0;
    u8 bit = (u8)(1u << (i & 7));
    VqOp op = { 0, addr, val, 0, VQ_WORD, 0 };
    if (!push(q, &op)) return 0;
    q->scb_hw[i] = val;
    q->scb_valid[i >> 3] |= bit;
    return 1;
}

int vq_vram_word(VramQueue *q, u16 addr, u16 val) {
    VqOp op = { 0, addr, val, 0, VQ_WORD, 0 };
    return push(q, &op);
}

int vq_strip(VramQueue *q, u16 sprite, const u16 *tiles, u16 base, u8 rows, u16 attr) {
    VqStripKey *k = &q->strip[sprite];
    if (k->tiles == tiles && k->base == base && k->attr == attr && k->rows == rows) return 1;
    VqOp op = { tiles, sprite, base, attr, VQ_STRIP, rows };
    if (!push(q, &op)) return 0;
    k->tiles = tiles; k->base = base; k->attr = attr; k->rows = rows;
    return 1;
}

int vq_pal(VramQueue *q, u16 idx, u16 val) {
    VqOp op = { 0, idx, val, 0, VQ_PAL, 0 };
    return push(q, &op);
}

void vq_fix_put(VramQueue *q, u8 x, u8 y, u16 cell) {
    if (x >= VQ_FIX_COLS || y >= VQ_FIX_ROWS) return;
    u16 i = (u16)(x * VQ_FIX_ROWS + y);
    if (q->fix_want[i] == cell) return;
    q->fix_want[i] = cell;
    q->fix_dirty[x] = 1;
}

void vq_fix_fill(VramQueue *q, u16 cell) {
    for (u16 i = 0; i < VQ_FIX_COLS * VQ_FIX_ROWS; i++) q->fix_want[i] = cell;
    for (u16 x = 0; x < VQ_FIX_COLS; x++) q->fix_dirty[x] = 1;
}

int vq_fix_commit(VramQueue *q) {
    for (u16 x = 0; x < VQ_FIX_COLS; x++) {
        if (!q->fix_dirty[x]) continue;
        for (u16 y = 0; y < VQ_FIX_ROWS; y++) {
            u16 i = (u16)(x * VQ_FIX_ROWS + y);
            if (q->fix_want[i] == q->fix_hw[i]) continue;
            VqOp op = { 0, (u16)(VQ_FIX_BASE + i), q->fix_want[i], 0, VQ_WORD, 0 };
            if (!push(q, &op)) return 0;
            q->fix_hw[i] = q->fix_want[i];
        }
        q->fix_dirty[x] = 0;
    }
    return 1;
}
