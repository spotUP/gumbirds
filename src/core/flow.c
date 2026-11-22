#include "flow.h"
#include "trip_hit.h"

static void enter(Flow *f, FlowState s)
{
    if (s == FLOW_ATTRACT_TITLE) { /* each attract loop shows the next mood: a demo match changed it already, a Gum Trip demo did not */
        if (f->game.mood == f->title_mood) {
            game_next_mood(&f->game);
        }
        f->title_mood = f->game.mood;
    }
    if (s == FLOW_ATTRACT_TITLE && f->mode == GAME_MODE_GUM) f->mode = GAME_MODE_PARTY; /* the merged PARTY row: GUM is only the mode of a gum game under the open submenu cursor */
    f->state = (uint8_t)s;
    f->timer = 0;
    f->reset_hold = 0;
    f->reset_fired = 0;
    f->sub_open = 0;
}

/* The PARTY row plays the event under the submenu cursor (sub_i): a gum game runs as GAME_MODE_GUM. */
static void title_resolve(Flow *f)
{
    if (f->mode == GAME_MODE_PARTY && f->sub_i >= PARTY_RULE_COUNT - 1) f->mode = GAME_MODE_GUM;
}

static void start_game(Flow *f, uint32_t seed, int demo)
{
    if (!demo) title_resolve(f);
    game_reset(&f->game, seed);
    if (demo) {
        game_set_mode(&f->game, f->demo_mode); /* each demo plays the next mode; the title highlight (f->mode) is untouched */
        f->demo_mode = (uint8_t)(f->demo_mode == GAME_MODE_ARCADE ? GAME_MODE_ARENA : f->demo_mode + 1); /* count and wrap, no % */
    } else {
        game_set_mode(&f->game, f->mode);
        if (f->mode == GAME_MODE_PARTY) f->game.party_rule = f->party_rule;
        if (f->mode == GAME_MODE_PARTY && f->party_rule == PARTY_TOSS) game_gg_start_toss(&f->game);
        if (f->mode == GAME_MODE_PARTY && f->party_rule == PARTY_TUG) game_gg_start_tug(&f->game);
        if (f->mode == GAME_MODE_GUM && f->gg_event == GG_BURST_RACE) game_gg_start_race(&f->game);
        if (f->mode == GAME_MODE_GUM && f->gg_event == GG_POP_DROP) game_gg_start_pop(&f->game);
        if (f->mode == GAME_MODE_GUM && f->gg_event == GG_FLAP_DASH) game_gg_start_dash(&f->game);
        if (f->mode == GAME_MODE_GUM && f->gg_event == GG_BUBBLE_GATHER) game_gg_start_gather(&f->game);
        if (f->mode == GAME_MODE_GUM && f->gg_event == GG_FLING) game_gg_start_fling(&f->game);
        if (f->mode == GAME_MODE_GUM && f->gg_event == GG_POOP_MAN) game_gg_start_poop(&f->game);
    }
    f->demo = (uint8_t)demo;
    f->howto = 0;
    f->gg_card = 0;
    f->demo_in = 0;
    if (demo) ai_init(&f->demo_ai, &f->game.rng, DEMO_AI_RANK);
    attract_overlay_reset(&f->ov);
    f->game.rounds = (uint8_t)(!demo && f->mode != GAME_MODE_TRIP && f->mode != GAME_MODE_GUM && !f->game.gg_toss && !f->game.gg_tug); /* real arena games get the round end and round start phases */
    f->highlight = -1;
    f->new_row = -1;
    f->reset_flash = 0;
    f->select_open = 0;
    enter(f, demo ? FLOW_ATTRACT_DEMO : FLOW_PLAYING);
}

/* Start on the title or a table screen: a PARTY match opens with the how-to demo (the attract demo pilot, party rule on, fixed seed),
 * any other mode starts at once. The demo runs as FLOW_PLAYING with howto set and no round phases. */
