/* Host tests for the parallax background math (src/core/bg_scroll.c) against the generated plane tables. */
#include <stdio.h>
#include <stdint.h>
#include "../../src/core/bg_scroll.h"
#include "../../src/core/camera.h"
#include "../../src/core/vram_queue.h"
#include "gen/city_tables.h"

static int failures, checks;
static VramQueue q;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static const unsigned char K[] = CITY_TABLE_PLANE_K;
static const unsigned char COLS[] = CITY_TABLE_PLANE_COLS;
static const unsigned char TOP[] = CITY_TABLE_PLANE_TOP;

/* 64 bit reference of the plane offset: floor(u * k / 16) mod period. */
static uint32_t ref_off(uint32_t u, uint32_t k, uint32_t period) { return (uint32_t)((((uint64_t)u * k) >> 4) % period); }

int main(void)
{
    unsigned p, u, c;
    const unsigned top = 2 * CAM_LAP_PERIOD_PX + 383;
    CHECK(sizeof K == BG_PLANE_COUNT && sizeof COLS == BG_PLANE_COUNT && sizeof TOP == BG_PLANE_COUNT);
    /* sky fixed, near at world speed, the others in between and in order */
    CHECK(K[0] == 0 && K[BG_PLANE_COUNT - 1] == BG_K_ONE);
    for (p = 1; p < BG_PLANE_COUNT; p++) CHECK(K[p] > K[p - 1] && TOP[p] >= TOP[p - 1]);
    /* the planes are the agreed loops: widths 320 (sky, static), 336, 352, 368, 384 and factors 0, 4, 8, 12, 16 */
    for (p = 0; p < BG_PLANE_COUNT; p++) CHECK(COLS[p] * 16u == 320u + 16u * p && K[p] == 4u * p && K[p] % 4 == 0);
    for (p = 0; p < BG_PLANE_COUNT; p++) {
        unsigned W = COLS[p] * 16u, prev;
        /* forward, every unwrapped camera x over two laps plus a ring: equals the 64 bit reference (the compiled divide is exact) */
        for (u = 0; u <= top; u++) {
            unsigned off = bg_loop_offset(u, K[p], W);
            CHECK(off == ref_off(u, K[p], W) && off < W);
        }
        /* backward, same range */
        for (u = top + 1; u-- > 0;) CHECK(bg_loop_offset(u, K[p], W) == ref_off(u, K[p], W));
        /* the lap drop moves no plane: u and u - CAM_LAP_PERIOD_PX give the same offset (the camera hands over exactly there) */
        for (u = CAM_LAP_PERIOD_PX; u < CAM_LAP_PERIOD_PX + 384; u++)
            CHECK(bg_loop_offset(u, K[p], W) == bg_loop_offset(u - CAM_LAP_PERIOD_PX, K[p], W));
        /* the camera's own sequence across the drop, one px per step: the offset never steps by more than the plane's share (<= 1 px at k 16) */
        prev = bg_loop_offset(CAM_LAP_PERIOD_PX - 600, K[p], W);
        for (u = CAM_LAP_PERIOD_PX - 599; u < CAM_LAP_PERIOD_PX + 400; u++) {
            unsigned cam = u >= CAM_LAP_PERIOD_PX + 384 ? u - CAM_LAP_PERIOD_PX : u, off = bg_loop_offset(cam, K[p], W);
            CHECK(off == (prev + 1) % W || off == prev);
            prev = off;
        }
        /* placement: at every offset the columns tile the screen 0..319 exactly once, each pixel shows art column (s + off) mod W */
        for (u = 0; u < (K[p] ? W : 1u); u++) { /* the sky is static: only offset 0 occurs */
            unsigned char cov[320] = {0};
            unsigned s;
            for (c = 0; c < COLS[p]; c++) {
                int x = bg_column_x(u, c, W);
                CHECK(x > -16 && x < (int)W);
                for (s = 0; s < 16; s++) if (x + (int)s >= 0 && x + (int)s < 320) { cov[x + s]++; CHECK((((unsigned)(x + (int)s) + u) % W) / 16 == c); }
            }
            for (s = 0; s < 320; s++) CHECK(cov[s] == 1);
        }
    }
    /* ramp: for every plane width (sky 320, far 336, mid A 352, mid B 368, near 384) and every offset the op the producer queues
     * expands to the same words as the per-column model, and it touches no shadow (the range has no other writer) */
    for (p = 0; p < BG_PLANE_COUNT; p++) {
        unsigned W = COLS[p] * 16u, a = 0x8400u + 8u + p * 32u;
        for (u = 0; u < W; u++) {
            BgRamp r;
            u16 out[32];
            const VqOp *op;
            vq_init(&q);
            bg_ramp(u, W, &r);
            CHECK(vq_scb_ramp(&q, (u16)a, COLS[p], r.split, r.v1, r.v2) && vq_pending(&q) == 1);
            op = vq_peek(&q);
            CHECK(op->kind == VQ_RAMP && op->a == a && op->rows == COLS[p] && op->cost == VQ_US_RAMP + VQ_US_RAMP_WORD * COLS[p]);
            vq_ramp_expand(op, out);
            for (c = 0; c < COLS[p]; c++) CHECK(out[c] == VQ_SCB4_X(bg_column_x(u, c, W)));
            for (c = 0; c < VQ_SCB_WORDS / 8; c++) CHECK(q.scb_valid[c] == 0);
            CHECK(r.split < COLS[p]);
        }
    }
    CHECK(bg_loop_offset(top, K[0], 320) == 0);           /* sky never moves */
    CHECK(bg_loop_offset(100, K[4], 384) == 100);         /* near follows the world 16/16 */
    CHECK(bg_loop_offset(100, K[1], 336) == 25);          /* far moves a quarter */
    /* the wrapped ring camera is the WRONG feed: at the ring seam (384 -> 0) far, mid A and mid B jump by 96, 192, 288 px */
    CHECK(bg_loop_offset(384, K[1], 336) == 96 && bg_loop_offset(384, K[2], 352) == 192 && bg_loop_offset(384, K[3], 368) == 288);
    CHECK(bg_loop_offset(384, K[4], 384) == 0);
    printf("test_bg: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
