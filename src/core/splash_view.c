#include "splash_view.h"

uint8_t splash_ticks(uint8_t kind) { return kind == SPLASH_KIND_GUM ? SPLASH_GUM_TICKS : kind == HZ_LAVA ? SPLASH_LAVA_TICKS : SPLASH_TICKS; }

void splash_step(Splash *s, int start, uint8_t kind, int32_t x)
{
    if (start && (kind == HZ_WATER || kind == HZ_LAVA || kind == SPLASH_KIND_GUM)) { s->active = 1; s->kind = kind; s->x = x; s->t = 0; return; }
    if (!s->active) return;
    if (++s->t >= (uint16_t)(SPLASH_FRAMES * splash_ticks(s->kind))) s->active = 0;
}

uint8_t splash_frame(const Splash *s) { return (uint8_t)(s->t / splash_ticks(s->kind)); }

int splash_top(uint8_t kind, int floor_y) { return (kind == SPLASH_KIND_GUM ? floor_y : hazard_kill_px(kind) - HAZARD_DIP) - SPLASH_SURFACE_ROW; }

int splash_enabled(int running, int trip) { (void)trip; return running; }
