#include "sound_events.h"

static void forget_fliers(SoundEvents *e)
{
    int i;
    for (i = 0; i < SE_WATCHED; i++) { e->seen_state[i] = SE_UNSEEN; e->drop[i] = 0; }
}

void se_init(SoundEvents *e)
{
    e->prev_state = 0xff; e->prev_matches = 0; e->primed = 0; e->prev_flaps[0] = e->prev_flaps[1] = 0; e->prev_gum = SE_UNSEEN_GUM;
    e->n_die = e->n_fall = e->n_splosh = e->n_spike = e->n_pop = 0;
    e->cues = 0; e->ne_seen = 0;
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
    uint16_t ev;
    uint8_t was, was_b;
    if (!live) { e->seen_state[slot] = SE_UNSEEN; e->drop[slot] = 0; return 0; }   /* the cheap path: an empty slot costs no frame time */
    ev = liquid_edge(e, f, hazard);
    was = e->seen_state[slot]; was_b = e->seen_balloons[slot];
    if (was != SE_UNSEEN && was <= FLIER_PARACHUTE) {
        if (f->state == FLIER_DROWNED) {
            if (hazard == HZ_SPIKES) { e->n_spike++; ev |= SE_SPIKE; }
            else if (hazard == HZ_FIRE) ev |= SE_SIZZLE;
            else { e->n_splosh++; e->splosh_x = f->x >> 16; ev |= SE_SPLOSH; }
        } else {
            if (pops && f->balloons < was_b && f->state != FLIER_GONE) e->n_pop++;   /* every burst, the last one too */
            if (was_b > 0 && f->balloons == 0 && f->state != FLIER_GONE) { e->n_die++; ev |= SE_DIE; }
            if (f->state == FLIER_FALLING) { e->n_fall++; ev |= SE_FALL; }
            if (was == FLIER_ALIVE && f->state == FLIER_PARACHUTE) e->cues |= 1ul << SC_CHUTE;
        }
    }
    /* A flier that lost its last balloon on the ground stays ALIVE and walks: off an edge it drops without ever being FLIER_FALLING. */
    if (f->state == FLIER_ALIVE && !f->balloons && !f->on_ground) {
        if (!e->drop[slot] && f->vy >= SE_DROP_VY) { e->drop[slot] = 1; e->n_fall++; ev |= SE_FALL; }
    } else e->drop[slot] = 0;
    e->seen_state[slot] = f->state;
    e->seen_balloons[slot] = f->balloons;
    return ev;
}

static uint16_t death_events(SoundEvents *e, const Game *g, uint8_t playing)
{
    uint16_t ev = 0;
    int i;
    e->n_die = e->n_fall = e->n_splosh = e->n_spike = e->n_pop = 0;
    if (!playing) { forget_fliers(e); e->prev_gum = SE_UNSEEN_GUM; return 0; }
    for (i = 0; i < HUMANS; i++) /* the Trip: balloons follow the gum, the pop is the gum edge below; a human not in play stays unseen */
        ev |= flier_edges(e, i, &g->hero[i], playing && i < g->players, g->hazard_kind, g->mode != GAME_MODE_TRIP);
    for (i = 0; i < STAGE_SPAWN_COUNT; i++) /* arena and arcade computer fliers; other modes leave these slots unseen */
        ev |= flier_edges(e, HUMANS + i, &g->cpu[i], playing && (g->mode == GAME_MODE_ARENA || g->mode == GAME_MODE_ARCADE) && i < g->cpu_count, g->hazard_kind, 1);
    if (g->mode == GAME_MODE_TRIP) {   /* outside the Trip these slots stay unseen (forget_fliers), so the loop is skipped: frame time */
        for (i = 0; i < TRIP_RIVAL_MAX; i++)
            ev |= flier_edges(e, HUMANS + STAGE_SPAWN_COUNT + i, &g->trip_rivals.r[i].f, g->trip_rivals.r[i].active, g->hazard_kind, 1);
        if (e->prev_gum != SE_UNSEEN_GUM && e->prev_gum > 0 && g->trip.gum == 0) e->n_pop++;   /* the player's bubble bursts */
        if (e->prev_gum != SE_UNSEEN_GUM && e->prev_gum >= SE_GUM_LOW && g->trip.gum < SE_GUM_LOW && g->trip.gum > 0) e->cues |= 1ul << SC_GUM_LOW;
        e->prev_gum = g->trip.gum;
    } else e->prev_gum = SE_UNSEEN_GUM;
    return ev;
}

