/* Host tests for the video write queue (src/core/vram_queue.c): dedup, ordering, overflow, fix diff. */
#include <stdio.h>
#include <string.h>
#include "../../src/core/vram_queue.h"
#include "gen/fix_font.h"

static int failures, checks;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static VramQueue q;
static const u16 tiles_a[4] = {1, 2, 3, 4}, tiles_b[4] = {5, 6, 7, 8};

/* Reference model of the SCB shadow before the byte-per-word valid flag (bit array, vblank-demo.md Part 6): random runs,
 * forgets and pushes must give the same queued ops and the same VRAM words. */
static u16 ref_hw[VQ_SCB_WORDS], ref_vram[VQ_SCB_WORDS], q_vram[VQ_SCB_WORDS];
static u8 ref_valid[VQ_SCB_WORDS / 8];
static uint32_t lcg = 12345;
static u16 rnd(u16 n) { lcg = lcg * 1103515245u + 12345u; return (u16)((lcg >> 16) % n); }
static void drain_to(u16 *vram) {
    const VqOp *op;
    while ((op = vq_peek(&q))) {
        if (op->kind == VQ_RUN) for (u8 k = 0; k < op->rows; k++) vram[op->a - VQ_SCB_BASE + k * op->b] = op->tiles[k * op->b];
        else if (op->kind == VQ_WORD) vram[op->a - VQ_SCB_BASE] = op->b;
        vq_pop(&q);
    }
}
static void scb_shadow_equivalence(void)
{
    static const u16 vals[4] = {0, 0xFFF, 0x40, 0x1234};
    u16 v[48];
    vq_init(&q);
    memset(ref_hw, 0, sizeof ref_hw); memset(ref_valid, 0, sizeof ref_valid);
    for (int it = 0; it < 20000; it++) {
        u16 i = rnd(VQ_SCB_WORDS - 200), mod = (u16)(1 + rnd(3)), n = (u16)(1 + rnd(48));
        int what = rnd(4);
        for (u16 k = 0; k < n; k++) v[k] = vals[rnd(4)];
        if (what == 0) { vq_scb_forget(&q, (u16)(VQ_SCB_BASE + i), n);
            for (u16 k = 0; k < n; k++) ref_valid[(i + k) >> 3] &= (u8)~(1u << ((i + k) & 7));
        } else if (what == 1) { CHECK(vq_scb_word_push(&q, (u16)(VQ_SCB_BASE + i), v[0]));
            ref_hw[i] = v[0]; ref_valid[i >> 3] |= (u8)(1u << (i & 7)); ref_vram[i] = v[0];
        } else {
            CHECK(vq_scb_run(&q, (u16)(VQ_SCB_BASE + i), mod, v, (u8)n));
            int first = -1, last = 0;
            for (u16 k = 0; k < n; k++) {
                u16 j = (u16)(i + k * mod);
                if (ref_hw[j] == v[k] && (ref_valid[j >> 3] & (1u << (j & 7)))) continue;
                ref_hw[j] = v[k]; ref_valid[j >> 3] |= (u8)(1u << (j & 7));
                if (first < 0) first = k;
                last = k;
            }
            const VqOp *op = vq_peek(&q);
            if (first < 0) CHECK(!op);
            else {
                CHECK(op && op->a == VQ_SCB_BASE + i + first * mod && op->rows == last - first + 1 && op->b == mod);
                for (int k = first; k <= last; k++) ref_vram[i + k * mod] = v[k];
            }
        }
        drain_to(q_vram);
        for (u16 j = i; j < i + 48 * 3 && j < VQ_SCB_WORDS; j++)
            if (q_vram[j] != ref_vram[j] || q.scb_hw[j] != ref_hw[j] || !q.scb_valid[j] != !(ref_valid[j >> 3] & (1u << (j & 7)))) { CHECK(0); return; }
    }
    CHECK(!memcmp(q_vram, ref_vram, sizeof q_vram));
}

static u16 total_cost(void)
{
    u16 n = 0;
    const VqOp *op;
    while ((op = vq_peek(&q)) != 0) { n = (u16)(n + vq_cost(op)); vq_pop(&q); }
    return n;
}

