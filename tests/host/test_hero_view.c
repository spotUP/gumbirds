/* Host tests for the hero look after a hit (src/core/hero_view.c) driven by the real core. */
#include <stdio.h>
#include "../../src/core/hero_view.h"

static int failures, checks;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

int main(void)
{
    Game g;
    int vis, i, hit_frame = -1;
    HeroLook look;

    /* no hit: normal pose, visible */
    game_reset(&g, 7);
    look = hero_view_look(&g, &vis);
    CHECK(g.invuln == 0 && look == HV_LOOK_NORMAL && vis == 1);

    /* run into the first obstacle with the real core: the frame invuln is set is frame 0 of the look */
    for (i = 0; i < 3000 && hit_frame < 0; i++) {
        game_step(&g, 0);
        if (g.invuln == INVULN_FRAMES) hit_frame = i;
    }
    CHECK(hit_frame >= 0);
    for (i = 0; i < INVULN_FRAMES; i++) {
        int want_vis;
        look = hero_view_look(&g, &vis);
        if (i < HIT_POSE_FRAMES) {
            CHECK(look == HV_LOOK_HIT && vis == 1);
        } else {
            want_vis = (((i - HIT_POSE_FRAMES) / HIT_BLINK_FRAMES) & 1) == 0;
            CHECK(look == HV_LOOK_NORMAL && vis == want_vis);
        }
        game_step(&g, 0); /* a second hit would reset invuln; the hero is invulnerable meanwhile */
    }
    look = hero_view_look(&g, &vis);
    CHECK(g.invuln == 0 && look == HV_LOOK_NORMAL && vis == 1);

    /* both blink phases occur, and the first blink phase is visible */
    g.invuln = (uint16_t)(INVULN_FRAMES - HIT_POSE_FRAMES);
    hero_view_look(&g, &vis); CHECK(vis == 1);
    g.invuln = (uint16_t)(INVULN_FRAMES - HIT_POSE_FRAMES - HIT_BLINK_FRAMES);
    hero_view_look(&g, &vis); CHECK(vis == 0);

    printf("hero_view: %d checks, %d failures\n", checks, failures);
    return failures != 0;
}
