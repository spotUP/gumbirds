/* Host test for the PARTY Hot Gum rule (game.c): one carrier at start, a touch passes the gum after the cooldown and scores for a human,
 * stomps do not pop, the fuse pops one carrier balloon and moves the gum, the fuse shortens per round won, rivals flee the carrier. */
#include <stdio.h>
#include "../../src/core/game.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static Game g;

static void start(void) {
    int i;
    game_reset(&g, 11);
    game_set_mode(&g, GAME_MODE_ARENA);
    g.party_rule = PARTY_HOT;
    g.rounds = 1;
    for (i = 0; i < 600 && (g.cpu_count == 0 || g.round_start != RS_NONE); i++) game_step(&g, 0);
}

static void flying(void) { g.pump[0].state = ARC_PUMP_FLYING; g.hpump[0].state = ARC_PUMP_FLYING; } /* no pump window: a touch would defeat a pumping rival */

static void put(Flier *f, int x, int y) {
    f->state = FLIER_ALIVE; f->x = FL_PX(x); f->y = FL_PX(y); f->vx = 0; f->vy = 0;
    f->invincible = 0; f->spawn_inv = 0; f->on_ground = 0; f->balloons = 2;
}

int main(void) {
    int i, n, c0;
    start();
    n = g.players + g.cpu_count;
    CHECK(g.mode == GAME_MODE_ARENA && g.party_rule == PARTY_HOT && g.hot.carrier < n);
    CHECK(game_hot_carrier(&g) != 0);
    CHECK(g.hot.fuse > 0 && g.hot.fuse <= HOT_FUSE_FRAMES);

    /* a touch from the carrier hands the gum over once the cooldown has run out, and a human carrier scores */
    g.hot.carrier = 0; g.hot.cool = 0; g.hot.fuse = 5000;
    g.cpu_count = 1; flying();
    put(&g.hero[0], 147, 140); put(&g.cpu[0], 153, 140);
    g.hero[0].vx = FL_PX(1); g.cpu[0].vx = -FL_PX(1);
    g.score = 0;
    game_step(&g, 0);
    CHECK(g.hot.carrier == g.players && g.score == SCORE_HOT_PASS);
    CHECK(g.hot.cool > 0);

    /* during the cooldown a touch passes nothing */
    c0 = g.hot.carrier;
    put(&g.hero[0], 147, 140); put(&g.cpu[0], 153, 140);
    g.hero[0].vx = FL_PX(1); g.cpu[0].vx = -FL_PX(1);
    game_step(&g, 0);
    CHECK(g.hot.carrier == c0);

    /* stomps do not pop in this rule */
    start();
    g.cpu_count = 1; g.hot.fuse = 5000; flying();
    put(&g.cpu[0], 100, 100); put(&g.hero[0], 100, 80); g.hero[0].vy = FL_PX(2);
    for (i = 0; i < 10; i++) game_step(&g, 0);
    CHECK(g.cpu[0].state <= FLIER_PARACHUTE);

    /* the fuse ends: the carrier loses a balloon and the gum moves to a survivor, with a fresh fuse */
    start();
    g.cpu_count = 1; flying();
    put(&g.hero[0], 40, 120); put(&g.cpu[0], 300, 120);
    g.hot.carrier = 0; g.hot.cool = 0; g.hot.fuse = 2;
    c0 = g.hero[0].balloons;
    game_step(&g, 0); game_step(&g, 0);
    CHECK(g.hero[0].balloons == c0 - 1 || g.hero[0].state != FLIER_ALIVE);
    CHECK(g.hot.fuse > 2 || g.hot.carrier != 0);

    /* the fuse shortens per round won and never below HOT_FUSE_MIN */
    start();
    g.matches_won = 3;
    g.hot.carrier = 0xFF;
    game_step(&g, 0);
    CHECK(g.hot.fuse >= HOT_FUSE_MIN && g.hot.fuse < HOT_FUSE_FRAMES);

    /* a long run stays sane: the carrier index is always in range or none */
    start();
    for (i = 0; i < 3000 && !g.over; i++) {
        game_step(&g, (uint8_t)(i & 0x20 ? 0x10 : 0));
        CHECK(g.hot.carrier == 0xFF || g.hot.carrier < g.players + g.cpu_count);
    }

    /* rivals flee the carrier */
    start();
    g.hot.carrier = 0; g.hot.fuse = 5000;
    put(&g.cpu[0], 300, 100); flying();
    game_step(&g, 0);
    CHECK(g.cpu_count < 1 || g.ai[0].flee == 1);

    printf("%d checks, %d failures\n", checks, failures);
    return failures != 0;
}
