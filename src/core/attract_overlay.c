#include "attract_overlay.h"

void attract_overlay_reset(AttractOverlay *o)
{
    o->key = AO_NONE;
    o->age = 0;
}

void attract_overlay_step(AttractOverlay *o, uint8_t input)
{
    uint8_t want = (uint8_t)((input & IN_A) ? AO_FLAP : (input & IN_LEFT) ? AO_STEER_LEFT : AO_STEER_RIGHT);
    if (o->key == AO_NONE) {
        o->key = want;
        o->age = 0;
        return;
    }
    if (o->age < 255u) o->age++;
    if (want != o->key && o->age >= ATTRACT_HOLD_FRAMES) {
        o->key = want;
        o->age = 0;
    }
}
