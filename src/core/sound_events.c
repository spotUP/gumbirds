#include "sound_events.h"

void se_init(SoundEvents *e)
{
    e->prev_state = FLOW_ATTRACT_TITLE; e->primed = 0; e->prev_air = 0; e->prev_shots = 0; e->prev_hits = 0;
}

uint8_t se_step(SoundEvents *e, const FlowView *v)
{
    uint8_t ev = 0;
    uint8_t playing = v->state == FLOW_PLAYING && v->game;
    uint8_t air = playing && v->game->hero_h > 0;
    if (playing && e->prev_state != FLOW_PLAYING) {
        ev |= SE_START;
    } else if (playing && e->primed) {
        if (air && !e->prev_air) ev |= SE_JUMP;
        if (v->game->hits > e->prev_hits) ev |= SE_HIT;
        if (v->game->shots > e->prev_shots) ev |= SE_LASER;
    }
    if (!playing && e->prev_state == FLOW_PLAYING && v->state == FLOW_GAME_OVER) ev |= SE_GAME_OVER;
    e->prev_state = (uint8_t)v->state;
    e->primed = playing;
    e->prev_air = air;
    e->prev_shots = playing ? v->game->shots : 0;
    e->prev_hits = playing ? v->game->hits : 0;
    return ev;
}