static void start_title_game(Flow *f, uint32_t seed)
{
    title_resolve(f);
    if (f->mode != GAME_MODE_PARTY || f->party_rule == PARTY_TOSS || f->party_rule == PARTY_TUG) {   /* Toss Gum and Tug Gum have no how-to demo */
        start_game(f, seed, 0);
        f->gg_card = f->mode == GAME_MODE_GUM && flow_gg_card(f->gg_event);
        f->card_t = 0;
        return;
    }
    start_game(f, PARTY_HOWTO_SEED, 0);
    f->game.rounds = 0;
    ai_init(&f->demo_ai, &f->game.rng, DEMO_AI_RANK);
    f->howto = 1;
    f->howto_a2 = 1; /* a P2 A still held from the title does not skip */
}

/* P2 Start in play (a credit was taken). Arcade: parachute drop-in. Arena and Party: the whole match restarts through start_game with both humans
 * (scores, rounds, CPUs fresh; party_rule kept). Returns 0 when refused (the caller keeps the credit). */
int flow_join_p2(Flow *f, uint32_t seed)
{
    Game *g = &f->game;
    if (f->state != FLOW_PLAYING || !game_can_join_p2(g)) return 0;
    if (g->mode != GAME_MODE_ARENA) return game_join_p2(g);
    start_game(f, seed, 0);
    arc_lives_start(&g->lives[0]);
    game_start_p2(g);
    return 1;
}

void flow_init(Flow *f, const uint8_t *image, size_t len)
{
    f->dirty = 0;
    f->highlight = -1;
    f->new_row = -1;
    f->demo = 0;
    f->demo_mode = GAME_MODE_ARENA;
    f->demo_in = 0;
    f->howto = 0;
    attract_overlay_reset(&f->ov);
    f->select_open = 0;
    f->credit_hold = 0;
    f->mode = GAME_MODE_ARENA;
    f->party_rule = PARTY_ROUND;
    f->sub_i = 0;
    f->last_rule = PARTY_NONE;
    f->input_prev = 0;
    f->reset_flash = 0;
    f->reset_hold = 0;
    f->reset_fired = 0;
    f->last_score[0] = f->last_score[1] = 0;
    f->last_players = 1;
    f->entry_h = 0;
    f->last_mode = GAME_MODE_ARENA;
    /* a version 1 image (arena only) loads with the trip table at defaults; dirty stays 0 so the version 2 image is
     * written back on the first new entry, not at boot (user 2026-11-11) */
    if (!image || !score_load(&f->tables, image, len)) {
        score_tables_defaults(&f->tables);
    }
    game_reset(&f->game, 1);
    f->title_mood = 0xFF; /* no title shown yet: the first one keeps the boot mood */
    nameentry_init(&f->entry);
    enter(f, FLOW_ATTRACT_TITLE);
}

/* Would this score make the table? Tries the insert on a copy so the ranking rule
 * (ties rank below, zero never ranks) lives only in hiscore_insert, reached through score_qualifies. */
static int ranks(const Flow *f, uint32_t score)
{
    return score_qualifies(&f->tables, f->last_mode, score);
}

/* Start the name entry of the first human from h on whose score ranks (checked against the table as it is now, so P2 sees P1's row). 0 when none. */
static int next_entry(Flow *f, int h)
{
    for (; h < f->last_players; h++) {
        if (ranks(f, f->last_score[h])) {
            f->entry_h = (uint8_t)h;
            nameentry_init(&f->entry);
            enter(f, FLOW_NAME_ENTRY);
            return 1;
        }
    }
    return 0;
}

