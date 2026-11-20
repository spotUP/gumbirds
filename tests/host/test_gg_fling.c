/* test_gg_fling.c - Gum Games Gum Fling: angle mapping, fouls, ballistic landing, three attempts, best counts, qualifying mark, title pick. */
#include <stdio.h>
#include "game.h"
#include "flow.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

/* tap A every other frame for 2 * mash frames (mash counted presses), then hold B (first frame starts the needle,
 * then hold frames of needle), release; returns the event of the release frame */
static int shoot(GgFling *f, int mash, int hold)
{
    int i, ev = GF_EV_NONE;
    for (i = 0; i < 2 * mash; i++) gumfling_step(f, (uint8_t)((i & 1) ? 0 : IN_A));
    gumfling_step(f, 0);
    for (i = 0; i < 1 + hold; i++) gumfling_step(f, IN_B);
    ev = gumfling_step(f, 0);
    return ev;
}

static void fly(GgFling *f) { int g; for (g = 0; g < 4000 && f->phase == GF_FLIGHT; g++) gumfling_fly(f); }

static void next(GgFling *f) { int g, ev = 0; for (g = 0; g < 1000 && ev != GF_EV_NEXT && f->phase != GF_END; g++) ev = gumfling_step(f, 0); }

int main(void)
{
    GgFling f;
    int i;

    CHECK(gumfling_deg(0) == 0 && gumfling_deg(GF_AIM_CAP) == 90 && gumfling_deg(1000) == 90);
    CHECK(gumfling_deg(GF_AIM_CAP / 2) == 45);

    /* a good shot launches, flies, lands at a positive distance */
    gumfling_init(&f);
    CHECK(shoot(&f, 30, 64) == GF_EV_LAUNCH && !f.foul && f.phase == GF_FLIGHT && f.vx > 0 && f.vy > 0);
    fly(&f);
    CHECK(f.phase == GF_LANDED && f.dist > 0 && f.seq.best[0] == f.dist);

    /* fouls: too flat, too steep, no launch before the clock runs out */
    gumfling_init(&f);
    shoot(&f, 20, 4);
    CHECK(f.foul && f.dist == 0 && f.phase == GF_LANDED);
    gumfling_init(&f);
    shoot(&f, 20, 120);
    CHECK(f.foul && f.dist == 0 && f.phase == GF_LANDED);
    gumfling_init(&f);
    for (i = 0; i < (int)GF_WINDUP_FRAMES + 5 && f.phase == GF_WINDUP; i++) gumfling_step(&f, 0);
    CHECK(f.foul && f.phase == GF_LANDED);

    /* more run-up power flies farther at the same angle */
    { GgFling a, b; gumfling_init(&a); gumfling_init(&b);
      shoot(&a, 2, 48); fly(&a); shoot(&b, 40, 48); fly(&b);
      CHECK(b.dist > a.dist); }

    /* three attempts, the best counts, then the end */
    gumfling_init(&f);
    shoot(&f, 4, 48); fly(&f); next(&f);
    CHECK(f.phase == GF_WINDUP);
    shoot(&f, 40, 48); fly(&f);
    { uint32_t best = f.dist; next(&f);
      shoot(&f, 2, 4);
      CHECK(f.foul);
      next(&f);
      CHECK(f.phase == GF_END && f.seq.best[0] == best); }

    /* A taps count as power and never start the needle; C does nothing; B starts the needle */
    gumfling_init(&f);
    for (i = 0; i < 20; i++) gumfling_step(&f, (uint8_t)((i & 1) ? 0 : IN_A));
    CHECK(f.phase == GF_WINDUP && f.power == 10);
    for (i = 0; i < 40; i++) gumfling_step(&f, IN_A);
    for (i = 0; i < 40; i++) gumfling_step(&f, IN_C);
    CHECK(f.phase == GF_WINDUP && f.power == 11);
    gumfling_step(&f, IN_B);
    CHECK(f.phase == GF_AIM);

    /* sounds: a throw, a landing, a foul */
    gumfling_init(&f);
    f.sfx = 0; shoot(&f, 20, 48);
    CHECK(f.sfx & GF_SFX_THROW);
    f.sfx = 0; fly(&f);
    CHECK((f.sfx & GF_SFX_LAND) && !(f.sfx & GF_SFX_FOUL));
    gumfling_init(&f);
    f.sfx = 0; shoot(&f, 20, 4);
    CHECK(f.sfx & GF_SFX_FOUL);

    /* solo: the result phase shows pass / fail, then the end; a pass plays the win sound */
    gumfling_init(&f);
    for (i = 0; i < 3; i++) { shoot(&f, 40, 48); fly(&f); f.sfx = 0; next(&f); }
    CHECK(f.phase == GF_END && f.seq.qualified[0] == (f.seq.best[0] >= GF_MARK_PX));

    /* 2P: turns alternate P1, P2, P1..., three throws each, the longer best wins */
    gumfling_init(&f);
    gumfling_add_p2(&f);
    { int turns[6], k;
      for (k = 0; k < 6; k++) { turns[k] = f.seq.turn; shoot(&f, k & 1 ? 40 : 4, 48); fly(&f); if (k < 5) next(&f); }
      CHECK(turns[0] == 0 && turns[1] == 1 && turns[2] == 0 && turns[3] == 1 && turns[4] == 0 && turns[5] == 1);
      CHECK(f.phase == GF_LANDED && !f.more);
      for (k = 0; k < 400 && f.phase == GF_LANDED; k++) gumfling_step(&f, 0);
      CHECK(f.phase == GF_RESULT && (f.sfx & GF_SFX_WIN));
      CHECK(gumfling_winner(&f) == 1 && f.seq.best[1] > f.seq.best[0]);
      next(&f);
      CHECK(f.phase == GF_END); }

    /* aim preview: the path points are the real flight's positions, evenly in time, and the last one is the touch-down */
    {
        int16_t px[10], py[10];
        int mash = 20, hold = 40, frames, k, n = 0, t = 0;
        GgFling a;
        gumfling_init(&a);
        shoot(&a, mash, hold);
        CHECK(a.phase == GF_FLIGHT);
        frames = gumfling_path(a.power, (uint16_t)hold + 1, px, py, 10);   /* power is the counted presses, charge the frames of B held */
        CHECK(frames > 10 && px[9] > 0 && py[9] == 0);
        for (k = 0; k < frames && a.phase == GF_FLIGHT; k++) {
            gumfling_fly(&a); t++;
            if (n < 10 && t == frames * (n + 1) / 10) {
                CHECK(px[n] == (int16_t)(a.phase == GF_FLIGHT ? a.x >> 16 : a.dist) && py[n] == (int16_t)(a.h >> 16));
                n++;
            }
        }
        CHECK(n == 10 && a.phase == GF_LANDED && px[9] == (int16_t)a.dist);
        gumfling_init(&a); shoot(&a, 32, 40); gumfling_path(32, 41, px, py, 10);
        printf("path full power 56deg: last dx %d, apex dy %d\n", px[9], py[4]);
        gumfling_init(&a); shoot(&a, 20, 30); gumfling_path(20, 31, px, py, 10);
        printf("path mid: last dx %d, apex dy %d\n", px[9], py[4]);
    }

    /* range: the best angle at full power lands 400..470 px (inside the 512 px field) and passes the mark; half power falls short of it */
    {
        int16_t px[4], py[4];
        uint16_t c;
        int best_full = 0, best_half = 0, d;
        for (c = 1; c <= GF_AIM_CAP; c++) {
            if (gumfling_deg(c) < GF_DEG_MIN || gumfling_deg(c) > GF_DEG_MAX) continue;
            gumfling_path(GF_POWER_MAX, c, px, py, 4); d = px[3]; if (d > best_full) best_full = d;
            gumfling_path(GF_POWER_MAX / 2, c, px, py, 4); d = px[3]; if (d > best_half) best_half = d;
        }
        printf("best throw: full power %d px, half power %d px, mark %u px\n", best_full, best_half, (unsigned)GF_MARK_PX);
        CHECK(best_full >= 400 && best_full <= 470 && best_full >= (int)GF_MARK_PX);
        CHECK(best_half < (int)GF_MARK_PX);
    }

    /* flow: Left from Big Blow wraps to Gum Fling, Right from Gum Fling wraps to Big Blow; Start runs it */
    {
        Flow fl;
        flow_init(&fl, 0, 0);
        fl.mode = GAME_MODE_GUM; fl.gg_event = GG_BIG_BLOW;
        flow_coin(&fl);
        flow_step(&fl, IN_A, 0, 0); flow_step(&fl, 0, 0, 0); /* A opens the GUM GAMES list */
        flow_step(&fl, IN_UP, 0, 0); flow_step(&fl, 0, 0, 0);
        CHECK(fl.gg_event == GG_FLING);
        flow_step(&fl, IN_DOWN, 0, 0); flow_step(&fl, 0, 0, 0);
        CHECK(fl.gg_event == GG_BIG_BLOW);
        for (i = 0; i < 5; i++) { flow_step(&fl, IN_DOWN, 0, 0); flow_step(&fl, 0, 0, 0); }
        CHECK(fl.gg_event == GG_FLING);
        flow_step(&fl, 0, 1, 1);
        CHECK(fl.state == FLOW_PLAYING && fl.game.gg_fling && fl.game.players == 1);
    }

    puts(fails ? "FAIL test_gg_fling" : "PASS test_gg_fling");
    return fails != 0;
}
