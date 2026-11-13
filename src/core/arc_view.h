/*
 * arc_view.h - which art piece, frame and position each arcade stage element is drawn with (pure logic, C99, host testable).
 * main.c turns the blocks into sprite strips (ARC_ELEM_SPRITE slots) and checks the sizes below against the generated art tables.
 * Positions are world pixels of the block's top left corner; the glue adds the frame's pad and the camera.
 * Only element set A is drawn. Smoke and air particles are not drawn (no sprite slots left for them).
 */
#ifndef BRAWL_ARC_VIEW_H
#define BRAWL_ARC_VIEW_H

#include <stdint.h>
#include "arc_elements.h"
#include "arcade.h"

typedef enum { ARCV_BODY = 0, ARCV_SPARK, ARCV_FLIPPER, ARCV_GRABBER, ARCV_HATCH, ARCV_PIECES } ArcViewPiece;

typedef struct { uint8_t piece; uint8_t frame; int16_t x, y; } ArcSprite;   /* frame: index inside the piece's frame run */

#define ARC_VIEW_MAX (2 * ARC_ELEM_MAX)   /* a body plus a spark per element at most */
#define ARC_VIEW_SPARK_TICKS 4            /* ticks per spark frame (art table, asserted in main.c) */
#define ARC_VIEW_FLIP_TICKS 4             /* ticks per flipper frame */

/* Source art size in px (asserted against the generated ARCADE_*_ART_W/H in main.c) and sprite columns (16 px each). */
static const uint8_t ARC_VIEW_W[ARCV_PIECES] = { 32, 16, 40, 40, 32 };
static const uint8_t ARC_VIEW_H[ARCV_PIECES] = { 16, 16, 40, 44, 16 };
static const uint8_t ARC_VIEW_COLS[ARCV_PIECES] = { 2, 1, 3, 3, 2 };

/* Fills out[] (bodies first, then sparks) and returns the count. tick drives the flipper turn. */
int arc_view_build(const ArcElements *a, unsigned tick, ArcSprite *out);
/* Bonus stage bubbles: the Gum Trip pickup art (32 x 32 sprite, 2 columns, 16 idle frames; main.c asserts the sizes). For these blocks piece is the
 * bubble index (0..ARC_BONUS_BUBBLES-1, so a bubble keeps its sprite slot while the others come and go) and x, y are the sprite's top left in
 * world px: the 16 px catch box sits 8 px right of the sprite left and 12 px below its top, like the pickup in Gum Trip. */
#define ARC_VIEW_BUBBLE_FRAMES 16
#define ARC_VIEW_BUBBLE_LEFT_OFF 8
#define ARC_VIEW_BUBBLE_TOP_OFF 12
/* Fills out[ARC_BONUS_BUBBLES] with the rising bubbles (live only) and returns the count. */
int arc_view_bonus_build(const ArcBonus *b, ArcSprite *out);

/* Sprite columns that cover scanline y (0..223) when the first n blocks are drawn. */
int arc_view_line(const ArcSprite *s, int n, int y);

#endif