/* Nearest gum pickup ahead in the Gum Trip chunk ring, as a screen position (x ahead of the flier, y world); 0 when none is built. */
static int demo_pickup(const Game *g, const Flier *fl, int32_t *tx, int32_t *ty)
{
    int s = g->trip_gen.head, i, best = 0;
    int32_t bx = 0;
    for (i = 0; i < g->trip_gen.count; i++, s = (s + 1 == TRIP_GEN_RING) ? 0 : s + 1) {
        const TripChunk *c = &g->trip_gen.ring[s];
        int32_t x = (int32_t)(c->wx - g->trip.px) + c->pickup.x;
        if (c->pickup.present && x >= (fl->x >> 16) && (!best || x < bx)) { best = 1; bx = x; *ty = FL_PX(c->pickup.y - 8); } /* aim high: sinking onto its centre grazes the rock below */
    }
    *tx = FL_PX(bx);
    return best;
}

/* Gum Trip: move the aim ty off any hazard in the next DEMO_HAZ_AHEAD px, to whichever side of its sweep the band [lo, hi] holds.
 * A sweep too wide for the band falls back to the hazard's box now. */
static int32_t demo_haz_aim(const Game *g, const Flier *fl, int32_t ty, int32_t lo, int32_t hi)
{
    int s = g->trip_gen.head, i, k, fx = (int)(fl->x >> 16), y = (int)(ty >> 16);
    lo = (lo >> 16) + FLIER_HALF_W; hi = (hi >> 16) - FLIER_HALF_W;
    for (i = 0; i < g->trip_gen.count; i++, s = (s + 1 == TRIP_GEN_RING) ? 0 : s + 1) {
        const TripChunk *c = &g->trip_gen.ring[s];
        int base = (int)(int32_t)(c->wx - g->trip.px);
        for (k = 0; k < c->n_haz; k++) {
            const TripGenHazard *h = &c->haz[k];
            int dx = base + h->x - fx, m = h->hh + 12 + 4, hy = trip_hit_haz_y(h, g->trip.steps), up, dn;
            if (dx < -(h->hw + FLIER_HALF_W) || dx > DEMO_HAZ_AHEAD + h->hw) continue;
            up = h->y - h->amp - m; dn = h->y + h->amp + m;
            if (up < lo && dn > hi) { up = hy - m; dn = hy + m; }   /* sweep fills the band: dodge the box where it is */
            if (y <= up || y >= dn) continue;
            y = (up >= lo && (dn > hi || y - up < dn - y)) ? up : (dn <= hi ? dn : y);
        }
    }
    return FL_PX(y);
}

/* Demo input: a competent player, not a script. Arena and arcade: the rival AI (ai.c) steers the player flier at the nearest rival
 * while it holds the high line (flaps whenever below DEMO_HOVER_Y), so rivals that rise to it get stomped; it steps out from under
 * any rival above. Arcade also steers off vents and
 * grabbers like a rival does. Gum Trip: steer to the nearest gum pickup ahead, its height held inside the middle half of the cave
 * window (an aim near the rock overshoots into it) and moved off hazards ahead (demo_haz_aim); flaps on the predicted height, so a
 * climb coasting into the roof does not flap again. With no target it hovers and sweeps as the old script did. The AI runs on even
 * demo frames only (frame cost); an odd frame holds the steering and drops A, so the press edge survives. Every frame carries exactly
 * one side bit (the overlay shows one). */