/* Cue edges of one playing frame; emit is 0 on the first playing frame (it only records). */
static void cue_events(SoundEvents *e, const Game *g, uint8_t emit)
{
    uint32_t c = 0;
    int i;
    if (g->round_start != e->prev_round_start) {
        if (g->round_start == RS_GO) c |= 1ul << SC_GO;
        else if (g->round_start == RS_ROUND) c |= 1ul << SC_BANNER;
    }
    e->prev_round_start = g->round_start;
    if (g->bounces > e->prev_bounces) c |= 1ul << SC_BUMP;
    e->prev_bounces = g->bounces;
    if (g->mode == GAME_MODE_ARCADE) {
        uint8_t touch = 0;
        for (i = 0; i < STAGE_SPAWN_COUNT; i++) {
            const ArcPump *p = &g->pump[i];
            uint8_t was = e->prev_pump[i], now = (uint8_t)(p->state << 4 | (p->state == ARC_PUMP_PUMPING ? arc_pump_progress(p) : 0));
            e->prev_pump[i] = now;
            if (now == was || i >= g->cpu_count) continue;
            if (p->state == ARC_PUMP_PUMPING) { if (was >> 4 == ARC_PUMP_PUMPING && now > was) c |= 1ul << ((now & 1) ? SC_PUMP_A : SC_PUMP_B); }
            else if (p->state == ARC_PUMP_FLYING) { if (was >> 4 == ARC_PUMP_PUMPING) c |= 1ul << SC_RIVAL_LAUNCH; }
            else if (p->state == ARC_PUMP_DEFEATED) c |= 1ul << SC_DEFEAT;
        }
        for (i = 0; i < g->elems.n; i++) {
            const ArcElement *el = &g->elems.el[i];
            uint16_t t = el->timer, was = e->prev_el[i];
            e->prev_el[i] = t;
            if (t == was) continue;   /* frozen frames (banner, result) repeat the timer: no second sound */
            if (el->kind == ARC_EL_VENT) {
                if (t == ARC_VENT_TELEGRAPH) c |= 1ul << SC_VENT_WARN;
                else if (t == ARC_VENT_LAUNCH) c |= 1ul << SC_VENT_BURST;
            } else if (el->kind == ARC_EL_GRABBER && t) {
                if (!was) c |= 1ul << SC_GRAB_RISE;
                else if (arc_elements_grab_frame(t) == ARC_GRAB_HIT_FIRST && arc_elements_grab_frame(was) != ARC_GRAB_HIT_FIRST) c |= 1ul << SC_GRAB_BITE;
            }
        }
        if (g->elems.n && g->hero[0].state < FLIER_FALLING) {   /* the same boxes game.c arc_element_apply uses; the speeds go to scratch */
            int cx = (int)(g->hero[0].x >> 16), cy = (int)(g->hero[0].y >> 16), hh = (int)(flier_half_h(&g->hero[0]) >> 16);
            int32_t vx = 0, vy = 0;
            if (arc_elements_bounce(&g->elems, cx, cy, FLIER_HALF_W, hh, &vx, &vy)) touch |= 1;
            if (arc_elements_lift(&g->elems, cx, cy, FLIER_HALF_W, hh)) touch |= 2;
        }
        if (touch & ~e->prev_touch & 1) c |= 1ul << SC_FLIPPER;
        if (touch & ~e->prev_touch & 2) c |= 1ul << SC_GRATE;
        e->prev_touch = touch;
        if (g->bonus.spawned > e->prev_spawned) c |= 1ul << SC_BUBBLE_PUFF;
        if (g->bonus.caught > e->prev_caught && emit) e->n_pop++;   /* a caught bonus bubble bursts */
        e->prev_spawned = g->bonus.spawned; e->prev_caught = g->bonus.caught;
        for (i = 0; i < g->players; i++) {
            const ArcLives *l = &g->lives[i];
            if (l->lives < e->prev_lives[i]) c |= 1ul << SC_LIFE_LOST;
            if (l->state == ARC_LIFE_CONTINUE) {
                uint8_t s = (uint8_t)arc_continue_seconds(l);
                if (e->prev_life_state[i] != ARC_LIFE_CONTINUE || s != e->prev_seconds[i]) c |= 1ul << SC_CONTINUE_TICK;
                e->prev_seconds[i] = s;
            } else if (l->state == ARC_LIFE_PLAY && e->prev_life_state[i] == ARC_LIFE_CONTINUE) c |= 1ul << SC_CONTINUE_YES;
            e->prev_lives[i] = l->lives; e->prev_life_state[i] = (uint8_t)l->state;
        }
    } else if (g->mode == GAME_MODE_TRIP) {
        if (g->trip_events & TRIP_EV_PICKUP) c |= 1ul << (g->trip.streak >= SE_STREAK_MIN ? SC_PICKUP_STREAK : SC_PICKUP);
        if (g->trip_rival_events & TRIP_RIV_EV_SPAWN) c |= 1ul << SC_RIVAL_WARN;
    }
    if (emit) e->cues |= c;
}

