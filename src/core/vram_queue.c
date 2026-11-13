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

/* The free op at the tail, filled in place by the caller (then count++), or 0 when the queue is full. For the
 * per-frame producers: no op struct built on the stack and copied. */
static VqOp *tail_op(VramQueue *q) {
    if (q->count >= VQ_CAP) return 0;
    u16 tail = (u16)(q->head + q->count);
    if (tail >= VQ_CAP) tail = (u16)(tail - VQ_CAP);
    return &q->ops[tail];
}

void vq_invalidate(VramQueue *q) {
    q->head = q->count = 0;
    for (u16 i = 0; i < VQ_FIX_COLS * VQ_FIX_ROWS; i++) { q->fix_hw[i] = 0xFFFF; q->fix_want[i] = 0xFFFF; }
    for (u16 i = 0; i < VQ_FIX_COLS; i++) q->fix_dirty[i] = 0;
    q->fix_any = 0;
    for (u16 i = 0; i < VQ_SCB_WORDS / 8; i++) q->scb_valid[i] = 0;
    for (u16 i = 0; i < VQ_SPRITES; i++) q->strip[i].tiles = 0;
}

void vq_init(VramQueue *q) { vq_invalidate(q); }

u16 vq_pending(const VramQueue *q) { return q->count; }

int vq_scb_word_push(VramQueue *q, u16 addr, u16 val) {
    u16 i = (u16)(addr - VQ_SCB_BASE);
    if (i >= VQ_SCB_WORDS) return 0;
    /* Filled in place at the tail (same op as building one on the stack and copying it through push()): this is
     * the path of every changed sprite word sent one at a time, e.g. the sticky chains of a wave of new pool
     * objects in one frame. */
    VqOp *op = tail_op(q);
    if (!op) return 0;
    op->tiles = 0; op->a = addr; op->b = val; op->c = 0; op->kind = VQ_WORD; op->rows = 0; op->cost = VQ_US_OP;
    q->count++;
    q->scb_hw[i] = val;
    q->scb_valid[i >> 3] |= (u8)(1u << (i & 7));
    return 1;
}

int vq_scb_run(VramQueue *q, u16 addr, u16 mod, const u16 *vals, u8 n) {
    u16 i = (u16)(addr - VQ_SCB_BASE);
    if (!n || !mod || i >= VQ_SCB_WORDS || (u16)(i + (n - 1) * mod) >= VQ_SCB_WORDS) return 0;
    if (q->count >= VQ_CAP) return 0;  /* checked before the shadow changes: a failed call changes nothing */
    /* Per-frame path (the pool view sends 2 runs of POOL_MAX words): walk the shadow by pointer, the valid bit
     * only for a word whose value matches (an unchanged word is the common case and needs both tests). */
    /* The loop keeps every value in a register (int-sized index and counters, the valid bit computed only for a
     * word that needs it). The earlier form spilled first/last/mod/n to the stack and built the bit and byte
     * pointer for every word: about 250 cycles per word, 21 scanlines a frame for the pool's 64 words. */
    int first = -1, last = 0, k;
    unsigned idx = i;
    const unsigned step = mod;
    u16 *hw = &q->scb_hw[i];
    u8 *valid = q->scb_valid;
    for (k = 0; k < n; k++, idx += step, hw += step) {
        u16 val = vals[k];
        if (*hw == val) {
            if (valid[idx >> 3] & (u8)(1u << (idx & 7))) continue;
        } else {
            *hw = val;
        }
        valid[idx >> 3] |= (u8)(1u << (idx & 7));
        if (first < 0) first = k;
        last = k;
    }
    if (first < 0) return 1;
    u16 a = (u16)(addr + (u16)first * mod);
    u8 words = (u8)(last - first + 1);
    VqOp op = { &q->scb_hw[a - VQ_SCB_BASE], a, mod, 0, VQ_RUN, words, (u16)(VQ_US_RUN + VQ_US_RUN_WORD * words), 0 };
    return push(q, &op);
}