static uint8_t demo_input(Flow *f)
{
    Game *g = &f->game;
    const Flier *fl = &g->hero[0];
    int32_t lo = 0, hi = 0, tx, ty;
    uint8_t side = (uint8_t)(f->demo_in & (IN_LEFT | IN_RIGHT)), in;
    const Flier *t;
    int can_flap = !fl->flap_prev && fl->flap_cd == 0, low;
    int32_t py = fl->y + (fl->vy << 4); /* where it will be in 16 frames: a climb or a fall coasts on */
    low = fl->y > FL_PX(DEMO_HOVER_Y);                          /* below the roof line: may flap */
    if (side != IN_LEFT) side = IN_RIGHT;
    if (f->timer & 1u) return side;
    if (g->mode == GAME_MODE_TRIP && trip_hit_window(&g->trip, &g->trip_gen, fl, &lo, &hi)) {
        int32_t q = (hi - lo) >> 2;
        ty = lo + (q << 1);
        if (demo_pickup(g, fl, &tx, &ty)) side = ((tx - fl->x) >> 16) < -2 ? IN_LEFT : IN_RIGHT;
        if (ty < lo + q) ty = lo + q;
        if (ty > hi - q) ty = hi - q;
        ty = demo_haz_aim(g, fl, ty, lo, hi);
        return (uint8_t)(side | (can_flap && py > ty ? IN_A : 0));
    }
    t = g->mode == GAME_MODE_TRIP ? 0 : ai_nearest(fl, g->hero, g->players, g->cpu, g->cpu_count); /* none while the last rival falls: hover */
    if (t) {
        FlierInput ci;
        int near, k;
        ai_step(&f->demo_ai, &g->rng, fl, t, &ci);
        if (ci.dir) side = ci.dir > 0 ? IN_RIGHT : IN_LEFT;
        in = side;
        near = (t->x - fl->x < FL_PX(DEMO_DODGE_DX)) && (fl->x - t->x < FL_PX(DEMO_DODGE_DX));
        if (can_flap && low) in |= IN_A; /* hold the high line */
        for (k = 0; k < g->cpu_count; k++) { /* any rival above, not only the target, stomps: step out from under the first one */
            const Flier *c = &g->cpu[k];
            if (c->state == FLIER_ALIVE && c->y < fl->y && c->x - fl->x < FL_PX(DEMO_DODGE_DX) && fl->x - c->x < FL_PX(DEMO_DODGE_DX)) { t = c; near = 1; break; }
        }
        if (near && t->y < fl->y) in = (uint8_t)((t->x > fl->x ? IN_LEFT : IN_RIGHT) | (in & IN_A)); /* step out from under a rival above, no climb into it */
        if (g->mode == GAME_MODE_ARCADE) {
            int away = arc_elements_avoid_dir(&g->elems, (int)(fl->x >> 16), (int)(fl->y >> 16), FLIER_HALF_W, (int)(flier_half_h(fl) >> 16), fl->vx);
            if (away) in = (uint8_t)((away > 0 ? IN_RIGHT : IN_LEFT) | (can_flap ? IN_A : 0));
        }
        return in;
    }
    in = ((f->timer / DEMO_SWEEP_FRAMES) & 1u) ? IN_LEFT : IN_RIGHT;
    return (uint8_t)(in | (can_flap && low ? IN_A : 0));
}

static void title_reset_combo(Flow *f, uint8_t input)
{
    if ((input & FLOW_RESET_COMBO) == FLOW_RESET_COMBO) {
        if (f->reset_hold < 0xFFFFu) {
            f->reset_hold++;
        }
        if (!f->reset_fired && f->reset_hold >= RESET_HOLD_FRAMES) {
            score_tables_defaults(&f->tables); /* wipes both tables */
            f->dirty = 1;
            f->reset_fired = 1;
            f->reset_flash = 1;
        }
    } else {
        f->reset_hold = 0;
        f->reset_fired = 0;
    }
}

/* GUM GAMES submenu order (owner 2026-11-17): the GG_* events as listed on screen. */
static const uint8_t gg_order[GG_PICK_COUNT] = { GG_BIG_BLOW, GG_BURST_RACE, GG_BUBBLE_GATHER, GG_POP_DROP, GG_FLAP_DASH, GG_FLING, GG_POOP_MAN };
static const char *const gg_names[GG_PICK_COUNT] = { "BIG BLOW", "BURST RACE", "BUBBLE GATHER", "POP DROP", "FLAP DASH", "GUM FLING", "POOP THE MAN" };

uint8_t flow_gg_event(uint8_t i) { return gg_order[i]; }
const char *flow_gg_name(uint8_t i) { return gg_names[i]; }

