/* arc_elements.c - see arc_elements.h. */
#include "arc_elements.h"

/* trip_hit's rule (|centre distance| <= sum of half extents); flier.c's body_overlap is static and flier vs flier only. */
static int box_hit(int ax, int ay, int ahw, int ahh, int bx, int by, int bhw, int bhh) {
    int dx = ax - bx, dy = ay - by;
    if (dx < 0) dx = -dx;
    if (dy < 0) dy = -dy;
    return dx <= ahw + bhw && dy <= ahh + bhh;
}

static const uint8_t grab_ticks[ARC_GRAB_FRAMES] = { 7, 6, 4, 4, 8, 3, 4, 13, 5, 5, 5, 7 }; /* art frame_ticks ms at 60 Hz, rounded */

int arc_elements_grab_frame(uint16_t t) {   /* -1 while hidden */
    int f;
    if (!t) return -1;
    t = (uint16_t)(t - 1);
    for (f = 0; f < ARC_GRAB_FRAMES; f++) { if (t < grab_ticks[f]) return f; t = (uint16_t)(t - grab_ticks[f]); }
    return -1;
}

static void add(ArcElements *a, ArcElKind k, int x, int y, int x1) {
    ArcElement *e = &a->el[a->n++];
    e->kind = (uint8_t)k; e->x = (int16_t)x; e->x0 = (int16_t)x; e->y = (int16_t)y; e->param = (int16_t)x1; e->timer = 0; e->cycle = 0;
}

/* Source of all positions: thoughts/spot/drafts/2026-11-12-arcade-layouts/gen3.py (vent y = its island top, drain y = water line 188, grate y = hatch top 186). Posts have no kind here. */
void arc_elements_init(ArcElements *a, int s) {
    a->n = 0; a->nlow = 0;
    switch (s) {
    case 0:  add(a, ARC_EL_VENT, 184, 108, 0); break;                                              /* R01 */
    case 1:  add(a, ARC_EL_VENT, 160, 116, 0); add(a, ARC_EL_VENT, 246, 80, 0); break;            /* R02 */
    case 2:  add(a, ARC_EL_VENT, 196, 92, 0); add(a, ARC_EL_VENT, 60, 52, 0); break;              /* N05 */
    case 3:  add(a, ARC_EL_VENT, 322, 72, 0); add(a, ARC_EL_VENT, 168, 52, 0); add(a, ARC_EL_GRABBER, 112, 188, 224); add(a, ARC_EL_GRATE, 232, 186, 0); break; /* N03 */
    case 4:  add(a, ARC_EL_VENT, 204, 88, 0); add(a, ARC_EL_VENT, 306, 72, 0); add(a, ARC_EL_GRATE, 248, 186, 0); break; /* N06 */
    case 5:  add(a, ARC_EL_VENT, 110, 100, 0); add(a, ARC_EL_VENT, 296, 60, 0); break;            /* N04 */
    case 6:  add(a, ARC_EL_VENT, 180, 104, 0); add(a, ARC_EL_VENT, 252, 80, 0); add(a, ARC_EL_FLIPPER, 148, 72, 0); add(a, ARC_EL_GRABBER, 104, 188, 256); break; /* N08 */
    case 7:  add(a, ARC_EL_VENT, 174, 124, 0); add(a, ARC_EL_VENT, 300, 80, 0); add(a, ARC_EL_FLIPPER, 176, 76, 0); break; /* N02 */
    case 8:  add(a, ARC_EL_VENT, 224, 76, 0); add(a, ARC_EL_VENT, 314, 72, 0); add(a, ARC_EL_GRATE, 248, 186, 0); add(a, ARC_EL_FLIPPER, 252, 122, 0); add(a, ARC_EL_FLIPPER, 96, 92, 0); break; /* N09 */
    case 9:  add(a, ARC_EL_VENT, 160, 108, 0); add(a, ARC_EL_VENT, 320, 72, 0); add(a, ARC_EL_FLIPPER, 36, 84, 0); add(a, ARC_EL_FLIPPER, 176, 50, 0); add(a, ARC_EL_FLIPPER, 252, 110, 0); break; /* R10 */
    case 10: add(a, ARC_EL_VENT, 144, 136, 0); add(a, ARC_EL_VENT, 222, 112, 0); add(a, ARC_EL_FLIPPER, 280, 56, 0); break;     /* R07 */
    case 11: add(a, ARC_EL_VENT, 40, 96, 0); add(a, ARC_EL_VENT, 320, 80, 0); break;            /* R12b */
    default: break;
    }
}

void arc_elements_note_low(ArcElements *a, int cx, int cy) {
    if (a->nlow < ARC_LOW_MAX) { a->low_x[a->nlow] = (int16_t)cx; a->low_y[a->nlow] = (int16_t)cy; a->nlow++; }
}

/* Index of a noted flier that is low over this hand's water line and within dxmax px of its x, else -1. */
static int grab_target(const ArcElements *a, const ArcElement *e, int dxmax) {
    int k;
    for (k = 0; k < a->nlow; k++) {
        int dx = a->low_x[k] - e->x;
        if (dx < 0) dx = -dx;
        if (dx <= dxmax && a->low_y[k] >= e->y - ARC_GRAB_LOW_DY) return k;
    }
    return -1;
}

