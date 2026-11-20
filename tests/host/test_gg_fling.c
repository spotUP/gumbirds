/* test_gg_fling.c - Gum Games Gum Fling: angle mapping, fouls, ballistic landing, three attempts, best counts, qualifying mark, title pick. */
#include <stdio.h>
#include "game.h"
#include "flow.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

/* run-up: `mash` presses (A and B alternate, one every other frame) from the first frame, idle for the rest of the clock; ends in the
 * AIM phase. Then wait `wait` aim frames and press A; returns the event of the press frame. */
static int shoot(GgFling *f, int mash, int wait)
{
    int i;
    for (i = 0; i < (int)GF_WINDUP_FRAMES && f->phase == GF_WINDUP; i++)
        gumfling_step(f, (uint8_t)((i < 2 * mash && !(i & 1)) ? ((i & 2) ? IN_B : IN_A) : 0));
    for (i = 0; i < wait; i++) gumfling_step(f, 0);
    return gumfling_step(f, IN_A);
}

/* flight with a flap press every `period` frames (0 = none) */
static void fly_flap(GgFling *f, int period)
{
    int g;
    for (g = 0; g < 4000 && f->phase == GF_FLIGHT; g++) gumfling_fly(f, (uint8_t)(period && g % period == 0 ? ((g / period) & 1 ? IN_A : IN_B) : 0));
}
static void fly(GgFling *f) { fly_flap(f, 0); }

static void next(GgFling *f) { int g, ev = 0; for (g = 0; g < 1000 && ev != GF_EV_NEXT && f->phase != GF_END; g++) ev = gumfling_step(f, 0); }

