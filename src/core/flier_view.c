#include "flier_view.h"

void flier_anim_init(FlierAnim *a)
{
    a->clip = a->frame = a->tick = a->balloons = a->started = a->prev_ground = a->flapping = 0;
}

static void play(FlierAnim *a, uint8_t clip)
{
    a->clip = clip;
    a->frame = 0;
    a->tick = 0;
    a->flapping = 0;
}

static uint8_t count_idx(const Flier *f)
{
    return f->balloons > 2 ? 2 : f->balloons;
}

static int in_set(const uint8_t *set, uint8_t clip)
{
    return clip == set[0] || clip == set[1] || clip == set[2];
}

static uint8_t steady_clip(const Flier *f, const FlierClips *c)
{
    uint8_t b = count_idx(f);
    if (f->state >= FLIER_FALLING) return c->fall;
    if (f->on_ground) {
        int32_t vx = f->vx < 0 ? -f->vx : f->vx;
        return vx >= FLIER_WALK_MIN_VX ? c->walk[b] : c->breathe[b];
    }
    if (b == 0) return c->idle;
    return b == 1 ? c->flap1 : c->flap2;
}

/* Ticks the frame of a clip is shown. The ground clips and the flap clips read their knobs; every other clip keeps the
 * per frame ticks of the sheet. */
static uint8_t hold_of(const FlierClips *c, uint8_t clip, uint8_t frame, uint8_t shown)
{
    static const uint8_t breathe[4] = { FLIER_BREATHE_HOLD_0, FLIER_BREATHE_HOLD_1, FLIER_BREATHE_HOLD_2, FLIER_BREATHE_HOLD_3 };
    if (in_set(c->walk, clip)) return FLIER_WALK_HOLD;
    if (in_set(c->land, clip)) return frame == 0 ? FLIER_LAND_HOLD_0 : FLIER_LAND_HOLD_1;
    if (in_set(c->breathe, clip)) return breathe[frame > 3 ? 3 : frame];
    if (clip == c->flap1 || clip == c->flap2) return FLIER_FLAP_HOLD;
    return c->ticks[shown];
}

uint8_t flier_anim_step(FlierAnim *a, const Flier *f, const FlierClips *c, int *flip)
{
    uint8_t steady = steady_clip(f, c);
    uint8_t grounded = (uint8_t)(f->on_ground && f->state == FLIER_ALIVE);
    *flip = !f->facing;
    if (!a->started) {
        a->started = 1;
        play(a, f->balloons ? c->inflate : steady);
    } else if (f->balloons > a->balloons) {
        play(a, c->inflate);
    } else if (f->balloons < a->balloons) {
        play(a, (a->balloons == 2 && f->balloons == 1) ? c->pop2 : c->pop1);
    } else if (grounded && !a->prev_ground) {
        play(a, c->land[count_idx(f)]);
    }
    a->balloons = f->balloons;
    a->prev_ground = grounded;
    if (a->clip == c->inflate && f->state >= FLIER_FALLING) play(a, steady);
    if (in_set(c->land, a->clip) && !grounded) play(a, steady); /* leaving the ground cuts a landing */
    if (c->loop[a->clip] && a->clip != steady) play(a, steady);
    if (a->clip == c->flap1 || a->clip == c->flap2) {
        if (f->flapped) {
            play(a, a->clip); /* a press restarts the wingbeat */
            a->flapping = 1;
        } else if (!a->flapping) {
            return c->first[a->clip]; /* rest frame between presses */
        }
    }
    {
        uint8_t shown = (uint8_t)(c->first[a->clip] + a->frame);
        if (++a->tick >= hold_of(c, a->clip, a->frame, shown)) {
            a->tick = 0;
            if (++a->frame >= c->count[a->clip]) {
                if (a->clip == c->flap1 || a->clip == c->flap2) {
                    a->frame = 0;
                    a->flapping = 0; /* one play per press: back to the rest frame */
                } else if (c->loop[a->clip]) {
                    a->frame = 0;
                } else {
                    play(a, steady);
                }
            }
        }
        return shown;
    }
}

int flier_body_visible(const Flier *f) {
    if (f->state == FLIER_GONE) return 0;
    return (int)((f->y + flier_half_h(f)) >> 16) - FLIER_ART_H < SCREEN_H;
}

int flier_body_front(const Flier *f) {
    return f->solid_kill && f->bounced && f->state >= FLIER_FALLING && flier_body_visible(f);
}

int flier_view_visible(const Flier *f, uint32_t frame) {
    if (!(f->invincible || f->spawn_inv) || f->state >= FLIER_FALLING) return 1;
    return ((frame / FLIER_BLINK_HALF_PERIOD) & 1u) == 0;
}
