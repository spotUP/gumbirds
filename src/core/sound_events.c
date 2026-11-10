#include "sound_events.h"

void se_init(SoundEvents *e)
{
    e->prev_state = FLOW_ATTRACT_TITLE; e->primed = 0; e->prev_flaps = 0;
}

uint8_t se_step(SoundEvents *e, const FlowView *v)
{
    uint8_t ev = 0;
    uint8_t playing = v->state == FLOW_PLAYING && v->game;
    if (playing && e->prev_state != FLOW_PLAYING) {
        ev |= SE_START;
    } else if (playing && e->primed) {
        if (v->game->flaps > e->prev_flaps) ev |= SE_FLAP;
    }
    if (!playing && e->prev_state == FLOW_PLAYING && v->state == FLOW_GAME_OVER) ev |= SE_GAME_OVER;
    e->prev_state = (uint8_t)v->state;
    e->primed = playing;
    e->prev_flaps = playing ? v->game->flaps : 0;
    return ev;
}