int main(void)
{
    GgFling f;
    int i;

    /* aim angle: a triangle wave between the limits, one sweep in GF_AIM_SWEEP_FRAMES */
    CHECK(gumfling_deg(0) == GF_DEG_MIN && gumfling_deg(GF_AIM_SWEEP_FRAMES) == GF_DEG_MAX && gumfling_deg(2 * GF_AIM_SWEEP_FRAMES) == GF_DEG_MIN);
    for (i = 0; i < 1000; i++) CHECK(gumfling_deg((uint16_t)i) >= GF_DEG_MIN && gumfling_deg((uint16_t)i) <= GF_DEG_MAX);
    CHECK(gumfling_deg(GF_AIM_SWEEP_FRAMES / 2) > GF_DEG_MIN && gumfling_deg(GF_AIM_SWEEP_FRAMES + 5) < GF_DEG_MAX);

    /* power freezes when the clock ends; the needle then swings on its own and stays in range */
    gumfling_init(&f);
    for (i = 0; i < (int)GF_WINDUP_FRAMES; i++) gumfling_step(&f, (uint8_t)((i & 1) ? 0 : IN_A));
    CHECK(f.phase == GF_AIM && f.power > 0 && f.power < GF_POWER_MAX);
    { uint8_t p0 = f.power, lo = 255, hi = 0;
      for (i = 0; i < 2 * (int)GF_AIM_SWEEP_FRAMES; i++) {
          gumfling_step(&f, (uint8_t)((i & 1) ? 0 : IN_B));   /* B does not stop it, and presses no longer add power */
          if (f.deg < lo) lo = f.deg;
          if (f.deg > hi) hi = f.deg;
      }
      CHECK(f.phase == GF_AIM && f.power == p0 && lo == GF_DEG_MIN && hi == GF_DEG_MAX); }

    /* slow mashing cannot top out: the power drains */
    gumfling_init(&f);
    for (i = 0; i < (int)GF_WINDUP_FRAMES; i++) gumfling_step(&f, (uint8_t)(i % 60 == 0 ? IN_A : 0));
    CHECK(f.power < 4);
    /* frantic mashing tops out */
    gumfling_init(&f); shoot(&f, 180, 0);
    CHECK(f.power == GF_POWER_MAX);

    /* A stops the needle at the swinging angle and launches at once */
    gumfling_init(&f);
    CHECK(shoot(&f, 30, 10) == GF_EV_LAUNCH && !f.foul && f.phase == GF_FLIGHT && f.vx > 0 && f.vy > 0 && f.deg == gumfling_deg(10));
    fly(&f);
    CHECK(f.phase == GF_LANDED && f.dist > 0 && f.seq.best[0] == f.dist);

    /* no press: the throw goes at the current angle after the timeout */
    gumfling_init(&f);
    { int ev = 0;
      for (i = 0; i < (int)GF_WINDUP_FRAMES; i++) gumfling_step(&f, 0);
      for (i = 0; i < (int)GF_AIM_TIMEOUT_FRAMES + 2 && !ev; i++) ev = gumfling_step(&f, 0);
      CHECK(ev == GF_EV_LAUNCH && f.phase == GF_FLIGHT && !f.foul && f.deg == gumfling_deg(GF_AIM_TIMEOUT_FRAMES)); }

    /* more run-up power flies farther at the same angle */
    { GgFling a, b; gumfling_init(&a); gumfling_init(&b);
      shoot(&a, 4, 20); fly(&a); shoot(&b, 100, 20); fly(&b);
      CHECK(b.dist > a.dist); }

    /* three attempts, the best counts, then the end */
    gumfling_init(&f);
    shoot(&f, 4, 20); fly(&f); next(&f);
    CHECK(f.phase == GF_WINDUP);
    shoot(&f, 100, 20); fly(&f);
    { uint32_t best = f.dist; next(&f);
      shoot(&f, 2, 20); fly(&f);
      next(&f);
      CHECK(f.phase == GF_END && f.seq.best[0] == best); }

    /* a run-up with no useful input still ends in the aim (no foul) */
    gumfling_init(&f);
    for (i = 0; i < (int)GF_WINDUP_FRAMES + 5 && f.phase == GF_WINDUP; i++) gumfling_step(&f, IN_C);
    CHECK(f.phase == GF_AIM && !f.foul);

    /* sounds: a throw, a landing, a foul */
    gumfling_init(&f);
    f.sfx = 0; shoot(&f, 20, 10);
    CHECK(f.sfx & GF_SFX_THROW);
    f.sfx = 0; fly(&f);
    CHECK((f.sfx & GF_SFX_LAND) && !(f.sfx & GF_SFX_FOUL));

    /* solo: the result phase shows pass / fail, then the end; a pass plays the win sound */
    gumfling_init(&f);
    for (i = 0; i < 3; i++) { shoot(&f, 100, 20); fly(&f); f.sfx = 0; next(&f); }
    CHECK(f.phase == GF_END && f.seq.qualified[0] == (f.seq.best[0] >= GF_MARK_PX));

    /* 2P: turns alternate P1, P2, P1..., three throws each, the longer best wins */
    gumfling_init(&f);
    gumfling_add_p2(&f);
    { int turns[6], k;
      for (k = 0; k < 6; k++) { turns[k] = f.seq.turn; shoot(&f, k & 1 ? 100 : 4, 20); fly(&f); if (k < 5) next(&f); }
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
        int frames, k, n = 0, t = 0;
        GgFling a;
        gumfling_init(&a);
        shoot(&a, 20, 20);
        CHECK(a.phase == GF_FLIGHT);
        frames = gumfling_path(a.power, a.deg, px, py, 10);
        CHECK(frames > 10 && px[9] > 0 && py[9] == 0);
        for (k = 0; k < frames && a.phase == GF_FLIGHT; k++) {
            gumfling_fly(&a, 0); t++;
            if (n < 10 && t == frames * (n + 1) / 10) {
                CHECK(px[n] == (int16_t)(a.phase == GF_FLIGHT ? a.x >> 16 : a.dist) && py[n] == (int16_t)(a.h >> 16));
                n++;
            }
        }
        CHECK(n == 10 && a.phase == GF_LANDED && px[9] == (int16_t)a.dist);
    }

    /* range: the best angle at full power lands 400..470 px (inside the 512 px field) and passes the mark; half power falls short of it */
    {
        int16_t px[4], py[4];
        uint8_t d8;
        int best_full = 0, best_half = 0, d;
        for (d8 = GF_DEG_MIN; d8 <= GF_DEG_MAX; d8++) {
            gumfling_path(GF_POWER_MAX, d8, px, py, 4); d = px[3]; if (d > best_full) best_full = d;
            gumfling_path(GF_POWER_MAX / 2, d8, px, py, 4); d = px[3]; if (d > best_half) best_half = d;
        }
        printf("best throw: full power %d px, half power %d px, mark %u px\n", best_full, best_half, (unsigned)GF_MARK_PX);
        CHECK(best_full >= 400 && best_full <= 470 && best_full >= (int)GF_MARK_PX);
        CHECK(best_half < (int)GF_MARK_PX);
    }

    /* flapping in flight: A / B presses at a rate; only frantic mashing lengthens the flight (gain over the no-flap distance) */
    {
        static const int period[] = { 0, 12, 6, 4 };   /* none, 5, 10, 15 presses per second */
        uint32_t d0 = 0, d[4];
        int k;
        for (k = 0; k < 4; k++) {
            gumfling_init(&f); shoot(&f, 100, 20); fly_flap(&f, period[k]);
            d[k] = f.dist;
            if (!k) d0 = f.dist;
            printf("flap %2d/s: %u px, gain %d.%d%%\n", period[k] ? 60 / period[k] : 0, (unsigned)f.dist, (int)((d[k] - d0) * 100 / d0), (int)((d[k] - d0) * 1000 / d0 % 10));
        }
        CHECK(d[1] * 100 <= d0 * 103);
        CHECK(d[2] * 100 >= d0 * 110 && d[2] * 100 <= d0 * 115);
        CHECK(d[3] * 100 <= d0 * 122 && d[3] >= d[2]);
    }

    /* flight time: full power at 45 degrees stays up about 137 frames (about 205 before the 1.5 times speed-up) */
    {
        int16_t px[4], py[4];
        int frames = gumfling_path(GF_POWER_MAX, 45, px, py, 4);
        printf("full power flight: %d frames\n", frames);
        CHECK(frames >= 125 && frames <= 150);
    }

    /* power drain: one press lost per GF_POWER_DRAIN_FRAMES; mash at a steady rate for the run-up and see the bar */
    {
        int rates[] = { 5, 6, 7, 8, 10 }, r, t;
        for (r = 0; r < 5; r++) {
            int acc = 0, reached = -1;
            gumfling_init(&f);
            for (t = 0; t < (int)GF_WINDUP_FRAMES - 1; t++) {
                int press = 0;
                acc += 2 * rates[r];   /* two frames per loop */
                if (acc >= 60) { acc -= 60; press = 1; }
                gumfling_step(&f, press ? IN_A : 0);
                gumfling_step(&f, 0);   /* release between presses: every press is an edge (frame pairs, so the rate is per 2 frames) */
                t++;
                if (reached < 0 && f.power >= GF_POWER_MAX) reached = t;
            }
            printf("mash %d per s: power %u of %u, full at frame %d\n", rates[r], f.power, GF_POWER_MAX, reached);
            if (rates[r] == 5) CHECK(reached < 0 && f.power >= GF_POWER_MAX * 55 / 100 && f.power <= GF_POWER_MAX * 70 / 100);
            if (rates[r] == 8) CHECK(reached > 0 && reached <= 330);
        }
        /* idle bar drains back to zero, never below */
        gumfling_init(&f);
        for (i = 0; i < 6; i++) { gumfling_step(&f, IN_A); gumfling_step(&f, 0); }
        CHECK(f.power == 6);
        for (i = 0; i < 6 * (int)GF_POWER_DRAIN_FRAMES + 10; i++) gumfling_step(&f, 0);
        CHECK(f.power == 0);
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
