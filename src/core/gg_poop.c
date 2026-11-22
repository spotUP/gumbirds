#include "gg_poop.h"
#include "nameentry.h"   /* IN_UP.. */

static const uint8_t walker_h[4] = { 48, 40, 42, 30 };   /* hat, bald, woman, kid: cell height in px (draft v2 numbers) */
uint8_t gm_kind_mult(uint8_t kind) { return kind == PM_HAT ? 2 : kind == PM_BALD ? 3 : 1; }

static void bird_begin(PmBird *b, int x)
{
    b->x = (int16_t)x; b->y = 48; b->xf = b->yf = 0;
    b->flip = 0; b->streak = 0; b->stun = 0; b->prev_in = 0; b->drop_t = 0; b->score = 0;
    b->vy16 = 0; b->drop_cd = b->flap_cd = b->flap_t = b->dead = b->inv = 0;
}

void gm_init(GgPoop *p, uint32_t seed, uint8_t storm)
{
    int i;
    rng_seed(&p->rng, seed);
    gg_seq_start(&p->seq, GG_POOP_MAN, 1);
    p->seq.tickets[0] = 1;
    p->phase = PM_PLAY; p->done = 0; p->storm = storm;
    bird_begin(&p->b[0], 96); bird_begin(&p->b[1], 192);
    for (i = 0; i < PM_WALKERS; i++) p->w[i].live = 0;
    for (i = 0; i < PM_POOPS; i++) p->poop[i].live = 0;
    for (i = 0; i < PM_SHOES; i++) p->shoe[i].live = 0;
    p->sfx = p->splat_n = p->sfx_n = 0;
    p->timer = 0; p->end_t = 0; p->scroll = 0; p->last_hit_pts_ev = 0; p->last_pts = 0;
}

void gm_add_p2(GgPoop *p)
{
    p->seq.players = 2;
    p->seq.tickets[1] = 1;
}

static int walker_top(const PmWalker *w) { return PM_FEET_Y - walker_h[w->kind]; }
static int iabs(int v) { return v < 0 ? -v : v; }

static void spawn_walker(GgPoop *p)
{
    int i;
    for (i = 0; i < PM_WALKERS; i++) if (!p->w[i].live) {
        PmWalker *w = &p->w[i];
        w->live = 1; w->kind = (uint8_t)rng_range(&p->rng, 4); w->st = PM_WALK; w->t = 0; w->umb = 0; w->owner = 0;
        w->umb_prone = p->storm ? 1 : (uint8_t)(rng_range(&p->rng, 4) == 0);
        w->dx8 = (int16_t)(rng_range(&p->rng, 2) ? 6 : -6);
        w->x8 = (int16_t)((PM_W + 24) * 8);
        return;
    }
}

static void spawn_poop(GgPoop *p, int k, int vx16)
{
    int i;
    for (i = 0; i < PM_POOPS; i++) if (!p->poop[i].live) {
        PmPoop *o = &p->poop[i];
        o->live = 1; o->st = PM_POOP_FALL; o->t = 0; o->owner = (uint8_t)k;
        o->x16 = (int32_t)p->b[k].x * 16; o->y16 = (int32_t)(p->b[k].y + 8) * 16;
        o->vx16 = (int16_t)vx16; o->vy16 = 0;
        return;
    }
}

static int bird_hit(const PmBird *b, int x, int y) { return iabs(x - b->x) <= PM_BIRD_HALF_W && iabs(y - b->y) <= PM_BIRD_HALF_H; }

static void bird_kill(GgPoop *p, PmBird *b)
{
    b->dead = PM_DEAD_FRAMES; b->streak = 0; b->stun = 0; b->vy16 = -20; p->sfx |= PM_SFX_DEAD;
}

