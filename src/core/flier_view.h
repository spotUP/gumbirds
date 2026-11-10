/*
 * flier_view.h - which Sootling frame a flier shows. Pure, host tested (tests/host/test_flier_view.c); the Neo Geo
 * glue in src/main.c turns the pose into sprite registers. Pose numbers are the frame order of the source sheet
 * (assets/flier/sootling_sheet.json, tools/import_flier_sheet.py); src/main.c asserts the counts match the generated set.
 *   2 balloons: glide, up, down    1 balloon: glide, up    0 balloons: glide    falling or dead: fall
 * Up = flapping (button held) or rising in the air; down = sinking in the air with 2 balloons (1 and 0 balloons
 * have no down frame and glide). On the ground: glide. The sprite is mirrored when the flier faces left.
 */
#ifndef ROOFLINE_FLIER_VIEW_H
#define ROOFLINE_FLIER_VIEW_H

#include "flier.h"

typedef enum {
    FV_GLIDE2 = 0, FV_UP2, FV_DOWN2, FV_GLIDE1, FV_UP1, FV_GLIDE0, FV_FALL, FV_POSE_COUNT
} FlierPose;

/* Pose for the flier; *flip is 1 when the sprite must be mirrored (facing left), else 0. */
FlierPose flier_view_pose(const Flier *f, int *flip);

#endif
