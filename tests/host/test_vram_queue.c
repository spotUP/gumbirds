/* Host tests for the video write queue (src/core/vram_queue.c): dedup, ordering, overflow, fix diff. */
#include <stdio.h>
#include "../../src/core/vram_queue.h"

static int failures, checks;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static VramQueue q;
static const u16 tiles_a[4] = {1, 2, 3, 4}, tiles_b[4] = {5, 6, 7, 8};

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

int main(void)
{
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
    CHECK(vq_strip(&q, 11, tiles_b, 256, 3, 0x400) && vq_pending(&q) == 5);
    CHECK(vq_cost(vq_peek(&q)) == VQ_US_STRIP + 2 * VQ_US_ROW);
    (void)total_cost();
    /* palette and plain words are never deduplicated */
    CHECK(vq_pal(&q, 5, 1) && vq_pal(&q, 5, 1) && vq_pending(&q) == 2 && total_cost() == 2 * VQ_US_OP);
    CHECK(vq_vram_word(&q, 0, 1) && vq_vram_word(&q, 0, 1) && vq_pending(&q) == 2);
    (void)total_cost();
    /* fix layer: a clear plus the same text is no hardware change after the first commit */
    vq_fix_fill(&q, 0x20);
    vq_fix_put(&q, 2, 3, 0x1041);
    CHECK(commit_all() == VQ_FIX_COLS * VQ_FIX_ROWS);
    vq_fix_fill(&q, 0x20);
    vq_fix_put(&q, 2, 3, 0x1041);
    CHECK(commit_all() == 0);
    vq_fix_put(&q, 2, 3, 0x1042);
    vq_fix_put(&q, 2, 3, 0x1042);
    CHECK(vq_fix_commit(&q) && vq_pending(&q) == 1);
    CHECK(vq_peek(&q)->a == VQ_FIX_BASE + 2 * VQ_FIX_ROWS + 3 && vq_peek(&q)->b == 0x1042);
    (void)total_cost();
    vq_fix_put(&q, 40, 0, 1); /* out of range is ignored */
    CHECK(commit_all() == 0);
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

    printf("%d checks, %d failed\n", checks, failures);
    return failures ? 1 : 0;
}