/* Commit the fix layer, draining the queue whenever it fills; returns the number of cells written. */
static int commit_all(void)
{
    int n = 0;
    while (!vq_fix_commit(&q)) { n += vq_pending(&q); (void)total_cost(); }
    n += vq_pending(&q);
    (void)total_cost();
    return n;
}

/* VQ_RAMP: generated words, two segments, no shadow change, bounds */
static void ramp_tests(void)
{
    u16 out[24];
    const VqOp *op;
    vq_init(&q);
    CHECK(vq_scb_ramp(&q, 0x8420, 5, 2, 0x1000, 0x0F80) && vq_pending(&q) == 1);
    op = vq_peek(&q);
    CHECK(op->kind == VQ_RAMP && op->a == 0x8420 && op->rows == 5 && vq_cost(op) == VQ_US_RAMP + 5 * VQ_US_RAMP_WORD);
    vq_ramp_expand(op, out);
    CHECK(out[0] == 0x1000 && out[1] == 0x1800 && out[2] == 0x0F80 && out[3] == 0x1780 && out[4] == 0x1F80);
    CHECK(q.scb_valid[0x420] == 0);            /* no shadow written */
    vq_pop(&q);
    vq_ramp_expand(&(VqOp){ 0, 0, 0xF800, 0x0000, VQ_RAMP, 2, 0, 2 }, out);   /* u16 wrap: x 496 + 16 = 512 -> 0 */
    CHECK(out[0] == 0xF800 && out[1] == 0x0000);
    CHECK(!vq_scb_ramp(&q, 0x8420, 0, 0, 0, 0));      /* empty */
    CHECK(!vq_scb_ramp(&q, 0x8420, 4, 5, 0, 0));      /* split beyond n */
    CHECK(!vq_scb_ramp(&q, 0x7FFF, 4, 1, 0, 0));      /* below SCB2 */
    CHECK(!vq_scb_ramp(&q, 0x8000 + VQ_SCB_WORDS - 3, 4, 1, 0, 0));   /* runs past SCB4 */
    CHECK(vq_pending(&q) == 0);
    { int i; for (i = 0; i < VQ_CAP; i++) CHECK(vq_scb_ramp(&q, 0x8420, 3, 1, 0, 0)); }
    CHECK(!vq_scb_ramp(&q, 0x8420, 3, 1, 0, 0));      /* full */
    vq_init(&q);
}

