#include "laser_view.h"

int laser_view_beam(const Game *g, int i, int *x, int *y)
{
    const Bolt *b;
    if (i < 0 || i >= MAX_BOLTS || !g->bolts[i].active) {
        return 0;
    }
    b = &g->bolts[i];
    *x = (b->x >> 8) + LASER_W - LV_BEAM_W;
    *y = b->y + (LASER_H - LV_BEAM_H) / 2;
    return 1;
}

int laser_view_flash(const Game *g, int *cx, int *cy, int *frame)
{
    uint32_t age;
    if (g->kills == 0) {
        return 0;
    }
    age = g->frame - g->kill_frame;
    if (age >= (uint32_t)(LV_FLASH_FRAMES * LV_FLASH_TICKS)) {
        return 0;
    }
    *cx = g->kill_x;
    *cy = g->kill_y;
    *frame = (int)(age / LV_FLASH_TICKS);
    return 1;
}

LaserPose laser_view_pose(const Game *g)
{
    if (g->shots == 0 || g->fire_cd == 0) {
        return LV_POSE_NONE;
    }
    return g->fire_cd > LASER_FIRE_INTERVAL / 2 ? LV_POSE_RECOIL : LV_POSE_SHOOT;
}

int laser_view_cells(uint16_t heat)
{
    int n = (int)(((uint32_t)heat * LV_BAR_CELLS + HEAT_MAX - 1) / HEAT_MAX);
    return n > LV_BAR_CELLS ? LV_BAR_CELLS : n;
}

int laser_view_bar_frame(const Game *g, int pair)
{
    int fill = laser_view_cells(g->heat) - 2 * pair;
    fill = fill < 0 ? 0 : (fill > 2 ? 2 : fill);
    return pair * 3 + fill;
}

int laser_view_bar_visible(const Game *g)
{
    return g->lockout == 0 || ((g->lockout / LV_BAR_BLINK) & 1) == 0;
}
