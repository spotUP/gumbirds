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
    q->fix_col = 0;
    for (u16 i = 0; i < VQ_SCB_WORDS; i++) q->scb_valid[i] = 0;
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
    q->scb_valid[i] = 1;
    return 1;
}

int vq_scb_run(VramQueue *q, u16 addr, u16 mod, const u16 *vals, u8 n) {
    u16 i = (u16)(addr - VQ_SCB_BASE);
    if (!n || !mod || i >= VQ_SCB_WORDS || (u16)(i + (n - 1) * mod) >= VQ_SCB_WORDS) return 0;
    if (q->count >= VQ_CAP) return 0;  /* checked before the shadow changes: a failed call changes nothing */
    /* Per-frame path (the pool view sends 2 runs of POOL_MAX words; the hazard strip 2-4 runs of 24). An index-and-bit
     * form spilled its counters and cost about 250 cycles per word, 21 scanlines a frame for the pool's 64 words. */
    /* Pointer walk with a byte valid flag: no index, bit or spilled counter per word (vblank-demo.md Part 6). */
    const unsigned step = mod;
    u16 *hw = &q->scb_hw[i];
    u8 *valid = &q->scb_valid[i];
    /* Two loops, so no first/last flag is tested per word: gcc kept fp/lp and the strides on the stack in the single loop,
     * about 150 cycles per changed word, 9 scanlines for the island SCB4 run alone (vblank-demo.md Part 7). */
    const u16 *v = vals, *const vend = vals + n, *fp, *lp;
    for (; v != vend; v++, hw += step, valid += step)
        if (*hw != *v || !*valid) break;
    if (v == vend) return 1;
    fp = v;
    do {
        *hw = *v;
        *valid = 1;
        lp = v;
        do { v++; hw += step; valid += step; } while (v != vend && *hw == *v && *valid);
    } while (v != vend);
    int first = (int)(fp - vals), last = (int)(lp - vals);
    u16 a = (u16)(addr + (u16)first * mod);
    u8 words = (u8)(last - first + 1);
    VqOp op = { &q->scb_hw[a - VQ_SCB_BASE], a, mod, 0, VQ_RUN, words, (u16)(VQ_US_RUN + VQ_US_RUN_WORD * words), 0 };
    return push(q, &op);
}

