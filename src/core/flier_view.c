#include "flier_view.h"

FlierPose flier_view_pose(const Flier *f, int *flip)
{
    int up;
    *flip = !f->facing;
    if (f->state >= FLIER_FALLING) {
        return FV_FALL;
    }
    if (f->balloons == 0) {
        return FV_GLIDE0;
    }
    up = !f->on_ground && (f->flap_prev || f->vy < 0);
    if (f->balloons == 1) {
        return up ? FV_UP1 : FV_GLIDE1;
    }
    if (up) {
        return FV_UP2;
    }
    return (!f->on_ground && f->vy > 0) ? FV_DOWN2 : FV_GLIDE2;
}
