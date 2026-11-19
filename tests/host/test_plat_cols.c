/* plat_build: the contiguous-run fill of plat_cols against the old per-column wrap fill, every layout, several rings. */
#include <stdio.h>
#include <string.h>
#include "../../src/core/stage.c" /* static plat_cols; run.sh leaves stage.c out of this test's source list */

static void old_fill(uint8_t *out) {
    memset(out, 0, ARENA_W);
    for (int i = 0; i < plat_n; i++) {
        int r = plat_tab[i].half + FLIER_SOLID_MAX_HALF_W + SOLID_REACH_PX + 2;
        int x = plat_tab[i].cx - r + 1;
        while (x < 0) x += (int)col_ring;
        for (int k = 2 * r - 1; k > 0; k--) {
            if (x >= col_ring) x -= (int)col_ring;
            out[x++] |= (uint8_t)(1u << i);
        }
    }
}

int main(void) {
    int diffs = 0, cases = 0;
    int rings[] = { ARENA_W, FIELD_RING_W, 256 };
    for (unsigned q = 0; q < sizeof rings / sizeof rings[0]; q++) {
        arena_ring = rings[q];
        for (int l = 0; l < LAYOUT_TOTAL; l++) {
            uint8_t ref[ARENA_W];
            stage_select(l);
            old_fill(ref);
            cases++;
            if (memcmp(ref, plat_cols, ARENA_W)) { diffs++; printf("FAIL layout %d ring %d\n", l, rings[q]); }
        }
    }
    printf("test_plat_cols: %d cases, %d differences\n", cases, diffs);
    return diffs != 0;
}