static void bird_step(GgPoop *p, int k, uint8_t in)
{
    PmBird *b = &p->b[k];
    int i, vx = PM_BIRD_VX;
    int flap = (in & IN_A) && !(b->prev_in & IN_A), drop = (in & IN_B) && !(b->prev_in & IN_B);
    if (b->drop_t && b->drop_t < 255) b->drop_t++;
    if (b->flap_t && b->flap_t < 255) b->flap_t++;
    if (b->drop_cd) b->drop_cd--;
    if (b->flap_cd) b->flap_cd--;
    if (b->inv) b->inv--;
    b->prev_in = in;
    if (b->dead) {   /* falls off screen, input ignored; the fall stops far below the view */
        b->vy16 = (int16_t)(b->vy16 + PM_GRAVITY > PM_FALL_MAX ? PM_FALL_MAX : b->vy16 + PM_GRAVITY);
        if (b->y < 300) { b->yf = (int16_t)(b->yf + b->vy16); b->y = (int16_t)(b->y + (b->yf >> 4)); b->yf &= 15; }
        if (--b->dead == 0) { b->y = PM_SPAWN_Y; b->yf = 0; b->vy16 = 0; b->inv = PM_INV_FRAMES; }
        return;
    }
    if (b->stun) { b->stun--; return; }
    if (in & IN_LEFT) vx = 8;
    if (in & IN_RIGHT) vx = 40;
    b->vy16 = (int16_t)(b->vy16 + PM_GRAVITY);
    if (flap && !b->flap_cd) { b->vy16 = -PM_FLAP_VY; b->flap_cd = PM_FLAP_CD; b->flap_t = 1; p->sfx |= PM_SFX_FLAP; }
    if (b->vy16 > PM_FALL_MAX) b->vy16 = PM_FALL_MAX;
    if (b->vy16 < -PM_RISE_MAX) b->vy16 = -PM_RISE_MAX;
    b->xf = (int16_t)(b->xf + vx); b->x = (int16_t)(b->x + (b->xf >> 4)); b->xf &= 15;
    if (b->x >= PM_W) b->x = (int16_t)(b->x - PM_W);
    b->yf = (int16_t)(b->yf + b->vy16); b->y = (int16_t)(b->y + (b->yf >> 4)); b->yf &= 15;   /* arithmetic shift: floor for negatives */
    if (b->y < PM_BIRD_Y_MIN) { b->y = PM_BIRD_Y_MIN; if (b->vy16 < 0) b->vy16 = 0; }
    if (b->y + PM_BIRD_HALF_H >= PM_FEET_Y) {   /* the pavement kills; invulnerable birds stop on it */
        if (b->inv) { b->y = (int16_t)(PM_FEET_Y - PM_BIRD_HALF_H); b->vy16 = 0; }
        else { bird_kill(p, b); return; }
    }
    if (!b->inv) for (i = 0; i < PM_WALKERS; i++) {
        const PmWalker *w = &p->w[i];
        if (w->live && iabs(b->x - (w->x8 >> 3)) <= PM_BIRD_HALF_W + PM_BODY_HALF_W && b->y + PM_BIRD_HALF_H >= walker_top(w)) { bird_kill(p, b); return; }
    }
    if (drop && !b->drop_cd) { b->drop_cd = PM_DROP_CD; b->drop_t = 1; spawn_poop(p, k, vx); }
}

static void poop_end_streak(GgPoop *p, const PmPoop *o) { p->b[o->owner].streak = 0; }

static void poop_step(GgPoop *p, PmPoop *o)
{
    int i, x, y;
    if (o->st == PM_POOP_SPLAT) { o->x16 -= PM_SCROLL * 16; if (++o->t >= PM_SPLAT_FRAMES) o->live = 0; return; }
    if (o->st == PM_POOP_BOUNCE) {   /* bounced off an umbrella: arcs up and away, harmless */
        o->vy16 = (int16_t)(o->vy16 + 4);
        o->x16 += o->vx16; o->y16 += o->vy16;
        if (++o->t > 20 || o->y16 > PM_PAVE_Y * 16) o->live = 0;
        return;
    }
    o->vy16 = (int16_t)(o->vy16 + 4 > 96 ? 96 : o->vy16 + 4);
    o->x16 += o->vx16;   /* screen space: the street scrolls under it via the walkers */
    o->y16 += o->vy16;
    x = (int)(o->x16 >> 4); y = (int)(o->y16 >> 4);
    for (i = 0; i < PM_WALKERS; i++) {
        PmWalker *w = &p->w[i];
        int wx = w->x8 >> 3, top;
        if (!w->live || w->st != PM_WALK || iabs(x - wx) > (w->umb ? PM_UMB_HALF_W : PM_HEAD_HALF_W)) continue;
        top = walker_top(w);
        if (w->umb && y >= top - PM_UMB_Y && y <= top - PM_UMB_Y + PM_UMB_H) {
            o->st = PM_POOP_BOUNCE; o->t = 0; o->vy16 = -40; o->vx16 = (int16_t)(x < wx ? -16 : 16);
            poop_end_streak(p, o);
            p->sfx |= PM_SFX_BOUNCE; p->sfx_n++;
            return;
        }
        if (iabs(x - wx) <= PM_HEAD_HALF_W && y >= top && y <= top + PM_HEAD_H) {
            PmBird *b = &p->b[o->owner];
            uint32_t pts;
            if (b->streak < 255) b->streak++;
            pts = PM_BASE * gm_kind_mult(w->kind) * (b->streak > PM_COMBO_CAP ? PM_COMBO_CAP : b->streak);
            b->score += pts; p->last_pts = pts; p->last_hit_b = o->owner; p->last_hit_pts_ev = 1;
            w->st = PM_HIT; w->t = 0; w->umb = 0; w->owner = o->owner; p->splat_n++;
            o->live = 0;
            return;
        }
    }
    if (y >= PM_PAVE_Y && x >= -16 && x <= PM_W + 16) { poop_end_streak(p, o); o->st = PM_POOP_SPLAT; o->t = 0; o->y16 = PM_PAVE_Y * 16; p->splat_n++; return; }
    if (x < -16 || x > PM_W + 16) { poop_end_streak(p, o); o->live = 0; }
}