void vq_scb_forget(VramQueue *q, u16 addr, u16 n) {
    for (u16 i = (u16)(addr - VQ_SCB_BASE); n && i < VQ_SCB_WORDS; i++, n--) q->scb_valid[i >> 3] &= (u8)~(1u << (i & 7));
}

int vq_scb_ramp(VramQueue *q, u16 addr, u8 n, u8 split, u16 v1, u16 v2) {
    u16 i = (u16)(addr - VQ_SCB_BASE);
    if (!n || split > n || i >= VQ_SCB_WORDS || (u16)(i + n - 1) >= VQ_SCB_WORDS) return 0;
    VqOp *op = tail_op(q);
    if (!op) return 0;
    op->tiles = 0; op->a = addr; op->b = v1; op->c = v2; op->kind = VQ_RAMP; op->rows = n;
    op->cost = (u16)(VQ_US_RAMP + VQ_US_RAMP_WORD * n); op->split = split;
    q->count++;
    return 1;
}

void vq_ramp_expand(const VqOp *op, u16 *out) {
    u16 v = op->b;
    for (u8 k = 0; k < op->rows; k++) {
        if (k == op->split) v = op->c;
        out[k] = v;
        v = (u16)(v + VQ_SCB4_COL);
    }
}

int vq_vram_word(VramQueue *q, u16 addr, u16 val) {
    VqOp op = { 0, addr, val, 0, VQ_WORD, 0, VQ_US_OP, 0 };
    return push(q, &op);
}

u8 vq_strips(VramQueue *q, u16 first, u8 cols, u8 rows, const u16 *tiles, u16 base, u16 attr) {
    VqStripKey *k = &q->strip[first];
    u16 cost = (u16)(VQ_US_STRIP + VQ_US_ROW * rows);
    /* Count and tail op stay in locals for the whole call and the op pointer wraps by compare: a frame where
     * many pool objects change animation frame together queues dozens of columns here, and re-deriving the tail
     * from head + count for each one was most of the per-column cost. Same ops in the same order as one
     * tail_op() per column. */
    u16 count = q->count;
    u16 tail = (u16)(q->head + count);
    if (tail >= VQ_CAP) tail = (u16)(tail - VQ_CAP);
    VqOp *op = &q->ops[tail];
    VqOp *const end = &q->ops[VQ_CAP];
    u8 c = 0;
    for (; c < cols; c++, k++, tiles += rows) {
        if (k->tiles == tiles && k->base == base && k->attr == attr && k->rows == rows) continue;
        if (count >= VQ_CAP) break;
        op->tiles = tiles; op->a = (u16)(first + c); op->b = base; op->c = attr; op->kind = VQ_STRIP; op->rows = rows;
        op->cost = cost;
        count++;
        if (++op == end) op = q->ops;
        k->tiles = tiles; k->base = base; k->attr = attr; k->rows = rows;
    }
    q->count = count;
    return c;
}

int vq_strip(VramQueue *q, u16 sprite, const u16 *tiles, u16 base, u8 rows, u16 attr) {
    return vq_strips(q, sprite, 1, rows, tiles, base, attr) == 1;
}

int vq_strip_attr(VramQueue *q, u16 sprite, const u16 *pairs, u16 base, u8 rows) {
    VqOp op = { pairs, sprite, base, 0, VQ_STRIP_ATTR, rows, (u16)(VQ_US_STRIP + VQ_US_ROW * rows), 0 };
    q->strip[sprite].tiles = 0; /* the plain strip dedupe must not believe the column still holds its old tiles */
    return push(q, &op);
}

int vq_pal(VramQueue *q, u16 idx, u16 val) {
    VqOp op = { 0, idx, val, 0, VQ_PAL, 0, VQ_US_PAL, 0 };
    return push(q, &op);
}