static void grab_step(const ArcElements *a, ArcElement *e) {
    int k;
    if (!e->timer) {   /* hidden: patrol, rise on a low flier at this x */
        int x = e->x + ARC_GRAB_PATROL;
        e->x = (int16_t)(x > e->param ? e->x0 : x);
        if (grab_target(a, e, ARC_GRAB_TRIG_DX) >= 0) { e->timer = 1; e->cycle++; }
        return;
    }
    if (e->timer <= ARC_GRAB_RISE) {   /* rising: the target must still be low at the hand, else retreat at once; follow its x */
        k = grab_target(a, e, ARC_GRAB_TRACK_DX);
        if (k < 0) e->timer = ARC_GRAB_SINK_AT;
        else {
            int d = a->low_x[k] - e->x, x;
            if (d > ARC_GRAB_FOLLOW) d = ARC_GRAB_FOLLOW;
            if (d < -ARC_GRAB_FOLLOW) d = -ARC_GRAB_FOLLOW;
            x = e->x + d;
            e->x = (int16_t)(x < e->x0 ? e->x0 : x > e->param ? e->param : x);
        }
    }
    if (++e->timer > ARC_GRAB_LOOP) e->timer = 0;
}

void arc_elements_step(ArcElements *a) {
    int i;
    for (i = 0; i < a->n; i++) {
        ArcElement *e = &a->el[i];
        if (e->kind == ARC_EL_VENT) { if (++e->timer >= ARC_VENT_LOOP) e->timer = 0; }
        else if (e->kind == ARC_EL_GRABBER) grab_step(a, e);
    }
    a->nlow = 0;
}

int arc_elements_kill(const ArcElements *a, int cx, int cy, int hw, int hh) {
    int i;
    for (i = 0; i < a->n; i++) {
        const ArcElement *e = &a->el[i];
        if (e->kind == ARC_EL_VENT && e->timer >= ARC_VENT_LAUNCH && e->timer < ARC_VENT_LAUNCH + ARC_VENT_BURST_TICKS
            && box_hit(cx, cy, hw, hh, e->x, e->y - ARC_VENT_PLUME_H / 2, ARC_VENT_HALF_W, ARC_VENT_PLUME_H / 2)) return 1;
        if (e->kind == ARC_EL_GRABBER) {
            int f = arc_elements_grab_frame(e->timer);
            if (f >= ARC_GRAB_HIT_FIRST && f <= ARC_GRAB_HIT_LAST
                && box_hit(cx, cy, hw, hh, e->x, e->y - ARC_GRAB_HIT_H / 2, ARC_GRAB_HALF_W, ARC_GRAB_HIT_H / 2)) return 1;
        }
    }
    return 0;
}

int arc_elements_avoid_dir(const ArcElements *a, int cx, int cy, int hw, int hh, int32_t vx) {
    /* The side is judged where the flier will be in ARC_AVOID_AHEAD ticks (16.16 times a constant, no divide): steering is one thrust
       per flap, so judging the present spot let a rival between two vents fly from one plume past the midpoint into the other. */
    int px = cx + (int)((vx * ARC_AVOID_AHEAD) >> 16);
    int i, best = -1, bd = 0;
    for (i = 0; i < a->n; i++) {
        const ArcElement *e = &a->el[i];
        int dx = px - e->x;
        if (dx < 0) dx = -dx;
        if (e->kind == ARC_EL_VENT) {
            if (e->timer < ARC_VENT_TELEGRAPH || e->timer >= ARC_VENT_LAUNCH + ARC_VENT_BURST_TICKS) continue;
            if (!box_hit(cx, cy, hw + ARC_AVOID_LOOK, hh + ARC_AVOID_PAD, e->x, e->y - ARC_VENT_PLUME_H / 2, ARC_VENT_HALF_W, ARC_VENT_PLUME_H / 2)) continue;
        } else if (e->kind == ARC_EL_GRABBER) {   /* any hand state: the hand patrols hidden, so stay off the water near it */
            int gx = cx - e->x;
            if (gx < 0) gx = -gx;
            if (cy < e->y - ARC_GRAB_LOW_DY || gx > ARC_GRAB_HALF_W + hw + ARC_AVOID_PAD) continue;
        } else continue;
        if (best < 0 || dx < bd) { best = i; bd = dx; }   /* the nearest threat decides: two vents' look boxes meet between them */
    }
    if (best < 0) return 0;
    return px >= a->el[best].x ? 1 : -1;   /* stage_overhead_edge_dir rule: right of centre (or dead centre) goes right */
}

int arc_elements_bounce(const ArcElements *a, int cx, int cy, int hw, int hh, int32_t *vx, int32_t *vy) {
    int i;
    for (i = 0; i < a->n; i++) {
        const ArcElement *e = &a->el[i];
        if (e->kind == ARC_EL_FLIPPER && box_hit(cx, cy, hw, hh, e->x, e->y, ARC_FLIP_HALF, ARC_FLIP_HALF)) {
            *vx = cx < e->x ? -ARC_FLIP_SPEED : ARC_FLIP_SPEED;   /* dead centre goes right/down */
            *vy = cy < e->y ? -ARC_FLIP_SPEED : ARC_FLIP_SPEED;
            return 1;
        }
    }
    return 0;
}

int32_t arc_elements_lift(const ArcElements *a, int cx, int cy, int hw, int hh) {
    int32_t d = 0; int i;
    for (i = 0; i < a->n; i++) {
        const ArcElement *e = &a->el[i];
        if (e->kind == ARC_EL_GRATE && box_hit(cx, cy, hw, hh, e->x, e->y - ARC_GRATE_H / 2, ARC_GRATE_HALF_W, ARC_GRATE_H / 2)) d -= ARC_GRATE_LIFT;
    }
    return d;
}
