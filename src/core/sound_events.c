#include "sound_events.h"

static void forget_fliers(SoundEvents *e)
{
    int i;
    for (i = 0; i < SE_WATCHED; i++) e->seen_state[i] = SE_UNSEEN;
}

void se_init(SoundEvents *e)
{
    e->prev_state = FLOW_ATTRACT_TITLE; e->primed = 0; e->prev_flaps = 0; e->prev_gum = SE_UNSEEN_GUM;
    e->n_die = e->n_fall = e->n_splosh = e->n_spike = e->n_pop = 0;
    forget_fliers(e);
}

/* A dead body that fell through the surface without ever being DROWNED (liquid_hit, flier.c): the same splosh as the DROWNED edge. */
static uint16_t liquid_edge(SoundEvents *e, const Flier *f, uint8_t hazard)
{
    if (!f->liquid_hit || (hazard != HZ_WATER && hazard != HZ_LAVA)) return 0;
    e->n_splosh++; e->splosh_x = f->x >> 16;
    return SE_SPLOSH;
}

/* One flier's edges against what it was last frame; a flier not seen last frame (new slot, new round) only primes. */
static uint16_t flier_edges(SoundEvents *e, int slot, const Flier *f, uint8_t live, uint8_t hazard, uint8_t pops)
{
    uint16_t ev = live ? liquid_edge(e, f, hazard) : 0;
    uint8_t was = e->seen_state[slot], was_b = e->seen_balloons[slot];
    if (live && was != SE_UNSEEN && was <= FLIER_PARACHUTE) {
        if (f->state == FLIER_DROWNED) {
            if (hazard == HZ_SPIKES) { e->n_spike++; ev |= SE_SPIKE; }
            else if (hazard == HZ_FIRE) ev |= SE_SIZZLE;
            else { e->n_splosh++; e->splosh_x = f->x >> 16; ev |= SE_SPLOSH; }
        } else {
            if (pops && f->balloons < was_b && f->state != FLIER_GONE) e->n_pop++;   /* every burst, the last one too */
            if (was_b > 0 && f->balloons == 0 && f->state != FLIER_GONE) { e->n_die++; ev |= SE_DIE; }
            if (f->state == FLIER_FALLING) { e->n_fall++; ev |= SE_FALL; }
        }
    }
    e->seen_state[slot] = live ? f->state : SE_UNSEEN;
    e->seen_balloons[slot] = f->balloons;
    return ev;
}

static uint16_t death_events(SoundEvents *e, const Game *g, uint8_t playing)
{
    uint16_t ev = 0;
    int i;
    e->n_die = e->n_fall = e->n_splosh = e->n_spike = e->n_pop = 0;
    if (!playing) { forget_fliers(e); e->prev_gum = SE_UNSEEN_GUM; return 0; }
    ev |= flier_edges(e, 0, &g->flier, playing, g->hazard_kind, g->mode != GAME_MODE_TRIP);   /* Trip: balloons follow the gum, the pop is the gum edge below */
    for (i = 0; i < CPU_MAX; i++) /* arena computer fliers only: arcade rivals (slots past CPU_MAX) make no events, so their slots stay unseen */
        ev |= flier_edges(e, 1 + i, &g->cpu[i], playing && g->mode == GAME_MODE_ARENA && i < g->cpu_count, g->hazard_kind, 1);
    if (g->mode == GAME_MODE_ARCADE) /* arcade rivals past CPU_MAX: the liquid splash only */
        for (i = CPU_MAX; i < STAGE_SPAWN_COUNT; i++)
            if (i < g->cpu_count) ev |= liquid_edge(e, &g->cpu[i], g->hazard_kind);
    for (i = 0; i < TRIP_RIVAL_MAX; i++)
        ev |= flier_edges(e, 1 + STAGE_SPAWN_COUNT + i, &g->trip_rivals.r[i].f, playing && g->mode == GAME_MODE_TRIP && g->trip_rivals.r[i].active, g->hazard_kind, 1);
    if (g->mode == GAME_MODE_TRIP) {
        if (e->prev_gum != SE_UNSEEN_GUM && e->prev_gum > 0 && g->trip.gum == 0) e->n_pop++;   /* the player's bubble bursts */
        e->prev_gum = g->trip.gum;
    } else e->prev_gum = SE_UNSEEN_GUM;
    return ev;
}

uint16_t se_step(SoundEvents *e, const FlowView *v)
{
    uint16_t ev = 0;
    uint8_t playing = v->state == FLOW_PLAYING && v->game;
    if (playing && e->prev_state != FLOW_PLAYING) {
        ev |= SE_START;
    } else if (playing && e->primed) {
        if (v->game->flaps > e->prev_flaps) ev |= SE_FLAP;
        if (v->game->trip_events & TRIP_EV_HIT) ev |= SE_HIT;
    }
    if (!playing && e->prev_state == FLOW_PLAYING && v->state == FLOW_GAME_OVER) ev |= SE_GAME_OVER;
    ev |= death_events(e, playing ? v->game : 0, playing);
    e->prev_state = (uint8_t)v->state;
    e->primed = playing;
    e->prev_flaps = playing ? v->game->flaps : 0;
    return ev;
}

uint8_t coin_drain(uint8_t *pending)
{
    if (!*pending) return 0;
    (*pending)--;
    return 1;
}
