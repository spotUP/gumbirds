/* attract_overlay.h - which how-to-play state the attract demo overlay shows. Portable C99, no drawing.
 * The state follows the scripted demo input (flow.c demo_input): FLAP while the demo presses A, else STEER with the lever on the sweep
 * direction. A state is held for at least ATTRACT_HOLD_FRAMES frames so the action word and the icons do not flicker. */
#ifndef ATTRACT_OVERLAY_H
#define ATTRACT_OVERLAY_H

#include <stdint.h>
#include "tuning.h"
#include "game.h"
#include "nameentry.h"

enum { AO_FLAP, AO_STEER_LEFT, AO_STEER_RIGHT, AO_NONE = 0xFF };

typedef struct {
    uint8_t key;  /* AO_FLAP, AO_STEER_LEFT, AO_STEER_RIGHT, or AO_NONE before the first demo frame */
    uint8_t age;  /* frames since key was set (saturates) */
} AttractOverlay;

void attract_overlay_reset(AttractOverlay *o);
void attract_overlay_step(AttractOverlay *o, uint8_t input); /* once per demo frame */

#endif
