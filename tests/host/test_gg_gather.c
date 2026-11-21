/* test_gg_gather.c - Gum Games Bubble Gather: the Arcade bonus stage as an event (layout 24, ArcBonus, result screen), clock, record, title pick. */
#include <stdio.h>
#include "game.h"
#include "flow.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

static void right(Flow *f) { flow_step(f, IN_DOWN, 0, 0); flow_step(f, 0, 0, 0); }
static void left(Flow *f) { flow_step(f, IN_UP, 0, 0); flow_step(f, 0, 0, 0); }

int main(void)
{
    Game g;
    int i, guard;

    /* idle hero: nobody catches, all 20 bubbles leave or the 45 s clock ends it, then the result screen, then the event is over */
    game_reset(&g, 1);
    game_set_mode(&g, GAME_MODE_GUM);
    game_gg_start_gather(&g);
    CHECK(g.gg_gather && g.players == 1 && g.cpu_count == 0 && stage_layout_index() == ARC_LAYOUT_BONUS && !g.res.active);
    for (i = 0; i < (int)GG_GATHER_CLOCK + 2 && !g.res.active; i++) game_step(&g, 0);
    CHECK(g.res.active && g.bonus.over && g.gather_clock <= GG_GATHER_CLOCK && g.over == 0);
    CHECK(g.bonus.spawned <= ARC_BONUS_BUBBLES && g.bonus.caught <= ARC_BONUS_BUBBLES);
    for (guard = 0; guard < 2000 && !g.over; guard++) game_step(&g, guard % 4 == 0 ? IN_A : 0);
    CHECK(g.over == 1 && !g.res.active);

    /* one screen wide: the ring is 320 + margin, the camera stays at 0, a hero flying right comes out at the left, and game_reset restores the arena ring */
    game_reset(&g, 1);
    game_set_mode(&g, GAME_MODE_GUM);
    game_gg_start_gather(&g);
    {
        int wrapped = 0, prev = (int)(g.hero[0].x >> 16);
        CHECK(arena_ring == FIELD_RING_W && FIELD_RING_W < ARENA_W);
        for (i = 0; i < 900 && !wrapped; i++) {
            int x;
            game_step(&g, (uint8_t)(IN_RIGHT | (i % 8 == 0 ? IN_A : 0)));
            x = (int)(g.hero[0].x >> 16);
            CHECK(x >= 0 && x < FIELD_RING_W && game_camera_px(&g) == 0);
            if (prev > FIELD_RING_W - 40 && x < 40) wrapped = 1;
            prev = x;
        }
        CHECK(wrapped);
        g.hero[0].x = FL_PX(FIELD_RING_W - 1) + 40000; /* past the seam by the next step: reappears at the left */
        CHECK(arena_wrap_x(g.hero[0].x + FL_PX(2)) < FL_PX(2));
        CHECK(arena_wrap_x(-FL_PX(2)) == FL_PX(FIELD_RING_W - 2));
    }
    game_reset(&g, 1);
    CHECK(arena_ring == ARENA_W);

    /* a hero parked in a bubble's path catches it, and the score is the result screen's tally */
    game_reset(&g, 1);
    game_set_mode(&g, GAME_MODE_GUM);
    game_gg_start_gather(&g);
    for (i = 0; i < 3000 && !g.res.active; i++) {
        int b;
        for (b = 0; b < ARC_BONUS_LIVE_MAX; b++) if (g.bonus.b[b].live) { g.hero[0].x = (int32_t)(g.bonus.b[b].x + 8) << 16; g.hero[0].y = (int32_t)((g.bonus.b[b].y16 >> 16) + 8) << 16; }
        game_step(&g, 0);
    }
    CHECK(g.bonus.caught >= 1 && g.bonus_caught[0] == g.bonus.caught);
    for (guard = 0; guard < 2000 && !g.over; guard++) game_step(&g, guard % 4 == 0 ? IN_A : 0);
    CHECK(g.over == 1 && g.score >= (uint32_t)g.bonus.caught * (uint32_t)arc_bonus_value(1));

    /* flow: Right twice from Big Blow picks Bubble Gather (both directions wrap), Start runs it, the best catch is the record (higher is better) */
    {
        Flow f;
        flow_init(&f, 0, 0);
        f.mode = GAME_MODE_PARTY;  /* merged PARTY list: sub_i 0 = Rule of the Round, 4 = Big Blow ... 10 = Poop the Man */
        flow_coin(&f);
        flow_step(&f, IN_A, 0, 0); flow_step(&f, 0, 0, 0);
        left(&f); CHECK(f.gg_event == GG_POOP_MAN);
        right(&f); CHECK(f.party_rule == PARTY_ROUND);
        { int k; for (k = 0; k < 6; k++) right(&f); }
        CHECK(f.gg_event == GG_BUBBLE_GATHER);
        f.tables.gg_record[GG_BUBBLE_GATHER] = 9;
        flow_step(&f, 0, 1, 1);
        CHECK(f.state == FLOW_PLAYING && f.game.gg_gather);
        for (i = 0; i < 6000 && f.state == FLOW_PLAYING; i++) flow_step(&f, i % 4 == 0 ? IN_A : 0, 0, 0);
        CHECK(f.state == FLOW_GAME_OVER && f.tables.gg_record[GG_BUBBLE_GATHER] == 9);
        flow_init(&f, 0, 0);
        f.mode = GAME_MODE_GUM; f.gg_event = GG_BUBBLE_GATHER;
        flow_coin(&f);
        flow_step(&f, IN_A, 0, 0); flow_step(&f, 0, 0, 0);
        flow_step(&f, 0, 1, 1);
        f.game.bonus.over = 1; f.game.bonus.caught = 14;
        for (i = 0; i < 6000 && f.state == FLOW_PLAYING; i++) flow_step(&f, i % 4 == 0 ? IN_A : 0, 0, 0);
        CHECK(f.tables.gg_record[GG_BUBBLE_GATHER] == 14 && f.tables.gg_record[GG_BIG_BLOW] == 0);
    }

    puts(fails ? "FAIL test_gg_gather" : "PASS test_gg_gather");
    return fails != 0;
}
