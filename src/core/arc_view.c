/* arc_view.c - see arc_view.h. */
#include "arc_view.h"

int arc_view_build(const ArcElements *a, unsigned tick, ArcSprite *out) {
    int n = 0, i;
    for (i = 0; i < a->n; i++) {
        const ArcElement *e = &a->el[i];
        ArcSprite *s = &out[n];
        switch (e->kind) {
        case ARC_EL_VENT: {
            unsigned t = e->timer;
            s->piece = ARCV_BODY; s->frame = 0;
            if (t >= ARC_VENT_LAUNCH - 72 && t < ARC_VENT_LAUNCH) s->frame = (uint8_t)(1 + (t - (ARC_VENT_LAUNCH - 72)) / 24);
            else if (t >= ARC_VENT_LAUNCH && t < ARC_VENT_LAUNCH + ARC_VENT_BURST_TICKS) s->frame = 4;
            s->x = (int16_t)(e->x - ARC_VIEW_W[ARCV_BODY] / 2); s->y = (int16_t)(e->y - ARC_VIEW_H[ARCV_BODY]);
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
    /* One spark per vent during the burst, rising 2.6 px per tick (13 per 5). */
    for (i = 0; i < a->n; i++) {
        const ArcElement *e = &a->el[i];
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
    for (i = 0; i < ARC_BONUS_BUBBLES; i++) {
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
