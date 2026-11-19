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

static void ease_step(Camera *c, const int32_t *x, int n) {
    int32_t t, d, step;
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

/* Camera clamped so the arc lo..hi (absolute x, lo <= hi) sits inside [CAM_EDGE_MARGIN_PX, SCREEN_W - margin]; an arc that
 * cannot fit leaves cam alone. The copy of the arc nearest the camera is used, so the camera never changes side. */
static int32_t fit_arc(int32_t cam, int32_t lo, int32_t hi) {
    int32_t mid, p, lo_cam, hi_cam;
    if (hi - lo > (int32_t)(SCREEN_W - 2 * CAM_EDGE_MARGIN_PX) * 65536) return cam;
    mid = lo + ((hi - lo) >> 1);
    p = arena_near_x(cam + (int32_t)(SCREEN_W / 2) * 65536, mid) - mid;
    lo_cam = hi + p - (int32_t)(SCREEN_W - CAM_EDGE_MARGIN_PX) * 65536;
    hi_cam = lo + p - (int32_t)CAM_EDGE_MARGIN_PX * 65536;
    return cam < lo_cam ? lo_cam : cam > hi_cam ? hi_cam : cam;
}

/* Co-op soft edges: with two humans keep both inside the screen margins, whatever the easing did. Both arcs between them
 * are tried (near 192 apart either may be on screen) and the smaller camera move wins, so the choice never jumps. */
static void clamp_edges(Camera *c, const int32_t *x) {
    int32_t lo = x[0], hi = arena_near_x(x[0], x[1]), a, b;
    if (hi < lo) { lo = hi; hi = x[0]; }
    a = fit_arc(c->cam, lo, hi); /* the shortest arc is at most half a ring, so it always fits */
    b = fit_arc(c->cam, hi, lo + ARENA_W16);
    if (ARENA_W16 - (hi - lo) <= (int32_t)(SCREEN_W - 2 * CAM_EDGE_MARGIN_PX) * 65536 && (b > c->cam ? b - c->cam : c->cam - b) < (a > c->cam ? a - c->cam : c->cam - a)) a = b;
    c->cam = a;
    normalise(c);
}

void camera_step(Camera *c, const int32_t *x, int n) {
    if (n <= 0) return;
    ease_step(c, x, n);
    if (n == 2) clamp_edges(c, x); /* shortcut: two humans only (HUMANS 2) */
}

void camera_scroll(Camera *c, uint32_t step16) {
    c->cam += (int32_t)step16;
    c->moving = 1;
    normalise(c);
}

int32_t arena_ring = ARENA_W;

int camera_px(const Camera *c) { return (int)(c->cam >> 16); }

int32_t camera_unwrapped_px(const Camera *c) { return c->lap + (int32_t)(c->cam >> 16); }

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
