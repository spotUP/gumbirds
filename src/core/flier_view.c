#include "flier_view.h"
#include "fastdiv.h"

void flier_anim_init(FlierAnim *a)
{
    a->clip = a->frame = a->tick = a->balloons = a->started = a->prev_ground = a->facing = 0;
    a->sway_clip = a->sway_frame = a->sway_tick = 0;
}

static void play(FlierAnim *a, uint8_t clip)
{
    a->clip = clip;
    a->frame = 0;
    a->tick = 0;
}

static uint8_t steady_clip(const Flier *f, const FlierClips *c)
{
    if (f->state >= FLIER_FALLING) return c->fall;
    if (f->on_ground) {
        int32_t vx = f->vx < 0 ? -f->vx : f->vx;
        if (vx >= FLIER_WALK_MIN_VX) return c->walk; /* walking stays side-on */
        return f->balloons == 0 ? c->breathe_front : c->breathe;
    }
    return f->balloons == 0 ? c->idle : c->fly;
}

/* Ticks the frame of a clip is shown. The ground clips read their knobs; every other clip keeps the per frame ticks of
 * the sheet. */
static uint8_t hold_of(const FlierClips *c, uint8_t clip, uint8_t frame, uint8_t shown)
{
    static const uint8_t breathe[4] = { FLIER_BREATHE_HOLD_0, FLIER_BREATHE_HOLD_1, FLIER_BREATHE_HOLD_2, FLIER_BREATHE_HOLD_3 };
    if (clip == c->walk) return FLIER_WALK_HOLD;
    if (clip == c->land) return frame == 0 ? FLIER_LAND_HOLD_0 : FLIER_LAND_HOLD_1;
    if (clip == c->breathe) return breathe[frame > 3 ? 3 : frame];
    return c->ticks[shown];
}

uint8_t flier_anim_step_n(FlierAnim *a, const Flier *f, const FlierClips *c, int *flip, int ticks)
{
    uint8_t steady = steady_clip(f, c);
    uint8_t grounded = (uint8_t)(f->on_ground && f->state == FLIER_ALIVE);
    uint8_t facing = (uint8_t)(f->facing != 0);
    *flip = !f->facing;
    if (!a->started) {
        a->started = 1;
        a->facing = facing;
        play(a, f->balloons ? c->inflate : steady);
    } else if (f->balloons > a->balloons) {
        play(a, c->inflate);
    } else if (f->balloons < a->balloons) {
        play(a, (a->balloons == 2 && f->balloons == 1) ? c->pop2 : c->pop1);
    } else if (grounded && !a->prev_ground) {
        play(a, c->land);
    } else if (f->flapped && steady == c->fly && (a->clip == c->fly || a->clip == c->flap || a->clip == c->settle)) {
        if (a->clip != c->flap) { /* the sway keeps its phase under the wingbeat */
            a->sway_clip = a->clip;
            a->sway_frame = a->frame;
            a->sway_tick = a->tick;
        }
        play(a, c->flap); /* a press restarts the wingbeat */
    }
    if (facing != a->facing && steady == c->fly) {
        if (a->clip == c->flap) { /* a turn under a wingbeat: the sway starts below it */
            a->sway_clip = c->settle;
            a->sway_frame = a->sway_tick = 0;
        } else if (a->clip == c->fly || a->clip == c->settle) {
            play(a, c->settle); /* a turn in the air: the damped sway, mirrored by the flip */
        }
    }
    a->facing = facing;
    a->balloons = f->balloons;
    a->prev_ground = grounded;
    if (a->clip == c->inflate && f->state >= FLIER_FALLING) play(a, steady);
    if (a->clip == c->land && !grounded) play(a, steady); /* leaving the ground cuts a landing */
    if ((a->clip == c->flap || a->clip == c->settle) && steady != c->fly) play(a, steady);
    if (c->loop[a->clip] && a->clip != steady) play(a, steady);
    {
        uint8_t first = (uint8_t)(c->first[a->clip] + a->frame);
        int t;
        for (t = 0; t < ticks; t++) { /* ticks > 1: a staggered rival advances several ticks on its frame; the checks above ran once */
        uint8_t shown = (uint8_t)(c->first[a->clip] + a->frame);
        if (a->clip == c->flap) { /* the wingbeat shows on the body the sway has now, and the sway runs on */
            uint8_t s = (uint8_t)(c->first[a->sway_clip] + a->sway_frame);
            if (c->sway[s]) shown = (uint8_t)(c->first[c->sway[s] == 1 ? c->flap_r : c->flap_l] + a->frame);
            if (t == 0) first = shown;
            if (++a->sway_tick >= c->ticks[s]) {
                a->sway_tick = 0;
                if (++a->sway_frame >= c->count[a->sway_clip]) { /* fly loops; settle ends into fly */
                    a->sway_clip = c->fly;
                    a->sway_frame = 0;
                }
            }
        }
        if (++a->tick >= hold_of(c, a->clip, a->frame, shown)) {
            a->tick = 0;
            if (++a->frame >= c->count[a->clip]) {
                if (c->loop[a->clip]) a->frame = 0;
                else if (a->clip == c->flap) { /* back to the sway where it is now */
                    a->clip = a->sway_clip;
                    a->frame = a->sway_frame;
                    a->tick = a->sway_tick;
                } else play(a, steady);
            }
        }
        }
        return first;
    }
}

uint8_t flier_anim_step(FlierAnim *a, const Flier *f, const FlierClips *c, int *flip)
{
    return flier_anim_step_n(a, f, c, flip, 1);
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

int flier_gum_burst(const Flier *f) { return f->balloons == 0 && (f->state >= FLIER_FALLING || f->state == FLIER_PARACHUTE); }

uint8_t flier_pump_frame(const FlierClips *c, int progress)
{
    int n = c->count[c->pump], p = progress < 0 ? 0 : (progress > ARC_PUMP_STAGES - 1 ? ARC_PUMP_STAGES - 1 : progress);
    int x = fd_mul16(p, n - 1), q = 0;
    while (x >= ARC_PUMP_STAGES - 1) { x -= ARC_PUMP_STAGES - 1; q++; } /* x / (STAGES - 1) without a libgcc divide: per pumping rival per frame */
    return (uint8_t)(c->first[c->pump] + q);
}