/* Result screen title of the minigame being played: 1 + its PARTY menu index (Result.ev, flow_menu_name). */
static uint8_t event_title(const Flow *f)
{
    uint8_t i;
    if (f->game.gg_toss) return PARTY_TOSS;
    if (f->game.gg_tug) return PARTY_TUG;
    for (i = 0; i < GG_PICK_COUNT; i++) if (gg_order[i] == f->gg_event) return (uint8_t)(PARTY_RULE_COUNT + i);
    return 0;
}

/* PARTY submenu (owner 2026-11-21): the party rules, then the gum games in gg_order. One list, one cursor (sub_i). */
const char *flow_menu_name(uint8_t i) { return i < PARTY_RULE_COUNT - 1 ? game_party_name((uint8_t)(i + 1)) : gg_names[i - (PARTY_RULE_COUNT - 1)]; }
const char *flow_menu_goal(uint8_t i) { return i < PARTY_RULE_COUNT - 1 ? game_party_goal((uint8_t)(i + 1)) : 0; }
const GgCard *flow_menu_card(uint8_t i) { return i < PARTY_RULE_COUNT - 1 ? 0 : flow_gg_card(gg_order[i - (PARTY_RULE_COUNT - 1)]); }

/* The cursor entry becomes the pick: party_rule or gg_event, and the mode (PARTY, or GUM for a gum game) so the title table follows. */
static void menu_sync(Flow *f)
{
    if (f->sub_i < PARTY_RULE_COUNT - 1) { f->party_rule = (uint8_t)(f->sub_i + 1); f->mode = GAME_MODE_PARTY; }
    else { f->gg_event = gg_order[f->sub_i - (PARTY_RULE_COUNT - 1)]; f->mode = GAME_MODE_GUM; }
}

/* Rules cards in gg_order order (owner 2026-11-17: Gum Fling first, the other events get theirs later). */
static const GgCard gg_cards[GG_PICK_COUNT] = {
    [1] = { "BLOW YOUR BUBBLE BIGGER THAN THE RIVAL",
            { { "PRESS A OR B", "FAST TO PUMP" }, { "EVERY NEW PRESS", "COUNTS ONCE" }, { "FIRST TO BURST", "WINS" } },
            { "HOLDING A BUTTON", "DOES NOT COUNT" } },
    [5] = { "FLING THE GUM AS FAR AS YOU CAN",
            { { "MASH A+B", "FOR POWER" }, { "A LOCKS", "THE ANGLE" }, { "MASH TO", "FLAP" } },
            { "SAFE ANGLE: 15 TO 75 DEGREES", "TAKE TURNS: 3 THROWS EACH" } },
    [6] = { "POOP ON THE WALKERS' HEADS FOR POINTS",
            { { "A FLAPS, B DROPS", "POOP ON WALKERS" }, { "HITS IN A ROW", "SCORE MORE" }, { "TOUCH A WALKER", "OR STREET: OUT" } },
            { "UMBRELLAS BLOCK, ANGRY SHOES STUN", "60 SECONDS, 1 OR 2 PLAYERS" } },
};
const GgCard *flow_gg_card(uint8_t event)
{
    uint8_t i;
    for (i = 0; i < GG_PICK_COUNT; i++) if (gg_order[i] == event) return gg_cards[i].goal ? &gg_cards[i] : 0;
    return 0;
}

/* 1 when A on the title would open the submenu (PARTY row, list open, submenu closed): the caller must not take a credit for that A. */
int flow_a_opens_submenu(const Flow *f)
{
    return f->state == FLOW_ATTRACT_TITLE && f->select_open && !f->sub_open && f->mode == GAME_MODE_PARTY;
}

/* Title mode select: a press edge steps through Arena, Gum Trip, Arcade, Party: Down forward, Up back, both wrap (both on one frame: forward). A held stick does not repeat.
 * With the PARTY submenu open (party rules and gum games, PARTY_MENU_COUNT entries) Up/Down move its cursor sub_i (wrapping) and B closes it; Left/Right do nothing. */
