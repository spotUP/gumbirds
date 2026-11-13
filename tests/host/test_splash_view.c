/* splash_view: sheet frame per game frame, end of the animation, restart at a new x, only liquids start one, placement. */
#include <stdio.h>
#include "../../src/core/splash_view.h"
#include "../../src/core/sound_events.h"

static int bad;
static void check(int ok, const char *what, int got, int want)
{
    if (!ok) { printf("FAIL %s: got %d, want %d\n", what, got, want); bad++; }
}

int main(void)
{
    uint8_t k;
    check(splash_enabled(1, 0) == 1 && splash_enabled(0, 0) == 0, "arena splash follows the running game", splash_enabled(1, 0), 1);
    check(splash_enabled(1, 1) == 0, "no splash in Gum Trip (no liquid)", splash_enabled(1, 1), 0);
    int t, ticks;
    Splash s = {0};
    check(SPLASH_TICKS == 3 && SPLASH_LAVA_TICKS == 4, "tuning defaults", SPLASH_TICKS, 3);
    for (k = HZ_WATER; k <= HZ_LAVA; k++) {
        ticks = splash_ticks(k);
        check(ticks == (k == HZ_LAVA ? 4 : 3), "ticks per liquid", ticks, k == HZ_LAVA ? 4 : 3);
        s.active = 0;
        splash_step(&s, 0, k, 0);
        check(!s.active, "idle splash stays idle", s.active, 0);
        splash_step(&s, 1, k, 300);
        check(s.active && s.x == 300 && s.kind == k && splash_frame(&s) == 0, "start", s.active, 1);
        for (t = 1; t < SPLASH_FRAMES * ticks; t++) {
            splash_step(&s, 0, k, 0);
            check(s.active, "runs until the last tick", t, SPLASH_FRAMES * ticks - 1);
            check(splash_frame(&s) == t / ticks, "sheet frame", splash_frame(&s), t / ticks);
        }
        check(splash_frame(&s) == SPLASH_FRAMES - 1, "last sheet frame shown", splash_frame(&s), SPLASH_FRAMES - 1);
        splash_step(&s, 0, k, 0);
        check(!s.active, "done after frames * ticks", s.active, 0);
        /* restart while running moves it to the new x and rewinds */
        splash_step(&s, 1, k, 100);
        for (t = 0; t < 10; t++) splash_step(&s, 0, k, 0);
        splash_step(&s, 1, k, 500);
        check(s.active && s.x == 500 && s.t == 0 && splash_frame(&s) == 0, "restart at new x", s.x, 500);
    }
    /* spikes and fire make none; a running splash is not disturbed by them */
    s.active = 0;
    splash_step(&s, 1, HZ_SPIKES, 10); check(!s.active, "spikes start none", s.active, 0);
    splash_step(&s, 1, HZ_FIRE, 10);   check(!s.active, "fire starts none", s.active, 0);
    splash_step(&s, 1, HZ_WATER, 70);
    splash_step(&s, 1, HZ_FIRE, 10);
    check(s.active && s.x == 70 && s.kind == HZ_WATER, "fire leaves a running splash alone", s.x, 70);
    /* placement: sheet row 42 on the surface line (kill line - dip): water 204 -> 162, lava 202 -> 160 */
    check(splash_top(HZ_WATER) == 162, "water cell top", splash_top(HZ_WATER), 162);
    check(splash_top(HZ_LAVA) == 160, "lava cell top", splash_top(HZ_LAVA), 160);
    check(splash_top(HZ_WATER) + SPLASH_SURFACE_ROW == hazard_kill_px(HZ_WATER) - HAZARD_DIP, "water surface row on the surface", 0, 1);
    printf("%s splash_view\n", bad ? "FAIL" : "PASS");
    return bad != 0;
}
