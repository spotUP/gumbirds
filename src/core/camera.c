#include "camera.h"

#define SPAN_MAX_PX (SCREEN_W - 16) /* both humans fit on screen with a 16 px sprite */

void camera_init(Camera *c) {
    c->cam = ((int32_t)(ARENA_CAM_MAX / 2) * 65536);
    c->moving = 0;
}

int32_t camera_target(const int32_t *x, int n) {
    int32_t lo, hi, t;
    int i;
    if (n <= 0) return ((int32_t)(ARENA_CAM_MAX / 2) * 65536);
    lo = hi = x[0];
    for (i = 1; i < n; i++) {
        if (x[i] < lo) lo = x[i];
        if (x[i] > hi) hi = x[i];
    }
    if (hi - lo > (int32_t)SPAN_MAX_PX * 65536) return -1; /* straddling the seam: hold */
    t = lo + ((hi - lo) >> 1) - (int32_t)(SCREEN_W / 2) * 65536;
    if (t < 0) t = 0;
    if (t > (int32_t)ARENA_CAM_MAX * 65536) t = (int32_t)ARENA_CAM_MAX * 65536;
    return t;
}

void camera_step(Camera *c, const int32_t *x, int n) {
    int32_t t = camera_target(x, n), d, step;
    if (t < 0) return;
    d = t - c->cam;
    if (!c->moving) {
        if ((d < 0 ? -d : d) < (int32_t)CAM_DEAD_ZONE_PX * 65536) return;
        c->moving = 1;
    }
    if ((d < 0 ? -d : d) < 65536) { c->cam = t; c->moving = 0; return; } /* snap: ARENA_CAM_MAX must be reachable */
    step = d >> CAM_EASE_SHIFT;
    if (step > (int32_t)CAM_MAX_STEP_PX * 65536) step = (int32_t)CAM_MAX_STEP_PX * 65536;
    if (step < -(int32_t)CAM_MAX_STEP_PX * 65536) step = -(int32_t)CAM_MAX_STEP_PX * 65536;
    c->cam += step;
}

int camera_px(const Camera *c) { return (int)(c->cam >> 16); }

int camera_screen_x(int world_px, int cam_px, int w) {
    int sx;
    while (world_px < 0) world_px += ARENA_W;
    while (world_px >= ARENA_W) world_px -= ARENA_W;
    sx = world_px - cam_px;
    if (sx < -w) sx += ARENA_W;
    else if (sx >= ARENA_W - w) sx -= ARENA_W;
    return sx;
}

int camera_visible(int sx, int w) { return sx > -w && sx < SCREEN_W; }

int camera_hazard_x(int cam_px) { return -cam_px; }

int camera_edge_marker(int sx, int w) {
    if (sx <= -w) return -1;
    if (sx >= SCREEN_W) return 1;
    return 0;
}