void vq_scb_forget(VramQueue *q, u16 addr, u16 n) {
    for (u16 i = (u16)(addr - VQ_SCB_BASE); n && i < VQ_SCB_WORDS; i++, n--) q->scb_valid[i] = 0;
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

int vq_vram_run(VramQueue *q, u16 addr, u16 mod, const u16 *src, u8 n) {
    if (!n || !mod) return 1;   /* nothing to write; 0 would make gfx RETRY wait forever */
    VqOp op = { src, addr, mod, 0, VQ_RUN, n, (u16)(VQ_US_RUN + VQ_US_RUN_WORD * n), 0 };
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
/* Two cells per compare and store: the cell-by-cell loop cost about 99 raster lines for a full clear (the arcade stage entry after
 * the bonus result screen, thoughts/spot/reports/stage-spike.md). Only a pair that differs pays the per-cell check, so the dirty bits stay exact. */
typedef uint32_t __attribute__((may_alias)) vq_pair;
void vq_fix_fill(VramQueue *q, u16 cell) {
    vq_pair *w = (vq_pair *)q->fix_want;
    const vq_pair cc = ((vq_pair)cell << 16) | cell;
    for (u16 x = 0; x < VQ_FIX_COLS; x++) {
        uint32_t m = 0, bit = 1; /* row 2y; bit << 1 is row 2y + 1 (no mask maths per pair: a full clear of the result screen
                                     differs on most pairs and cost about 127 raster lines on the stage entry frame) */
        for (u16 y = 0; y < VQ_FIX_ROWS / 2; y++, w++, bit <<= 2)
            if (*w != cc) {
                const u16 *h = (const u16 *)w;
                if (h[0] != cell) m |= bit;
                if (h[1] != cell) m |= bit + bit;
                *w = cc;
            }
        q->fix_dirty[x] |= m;
        if (m) q->fix_any = 1;
    }
}

/* Blank the whole layer without comparing: every cell wanted blank, every column dirty. vq_fix_fill's per-pair compare cost 164
 * raster lines when the result screen ends (it wrote nearly every cell); the commit still pushes only cells that differ from the
 * hardware, in the same order, so the screen is the same. Use it only when most cells are known non-blank. */
void vq_fix_wipe(VramQueue *q, u16 cell) {
    vq_pair *w = (vq_pair *)q->fix_want;
    const vq_pair cc = ((vq_pair)cell << 16) | cell;
    for (u16 i = 0; i < VQ_FIX_COLS * VQ_FIX_ROWS / 2; i++) w[i] = cc;
    for (u16 x = 0; x < VQ_FIX_COLS; x++) q->fix_dirty[x] = 0xFFFFFFFFul;
    q->fix_any = 1;
}

/* One pass with no per-cell call: blanking the 22 x 8 round clear banner through vq_fix_put cost about 200 raster lines
 * on the stage switch frame and pushed the logic of that frame past vblank (make test-arcade-walk). */
u16 vq_fix_clear_shadowed(VramQueue *q, u8 x, u8 y, u8 w, u8 h, u16 *shadow, u16 cell) {
    u16 n = 0;
    if (x + w > VQ_FIX_COLS || y + h > VQ_FIX_ROWS) return 0;
    for (u8 c = 0; c < w; c++) {
        u16 *want = &q->fix_want[(x + c) * VQ_FIX_ROWS + y], *sh = shadow + c;
        uint32_t m = 0, bit = 1ul << y;
        for (u8 r = 0; r < h; r++, want++, sh += w, bit <<= 1) {
            if (*sh == cell) continue;
            *sh = cell;
            if (*want != cell) { *want = cell; m |= bit; }
            n++;
        }
        q->fix_dirty[x + c] |= m;
        if (m) q->fix_any = 1;
    }
    return n;
}

/* Column-major like fix_want, one dirty mask per column: blanking the 36 x 3 round-start rows through vq_fix_text cost
 * about 34 raster lines and pushed the pool stress frame past vblank (make test-vblank, thoughts/spot/reports/cpu-gum-vblank.md). */
void vq_fix_clear(VramQueue *q, u8 x, u8 y, u8 w, u8 h, u16 cell) {
    if (x + w > VQ_FIX_COLS || y + h > VQ_FIX_ROWS) return;
    for (u8 c = 0; c < w; c++) {
        u16 *want = &q->fix_want[(x + c) * VQ_FIX_ROWS + y];
        uint32_t m = 0, bit = 1ul << y;
        for (u8 r = 0; r < h; r++, want++, bit <<= 1)
            if (*want != cell) { *want = cell; m |= bit; }
        if (m) { q->fix_dirty[x + c] |= m; q->fix_any = 1; }
    }
}

/* Walks only the dirty bits: the cost is per changed cell, not per touched column (a whole-column scan cost about
 * 3.6 raster lines per column at the end of the logic frame and pushed "cam moved" frames past line 224). */
/* Close the open run: one changed cell goes out as a plain word op (18 us), more as one VQ_RUN read from fix_hw at
 * flush time (22 + 4 us per word). A later change to a run cell writes its own op, so reading the shadow late is safe. */
static void fix_run_close(VramQueue *q, VqOp *op) {
    if (op->rows == 1) { op->kind = VQ_WORD; op->b = *op->tiles; op->cost = VQ_US_OP; }
    q->count++;
}

/* index of the lowest set bit of a byte (0 for 0): lets the commit jump to the next dirty row instead of testing 32 bits one by one */
static const uint8_t CTZ8[256] = {
    0, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0, 4, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,
    5, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0, 4, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,
    6, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0, 4, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,
    5, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0, 4, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,
    7, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0, 4, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,
    5, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0, 4, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,
    6, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0, 4, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,
    5, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0, 4, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0 };

/* Changed rows next to each other in a column (column-major: consecutive fix addresses) share one VQ_RUN op. Storm rain
 * changes about 70 cells a frame in short vertical streaks; one op per cell cost about 63 lines of logic frame and
 * pushed the commit past VQ_FIX_LINE_END (budget 0: no rain reached VRAM, make test-rain / test-vblank).
 * The budget still counts cells, so the flush time bound is unchanged. */
/* The cell budget alone did not bound the commit time: storm rain frames reached the commit at line 0x1BD with a 41 cell budget
 * and ended at 0x1F2..0x1F8, past vblank (the dirty bit walk and the run ops cost more than a line a cell; 19 dropped frames in
 * make test-rain). With lspc the commit reads the raster line before each dirty column and stops at VQ_FIX_LINE_END. Not per
 * cell: a read per queued cell made the pool stress frames of make test-vblank miss every other vblank (665 of 1331) and froze
 * the walk clip in make test-flier. */
static int late(const volatile u16 *lspc) {
    if (!lspc) return 0;
    u16 l = VQ_RASTER_LINE(*lspc);
    return l >= VQ_FIX_LINE_END && l < 0x1F0u;
}
static int fix_commit(VramQueue *q, u16 budget, const volatile u16 *lspc) {
    if (!q->fix_any) return 1;
    for (u16 n = 0, x = q->fix_col; n < VQ_FIX_COLS; n++, x = (u16)(x + 1 == VQ_FIX_COLS ? 0 : x + 1)) {
        uint32_t m = q->fix_dirty[x];
        if (!m) continue;
        if (late(lspc)) { q->fix_col = (u8)x; return 1; }
        u16 i = (u16)(x * VQ_FIX_ROWS), r = 0;
        VqOp *op = 0;
        for (; m; m >>= 1, i++, r++) {
            if (!(m & 0xFFu)) {
                if (op) { fix_run_close(q, op); op = 0; }
                do { m >>= 8; i = (u16)(i + 8); r = (u16)(r + 8); } while (!(m & 0xFFu));
            }
            u16 t = CTZ8[m & 0xFFu];
            if (t) { /* a gap of clean rows ends the run */
                if (op) { fix_run_close(q, op); op = 0; }
                m >>= t; i = (u16)(i + t); r = (u16)(r + t);
            }
            if (q->fix_want[i] == q->fix_hw[i]) {
                if (op) { fix_run_close(q, op); op = 0; }
                continue;
            }
            if (!op) {
                if (!(op = tail_op(q))) { q->fix_dirty[x] = m << r; q->fix_col = (u8)x; return 0; }
                op->tiles = &q->fix_hw[i]; op->a = (u16)(VQ_FIX_BASE + i); op->b = 1; op->c = 0;
                op->kind = VQ_RUN; op->rows = 0; op->cost = VQ_US_RUN; op->split = 0;
            }
            q->fix_hw[i] = q->fix_want[i];
            op->rows++;
            op->cost = (u16)(op->cost + VQ_US_RUN_WORD);
            if (--budget == 0) { fix_run_close(q, op); q->fix_dirty[x] = (m >> 1) << (r + 1); q->fix_col = (u8)x; return 1; }
        }
        if (op) fix_run_close(q, op);
        q->fix_dirty[x] = 0;
    }
    q->fix_any = 0;
    return 1;
}

/* shortcut: counts ops, not VRAM words; the reserve is tuned in ops (gfx.c). Cells per commit <= ops, so room holds. */
int vq_fix_commit_n(VramQueue *q, u16 budget) { return fix_commit(q, budget, 0); }

int vq_fix_commit_room(VramQueue *q, u16 max, u16 reserve, const volatile u16 *lspc) {
    u16 pend = vq_pending(q);
    if (pend + reserve >= VQ_CAP) return 1; /* no room above the reserve: the columns stay dirty for the next frame */
    u16 room = (u16)(VQ_CAP - reserve - pend);
    return fix_commit(q, room < max ? room : max, lspc);
}

int vq_fix_commit(VramQueue *q) { return vq_fix_commit_n(q, 0xFFFFu); }
