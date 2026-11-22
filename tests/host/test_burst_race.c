/* test_burst_race.c - Gum Games Burst Race through the Game and Flow: computer win, player win and time, 2P join, ties, idle clock, pump frames, record, title pick. */
#include <stdio.h>
#include "game.h"
#include "flow.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

/* a human press is 2 frames down and 2 up, alternating A and B: one press per 4 frames, faster than the computer's 5 */
static uint8_t press(int i) { return (i & 2) ? 0 : (((i >> 2) & 1) ? IN_B : IN_A); }
static void play(Game *g, int p1_mash, int p2_mash, int max)
{
    for (int i = 0; i < max && g->race.phase == GG_RACE_PLAY; i++) {
        g->input2 = p2_mash ? press(i) : 0;
        game_step(g, p1_mash ? press(i) : 0);
    }
}
static void to_play(Game *g) { while (g->race.phase != GG_RACE_PLAY) game_step(g, 0); }
static void new_race(Game *g, int players)
{
    game_reset(g, 1);
    game_set_mode(g, GAME_MODE_GUM);
    game_gg_start_race(g);
    if (players == 2) CHECK(game_can_join_p2(g) && game_join_p2(g) && g->race.players == 2 && !game_can_join_p2(g));
}

int main(void)
{
    Game g;
    /* idle player: the computer bird bursts first (about 135 frames), no points, no record time */
    new_race(&g, 1);
    CHECK(g.gg_race && g.race.phase == GG_RACE_INTRO && g.race.seq.tickets[0] == 1 && game_can_join_p2(&g));
    to_play(&g);
    play(&g, 0, 0, 3000);
    CHECK(g.race.phase == GG_RACE_RESULT && g.race.winner == 1 && g.race.size[1] == GG_BLOW_MAX);
    CHECK(gg_race_bursts(&g.race, 1) && !gg_race_bursts(&g.race, 0));
    CHECK(g.race.frames >= 100 && g.race.frames <= 200 && g.race.last_points == 0 && g.score == 0 && g.race.seq.best[0] == 0);
    while (g.race.phase != GG_RACE_END) game_step(&g, 0);
    game_step(&g, 0);
    CHECK(g.over == 1);

    /* fast mash (a press every 2 frames) beats the computer: stage 4 plus the mark, 900, time is the record */
    new_race(&g, 1);
    to_play(&g);
    play(&g, 1, 0, 3000);
    CHECK(g.race.phase == GG_RACE_RESULT && g.race.winner == 0 && g.race.size[0] == GG_BLOW_MAX);
    CHECK(g.race.last_points == 900 && g.score == 900 && g.race.seq.best[0] == g.race.frames && g.race.frames < 130);

    /* 2P: the join is accepted in the intro only; idle P2 loses to a masher; the clock decides two idle humans */
    new_race(&g, 2);
    to_play(&g);
    CHECK(!game_can_join_p2(&g));
    play(&g, 1, 0, 3000);
    CHECK(g.race.winner == 0 && g.race.players == 2);
    new_race(&g, 2);
    to_play(&g);
    play(&g, 0, 0, 5000);
    CHECK(g.race.phase == GG_RACE_RESULT && g.race.frames == GG_RACE_CLOCK && g.race.winner == 0 && g.race.last_points == 900);
    new_race(&g, 2);
    to_play(&g);
    play(&g, 0, 1, 5000);
    CHECK(g.race.winner == 1 && g.race.last_points == 0 && g.race.seq.best[0] == 0);

    /* flow: A then Down on the GUM GAMES row picks Burst Race, Start runs it, the fastest win becomes the record */
    {
        Flow f;
        flow_init(&f, 0, 0);
        f.mode = GAME_MODE_PARTY;  /* merged PARTY list: sub_i 0 = Rule of the Round, 4 = Big Blow ... 10 = Poop the Man */
        flow_coin(&f);
        flow_step(&f, IN_A, 0, 0); flow_step(&f, 0, 0, 0); /* A opens the GUM GAMES list */
        { int k; for (k = 0; k < 5; k++) { flow_step(&f, IN_DOWN, 0, 0); flow_step(&f, 0, 0, 0); } }
        CHECK(f.gg_event == GG_BURST_RACE);
        f.tables.gg_record[GG_BURST_RACE] = 90;
        flow_step(&f, 0, 1, 1);
        while (f.gg_card) flow_step(&f, 0, 0, 0);                  /* the rules card holds the game until it times out */
        CHECK(f.state == FLOW_PLAYING && f.game.gg_race && f.game.rounds == 0);
        f.game.race.seq.best[0] = 120;
        f.game.race.phase = GG_RACE_END;
        flow_step(&f, 0, 0, 0);
        CHECK(f.state == FLOW_GAME_OVER && f.tables.gg_record[GG_BURST_RACE] == 90);
        flow_init(&f, 0, 0);
        f.mode = GAME_MODE_GUM; f.gg_event = GG_BURST_RACE;
        flow_coin(&f);
        flow_step(&f, IN_A, 0, 0); flow_step(&f, 0, 0, 0); /* A opens the GUM GAMES list */
        flow_step(&f, 0, 1, 1);
        while (f.gg_card) flow_step(&f, 0, 0, 0);                  /* the rules card holds the game until it times out */
        f.game.race.seq.best[0] = 80;
        f.game.race.phase = GG_RACE_END;
        flow_step(&f, 0, 0, 0);
        CHECK(f.tables.gg_record[GG_BURST_RACE] == 80 && f.dirty);   /* lower time replaces a record, and fills an empty one */
    }
    /* every new press of A or B pumps once (the same button repeated too); a held button pumps once */
    {
        GgMash m; uint8_t prev = 0; int n = 0;
        const GgCard *c = flow_gg_card(GG_BURST_RACE);
        gg_mash_reset(&m);
        for (int i = 0; i < 20; i++) { uint8_t in = (i & 1) ? 0 : IN_A; n += gg_mash_step(&m, in, prev); prev = in; }
        CHECK(n == 10);
        gg_mash_reset(&m); n = 0; prev = 0;
        for (int i = 0; i < 20; i++) { n += gg_mash_step(&m, IN_A, prev); prev = IN_A; }
        CHECK(n == 1);
        CHECK(c != 0 && c->step[0][1] && c->step[1][0]);
    }
    printf("test_burst_race: %d failures\n", fails);
    return fails != 0;
}
