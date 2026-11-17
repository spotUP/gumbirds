#ifndef GG_FLAPDASH_H
#define GG_FLAPDASH_H
#include <stdint.h>
#include "flier.h"
#include "gumgames.h"

/* Gum Games event Flap Dash (pure logic): mash A/B to flap the hero around the 384 px arena ring for GD_LAPS laps.
 * Record = frames from the first frame to the finish (lower is better). */
#define GD_LAPS 3u
#define GD_MAX_VX FL_PX(2)             /* CAM_MAX_STEP_PX: above this the bird outruns the camera */
#define GD_FLOOR_Y FL_PX(190)          /* surface under the hero's feet */
#define GD_MARK_FRAMES 1500u           /* qualifying time on the first medley loop (25 s; the cap alone needs about 580) */
#define GD_RESULT_FRAMES 150u          /* result screen after the finish, then the event is over (one run, no retry) */
#define GD_MARK_MIN 700u               /* floor of the tightened mark: the top air speed alone needs about 690 */

typedef struct {
    GgMash mash;
    uint8_t prev_in, laps, done, end_t;   /* end_t: frames shown on the result after the finish */
    uint32_t frames;
    int32_t lap_dist;                  /* 16.16 px travelled in the current lap, 0..ARENA_W16 */
} GgDash;

/* Place the hero at the start line and clear the run. */
void gumdash_init(GgDash *d, Flier *hero);
/* One frame. dir is forced to +1, A/B alternation is the flap. Returns 1 on the frame the last lap completes (and keeps returning 0 after). */
int gumdash_step(GgDash *d, Flier *hero, uint8_t in);
/* Qualifying time in frames on medley loop `loop` (0 = first): 5% tighter each loop. */
uint32_t gumdash_mark(uint32_t loop);
#endif
