/* test_big_blow.c - Gum Games Big Blow through the Game: mash growth, leak, burst, qualifying, tickets, game over, pump frame, record. */
#include <stdio.h>
#include "game.h"
#include "flow.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

static void frames(Game *g, int n, uint8_t in) { while (n-- > 0) game_step(g, in); }
/* n alternating presses, each a 2-frame press and a 2-frame gap */
static int turn;
static void mash(Game *g, int n)
{
    for (int i = 0; i < n; i++) { uint8_t b = (turn++ & 1) ? IN_B : IN_A; frames(g, 2, b); frames(g, 2, 0); }
}
static void to_play(Game *g) { while (g->blow.phase != GG_BLOW_PLAY) game_step(g, 0); }
static void to_next(Game *g) { while (g->blow.phase == GG_BLOW_PLAY || g->blow.phase == GG_BLOW_BURST || g->blow.phase == GG_BLOW_RESULT) game_step(g, 0); }

int main(void)
{
    Game g;
    game_reset(&g, 1);
    game_set_mode(&g, GAME_MODE_GUM);
    CHECK(g.mode == GAME_MODE_GUM && g.blow.phase == GG_BLOW_INTRO && g.blow.seq.tickets[0] == GG_ATTEMPTS);
    CHECK(game_begin(&g) == 0 && !game_can_join_p2(&g));

    /* attempt 1: B first and A second both count; the pump frame follows the size into the right stage */
    to_play(&g);
    mash(&g, 4);
    CHECK(g.blow.size >= 9 && g.blow.size <= 12);
    for (int s = 0; s < (int)GG_BLOW_MAX; s++) {
        g.blow.size = (uint8_t)s;
        game_step(&g, 0);
        if (g.blow.size == (uint8_t)s || g.blow.size == (uint8_t)(s - 1)) CHECK(arc_pump_progress(&g.hpump[0]) == g.blow.size / (int)GG_BLOW_STAGE);
    }
    CHECK(arc_pump_in_window(&g.hpump[0]));

    /* leak: no input, the clock runs out with a small bubble: not qualified, 0 points of stage 0 */
    g.blow.size = 20;
    while (g.blow.phase == GG_BLOW_PLAY) game_step(&g, 0);
    CHECK(g.blow.phase == GG_BLOW_RESULT && g.blow.last_qualified == 0 && g.blow.seq.tickets[0] == 2);
    to_next(&g);
    CHECK(g.blow.phase == GG_BLOW_INTRO && !g.over);

    /* attempt 2: mash past the limit: burst, result 0, no points, ticket spent */
    to_play(&g);
    mash(&g, 40);
    CHECK(g.blow.phase == GG_BLOW_BURST && g.blow.last_size == 0 && g.blow.last_qualified == 0 && g.blow.seq.tickets[0] == 1);
    to_next(&g);

    /* attempt 3: hold the bubble at stage 3 until the clock ends: qualified, 3 * 100 + 500, game over after the result */
    to_play(&g);
    g.blow.size = 50;
    while (g.blow.phase == GG_BLOW_PLAY) { if (g.blow.size < 52) mash(&g, 1); else game_step(&g, 0); }
    CHECK(g.blow.phase == GG_BLOW_RESULT && g.blow.last_qualified == 1 && g.blow.last_stage == 3 && g.blow.last_size >= 48);
    CHECK(g.blow.last_points == 800 && g.score == 800 && g.blow.more == 0 && !g.over);
    to_next(&g);
    CHECK(g.blow.phase == GG_BLOW_END && g.over == 1 && g.score == 800);

    /* flow: the title GUM GAMES row starts the event, no round phases; the best size becomes the record */
    {
        Flow f;
        flow_init(&f, 0, 0);
        f.mode = GAME_MODE_GUM;
        f.tables.gg_record[GG_BIG_BLOW] = 0;
        flow_coin(&f);
        flow_step(&f, 0, 1, 1);
        CHECK(f.state == FLOW_PLAYING && f.game.mode == GAME_MODE_GUM && f.game.rounds == 0);
        f.game.blow.seq.best[0] = 52;
        f.game.blow.phase = GG_BLOW_END;
        flow_step(&f, 0, 0, 0);
        CHECK(f.state == FLOW_PLAYING && f.game.res.active && f.game.res.ev);   /* the event ends on its result screen, not GAME OVER */
        for (int i = 0; i < 40; i++) flow_step(&f, 0, 0, 0);
        flow_step(&f, IN_A, 0, 0);
        CHECK(f.state != FLOW_PLAYING && f.state != FLOW_GAME_OVER && f.tables.gg_record[GG_BIG_BLOW] == 52 && f.dirty);
    }
    printf("test_big_blow: %d failures\n", fails);
    return fails != 0;
}
