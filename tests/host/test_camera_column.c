/* Ring column placement (plan R5): camera_column_x gives the screen x of ONE 16 px column or CAMERA_COL_HIDDEN. The sweep
 * checks the property that islands need: for a 96 px island at every camera value each column is hidden or inside
 * -15..319, and visible columns keep 16 px spacing on the ring. The old placement (one chain at camera_screen_x of the
 * whole island, head x + 16c) is computed alongside and its mismatches counted, to show what this replaces. */
#include <stdio.h>
#include "../../src/core/camera.h"
#include "../../src/core/stage.h"
#include "../../src/core/island_layout.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 10) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)
#define H CAMERA_COL_HIDDEN

/* Independent maths: ring distance of the column left edge ahead of the camera, 0..383, then folded to -16..367. */
static int want_x(int world, int cam) {
    int v = ((world - cam) % 384 + 384) % 384;
    if (v >= 368) v -= 384;
    return (v > -16 && v < 320) ? v : H;
}

/* Old single chain: head at camera_screen_x of the whole island, column c at head + 16c. */
static int old_x(int ix, int w, int c, int cam) {
    int sx = camera_screen_x(ix, cam, w) + 16 * c;
    return (sx > -16 && sx < 320) ? sx : H;
}

int main(void) {
    CHECK(camera_column_x(200, 100) == 100);
    CHECK(camera_column_x(0, 0) == 0);
    CHECK(camera_column_x(304, 0) == 304);
    CHECK(camera_column_x(320, 0) == H);
    CHECK(camera_column_x(64, 64) == 0);
    CHECK(camera_column_x(0, 64) == H);
    CHECK(camera_column_x(16, 64) == H);
    CHECK(camera_column_x(368, 64) == 304);
    CHECK(camera_column_x(0, 65) == 319);
    CHECK(camera_column_x(64, 65) == -1);
    CHECK(camera_column_x(304, 370) == 318);
    CHECK(camera_column_x(0, 370) == 14);
    CHECK(camera_column_x(368, 370) == -2);
    CHECK(camera_column_x(0, 383) == 1);
    CHECK(camera_column_x(368, 383) == -15);
    CHECK(camera_column_x(16, 383) == 17);
    CHECK(camera_column_x(304 + 16 * 6, 100) == camera_column_x(304 + 96 - 384, 100));
    /* failing examples of the old placement: island x 144 w 96 at camera 218, island x 304 w 80 at camera 370 */
    CHECK(camera_column_x(144, 218) == 310);
    CHECK(old_x(144, 96, 0, 218) != 310);
    CHECK(camera_column_x(304, 370) == 318);
    CHECK(old_x(304, 80, 0, 370) != 318);

    int old_bad = 0, new_bad = 0;
    for (int cam = 0; cam < 384; cam++) {
        int vis = 0;
        for (int c = 0; c < 24; c++) {
            int x = camera_column_x(16 * c, cam);
            CHECK(x == want_x(16 * c, cam));
            CHECK(x == H || (x > -16 && x < 320));
            if (x != H) vis++;
        }
        CHECK(vis == (cam % 16 == 0 ? 20 : 21));
        for (int ix = 0; ix < 384; ix += 8) {
            int prev = H;
            for (int c = 0; c < 6; c++) {
                int x = camera_column_x(ix + 16 * c, cam);
                if (x != want_x(ix + 16 * c, cam)) new_bad++;
                if (old_x(ix, 96, c, cam) != want_x(ix + 16 * c, cam)) old_bad++;
                CHECK(x == H || (x >= -15 && x <= 319));
                if (x != H && prev != H) CHECK(x - prev == 16);
                prev = x;
            }
        }
    }
    printf("old placement: %d column mismatches (96 px islands, all cameras, 48 x positions); new: %d\n", old_bad, new_bad);

    /* Hazard strip: 24 columns, hidden ones parked at x 320. Old placement: head -cam, column c at (-cam + 16c) & 0x1FF. */
    CHECK(camera_parked_column_x(0, 100) == 284 && camera_parked_column_x(32, 100) == 316);
    CHECK(((-100 + 0) & 0x1FF) != 284);                  /* old column 0 at camera 100: 412, the right 36 px stay empty */
    CHECK(camera_parked_column_x(0, 64) == 320 && camera_parked_column_x(368, 64) == 304);
    CHECK(camera_parked_column_x(0, 370) == 14);
    int old_uncovered = 0, new_uncovered = 0, new_double = 0, old_cam_bad = 0;
    for (int cam = 0; cam < 384; cam++) {
        int cov_new[320] = {0}, cov_old[320] = {0}, old_bad_cam = 0;
        for (int c = 0; c < 24; c++) {
            int nx = camera_parked_column_x(16 * c, cam);
            int ox = ((-cam + 16 * c) & 0x1FF);
            if (ox >= 496) ox -= 512;                   /* 9 bit x is signed on the hardware: 496..511 = -16..-1 */
            for (int px = 0; px < 16; px++) {
                if (nx + px >= 0 && nx + px < 320) cov_new[nx + px]++;
                if (ox + px >= 0 && ox + px < 320) cov_old[ox + px]++;
            }
            CHECK(nx == H ? 0 : (nx == 320 || (nx > -16 && nx < 320)));
        }
        for (int px = 0; px < 320; px++) {
            if (cov_new[px] == 0) new_uncovered++;
            if (cov_new[px] > 1) new_double++;
            if (cov_old[px] != 1) { old_uncovered++; old_bad_cam = 1; }
        }
        old_cam_bad += old_bad_cam;
    }
    CHECK(new_uncovered == 0 && new_double == 0);
    printf("hazard strip: old placement leaves %d pixel columns not covered exactly once over 384 cameras (%d cameras bad); new: %d uncovered, %d doubled\n",
           old_uncovered, old_cam_bad, new_uncovered, new_double);
    /* B1: the per sprite adds (camera_strip_x, camera_strip_parked_x) equal the per column camera_column_x /
     * camera_parked_column_x for every camera in the ring: every stage platform at every column, and the 24 column hazard strip. */
    int strip_bad = 0, strip_n = 0;
    for (int cam = 0; cam < 384; cam++) {
        for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) {
            int cols = island_columns(stage_platforms[i].w), sx0 = camera_screen_x(stage_platforms[i].x, cam, 16);
            for (int c = 0; c < cols; c++, sx0 += 16) {
                strip_n++;
                if (camera_strip_x(sx0) != camera_column_x(stage_platforms[i].x + 16 * c, cam)) strip_bad++;
            }
        }
        int hx0 = camera_screen_x(0, cam, 16);
        for (int c = 0; c < 24; c++, hx0 += 16) {
            strip_n++;
            if (camera_strip_parked_x(hx0) != camera_parked_column_x(16 * c, cam)) strip_bad++;
        }
        for (int wx = 0; wx < 384; wx += 8) { /* any strip start inside the ring, up to 24 columns */
            int x0 = camera_screen_x(wx, cam, 16);
            for (int c = 0; c < 24; c++, x0 += 16) {
                strip_n++;
                if (camera_strip_x(x0) != camera_column_x(wx + 16 * c, cam)) strip_bad++;
            }
        }
    }
    CHECK(strip_bad == 0);
    printf("strip placement: %d columns compared with camera_column_x, %d mismatches\n", strip_n, strip_bad);
    printf("camera_column: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
