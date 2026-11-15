/* arc_view.c - see arc_view.h. */
#include "arc_view.h"

/* Vent warning, variant B (owner pick 2026-11-15; values copied from thoughts/shared/drafts/2026-11-15-vent-warn/draw_vent_warn.py).
   The body shakes (drawing only, the kill box stays), boil bubbles sit on its top and the palette line heats up (arc_view_heat). */
static const int8_t SHAKE[(ARC_VENT_LAUNCH - ARC_VENT_TELEGRAPH) / 2][2] = { /* dx, dy per 2 ticks of the 72 tick warning (tests/host/test_arc_view.c): calm, restless, violent */
    {0,0},{0,0},{1,0},{0,0},{0,0},{-1,0}, {0,0},{0,0},{1,0},{0,0},{0,0},{-1,0},
    {1,0},{0,0},{-1,0},{0,-1},{1,0},{-1,0}, {1,0},{0,0},{-1,0},{0,-1},{1,0},{-1,0},
    {2,0},{-1,-1},{1,0},{-2,0},{1,-1},{-1,0},{2,-1},{-2,0},{1,0},{-1,-1},{2,0},{-2,-1} };
static const uint8_t BOIL_START[] = { 0, 6, 12, 18, 23, 28, 33, 38, 42, 46, 50, 54, 57, 60, 63, 66, 69 }; /* first tick of each hold: 6,6,6,5,5,5,5,4,4,4,4,3.. ticks */
#define BOIL_FRAMES 10
static const uint8_t HEAT_AT[][2] = { {0,1},{14,2},{26,3},{36,4},{45,5},{53,6},{60,7},{66,6},{68,7},{70,6} }; /* warning tick, step: rises, then flickers */
static const uint8_t COOL_AT[][2] = { {0,7},{40,5},{50,3},{60,1},{70,0} };                                  /* ticks after the launch, step */

static int step_at(const uint8_t (*tab)[2], int n, unsigned t) {
    int v = tab[0][1], i;
    for (i = 1; i < n && t >= tab[i][0]; i++) v = tab[i][1];
    return v;
}

int arc_view_heat(const ArcElements *a) {
    int i;
    for (i = 0; i < a->n; i++)
        if (a->el[i].kind == ARC_EL_VENT) {
            unsigned t = a->el[i].timer;
            if (t >= ARC_VENT_LAUNCH) return step_at(COOL_AT, (int)(sizeof COOL_AT / sizeof COOL_AT[0]), t - ARC_VENT_LAUNCH);
            if (t >= ARC_VENT_TELEGRAPH) return step_at(HEAT_AT, (int)(sizeof HEAT_AT / sizeof HEAT_AT[0]), t - ARC_VENT_TELEGRAPH);
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
            if (warn) s->frame = (uint8_t)(1 + (t - ARC_VENT_TELEGRAPH) / 24);
            else if (t >= ARC_VENT_LAUNCH && t < ARC_VENT_LAUNCH + ARC_VENT_BURST_TICKS) s->frame = 4;
            s->x = (int16_t)(e->x - ARC_VIEW_W[ARCV_BODY] / 2); s->y = (int16_t)(e->y - ARC_VIEW_H[ARCV_BODY]);
            if (warn) { s->x = (int16_t)(s->x + SHAKE[(t - ARC_VENT_TELEGRAPH) / 2][0]); s->y = (int16_t)(s->y + SHAKE[(t - ARC_VENT_TELEGRAPH) / 2][1]); }
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
    /* One spark per vent during the burst, rising 2.6 px per tick (13 per 5); before it, during the warning, one boil on the body top
       (1 px into the body, shaking with it). Built after the bodies: drawn behind them. */
    for (i = 0; i < a->n; i++) {
        const ArcElement *e = &a->el[i];
        if (e->kind == ARC_EL_VENT && e->timer >= ARC_VENT_TELEGRAPH && e->timer < ARC_VENT_LAUNCH) {
            unsigned w = e->timer - ARC_VENT_TELEGRAPH, h = 0;
            ArcSprite *s = &out[n++];
            while (h + 1 < sizeof BOIL_START && w >= BOIL_START[h + 1]) h++;
            s->piece = ARCV_BOIL; s->frame = (uint8_t)(h % BOIL_FRAMES);
            s->x = (int16_t)(e->x - ARC_VIEW_W[ARCV_BOIL] / 2 + SHAKE[w / 2][0]);
            s->y = (int16_t)(e->y - ARC_VIEW_H[ARCV_BODY] - (ARC_VIEW_H[ARCV_BOIL] - 1) + SHAKE[w / 2][1]);
        }
        if (e->kind == ARC_EL_VENT && e->timer >= ARC_VENT_LAUNCH && e->timer < ARC_VENT_LAUNCH + ARC_VENT_BURST_TICKS) {
            unsigned dt = e->timer - ARC_VENT_LAUNCH;
            ArcSprite *s = &out[n++];
            s->piece = ARCV_SPARK; s->frame = (uint8_t)((dt / ARC_VIEW_SPARK_TICKS) & 7);
            s->x = (int16_t)(e->x - ARC_VIEW_W[ARCV_SPARK] / 2);
            s->y = (int16_t)(e->y - ARC_VIEW_H[ARCV_BODY] - (int)(dt * 13 / 5));
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
