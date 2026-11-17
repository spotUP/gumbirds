/* test_gg_flapdash.c - Gum Games Flap Dash: lap count, finish, speed clamp, mash gating, mark tightening, game wiring. */
#include <stdio.h>
#include "gg_flapdash.h"
#include "game.h"
#include "flow.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

/* Alternate A and B every `period` frames (press edge, release between); returns the finish frame or 0. */
static uint32_t run(GgDash *d, Flier *h, int period, uint32_t max, int32_t *top_vx, int *laps_jump)
{
    uint32_t f;
    uint8_t in = 0;
    for (f = 1; f <= max; f++) {
        uint8_t before = d->laps;
        in = (f % period == 0) ? (uint8_t)(((f / period) & 1) ? IN_A : IN_B) : 0;
        if (gumdash_step(d, h, in)) return f;
        if (h->vx > *top_vx) *top_vx = h->vx;
        if (d->laps > before + 1) (*laps_jump)++;
    }
    return 0;
}

int main(void)
{
    GgDash d; Flier h;
    int32_t top = 0; int jumps = 0; uint32_t fin, prev_laps_frame;
    int i;

    /* no mashing: no thrust, no lap */
    gumdash_init(&d, &h);
    for (i = 0; i < 300; i++) gumdash_step(&d, &h, 0);
    CHECK(d.laps == 0 && d.lap_dist == 0 && d.frames == 300);

    /* A,A,A held is one press: adds no thrust beyond the first */
    gumdash_init(&d, &h);
    for (i = 0; i < 120; i++) gumdash_step(&d, &h, IN_A);
    CHECK(d.mash.count == 1);

    /* fast mash: finishes after exactly 3 laps, speed never above the camera cap, frames == record */
    gumdash_init(&d, &h);
    fin = run(&d, &h, 6, 5000, &top, &jumps);
    CHECK(fin != 0 && d.done && d.laps == GD_LAPS && d.frames == fin);
    CHECK(top <= GD_MAX_VX && top > 0 && jumps == 0);
    CHECK(fin >= 580);                                   /* cap alone needs 3 * 384 / 2 = 576 frames */
    CHECK(gumdash_step(&d, &h, IN_A) == 0 && d.frames == fin);   /* finished: frozen */

    /* a lap is counted once per wrap */
    gumdash_init(&d, &h);
    h.vx = GD_MAX_VX;
    prev_laps_frame = 0;
    d.lap_dist = ARENA_W16 - 1;
    CHECK(d.laps == 0);
    gumdash_step(&d, &h, 0);
    CHECK(d.laps == 1 && d.lap_dist < GD_MAX_VX);
    gumdash_step(&d, &h, 0);
    CHECK(d.laps == 1);
    (void)prev_laps_frame;

    /* speed clamp: an over-fast bird is pulled back to the cap with x and vx in agreement */
    gumdash_init(&d, &h);
    h.vx = FL_PX(5);
    { int32_t x0 = h.x; gumdash_step(&d, &h, 0); CHECK(h.vx == GD_MAX_VX); CHECK(arena_wrap_x(h.x - x0 + ARENA_W16) % ARENA_W16 <= GD_MAX_VX); }

    /* marks tighten 5% per loop and stop at the floor */
    CHECK(gumdash_mark(0) == GD_MARK_FRAMES);
    CHECK(gumdash_mark(1) < gumdash_mark(0) && gumdash_mark(2) < gumdash_mark(1));
    CHECK(gumdash_mark(1) >= GD_MARK_FRAMES * 94 / 100 && gumdash_mark(1) <= GD_MARK_FRAMES * 96 / 100);
    CHECK(gumdash_mark(200) == GD_MARK_MIN);

    /* game wiring: game_step runs the dash on hero[0] */
    { Game g; game_reset(&g, 1); game_set_mode(&g, GAME_MODE_GUM); game_gg_start_dash(&g);
      for (i = 0; i < 200; i++) game_step(&g, (uint8_t)((i % 6 == 0) ? ((i / 6) & 1 ? IN_A : IN_B) : 0));
      CHECK(g.dash.frames == 200 && g.hero[0].x != 0 && g.cpu_count == 0); }

    /* flow: Right three times from Big Blow picks Flap Dash (a fourth Right goes on to Gum Fling), Start runs it; a finished run ends the event after the result and keeps the best (lowest) time */
    {
        Flow f;
        flow_init(&f, 0, 0);
        f.mode = GAME_MODE_GUM; f.gg_event = GG_BIG_BLOW;
        flow_coin(&f);
        flow_step(&f, IN_RIGHT, 0, 0); flow_step(&f, 0, 0, 0);
        flow_step(&f, IN_RIGHT, 0, 0); flow_step(&f, 0, 0, 0);
        flow_step(&f, IN_RIGHT, 0, 0); flow_step(&f, 0, 0, 0);
        CHECK(f.gg_event == GG_FLAP_DASH);
        flow_step(&f, IN_RIGHT, 0, 0); flow_step(&f, 0, 0, 0);
        CHECK(f.gg_event == GG_FLING);
        flow_step(&f, IN_LEFT, 0, 0); flow_step(&f, 0, 0, 0);
        CHECK(f.gg_event == GG_FLAP_DASH);
        f.tables.gg_record[GG_FLAP_DASH] = 900;
        flow_step(&f, 0, 1, 1);
        CHECK(f.state == FLOW_PLAYING && f.game.gg_dash);
        f.game.dash.done = 1; f.game.dash.frames = 1000; f.game.dash.laps = GD_LAPS;
        for (i = 0; i < (int)GD_RESULT_FRAMES + 2; i++) flow_step(&f, 0, 0, 0);
        CHECK(f.state == FLOW_GAME_OVER && f.tables.gg_record[GG_FLAP_DASH] == 900);
        flow_init(&f, 0, 0);
        f.mode = GAME_MODE_GUM; f.gg_event = GG_FLAP_DASH;
        flow_coin(&f);
        flow_step(&f, 0, 1, 1);
        f.game.dash.done = 1; f.game.dash.frames = 800;
        for (i = 0; i < (int)GD_RESULT_FRAMES + 2; i++) flow_step(&f, 0, 0, 0);
        CHECK(f.tables.gg_record[GG_FLAP_DASH] == 800);
    }

    puts(fails ? "FAIL test_gg_flapdash" : "PASS test_gg_flapdash");
    return fails != 0;
}