int main(void)
{
    ramp_tests();
    scb_shadow_equivalence();
    vq_init(&q);
    /* SCB words: first write queues, identical write queues nothing, changed write queues again */
    CHECK(vq_scb_word(&q, 0x8400, 7) && vq_pending(&q) == 1);
    CHECK(vq_scb_word(&q, 0x8400, 7) && vq_pending(&q) == 1);
    CHECK(vq_scb_word(&q, 0x8400, 8) && vq_pending(&q) == 2);
    CHECK(vq_peek(&q)->a == 0x8400 && vq_peek(&q)->b == 7);
    vq_pop(&q);
    CHECK(vq_peek(&q)->b == 8);
    vq_pop(&q);
    CHECK(vq_pending(&q) == 0 && vq_peek(&q) == 0);
    /* a value of 0xFFFF is a real value, not the "unknown" marker */
    CHECK(vq_scb_word(&q, 0x8200, 0xFFFF) && vq_pending(&q) == 1);
    CHECK(vq_scb_word(&q, 0x8200, 0xFFFF) && vq_pending(&q) == 1);
    CHECK(!vq_scb_word(&q, 0x7000, 1));
    (void)total_cost();
    /* strips dedup on descriptor */
    CHECK(vq_strip(&q, 10, tiles_a, 256, 2, 0x300) && vq_pending(&q) == 1);
    CHECK(vq_strip(&q, 10, tiles_a, 256, 2, 0x300) && vq_pending(&q) == 1);
    CHECK(vq_strip(&q, 10, tiles_b, 256, 2, 0x300) && vq_pending(&q) == 2);
    CHECK(vq_strip(&q, 10, tiles_b, 256, 2, 0x400) && vq_pending(&q) == 3);
    CHECK(vq_strip(&q, 10, tiles_b, 256, 3, 0x400) && vq_pending(&q) == 4);
    {   /* vq_strips: column c gets tiles + c * rows and sprite first + c; unchanged columns are skipped */
        static const u16 blk[6] = { 1, 2, 3, 4, 5, 6 };
        VramQueue s;
        vq_init(&s);
        CHECK(vq_strips(&s, 20, 3, 2, blk, 256, 0x300) == 3 && vq_pending(&s) == 3);
        CHECK(vq_peek(&s)->a == 20 && vq_peek(&s)->tiles == blk);
        vq_pop(&s);
        CHECK(vq_peek(&s)->a == 21 && vq_peek(&s)->tiles == blk + 2);
        CHECK(vq_strips(&s, 20, 3, 2, blk, 256, 0x300) == 3 && vq_pending(&s) == 2);
        CHECK(vq_strip(&s, 21, blk + 2, 256, 2, 0x300) && vq_pending(&s) == 2);
    }
    {   /* vq_strip_attr: one op per column, always queued, carries the {tile, attribute} pairs and the cost of a plain strip */
        static const u16 pairs[4] = { 1, 0x300, 2, 0x500 };
        VramQueue a;
        vq_init(&a);
        CHECK(vq_strip_attr(&a, 5, pairs, 256, 2) && vq_pending(&a) == 1);
        CHECK(vq_peek(&a)->kind == VQ_STRIP_ATTR && vq_peek(&a)->tiles == pairs && vq_peek(&a)->a == 5 && vq_peek(&a)->rows == 2);
        CHECK(vq_cost(vq_peek(&a)) == VQ_US_STRIP + 2 * VQ_US_ROW);
        CHECK(vq_strip(&a, 5, tiles_a, 256, 2, 0x300) && vq_pending(&a) == 2); /* a plain strip after it is not deduped away */
    }
    CHECK(vq_strip(&q, 11, tiles_b, 256, 3, 0x400) && vq_pending(&q) == 5);
    CHECK(vq_cost(vq_peek(&q)) == VQ_US_STRIP + 2 * VQ_US_ROW);
    (void)total_cost();
    /* palette and plain words are never deduplicated */
    CHECK(vq_pal(&q, 5, 1) && vq_pal(&q, 5, 1) && vq_pending(&q) == 2 && total_cost() == 2 * VQ_US_PAL);
    CHECK(vq_vram_word(&q, 0, 1) && vq_vram_word(&q, 0, 1) && vq_pending(&q) == 2);
    (void)total_cost();
    /* fix layer: a clear plus the same text is no hardware change after the first commit */
    vq_fix_fill(&q, 0x20);
    vq_fix_put(&q, 2, 3, 0x1041);
    CHECK(commit_all() == VQ_FIX_COLS * VQ_FIX_ROWS);
    vq_fix_fill(&q, 0x20);
    vq_fix_put(&q, 2, 3, 0x1041);
    CHECK(commit_all() == 0);
    /* fill_runs: one run per column, nothing left dirty, a later same-cell put pushes nothing */
    {
        static VramQueue r; vq_init(&r);
        CHECK(vq_fix_fill_runs(&r, 0x20) && vq_pending(&r) == VQ_FIX_COLS);
        const VqOp *op = vq_peek(&r);
        CHECK(op->kind == VQ_RUN && op->a == VQ_FIX_BASE && op->b == 1 && op->rows == VQ_FIX_ROWS && op->tiles[VQ_FIX_ROWS - 1] == 0x20);
        vq_fix_put(&r, 2, 3, 0x20);
        CHECK(vq_fix_commit(&r) && vq_pending(&r) == VQ_FIX_COLS);
    }
    /* wipe: same hardware result as a fill, only cells that differ are pushed */
    vq_fix_wipe(&q, 0x20);
    CHECK(commit_all() == 1);
    vq_fix_put(&q, 2, 3, 0x1041);
    CHECK(commit_all() == 1);
    vq_fix_put(&q, 2, 3, 0x1042);
    vq_fix_put(&q, 2, 3, 0x1042);
    CHECK(vq_fix_commit(&q) && vq_pending(&q) == 1);
    CHECK(vq_peek(&q)->a == VQ_FIX_BASE + 2 * VQ_FIX_ROWS + 3 && vq_peek(&q)->b == 0x1042);
    (void)total_cost();
    vq_fix_put(&q, 40, 0, 1); /* out of range is ignored */
    CHECK(commit_all() == 0);
    /* rectangle clear: only the changed cell is pushed, and its address is the column-major one; off-screen is ignored */
    vq_fix_put(&q, 5, 12, 0x1043);
    CHECK(commit_all() == 1);
    vq_fix_clear(&q, 4, 11, 3, 3, 0x20);
    CHECK(vq_fix_commit(&q) && vq_pending(&q) == 1 && vq_peek(&q)->a == VQ_FIX_BASE + 5 * VQ_FIX_ROWS + 12 && vq_peek(&q)->b == 0x20);
    (void)total_cost();
    vq_fix_clear(&q, 38, 0, 3, 1, 0x1044);
    CHECK(commit_all() == 0);
    /* clear by shadow: only the cells the shadow says differ change (a 2 x 2 box at (3, 4), one cell already blank) */
    {
        u16 sh[4] = { 0x1041, 0x20, 0x1042, 0x1043 }; /* row-major: (3,4) (4,4) / (3,5) (4,5) */
        vq_fix_put(&q, 3, 4, 0x1041); vq_fix_put(&q, 3, 5, 0x1042); vq_fix_put(&q, 4, 5, 0x1043);
        vq_fix_put(&q, 4, 4, 0x1055); /* not the banner's: its shadow cell is blank, so it stays */
        (void)commit_all();
        CHECK(vq_fix_clear_shadowed(&q, 3, 4, 2, 2, sh, 0x20) == 3);
        CHECK(sh[0] == 0x20 && sh[1] == 0x20 && sh[2] == 0x20 && sh[3] == 0x20);
        CHECK(q.fix_dirty[3] == ((1u << 4) | (1u << 5)) && q.fix_dirty[4] == (1u << 5));
        CHECK(commit_all() == 3);
        CHECK(vq_fix_clear_shadowed(&q, 3, 4, 2, 2, sh, 0x20) == 0 && commit_all() == 0);
        CHECK(vq_fix_clear_shadowed(&q, 39, 4, 2, 2, sh, 0x20) == 0); /* off the layer: ignored */
        vq_fix_put(&q, 4, 4, 0x20); /* leave the layer as the next block expects */
        (void)commit_all();
    }
    /* The commit runs at the end of the logic frame: its work must scale with the cells that changed, not with whole
     * columns (32 compares per touched column cost about 3.6 lines and pushed "cam moved" frames past line 224).
     * Dirty state is one bit per changed cell; a clear that changes nothing marks nothing. */
    {
        int clean = 1;
        vq_fix_fill(&q, 0x20);
        vq_fix_put(&q, 2, 3, 0x1041);
        for (u16 x = 0; x < VQ_FIX_COLS; x++) if (q.fix_dirty[x] != (x == 2 ? (1u << 3) : 0u)) clean = 0;
        CHECK(clean);
        (void)commit_all();
        vq_fix_fill(&q, 0x20);           /* same content again: no dirty cell outside the one that differs */
        clean = 1;
        for (u16 x = 0; x < VQ_FIX_COLS; x++) if (q.fix_dirty[x] != (x == 2 ? (1u << 3) : 0u)) clean = 0;
        CHECK(clean);
        (void)commit_all();
        for (u16 x = 0; x < VQ_FIX_COLS; x++) if (q.fix_dirty[x]) clean = 0;
        CHECK(clean);
        /* a budget cut mid-column keeps exactly the rows not queued yet */
        vq_fix_put(&q, 5, 1, 0x1001); vq_fix_put(&q, 5, 7, 0x1002); vq_fix_put(&q, 5, 31, 0x1003);
        CHECK(vq_fix_commit_n(&q, 2) && vq_pending(&q) == 2 && q.fix_dirty[5] == (1u << 31));
        CHECK(vq_fix_commit_n(&q, 2) && vq_pending(&q) == 3 && q.fix_dirty[5] == 0);
        /* A frame with no fix change (most play frames) must not walk the 40 columns: that empty walk cost about 6 lines
         * at the very end of the heaviest "cam moved" frames and pushed two past line 224. fix_any says a cell is dirty. */
        CHECK(q.fix_any == 0);
        vq_fix_put(&q, 5, 1, 0x1004); vq_fix_put(&q, 6, 2, 0x1005);
        CHECK(q.fix_any == 1);
        CHECK(vq_fix_commit_n(&q, 1) && q.fix_any == 1 && q.fix_dirty[6] == (1u << 2)); /* a budget cut keeps it set */
        CHECK(vq_fix_commit_n(&q, 1) && q.fix_dirty[6] == 0); /* budget spent on the last cell: the flag may stay set */
        {
            u16 p = vq_pending(&q);
            CHECK(vq_fix_commit_n(&q, 1) && q.fix_any == 0 && vq_pending(&q) == p); /* the next commit finds nothing, clears it */
        }
        vq_fix_fill(&q, 0x20);
        CHECK(q.fix_any == 1);
        (void)commit_all();
        CHECK(q.fix_any == 0);
        (void)total_cost();
    }
    /* budgeted commit with headroom: never fills the queue (the logic frame must not block), leftovers drain over frames */
    vq_fix_fill(&q, 0x30);
    {
        int frames = 0, total = 0;
        while (frames < 64) {
            u16 before = vq_pending(&q);
            CHECK(vq_fix_commit_room(&q, 128, 200));
            CHECK(vq_pending(&q) <= VQ_CAP - 200 || vq_pending(&q) == before);
            total += vq_pending(&q) - before;
            (void)total_cost();
            frames++;
            if (vq_pending(&q) == 0 && total == VQ_FIX_COLS * VQ_FIX_ROWS) break;
        }
        CHECK(total == VQ_FIX_COLS * VQ_FIX_ROWS && frames == 10);
    }
    /* a queue already full to the reserve takes no cells and keeps the columns dirty */
    vq_fix_fill(&q, 0x31);
    for (u16 i = 0; i < 190; i++) vq_pal(&q, i, i);
    CHECK(vq_fix_commit_room(&q, 128, 200) && vq_pending(&q) == 190); /* no room above the reserve */
    (void)total_cost();
    CHECK(vq_fix_commit_room(&q, 128, 200) && vq_pending(&q) == 128);
    (void)total_cost();
    (void)commit_all();
    /* font maps: plain, backed, tall (two rows), space and unknown are the blank tile 255 */
    vq_fix_fill(&q, FIXFONT_BLANK);
    (void)commit_all();
    vq_fix_text(&q, 0, 4, 3 << 12, fixfont_map, "A0 z\x01");
    vq_fix_text(&q, 0, 6, 3 << 12, fixfont_map_backed, "A0");
    vq_fix_text(&q, 0, 8, 1 << 12, fixfont_map_tall_top, "7");
    vq_fix_text(&q, 0, 9, 1 << 12, fixfont_map_tall_bottom, "7");
    CHECK(q.fix_want[0 * VQ_FIX_ROWS + 4] == (u16)((3 << 12) | FIXFONT_LETTER_A));
    CHECK(q.fix_want[1 * VQ_FIX_ROWS + 4] == (u16)((3 << 12) | FIXFONT_DIGIT_0));
    CHECK(q.fix_want[2 * VQ_FIX_ROWS + 4] == (u16)((3 << 12) | FIXFONT_BLANK));
    CHECK(q.fix_want[3 * VQ_FIX_ROWS + 4] == (u16)((3 << 12) | fixfont_map['Z']) && fixfont_map['z'] == fixfont_map['Z']);
    CHECK(q.fix_want[4 * VQ_FIX_ROWS + 4] == (u16)((3 << 12) | FIXFONT_BLANK));
    CHECK(q.fix_want[0 * VQ_FIX_ROWS + 6] == (u16)((3 << 12) | (FIXFONT_LETTER_A + FIXFONT_BACKED)));
    CHECK(q.fix_want[1 * VQ_FIX_ROWS + 6] == (u16)((3 << 12) | (FIXFONT_DIGIT_0 + FIXFONT_BACKED)));
    CHECK(q.fix_want[0 * VQ_FIX_ROWS + 8] == (u16)((1 << 12) | (FIXFONT_TALL_TOP + 7)));
    CHECK(q.fix_want[0 * VQ_FIX_ROWS + 9] == (u16)((1 << 12) | (FIXFONT_TALL_BOTTOM + 7)));
    vq_fix_text(&q, 0, 10, 2 << 12, fixfont_map_tall_top_backed, "7");
    vq_fix_text(&q, 0, 11, 2 << 12, fixfont_map_tall_bottom_backed, "7");
    CHECK(q.fix_want[0 * VQ_FIX_ROWS + 10] == (u16)((2 << 12) | (FIXFONT_TALL_TOP + 7 + FIXFONT_TALL_BACKED)));
    CHECK(q.fix_want[0 * VQ_FIX_ROWS + 11] == (u16)((2 << 12) | (FIXFONT_TALL_BOTTOM + 7 + FIXFONT_TALL_BACKED)));
    vq_fix_fill(&q, 0x20); /* restore the state the next check expects: all 0x20 except one lit cell */
    vq_fix_put(&q, 2, 3, 0x1042);
    (void)commit_all();
    /* clear erases only what was lit */
    vq_fix_fill(&q, 0x20);
    CHECK(commit_all() == 1);
    /* overflow: nothing is changed by a failed enqueue, the retry after a pop succeeds */
    for (u16 i = 0; i < VQ_CAP; i++) CHECK(vq_pal(&q, i, 1));
    CHECK(!vq_pal(&q, 0, 1));
    CHECK(!vq_scb_word(&q, 0x8401, 9));
    vq_pop(&q);
    CHECK(vq_scb_word(&q, 0x8401, 9) && vq_pending(&q) == VQ_CAP);
    (void)total_cost();
    /* a commit that runs out of room resumes where it stopped and loses no cell */
    vq_fix_fill(&q, 0x30);
    for (u16 i = 0; i < 300; i++) vq_fix_put(&q, (u8)(i % 40), (u8)(i % 32), (u16)(0x100 + i));
    CHECK(commit_all() == VQ_FIX_COLS * VQ_FIX_ROWS);
    /* invalidate forgets pending ops and shadows */
    CHECK(vq_scb_word(&q, 0x8400, 8));
    vq_invalidate(&q);
    CHECK(vq_pending(&q) == 0 && vq_scb_word(&q, 0x8400, 8) && vq_pending(&q) == 1);
    (void)total_cost();
    CHECK(vq_strip(&q, 10, tiles_a, 256, 2, 0x300) && vq_pending(&q) == 1);
    (void)total_cost();

    /* strided SCB runs: one op for the changed span, values read from the shadow at flush time, dedupe shared with
     * vq_scb_word */
    vq_invalidate(&q);
    {
        u16 v[4] = {10, 11, 12, 13};
        const VqOp *op;
        CHECK(vq_scb_run(&q, 0x8460, 3, v, 4) && vq_pending(&q) == 1);
        op = vq_peek(&q);
        CHECK(op->kind == VQ_RUN && op->a == 0x8460 && op->b == 3 && op->rows == 4);
        CHECK(vq_cost(op) == VQ_US_RUN + 4 * VQ_US_RUN_WORD);
        for (u16 k = 0; k < 4; k++) CHECK(op->tiles[k * 3] == v[k]);
        (void)total_cost();
        CHECK(vq_scb_run(&q, 0x8460, 3, v, 4) && vq_pending(&q) == 0);   /* unchanged: nothing queued */
        CHECK(vq_scb_word(&q, 0x8463, 11) && vq_pending(&q) == 0);       /* shadow shared with single words */
        v[1] = 21; v[2] = 22;
        CHECK(vq_scb_run(&q, 0x8460, 3, v, 4) && vq_pending(&q) == 1);   /* only the changed span */
        op = vq_peek(&q);
        CHECK(op->a == 0x8463 && op->rows == 2 && op->tiles[0] == 21 && op->tiles[3] == 22);
        CHECK(vq_scb_word(&q, 0x8466, 30));                              /* a later change: the run writes it too */
        CHECK(vq_peek(&q)->tiles[3] == 30);
        (void)total_cost();
        CHECK(!vq_scb_run(&q, 0x7000, 1, v, 4));                         /* out of range */
        CHECK(!vq_scb_run(&q, 0x85FE, 1, v, 4));                         /* runs past SCB4 */
        for (u16 i = 0; i < VQ_CAP; i++) CHECK(vq_pal(&q, i, 1));
        v[0] = 99;
        CHECK(!vq_scb_run(&q, 0x8460, 3, v, 4));                         /* full: shadow unchanged */
        (void)total_cost();
        CHECK(vq_scb_word(&q, 0x8460, 10) && vq_pending(&q) == 0);
    }

    /* round restart hides the hazard strip with one run op, not a word op per column: the bank swap writes SCB3 behind the
     * shadow, so the hide forgets the words and sends them as one run; a second hide in the same frame (start) adds nothing.
     * 96 word ops here made the restart frame overrun vblank start (thoughts/spot/2026-11-12-test-scroll-diagnosis.md). */
    vq_invalidate(&q);
    {
        static const u16 zero[50];
        const VqOp *op;
        CHECK(vq_scb_run(&q, 0x8304, 1, zero, 50) && vq_pending(&q) == 1);
        (void)total_cost();                                              /* hidden, shadow valid (one word each side too) */
        CHECK(vq_scb_run(&q, 0x8305, 1, zero, 48) && vq_pending(&q) == 0);   /* the swap wrote show words; shadow still says 0 */
        vq_scb_forget(&q, 0x8305, 48);
        CHECK(vq_scb_run(&q, 0x8305, 1, zero, 48) && vq_pending(&q) == 1);
        op = vq_peek(&q);
        CHECK(op && op->kind == VQ_RUN && op->a == 0x8305 && op->rows == 48);
        CHECK(op && vq_cost(op) == VQ_US_RUN + 48 * VQ_US_RUN_WORD);
        CHECK(vq_scb_run(&q, 0x8305, 1, zero, 24) && vq_scb_run(&q, 0x831D, 1, zero, 24) && vq_pending(&q) == 1);
        CHECK(vq_scb_word(&q, 0x8304, 0) && vq_scb_word(&q, 0x8335, 0) && vq_pending(&q) == 1); /* forget stays inside its range */
        (void)total_cost();
        vq_scb_forget(&q, 0x85FF, 8);                                    /* clipped at the end of SCB4 */
        vq_scb_forget(&q, 0x7000, 8);                                    /* below SCB2: ignored */
        CHECK(vq_scb_run(&q, 0x8305, 1, zero, 48) && vq_pending(&q) == 0);
    }

    /* Resume prologue IRQACK lands inside vblank: the raster gate accepts exactly the vblank lines minus the last one,
     * never a visible line (the bad write was at the first visible line, counter 0x110). Low bits (anim counter, PAL)
     * do not matter. */
    {
        int in = 0, vis_ok = 1;
        for (u16 line = 0xF8; line <= 0x1FF; line++) {
            u16 reg = (u16)((line << 7) | 0x7F);
            int gate = VQ_RASTER_IN_VBLANK(reg) ? 1 : 0;
            CHECK(gate == (VQ_RASTER_IN_VBLANK((u16)(line << 7)) ? 1 : 0));
            if (gate) in++;
            if (line >= 0x110 && line < 0x1F0 && gate) vis_ok = 0;
        }
        CHECK(in == 39);                                   /* 40 vblank lines, the last one is the margin */
        CHECK(vis_ok);
        CHECK(!VQ_RASTER_IN_VBLANK(0x110u << 7));          /* first visible line: the failing write */
        CHECK(!VQ_RASTER_IN_VBLANK(0x10Fu << 7));          /* last vblank line: no margin left */
        CHECK(VQ_RASTER_IN_VBLANK(0x1F0u << 7) && VQ_RASTER_IN_VBLANK(0xF8u << 7));
    }
    /* Fix commit budget by raster line: full early, shrinking late, none at the end line (arc-fix stage 1 entry). */
    CHECK(vq_fix_line_budget(0x100u) == VQ_FIX_COMMIT_MAX);
    CHECK(vq_fix_line_budget(0x120u) == VQ_FIX_COMMIT_MAX);
    CHECK(vq_fix_line_budget(0x1C9u) == (VQ_FIX_LINE_END - 0x1C9u) * VQ_FIX_CELLS_PER_LINE);
    CHECK(vq_fix_line_budget(VQ_FIX_LINE_END - 1u) == VQ_FIX_CELLS_PER_LINE);
    CHECK(vq_fix_line_budget(VQ_FIX_LINE_END) == 0 && vq_fix_line_budget(0x1FFu) == 0);

    printf("%d checks, %d failed\n", checks, failures);
    return failures ? 1 : 0;
}
