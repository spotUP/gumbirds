/* arc_view.c - see arc_view.h. */
#include "arc_view.h"
#include "fastdiv.h"

/* Vent warning, variant B (owner pick 2026-11-15; values copied from thoughts/shared/drafts/2026-11-15-vent-warn/draw_vent_warn.py).
   The body shakes (drawing only, the kill box stays), boil bubbles sit on its top (drawn into the body's warning frames, piece ARCV_WARN) and the palette line heats up (arc_view_heat). */
static const int8_t SHAKE[(ARC_VENT_LAUNCH - ARC_VENT_TELEGRAPH) / 2][2] = { /* dx, dy per 2 ticks of the 72 tick warning (tests/host/test_arc_view.c): calm, restless, violent */
    {0,0},{0,0},{1,0},{0,0},{0,0},{-1,0}, {0,0},{0,0},{1,0},{0,0},{0,0},{-1,0},
    {1,0},{0,0},{-1,0},{0,-1},{1,0},{-1,0}, {1,0},{0,0},{-1,0},{0,-1},{1,0},{-1,0},
    {2,0},{-1,-1},{1,0},{-2,0},{1,-1},{-1,0},{2,-1},{-2,0},{1,0},{-1,-1},{2,0},{-2,-1} };
/* Per tick tables (no loop or division per frame on the 68000); tests/host/test_arc_view.c checks them against the step lists they came from. */
static const uint8_t WARN_TAB[ARC_VENT_LAUNCH - ARC_VENT_TELEGRAPH] = { 0,0,0,0,0,0,1,1,1,1,1,1,2,2,2,2,2,2,3,3,3,3,3,4,5,5,5,5,6,6,6,6,6,7,7,7,7,7,8,8,8,8,9,9,9,9,10,10,11,11,12,12,12,12,13,13,13,14,14,14,15,15,15,16,16,16,17,17,17,18,18,18 }; /* warning frame per tick: body frame 1..3 (24 ticks each) with boil grid hold % 10, holds of 6,6,6,5,5,5,5,4,4,4,4,3.. ticks; the 19 pairs in the order they show (tools/import_arcade_sheet.py WARN) */
static const uint8_t HEAT_TAB[ARC_VENT_LAUNCH - ARC_VENT_TELEGRAPH] = { 1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,2,2,2,2,2,2,2,2,2,2,2,3,3,3,3,3,3,3,3,3,3,4,4,4,4,4,4,4,4,4,5,5,5,5,5,5,5,5,6,6,6,6,6,6,6,7,7,7,7,7,7,6,6,7,7,6,6 }; /* heat step per warning tick: rises, then flickers */
static const uint8_t COOL_TAB[71] = { 7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,5,5,5,5,5,5,5,5,5,5,3,3,3,3,3,3,3,3,3,3,1,1,1,1,1,1,1,1,1,1,0 }; /* heat step per tick after the launch (0 from tick 70) */

int arc_view_heat(const ArcElements *a) {
    int i;
    for (i = 0; i < a->n; i++)
        if (a->el[i].kind == ARC_EL_VENT) {
            unsigned t = a->el[i].timer;
            if (t >= ARC_VENT_LAUNCH) return t - ARC_VENT_LAUNCH < sizeof COOL_TAB ? COOL_TAB[t - ARC_VENT_LAUNCH] : 0;
            if (t >= ARC_VENT_TELEGRAPH) return HEAT_TAB[t - ARC_VENT_TELEGRAPH];
            return 0;
        }
    return 0;
}

