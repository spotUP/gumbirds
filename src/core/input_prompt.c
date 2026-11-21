#include "input_prompt.h"
#include "game.h"       /* IN_A .. IN_C, Gum Games phase enums via gumgames.h */
#include "gg_fling.h"
#include "gg_popdrop.h"
#include "gg_toss.h"

#define MASH_TICKS 6u    /* frames each cap stays down while mashing */
#define PRESS_CYCLE 48u  /* press once: lit, then pressed for the last PRESS_DOWN frames */
#define PRESS_DOWN 8u
#define STICK_TICKS 16u

InputPrompt input_prompt_for(uint8_t event, uint8_t phase)
{
    InputPrompt p = { 0, IP_STYLE_NONE, 0 };
    switch (event) {
    case IP_BLOW:   if (phase == GG_BLOW_PLAY) { p.buttons = IN_A | IN_B; p.style = IP_STYLE_MASH; } break;
    case IP_RACE:   if (phase == GG_RACE_PLAY) { p.buttons = IN_A | IN_B; p.style = IP_STYLE_MASH; } break;
    case IP_DASH:   if (phase == IP_PHASE_PLAY) { p.buttons = IN_A | IN_B; p.style = IP_STYLE_MASH; } break;
    case IP_GATHER: if (phase == IP_PHASE_PLAY) { p.buttons = IN_A; p.style = IP_STYLE_MASH; p.stick = 1; } break;
    case IP_POP:    if (phase == PD_FALL) { p.buttons = IN_B | IN_C; p.style = IP_STYLE_PRESS; p.stick = 1; } break;   /* B and C pick the pose; the A brake hop is not prompted */
    case IP_POOP:   if (phase == 0) { p.buttons = IN_A | IN_B; p.style = IP_STYLE_PRESS; p.stick = 1; } break;   /* A flaps, B drops; stick trims the speed */
    case IP_TOSS:   if (phase == GT_HOLD) { p.buttons = IN_A | IN_B | IN_C; p.style = IP_STYLE_PRESS; } break;
    case IP_FLING:
        if (phase == GF_WINDUP || phase == GF_FLIGHT) { p.buttons = IN_A | IN_B; p.style = IP_STYLE_MASH; }   /* mash until the clock ends; mash to flap in flight */
        else if (phase == GF_AIM) { p.buttons = IN_A; p.style = IP_STYLE_PRESS; }                             /* A locks the swinging angle */
        break;
    }
    return p;
}

uint8_t input_prompt_items(const InputPrompt *p, uint8_t *kind)
{
    uint8_t n = 0;
    if (p->style == IP_STYLE_NONE) return 0;
    if (p->stick) kind[n++] = IP_ITEM_STICK;
    if (p->buttons & IN_A) kind[n++] = IP_ITEM_CAP_A;
    if (p->buttons & IN_B) kind[n++] = IP_ITEM_CAP_B;
    if (p->buttons & IN_C) kind[n++] = IP_ITEM_CAP_C;
    return n;
}

uint8_t input_prompt_state(const InputPrompt *p, uint8_t kind, uint16_t tick)
{
    if (kind == IP_ITEM_STICK) {
        static const uint8_t sweep[4] = { IP_STICK_NEUTRAL, IP_STICK_LEFT, IP_STICK_NEUTRAL, IP_STICK_RIGHT };
        return sweep[(tick / STICK_TICKS) & 3];
    }
    if (p->style == IP_STYLE_PRESS) return (tick % PRESS_CYCLE) >= PRESS_CYCLE - PRESS_DOWN ? IP_CAP_DOWN : IP_CAP_GLOW;
    {
        uint8_t caps = 0, rank = 0, bit;
        for (bit = 0; bit < 3; bit++) {
            if (!(p->buttons & (1u << bit))) continue;
            if (bit < kind) rank++;
            caps++;
        }
        return (caps == 1 ? (tick / MASH_TICKS) & 1 : (tick / MASH_TICKS) % caps == rank) ? IP_CAP_DOWN : IP_CAP_UP;
    }
}