void vq_fix_put(VramQueue *q, u8 x, u8 y, u16 cell) {
    if (x >= VQ_FIX_COLS || y >= VQ_FIX_ROWS) return;
    u16 i = (u16)(x * VQ_FIX_ROWS + y);
    if (q->fix_want[i] == cell) return;
    q->fix_want[i] = cell;
    q->fix_dirty[x] |= 1ul << y;
    q->fix_any = 1;
}

void vq_fix_text(VramQueue *q, u8 x, u8 y, u16 hi, const u16 *map, const char *s) {
    if (y >= VQ_FIX_ROWS) return;
    u16 i = (u16)(x * VQ_FIX_ROWS + y);
    for (; *s && x < VQ_FIX_COLS; s++, x++, i = (u16)(i + VQ_FIX_ROWS)) {
        u16 cell = (u16)(hi | map[(u8)*s]);
        if (q->fix_want[i] == cell) continue;
        q->fix_want[i] = cell;
        q->fix_dirty[x] |= 1ul << y;
        q->fix_any = 1;
    }
}

/* Marks only the cells whose wanted value changes: a clear of a screen that is mostly blank already must not hand the
 * commit 1280 cells to compare (tests/host/test_vram_queue.c). */
void vq_fix_fill(VramQueue *q, u16 cell) {
    u16 *w = q->fix_want;
    for (u16 x = 0; x < VQ_FIX_COLS; x++) {
        uint32_t m = 0, bit = 1;
        for (u16 y = 0; y < VQ_FIX_ROWS; y++, w++, bit <<= 1)
            if (*w != cell) { *w = cell; m |= bit; }
        q->fix_dirty[x] |= m;
        if (m) q->fix_any = 1;
    }
}

/* Walks only the dirty bits: the cost is per changed cell, not per touched column (a whole-column scan cost about
 * 3.6 raster lines per column at the end of the logic frame and pushed "cam moved" frames past line 224). */
int vq_fix_commit_n(VramQueue *q, u16 budget) {
    if (!q->fix_any) return 1; /* most frames change no fix cell: the empty 40 column walk cost about 6 lines */
    for (u16 x = 0; x < VQ_FIX_COLS; x++) {
        uint32_t m = q->fix_dirty[x];
        if (!m) continue;
        u16 i = (u16)(x * VQ_FIX_ROWS), r = 0;
        for (; m; m >>= 1, i++, r++) {
            /* skip clean rows 8 at a time: a bit-per-row walk cost ~1.5 raster lines per column for one cell low on the screen (arc-fix) */
            while (!(m & 0xFFu)) { m >>= 8; i = (u16)(i + 8); r = (u16)(r + 8); }
            if (!(m & 1) || q->fix_want[i] == q->fix_hw[i]) continue;
            VqOp op = { 0, (u16)(VQ_FIX_BASE + i), q->fix_want[i], 0, VQ_WORD, 0, VQ_US_OP, 0 };
            if (!push(q, &op)) { q->fix_dirty[x] = m << r; return 0; } /* this row and the rest stay dirty */
            q->fix_hw[i] = q->fix_want[i];
            if (--budget == 0) { q->fix_dirty[x] = (m >> 1) << (r + 1); return 1; } /* the next commit resumes after row r */
        }
        q->fix_dirty[x] = 0;
    }
    q->fix_any = 0; /* the cut and queue-full returns above leave bits, and the flag, set */
    return 1;
}

/* shortcut: counts ops, not VRAM words; the reserve is tuned in ops (gfx.c) */
int vq_fix_commit_room(VramQueue *q, u16 max, u16 reserve) {
    u16 pend = vq_pending(q);
    if (pend + reserve >= VQ_CAP) return 1; /* no room above the reserve: the columns stay dirty for the next frame */
    u16 room = (u16)(VQ_CAP - reserve - pend);
    return vq_fix_commit_n(q, room < max ? room : max);
}

int vq_fix_commit(VramQueue *q) { return vq_fix_commit_n(q, 0xFFFFu); }