int arc_view_build(const ArcElements *a, unsigned tick, ArcSprite *out) {
    int n = 0, i;
    for (i = 0; i < a->n; i++) {
        const ArcElement *e = &a->el[i];
        ArcSprite *s = &out[n];
        switch (e->kind) {
        case ARC_EL_VENT: {
            unsigned t = e->timer;
            s->piece = ARCV_BODY; s->frame = 0;
            int warn = t >= ARC_VENT_TELEGRAPH && t < ARC_VENT_LAUNCH;
            if (t >= ARC_VENT_LAUNCH && t < ARC_VENT_LAUNCH + ARC_VENT_BURST_TICKS) s->frame = 4;
            s->x = (int16_t)(e->x - ARC_VIEW_W[ARCV_BODY] / 2); s->y = (int16_t)(e->y - ARC_VIEW_H[ARCV_BODY]);
            if (warn) { /* the warning frames are the body with the boil above it: same bottom edge, taller */
                unsigned w = t - ARC_VENT_TELEGRAPH;
                s->piece = ARCV_WARN; s->frame = WARN_TAB[w];
                s->x = (int16_t)(s->x + SHAKE[w / 2][0]); s->y = (int16_t)(e->y - ARC_VIEW_H[ARCV_WARN] + SHAKE[w / 2][1]);
            }
            n++;
            break;
        }
        case ARC_EL_FLIPPER:
            s->piece = ARCV_FLIPPER; s->frame = (uint8_t)((tick / ARC_VIEW_FLIP_TICKS) & 7);
            s->x = (int16_t)(e->x - ARC_VIEW_W[ARCV_FLIPPER] / 2); s->y = (int16_t)(e->y - ARC_VIEW_H[ARCV_FLIPPER] / 2);
            n++;
            break;
        case ARC_EL_GRABBER: {
            int f = arc_elements_grab_frame(e->timer);
            if (f < 0) break;
            s->piece = ARCV_GRABBER; s->frame = (uint8_t)f;
            s->x = (int16_t)(e->x - ARC_VIEW_W[ARCV_GRABBER] / 2); s->y = (int16_t)(e->y - ARC_VIEW_H[ARCV_GRABBER]);
            n++;
            break;
        }
        case ARC_EL_GRATE:
            s->piece = ARCV_HATCH; s->frame = 0;
            s->x = (int16_t)(e->x - ARC_VIEW_W[ARCV_HATCH] / 2); s->y = e->y;
            n++;
            break;
        default: break;
        }
    }
    /* One spark per vent during the burst, rising 2.6 px per tick (13 per 5). Built after the bodies: drawn behind them. */
    for (i = 0; i < a->n; i++) {
        const ArcElement *e = &a->el[i];
        if (e->kind == ARC_EL_VENT && e->timer >= ARC_VENT_LAUNCH && e->timer < ARC_VENT_LAUNCH + ARC_VENT_BURST_TICKS) {
            unsigned dt = e->timer - ARC_VENT_LAUNCH;
            ArcSprite *s = &out[n++];
            s->piece = ARCV_SPARK; s->frame = (uint8_t)((dt / ARC_VIEW_SPARK_TICKS) & 7);
            s->x = (int16_t)(e->x - ARC_VIEW_W[ARCV_SPARK] / 2);
            s->y = (int16_t)(e->y - ARC_VIEW_H[ARCV_BODY] - (int)fd_div16((dt & (ARC_VIEW_SPARK_RISE_TICKS - 1)) * 13, 5)); /* loops: the plume kills 40 ticks, one rise stays inside its 48 px box for 16 */
        }
    }
    return n;
}

int arc_view_bonus_build(const ArcBonus *b, ArcSprite *out) {
    int n = 0, i;
    for (i = 0; i < ARC_BONUS_LIVE_MAX; i++) {
        const ArcBubble *u = &b->b[i];
        ArcSprite *s = &out[n];
        if (!u->live) continue;
        s->piece = (uint8_t)i;
        s->frame = (uint8_t)(((b->frame + i) >> 2) & (ARC_VIEW_BUBBLE_FRAMES - 1)); /* phase by bubble: the tile loads spread over 4 frames */
        s->x = (int16_t)(u->x - ARC_VIEW_BUBBLE_LEFT_OFF);
        s->y = (int16_t)((u->y16 >> 16) - ARC_VIEW_BUBBLE_TOP_OFF);
        n++;
    }
    return n;
}

int arc_view_line(const ArcSprite *s, int n, int y) {
    int i, c = 0;
    for (i = 0; i < n; i++)
        if (y >= s[i].y && y < s[i].y + ARC_VIEW_H[s[i].piece]) c += ARC_VIEW_COLS[s[i].piece];
    return c;
}