static void title_mode_select(Flow *f, uint8_t input, uint8_t b_edge)
{
    uint8_t edge = (uint8_t)(input & ~f->input_prev & (IN_UP | IN_DOWN));
    if (f->sub_open) {
        if (b_edge) { f->sub_open = 0; f->mode = GAME_MODE_PARTY; }
        else if (edge) {
            f->sub_i = (edge & IN_DOWN) ? (uint8_t)(f->sub_i == PARTY_MENU_COUNT - 1 ? 0 : f->sub_i + 1) : (uint8_t)(f->sub_i == 0 ? PARTY_MENU_COUNT - 1 : f->sub_i - 1);
            menu_sync(f);
        }
        return;
    }
    if (edge) {
        if (edge & IN_DOWN) f->mode = f->mode == GAME_MODE_PARTY ? GAME_MODE_ARENA : (uint8_t)(f->mode + 1);
        else f->mode = f->mode == GAME_MODE_ARENA ? GAME_MODE_PARTY : (uint8_t)(f->mode - 1);
    }
}

/* A coin in any attract phase jumps to the title with the mode list open (the logo and the press start prompt). */
void flow_coin(Flow *f)
{
    if (f->state > FLOW_ATTRACT_DEMO) return;
    f->demo = 0;
    f->highlight = -1;
    f->select_open = 1;
    if (f->state != FLOW_ATTRACT_TITLE) enter(f, FLOW_ATTRACT_TITLE);
    else f->timer = 0;
}

