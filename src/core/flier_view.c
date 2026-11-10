#include "flier_view.h"

void flier_anim_init(FlierAnim *a)
{
    a->clip = a->frame = a->tick = a->balloons = a->started = 0;
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
    if (f->balloons == 0) return c->idle;
    return f->balloons == 1 ? c->flap1 : c->flap2;
}

uint8_t flier_anim_step(FlierAnim *a, const Flier *f, const FlierClips *c, int *flip)
{
    uint8_t steady = steady_clip(f, c);
    *flip = !f->facing;
    if (!a->started) {
        a->started = 1;
        play(a, f->balloons ? c->inflate : steady);
    } else if (f->balloons > a->balloons) {
        play(a, c->inflate);
    } else if (f->balloons < a->balloons) {
        play(a, (a->balloons == 2 && f->balloons == 1) ? c->pop2 : c->pop1);
    }
    a->balloons = f->balloons;
    if (a->clip == c->inflate && f->state >= FLIER_FALLING) play(a, steady);
    if (c->loop[a->clip]) {
        if (a->clip != steady) play(a, steady);
        if ((a->clip == c->flap2 || a->clip == c->flap1) && f->on_ground) {
            a->frame = 0;
            a->tick = 0;
            return (uint8_t)(c->first[a->clip]);
        }
    }
    {
        uint8_t shown = (uint8_t)(c->first[a->clip] + a->frame);
        if (++a->tick >= c->ticks[shown]) {
            a->tick = 0;
            if (++a->frame >= c->count[a->clip]) {
                if (c->loop[a->clip]) a->frame = 0;
                else play(a, steady);
            }
        }
        return shown;
    }
}