static void walker_step(GgPoop *p, PmWalker *w)
{
    int i, wx, near = 0;
    w->x8 = (int16_t)(w->x8 + w->dx8 - PM_SCROLL * 8);
    wx = w->x8 >> 3;
    if (wx < -24) { w->live = 0; return; }
    w->t++;
    if (w->st == PM_WALK) {
        if (w->umb_prone) {
            for (i = 0; i < p->seq.players; i++) near |= iabs(p->b[i].x - wx) <= PM_UMB_RANGE + (w->umb ? 16 : 0);
            w->umb = (uint8_t)near;
        }
    } else if (w->st == PM_HIT && w->t >= PM_HIT_FRAMES) {
        w->t = 0;
        if (rng_range(&p->rng, 2)) {   /* throw a shoe up at the bird that hit it */
            for (i = 0; i < PM_SHOES; i++) if (!p->shoe[i].live) {
                PmShoe *s = &p->shoe[i];
                int tx = p->b[w->owner].x;
                s->live = 1; s->x = (int16_t)wx; s->y = (int16_t)(walker_top(w) - 4); s->vy = -4;
                s->vx = (int8_t)(tx > wx + 8 ? 1 : tx < wx - 8 ? -1 : 0);
                break;
            }
            w->st = PM_THROW;
        } else w->st = PM_FIST;
    } else if ((w->st == PM_FIST || w->st == PM_THROW) && w->t >= PM_ANGRY_FRAMES) { w->st = PM_WALK; w->t = 0; }
}

static void shoe_step(GgPoop *p, PmShoe *s)
{
    int i;
    s->x = (int16_t)(s->x + s->vx); s->y = (int16_t)(s->y + s->vy);
    for (i = 0; i < p->seq.players; i++) if (!p->b[i].stun && !p->b[i].dead && !p->b[i].inv && bird_hit(&p->b[i], s->x, s->y)) {
        p->b[i].stun = PM_STUN; p->b[i].streak = 0; s->live = 0; return;
    }
    if (s->y < -16) s->live = 0;
}

static void end_event(GgPoop *p)
{
    int i;
    for (i = 0; i < p->seq.players; i++) {
        uint32_t st = p->b[i].score / PM_BASE;
        p->seq.turn = (uint8_t)i;   /* gg_seq_attempt books into the current turn */
        gg_seq_attempt(&p->seq, p->b[i].score, (uint8_t)(st > 255 ? 255 : st), p->b[i].score >= 1000u);
    }
    p->phase = PM_RESULT; p->end_t = 0;
}

int gm_step(GgPoop *p, uint8_t in1, uint8_t in2)
{
    int i, n = p->seq.players == 2 ? 2 : 1;
    p->last_hit_pts_ev = 0;
    if (p->phase == PM_RESULT) {
        if (++p->end_t >= PM_RESULT_FRAMES) { p->phase = PM_DONE; p->done = 1; return 1; }
        return 0;
    }
    if (p->phase != PM_PLAY) return 0;
    p->scroll = (uint16_t)(p->scroll + PM_SCROLL);
    if (p->timer % PM_SPAWN_EVERY == 0) spawn_walker(p);
    bird_step(p, 0, in1);
    if (n == 2) bird_step(p, 1, in2);
    for (i = 0; i < PM_WALKERS; i++) if (p->w[i].live) walker_step(p, &p->w[i]);
    for (i = 0; i < PM_POOPS; i++) if (p->poop[i].live) poop_step(p, &p->poop[i]);
    for (i = 0; i < PM_SHOES; i++) if (p->shoe[i].live) shoe_step(p, &p->shoe[i]);
    if (++p->timer >= PM_CLOCK) end_event(p);
    return 0;
}
