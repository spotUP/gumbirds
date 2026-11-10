#ifndef BG_STARS_H
#define BG_STARS_H
/* Star layer constants shared by src/bg.c and tests/mame/autoanim_probe.c (make test-autoanim). */
#define BG_STAR_STEP_FRAMES 6 /* video frames per auto-animation step; a star cycle is 8 steps */
/* Star pixel positions; same list as STARS in assets/city/draw_city.py. */
#define BG_STAR_POSITIONS \
    {12, 34}, {30, 70}, {52, 30}, {70, 84}, {96, 40}, {118, 66}, {134, 32}, {150, 56}, \
    {172, 38}, {186, 74}, {200, 30}, {214, 58}, {292, 36}, {304, 80}, {8, 92}, {160, 86}
#endif
