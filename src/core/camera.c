#include "camera.h"

/* Fold cam back into [0, ARENA_W16) and move the lap counter by the same whole laps. Loops, not modulo: cam moves
 * at most CAM_MAX_STEP_PX per frame, so at most one pass runs. */
static void normalise(Camera *c) {
    while (c->cam < 0) {
        c->cam += ARENA_W16;
        c->lap -= ARENA_W;
        if (c->lap < 0) c->lap += CAM_LAP_PERIOD_PX;
    }
    while (c->cam >= ARENA_W16) {
        c->cam -= ARENA_W16;
        c->lap += ARENA_W;
        if (c->lap >= CAM_LAP_PERIOD_PX) c->lap -= CAM_LAP_PERIOD_PX;
    }
}

void camera_init(Camera *c) {
    c->cam = (int32_t)(ARENA_W / 2 - SCREEN_W / 2) * 65536; /* world centre on screen centre: 32 */
    c->lap = 0;
    c->moving = 0;
}

int32_t camera_target(int32_t cam16, const int32_t *x, int n) {
    int32_t ref = cam16 + (int32_t)(SCREEN_W / 2) * 65536, lo, hi, p, mid;
    int i;
    if (n <= 0) return cam16;
    /* Anchor on the first human, then take every other human's copy nearest to the anchor: that is the shortest arc
     * between them (at most half a ring), so two humans either side of the seam are 80 px apart, not 304. */
    lo = hi = x[0];
    for (i = 1; i < n; i++) {
        p = arena_near_x(x[0], x[i]);
        if (p < lo) lo = p;
        if (p > hi) hi = p;
    }
    /* Midpoint of the arc, then the copy of that midpoint nearest the screen centre: the camera stays on the side it
     * is on and never snaps. With exactly opposite humans (arc 192) the two midpoints are 192 apart and the choice
     * flips with the camera; the target may jump but the camera still moves at most CAM_MAX_STEP_PX per frame. */
    mid = arena_near_x(ref, lo + ((hi - lo) >> 1));
    return mid - (int32_t)(SCREEN_W / 2) * 65536;
}

int camera_arrived(const Camera *c, const int32_t *x, int n) {
    int32_t d = camera_target(c->cam, x, n) - c->cam;
    return (d < 0 ? -d : d) < (int32_t)CAM_DEAD_ZONE_PX * 65536;
}

void camera_step(Camera *c, const int32_t *x, int n) {
    int32_t t, d, step;
    if (n <= 0) return;
    t = camera_target(c->cam, x, n);
    d = t - c->cam;
    if (!c->moving) {
        if ((d < 0 ? -d : d) < (int32_t)CAM_DEAD_ZONE_PX * 65536) return;
        c->moving = 1;
    }
    if ((d < 0 ? -d : d) < 65536) { c->cam = t; c->moving = 0; normalise(c); return; } /* snap the last pixel */
    step = d >> CAM_EASE_SHIFT;
    if (step > (int32_t)CAM_MAX_STEP_PX * 65536) step = (int32_t)CAM_MAX_STEP_PX * 65536;
    if (step < -(int32_t)CAM_MAX_STEP_PX * 65536) step = -(int32_t)CAM_MAX_STEP_PX * 65536;
    c->cam += step;
    normalise(c);
}

void camera_scroll(Camera *c, uint32_t step16) {
    c->cam += (int32_t)step16;
    c->moving = 1;
    normalise(c);
}

int camera_px(const Camera *c) { return (int)(c->cam >> 16); }

int32_t camera_unwrapped_px(const Camera *c) { return c->lap + (int32_t)(c->cam >> 16); }

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

int camera_column_x(int world_px, int cam_px) {
    int sx = camera_screen_x(world_px, cam_px, 16);
    return camera_visible(sx, 16) ? sx : CAMERA_COL_HIDDEN;
}

int camera_parked_column_x(int world_px, int cam_px) {
    int sx = camera_column_x(world_px, cam_px);
    return sx == CAMERA_COL_HIDDEN ? SCREEN_W : sx;
}

int camera_edge_marker(int sx, int w) {
    if (sx <= -w) return -1;
    if (sx >= SCREEN_W) return 1;
    return 0;
}
