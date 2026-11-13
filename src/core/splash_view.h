/*
 * splash_view.h - the splash a flier makes when it falls into water or lava. Pure, host tested (tests/host/test_splash_view.c);
 * src/splash.c turns it into sprite registers. One splash at a time: a new start restarts it at the new x. Sheet: 12 frames of
 * 48 x 48 per liquid (assets/splash/splash.json); sheet row SPLASH_SURFACE_ROW sits on the liquid surface line (kill line - HAZARD_DIP).
 */
#ifndef BRAWL_SPLASH_VIEW_H
#define BRAWL_SPLASH_VIEW_H

#include <stdint.h>
#include "tuning.h"
#include "hazard_kind.h"

#define SPLASH_FRAMES 12       /* sheet frames per liquid */
#define SPLASH_SURFACE_ROW 42  /* sheet row that lies on the liquid surface (assets/splash/splash.json) */
#define SPLASH_ANCHOR_X 24     /* sheet column that lies on the flier's x */

typedef struct { uint8_t active, kind; int32_t x; uint16_t t; } Splash;

/* Per game frame. start 0: advance a running splash (it ends after SPLASH_FRAMES sheet frames). start 1: begin (or restart) at world x
 * for a hazard kind; only HZ_WATER and HZ_LAVA start one, other kinds are ignored. */
void splash_step(Splash *s, int start, uint8_t kind, int32_t x);
/* Game frames per sheet frame of a liquid kind. */
uint8_t splash_ticks(uint8_t kind);
/* Sheet frame 0..SPLASH_FRAMES-1 of a running splash. */
uint8_t splash_frame(const Splash *s);
/* Screen line of the top of the 48 line cell for a liquid kind. */
int splash_top(uint8_t kind);

/* Whether the splash may run: while a game is on screen (running) and not in Gum Trip, which has no liquid for it to land on. */
int splash_enabled(int running, int trip);

#endif