static void name_entry_cues(SoundEvents *e, const FlowView *v)
{
    const NameEntry *n = v->entry;
    uint8_t sym;
    if (v->state != FLOW_NAME_ENTRY || !n) { e->ne_seen = 0; return; }
    sym = n->pos < NAME_LEN ? n->sym[n->pos] : 0;
    if (e->ne_seen) {
        if (n->done && !e->ne_done) e->cues |= 1ul << SC_NE_DONE;
        else if (n->pos > e->ne_pos) e->cues |= 1ul << SC_NE_CONFIRM;
        else if (n->pos < e->ne_pos || sym != e->ne_sym) e->cues |= 1ul << SC_NE_MOVE;
    }
    e->ne_seen = 1; e->ne_pos = n->pos; e->ne_sym = sym; e->ne_done = n->done;
}

uint16_t se_step(SoundEvents *e, const FlowView *v)
{
    uint16_t ev = 0;
    uint8_t playing = v->state == FLOW_PLAYING && v->game;
    e->cues = 0;
    if (playing && e->prev_state != FLOW_PLAYING) {
        ev |= SE_START;
    } else if (playing && e->primed) {
        if (v->game->flaps[0] > e->prev_flaps[0] || v->game->flaps[1] > e->prev_flaps[1]) ev |= SE_FLAP;
        if (v->game->trip_events & TRIP_EV_HIT) ev |= SE_HIT;
    }
    if (!playing && e->prev_state == FLOW_PLAYING && v->state == FLOW_GAME_OVER) ev |= SE_GAME_OVER;
    if (v->state <= FLOW_ATTRACT_DEMO && e->prev_state > FLOW_ATTRACT_DEMO) ev |= SE_TITLE;
    if (playing && e->primed && v->game->matches_won > e->prev_matches) ev |= SE_ROUND;
    e->prev_matches = playing ? v->game->matches_won : 0;
    ev |= death_events(e, playing ? v->game : 0, playing);
    if (playing) cue_events(e, v->game, e->primed);
    name_entry_cues(e, v);
    e->prev_state = (uint8_t)v->state;
    e->primed = playing;
    e->prev_flaps[0] = playing ? v->game->flaps[0] : 0;
    e->prev_flaps[1] = playing ? v->game->flaps[1] : 0;
    return ev;
}

uint8_t coin_drain(uint8_t *pending)
{
    if (!*pending) return 0;
    (*pending)--;
    return 1;
}
