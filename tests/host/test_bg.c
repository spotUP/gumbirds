/* Host tests for the parallax background math (src/core/bg_scroll.c) against the generated plane tables. */
#include <stdio.h>
#include "../../src/core/bg_scroll.h"
#include "../../src/core/arena.h"
#include "gen/city_tables.h"

static int failures, checks;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static const unsigned char K[] = CITY_TABLE_PLANE_K;
static const unsigned char COLS[] = CITY_TABLE_PLANE_COLS;
static const unsigned char TOP[] = CITY_TABLE_PLANE_TOP;

int main(void)
{
    unsigned p, cam;
    CHECK(sizeof K == BG_PLANE_COUNT && sizeof COLS == BG_PLANE_COUNT && sizeof TOP == BG_PLANE_COUNT);
    /* sky fixed, near at world speed, the others in between and in order */
    CHECK(K[0] == 0 && K[BG_PLANE_COUNT - 1] == BG_K_ONE);
    for (p = 1; p < BG_PLANE_COUNT; p++) CHECK(K[p] > K[p - 1] && TOP[p] >= TOP[p - 1]);
    for (cam = 0; cam <= (unsigned)ARENA_CAM_MAX; cam++) {
        for (p = 0; p < BG_PLANE_COUNT; p++) {
            unsigned off = bg_plane_offset(cam, K[p]);
            int x = bg_plane_x(cam, K[p]);
            /* the offset is exactly cam * k / 16 rounded down, and x its negative */
            CHECK(off == cam * K[p] / 16 && x == -(int)off);
            /* monotone, at most 1 px per camera px */
            if (cam) CHECK(off >= bg_plane_offset(cam - 1, K[p]) && off - bg_plane_offset(cam - 1, K[p]) <= 1);
            /* the plane covers the whole 320 px screen at every camera x: left edge at or before 0, right edge at or after 320 */
            CHECK(x <= 0 && x + (int)COLS[p] * BG_COL_PX >= 320);
        }
        CHECK(bg_plane_x(cam, K[0]) == 0);                                /* sky never moves */
        CHECK(bg_plane_x(cam, K[BG_PLANE_COUNT - 1]) == -(int)cam);       /* near follows the world 16/16 */
        CHECK(bg_plane_offset(cam, K[1]) == cam / 4);                      /* far moves a quarter */
    }
    /* the widths are tight: at the camera limit the right edge meets the screen edge exactly */
    for (p = 0; p < BG_PLANE_COUNT; p++)
        CHECK(-bg_plane_x(ARENA_CAM_MAX, K[p]) + 320 == (int)COLS[p] * BG_COL_PX);
    printf("test_bg: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
