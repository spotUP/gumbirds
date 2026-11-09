/* Host tests for the laser view helper (src/core/laser_view.c) driven by the real core. */
#include <stdio.h>
#include "../../src/core/laser_view.h"

static int failures, checks;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static void place_drone(Game *g, int xpx)
{
    Obstacle *o = &g->obs[0];
    o->active = 1; o->type = OB_DRONE; o->w = DRONE_W; o->h = DRONE_H;
    o->y = GROUND_Y - DRONE_BOTTOM - DRONE_H; o->x = (int32_t)xpx << 8; o->near = o->tainted = 0;
}

int main(void)
{
    Game g;
    int x, y, f, i, lit;

    /* cells and frames */
    CHECK(laser_view_cells(0) == 0);
    CHECK(laser_view_cells(1) == 1);
    CHECK(laser_view_cells(HEAT_MAX) == LV_BAR_CELLS);
    CHECK(laser_view_cells(HEAT_MAX / 2) == LV_BAR_CELLS / 2);
    game_reset(&g, 7);
    CHECK(laser_view_bar_frame(&g, 0) == 0 && laser_view_bar_frame(&g, 7) == 21);
    g.heat = HEAT_MAX;
    CHECK(laser_view_bar_frame(&g, 0) == 2 && laser_view_bar_frame(&g, 7) == 23);
    g.heat = (uint16_t)(HEAT_MAX * 3 / LV_BAR_CELLS); /* 3 cells: tile 0 full, tile 1 half */
    CHECK(laser_view_bar_frame(&g, 0) == 2 && laser_view_bar_frame(&g, 1) == 4 && laser_view_bar_frame(&g, 2) == 6);

    /* firing: beam appears at the hero muzzle, pose cycles, heat rises monotonically to the lockout */
    game_reset(&g, 7);
    CHECK(!laser_view_beam(&g, 0, &x, &y) && laser_view_pose(&g) == LV_POSE_NONE);
    game_step(&g, IN_A);
    CHECK(laser_view_beam(&g, 0, &x, &y));
    CHECK(x + LV_BEAM_W > HERO_X && y > 0 && y < GROUND_Y);
    CHECK(laser_view_pose(&g) == LV_POSE_RECOIL);
    for (i = 0; i < LASER_FIRE_INTERVAL - 1; i++) game_step(&g, IN_A);
    for (i = 0; i < 400 && g.overheats == 0; i++) {
        lit = laser_view_cells(g.heat);
        CHECK(lit >= 0 && lit <= LV_BAR_CELLS);
        game_step(&g, IN_A);
    }
    CHECK(g.overheats == 1 && laser_view_cells(g.heat) == LV_BAR_CELLS);
    {   /* blink: both phases occur during the lockout, never outside it */
        int on = 0, off = 0;
        while (g.lockout) { if (laser_view_bar_visible(&g)) on++; else off++; game_step(&g, 0); }
        CHECK(on > 0 && off > 0);
        CHECK(laser_view_bar_visible(&g) && g.heat == 0);
    }

    /* kill: flash at the enemy centre, 4 frames of 3 ticks, then gone; score +200 */
    game_reset(&g, 7);
    place_drone(&g, 200);
    for (i = 0; i < 60 && g.kills == 0; i++) game_step(&g, IN_A);
    CHECK(g.kills == 1 && g.bonus == (uint32_t)KILL_SCORE);
    CHECK(laser_view_flash(&g, &x, &y, &f) && f == 0);
    CHECK(x == g.kill_x && y == g.kill_y && y > 0 && y < GROUND_Y);
    for (i = 0; i < LV_FLASH_TICKS; i++) game_step(&g, 0);
    CHECK(laser_view_flash(&g, &x, &y, &f) && f == 1);
    for (i = 0; i < LV_FLASH_FRAMES * LV_FLASH_TICKS; i++) game_step(&g, 0);
    CHECK(!laser_view_flash(&g, &x, &y, &f));
    game_reset(&g, 7);
    CHECK(!laser_view_flash(&g, &x, &y, &f));

    printf("%s: %d checks, %d failures\n", failures ? "FAIL" : "PASS", checks, failures);
    return failures != 0;
}