void flow_step(Flow *f, uint8_t input, uint8_t start_pressed, uint32_t frame_counter)
{
    if (f->timer < 0xFFFFu) {
        f->timer++;
    }
    /* MB1/MB2: A is a second Start on the attract screens, B goes back to the title (press edges) */
    uint8_t a_edge = (uint8_t)(input & ~f->input_prev & IN_A);
    uint8_t b_edge = (uint8_t)(input & ~f->input_prev & IN_B);
    /* Owner rule "never force start": credits in hold the title, table and demo jump back to it (like a coin) */
    if (f->credit_hold && !start_pressed && (f->state == FLOW_ATTRACT_TABLE || f->state == FLOW_ATTRACT_DEMO)) flow_coin(f);
    switch (f->state) {
    case FLOW_ATTRACT_TITLE:
        /* banked credits keep the mode list open, however the title was entered (a game end resets select_open) */
        if (f->credit_hold) f->select_open = 1;
        title_reset_combo(f, input);
        if (a_edge && !start_pressed && flow_a_opens_submenu(f)) { f->sub_open = 1; menu_sync(f); } /* before the cursor logic: this A only opens */
        else title_mode_select(f, input, b_edge);
        if (f->select_open) f->highlight = -1; /* the mode list covers the highlighted table's rows (owner 2026-11-17) */
        if (start_pressed && (input & FLOW_RESET_COMBO) != FLOW_RESET_COMBO) {
            /* start_pressed means a credit was taken: it always becomes a game, in the highlighted mode */
            start_title_game(f, frame_counter);
        } else if (a_edge && (input & FLOW_RESET_COMBO) != FLOW_RESET_COMBO) {
            if (!f->select_open) { f->select_open = 1; f->highlight = -1; f->timer = 0; } /* A without a credit only opens the select */
        } else if (f->timer >= ATTRACT_TITLE_FRAMES && !f->credit_hold) {
            f->reset_flash = 0;
            f->select_open = 0;
            f->highlight = -1; /* the saved row was shown on the title, the table that follows is plain */
            enter(f, FLOW_ATTRACT_TABLE);
        }
        break;
    case FLOW_ATTRACT_TABLE:
        if (start_pressed) {
            f->highlight = -1;
            start_title_game(f, frame_counter);
        } else if (a_edge || b_edge) {
            f->highlight = -1;
            enter(f, FLOW_ATTRACT_TITLE);
            f->select_open = !b_edge || a_edge;
        } else if (f->timer >= ATTRACT_TABLE_FRAMES) {
            f->highlight = -1;
            start_game(f, frame_counter, 1);
        }
        break;
    case FLOW_ATTRACT_DEMO:
        if (start_pressed) {
            start_title_game(f, frame_counter);
        } else if (a_edge || b_edge) {
            f->demo = 0;
            enter(f, FLOW_ATTRACT_TITLE);
            f->select_open = !b_edge || a_edge;
        } else {
            f->demo_in = demo_input(f);
            attract_overlay_step(&f->ov, f->demo_in);
            if (!game_begin(&f->game)) game_step(&f->game, f->demo_in); /* match setup gets its own frame (arcade stage entry overran) */
            /* The demo never scores into the table: it only ever returns to the title. */
            if (f->game.over || f->timer >= ATTRACT_DEMO_FRAMES) {
                f->demo = 0;
                enter(f, FLOW_ATTRACT_TITLE);
            }
        }
        break;
    case FLOW_PLAYING:
        if (f->gg_card) {   /* rules card: the game waits (GET SET starts when the card goes); P2 may still join */
            if (++f->card_t >= GG_CARD_FRAMES || (f->card_t > GG_CARD_IGNORE && a_edge)) f->gg_card = 0;
            break;
        }
        if (f->howto) {
            uint8_t a2 = (uint8_t)(f->game.input2 & IN_A);
            if (start_pressed || a_edge || (a2 && !f->howto_a2) || f->game.start_in[1] || f->timer >= PARTY_HOWTO_FRAMES || f->game.over) {
                start_game(f, frame_counter, 0); /* the real match, round 1 banner next */
                f->game.cont_a[0] = (uint8_t)((input & IN_A) ? 1 : 0); /* the skipping press must not also skip the round banner */
                f->game.cont_start[0] = f->game.start_in[0];
            } else {
                f->demo_in = demo_input(f);
                if (!game_begin(&f->game)) game_step(&f->game, f->demo_in);
            }
            f->howto_a2 = a2;
            break;
        }
        game_step(&f->game, input);
        if (f->game.over && game_end_event(&f->game, event_title(f))) break;   /* a minigame shows its results first, never GAME OVER */
        if (f->game.over) {
            f->last_players = f->game.players;
            f->last_score[0] = f->game.score;
            f->last_score[1] = f->game.players == 2 ? f->game.lives[1].score : 0;
            f->entry_h = 0;
            f->last_mode = f->mode; /* the title pick: PARTY plays as arena, so game.mode would lose the PARTY table */
            f->last_rule = f->game.party_rule;
            if (f->game.mode == GAME_MODE_GUM && f->game.gg_pop) { /* Pop Drop: the best fall score of either player is the record */
                uint32_t n = f->game.pop.seq.best[0] > f->game.pop.seq.best[1] ? f->game.pop.seq.best[0] : f->game.pop.seq.best[1];
                if (n > f->tables.gg_record[GG_POP_DROP]) { f->tables.gg_record[GG_POP_DROP] = n; f->dirty = 1; }
            } else if (f->game.gg_poop) { /* Poop the Man: the best score of either player is the record */
                uint32_t n = f->game.poop.seq.best[0] > f->game.poop.seq.best[1] ? f->game.poop.seq.best[0] : f->game.poop.seq.best[1];
                if (n > f->tables.gg_record[GG_POOP_MAN]) { f->tables.gg_record[GG_POOP_MAN] = n; f->dirty = 1; }
            } else if (f->game.gg_fling) { /* Gum Fling: the longest fling is the record */
                uint32_t n = f->game.fling.seq.best[0];
                if (n > f->tables.gg_record[GG_FLING]) { f->tables.gg_record[GG_FLING] = n; f->dirty = 1; }
            } else if (f->game.mode == GAME_MODE_GUM && f->game.gg_gather) { /* Bubble Gather: the most bubbles caught is the record */
                uint32_t n = f->game.bonus.caught;
                if (n > f->tables.gg_record[GG_BUBBLE_GATHER]) { f->tables.gg_record[GG_BUBBLE_GATHER] = n; f->dirty = 1; }
            } else if (f->game.mode == GAME_MODE_GUM && (f->game.gg_race || f->game.gg_dash)) { /* Burst Race and Flap Dash: the fastest time is the record (lower is better, 0 = none) */
                uint8_t ev = f->game.gg_race ? GG_BURST_RACE : GG_FLAP_DASH;
                uint32_t t = f->game.gg_race ? f->game.race.seq.best[0] : f->game.dash.done ? f->game.dash.frames : 0;
                if (t && (!f->tables.gg_record[ev] || t < f->tables.gg_record[ev])) { f->tables.gg_record[ev] = t; f->dirty = 1; }
            } else if (f->game.mode == GAME_MODE_GUM) { /* Big Blow: the best size is the event record */
                uint32_t best = f->game.blow.seq.best[0];
                if (best > f->tables.gg_record[GG_BIG_BLOW]) { f->tables.gg_record[GG_BIG_BLOW] = best; f->dirty = 1; }
            }
            f->ended = 1;
            if (!f->game.res.ev) enter(f, FLOW_GAME_OVER);
            else if (!next_entry(f, 0)) enter(f, FLOW_ATTRACT_TITLE);   /* the result screen was the end screen */
        }
        break;
    case FLOW_GAME_OVER:
        if (f->timer >= GAMEOVER_FRAMES || (a_edge && f->timer >= GAMEOVER_SKIP_FRAMES)) { /* main.c folds a Start press into A here */
            if (!next_entry(f, 0)) enter(f, FLOW_ATTRACT_TITLE);
        }
        break;
    case FLOW_NAME_ENTRY:
        if (f->entry_h == 0) nameentry_step(&f->entry, start_pressed ? (uint8_t)(input | IN_A) : input); /* NE1: Start confirms a letter like A */
        else nameentry_step(&f->entry, f->game.start_in[1] ? (uint8_t)(f->game.input2 | IN_A) : f->game.input2); /* P2's own stick and Start */
        if (f->entry.done) {
            f->new_row = (int8_t)score_insert_rule(&f->tables, f->last_mode, f->entry.name, f->last_score[f->entry_h], f->last_rule);
            f->highlight = f->new_row;
            f->dirty = 1;
            if (!next_entry(f, f->entry_h + 1)) enter(f, FLOW_SAVE_REMINDER);
        }
        break;
    case FLOW_SAVE_REMINDER:
        if (f->timer >= REMINDER_FRAMES) {
            enter(f, FLOW_ATTRACT_TITLE); /* BG1: straight to the title; the highlight stays until the title times out */
        }
        break;
    }
    f->input_prev = input;
}

void flow_view(const Flow *f, FlowView *v)
{
    v->state = (FlowState)f->state;
    v->timer = f->timer;
    v->table_mode = (uint8_t)score_shown_mode(f->state, f->mode, f->last_mode, f->timer, SCORE_TABLE_SWAP_FRAMES);
    v->table = &f->tables.t[v->table_mode];
    v->highlight = v->table_mode == f->last_mode ? f->highlight : -1;
    v->game = &f->game;
    v->entry = &f->entry;
    v->score = f->last_score[f->entry_h];
    v->players = f->last_players;
    v->entry_h = f->entry_h;
    v->reset_progress = f->reset_hold >= RESET_HOLD_FRAMES
                            ? 100
                            : (int)(((uint32_t)f->reset_hold * 100u) / RESET_HOLD_FRAMES);
    v->reset_flash = f->reset_flash;
    v->mode = f->mode;
    v->sub_open = f->sub_open;
    v->gg_event = f->gg_event;
    v->party_rule = f->party_rule;
    v->sub_i = f->sub_i;
    v->select_open = f->select_open;
    v->howto = f->howto;
    v->card = f->gg_card ? flow_gg_card(f->gg_event) : 0;
    v->card_t = f->card_t;
    v->ov_key = f->ov.key;
}
