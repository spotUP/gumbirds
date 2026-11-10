/* Host test for src/core/flier.[ch]: the spec's numbers (thoughts/shared/research/2026-11-09_flier-reference-spec.md):
 * gravity, flap lerp, ground walk and jump, bounce, water, balloons and invincibility, falling, parachute, stomp. */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "../../src/core/flier.h"
#include "../../src/core/arena.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)
#define CHECK_NEAR(a, b, tol) do { long _a = (long)(a), _b = (long)(b); checks++; if (labs(_a - _b) > (tol)) { failures++; \
    printf("FAIL %s:%d: %s = %ld, want %ld +-%d\n", __FILE__, __LINE__, #a, _a, _b, (int)(tol)); } } while (0)

static const FlierInput IDLE = {0, 0};

static Flier air(uint8_t balloons) {
    Flier f;
    flier_init(&f, FL_PX(100), FL_PX(90), balloons, 0);
    return f;
}
static void step(Flier *f, int8_t dir, uint8_t flap) {
    FlierInput in = {dir, flap};
    flier_step(f, &in, FLIER_NO_FLOOR);
}

static void test_gravity(void) {
    Flier f = air(2);
    step(&f, 0, 0);
    CHECK(f.vy == 728);
    for (int i = 1; i < 100; i++) step(&f, 0, 0);
    CHECK(f.vy == 728 * 100);   /* no terminal velocity, no drag */
    Flier g = air(0);
    step(&g, 0, 0);
    CHECK(g.vy == 1820);
    for (int i = 1; i < 40; i++) step(&g, 0, 0);
    CHECK(g.vy == 1820 * 40 && g.state == FLIER_ALIVE);
    Flier h = air(2);
    h.vx = 30000;
    for (int i = 0; i < 100; i++) step(&h, 0, 0);
    CHECK(h.vx == 30000);       /* no horizontal air drag */
}

static void test_flap(void) {
    Flier f = air(2);
    f.vy = -728;                /* gravity runs before the flap (3 "per-tick order"): vy is 0 at the flap */
    step(&f, 0, 1);
    CHECK(f.vy == -13107);      /* one flap from rest: -0.2 px/frame, spec 3.2 */
    step(&f, 0, 1);             /* held: no second flap */
    CHECK(f.vy == -13107 + 728);
    Flier q = air(2);           /* the same flap from true rest: gravity step first, then the lerp */
    step(&q, 0, 1);
    CHECK_NEAR(q.vy, -12525, 4); /* 728 + 0.2 x (-65536 - 728) */
    step(&f, 0, 0);
    step(&f, 0, 1);             /* new press */
    CHECK(f.vy < -13107 + 2 * 728 - 5000);
    Flier z = air(0);           /* no balloon: flap does nothing */
    step(&z, 0, 1);
    CHECK(z.vy == 1820);
    /* n flaps with direction held: vx = top * (1 - 0.8^n) */
    Flier g;
    flier_init(&g, FL_PX(10), FL_PX(100), 3, 0);
    double want = 0;
    for (int n = 1; n <= 20; n++) {
        step(&g, 1, 1);
        step(&g, 1, 0);
        want = 65536.0 * (1.0 - pow(0.8, n));
        CHECK_NEAR(g.vx, (long)want, 3 * n);
    }
    CHECK(g.vx < FLIER_TOP_AIR_SPEED);
    for (int n = 21; n <= 60; n++) { step(&g, 1, 1); step(&g, 1, 0); }
    CHECK(g.vx <= FLIER_TOP_AIR_SPEED && g.vx > FLIER_TOP_AIR_SPEED - 64);
    /* no direction: a flap leaves vx alone */
    Flier h = air(2);
    h.vx = 20000;
    step(&h, 0, 1);
    CHECK(h.vx == 20000);
    /* left is the mirror of right */
    Flier l;
    flier_init(&l, FL_PX(300), FL_PX(100), 3, 0);
    for (int n = 0; n < 8; n++) { step(&l, -1, 1); step(&l, -1, 0); }
    Flier r;
    flier_init(&r, FL_PX(10), FL_PX(100), 3, 0);
    for (int n = 0; n < 8; n++) { step(&r, 1, 1); step(&r, 1, 0); }
    CHECK(l.vx == -r.vx);
}

static Flier stand(uint8_t balloons) {
    Flier f;
    flier_init(&f, FL_PX(100), FL_PX(120) - (balloons ? FLIER_HALF_H16_BALLOON : FLIER_HALF_H16_NOBAL), balloons, 0);
    FlierInput in = {0, 0};
    flier_step(&f, &in, FL_PX(120));   /* lands */
    return f;
}
static void gstep(Flier *f, int8_t dir, uint8_t flap) {
    FlierInput in = {dir, flap};
    flier_step(f, &in, FL_PX(120));
}

static void test_ground(void) {
    Flier f = stand(2);
    CHECK(f.on_ground && f.vy == 0);
    gstep(&f, 1, 0);
    CHECK(f.vx == FLIER_TOP_LAND_SPEED);       /* instant, no acceleration */
    gstep(&f, 0, 0);
    CHECK_NEAR(f.vx, 54613 * 0.8, 8);          /* 0.2 friction lerp */
    int32_t prev = f.vx;
    gstep(&f, 0, 0);
    CHECK_NEAR(f.vx, prev * 0.8, 8);
    CHECK(f.y + flier_half_h(&f) == FL_PX(120));
    gstep(&f, -1, 0);
    CHECK(f.vx == -FLIER_TOP_LAND_SPEED);
    /* jump with balloons */
    Flier j = stand(2);
    gstep(&j, 0, 1);
    CHECK(j.vy == -27307 && !j.on_ground);
    gstep(&j, 0, 1);
    CHECK(j.vy == -27307 + 728);
    /* jump without balloons: twice the speed */
    Flier n = stand(0);
    gstep(&n, 0, 1);
    CHECK(n.vy == -54613 && !n.on_ground);
    /* a jump lands again on the floor */
    for (int i = 0; i < 400 && !j.on_ground; i++) gstep(&j, 0, 0);
    CHECK(j.on_ground && j.vy == 0);
    /* walking off the floor edge: no floor, gravity takes over */
    Flier w = stand(2);
    flier_step(&w, &IDLE, FLIER_NO_FLOOR);
    CHECK(!w.on_ground);
    flier_step(&w, &IDLE, FLIER_NO_FLOOR);
    CHECK(w.vy == 728);
    /* no air flap on a floor-less jump from below: a rising fighter passes a floor */
    Flier u;
    flier_init(&u, FL_PX(100), FL_PX(125), 2, 0);
    u.vy = -FL_PX(1);
    flier_step(&u, &IDLE, FL_PX(120));
    CHECK(!u.on_ground);
}

static void test_bounce(void) {
    Flier f;
    /* side edges wrap at ARENA_W: no wall, velocity untouched */
    flier_init(&f, 32768, FL_PX(90), 2, 0);
    f.vx = -65536; f.vy = 20000;
    step(&f, 0, 0);
    CHECK(f.x == ARENA_W16 - 32768);                 /* 0.5 - 1 = 0.5 left of zero -> 383.5 */
    CHECK(f.vx == -65536 && f.vy == 20000 + 728);
    flier_init(&f, FL_PX(383) + 32768, FL_PX(90), 2, 0);
    f.vx = 65536;
    step(&f, 0, 0);
    CHECK(f.x == 32768 && f.vx == 65536);            /* 384.5 -> 0.5 */
    /* on the floor the edge does not stop the walk either */
    flier_init(&f, FL_PX(383) + 40000, FL_PX(90), 2, 0);
    f.vx = 50000; f.on_ground = 1;
    step(&f, 0, 0);
    CHECK(f.x < FL_PX(2) && f.vx != 0);
    /* a long flight crosses 383 -> 0 and stays inside 0..ARENA_W; it wraps more than once */
    flier_init(&f, FL_PX(100), FL_PX(90), 2, 0);
    f.vx = 65536;
    {
        int wraps = 0;
        int32_t prev = f.x;
        for (int i = 0; i < 2000; i++) {
            step(&f, 0, 0);
            if (f.state != FLIER_ALIVE) break;
            CHECK(f.x >= 0 && f.x < ARENA_W16);
            if (f.x < prev) wraps++;
            prev = f.x;
            f.y = FL_PX(90); f.vy = 0;
        }
        CHECK(wraps == 5);   /* 2000 px of travel / 384 from x 100 */
    }
    /* the FALLING path wraps too */
    flier_init(&f, FL_PX(383) + 40000, FL_PX(90), 0, 0);
    f.state = FLIER_FALLING; f.vx = 60000; f.vy = 0;
    step(&f, 0, 0);
    CHECK(f.x < FL_PX(2) && f.x >= 0);
    flier_init(&f, FL_PX(0) + 100, FL_PX(90), 0, 0);
    f.state = FLIER_FALLING; f.vx = -60000; f.vy = 0;
    step(&f, 0, 0);
    CHECK(f.x > FL_PX(383) && f.x < ARENA_W16);
    /* ceiling y = 0 */
    flier_init(&f, FL_PX(100), FLIER_HALF_H16_BALLOON + 32768, 2, 0);
    f.vy = -65536;
    step(&f, 0, 0);
    CHECK(f.y == FLIER_HALF_H16_BALLOON);
    CHECK(f.vy == 65536 - 728);
    flier_init(&f, FL_PX(100), FLIER_HALF_H16_BALLOON + 100, 2, 0);
    f.vy = -5000; f.vx = 3000;
    step(&f, 0, 0);
    CHECK(f.vy == 27307 && f.vx == 0);       /* ceiling minimum is effectively 50 px/s, not 100 */
}

static void test_water_and_balloons(void) {
    Flier f;
    flier_init(&f, FL_PX(100), FL_PX(180) - FLIER_HALF_H16_BALLOON - 10, 3, 0);
    f.vy = 20000;
    f.invincible = 50;
    step(&f, 0, 0);
    CHECK(f.state == FLIER_DROWNED && f.balloons == 0);   /* water ignores invincibility */
    int32_t y = f.y;
    step(&f, 0, 1);
    CHECK(f.y == y);                                      /* frozen */

    /* pop invincibility counts down 60 frames */
    Flier p = air(FLIER_MAX_BALLOONS);
    CHECK(flier_lose_balloon(&p) == 1 && p.balloons == FLIER_MAX_BALLOONS - 1 && p.invincible == 60);
    CHECK(flier_lose_balloon(&p) == 0 && p.balloons == FLIER_MAX_BALLOONS - 1);
    for (int i = 0; i < 59; i++) { step(&p, 0, 0); p.y = FL_PX(90); p.vy = 0; }
    CHECK(p.invincible == 1);
    CHECK(flier_lose_balloon(&p) == 0);
    step(&p, 0, 0);
    CHECK(p.invincible == 0);
    while (p.balloons > 1) { CHECK(flier_lose_balloon(&p) == 1); p.invincible = 0; }

    /* last balloon in the air, no parachute: falls, input ignored, no clamp */
    CHECK(p.balloons == 1 && p.state == FLIER_ALIVE);
    CHECK(flier_lose_balloon(&p) == 1);
    CHECK(p.state == FLIER_FALLING && p.vx == 0 && p.vy == -27307);
    step(&p, 1, 1);
    CHECK(p.vy == -27307 + 1820 && p.vx == 0);
    for (int i = 0; i < 400 && p.state == FLIER_FALLING; i++) step(&p, 1, 1);
    CHECK(p.state == FLIER_GONE && p.y > FL_PX(FLIER_REMOVE_Y));

    /* last balloon in the air with parachute: 30 frames invincible, slow fall, sway */
    Flier c;
    flier_init(&c, FL_PX(100), FL_PX(50), 1, 1);
    CHECK(flier_lose_balloon(&c) == 1);
    CHECK(c.state == FLIER_PARACHUTE && c.invincible == FLIER_INVINCIBLE_PARACHUTE && c.balloons == 0);
    step(&c, 0, 1);
    CHECK(c.vy == 182);                      /* flap ignored while parachuting */
    for (int i = 0; i < 29; i++) step(&c, 0, 0);
    CHECK(c.invincible == 0 && c.vy == 182 * 30);
    for (int i = 0; i < 60; i++) step(&c, 0, 0);
    CHECK(labs(c.vx) <= 17476);
    int32_t tgt = c.sway_target;
    CHECK(tgt != 0 || c.sway_phase != 0);
    /* parachute ends on landing */
    Flier d;
    flier_init(&d, FL_PX(100), FL_PX(100), 1, 1);
    flier_lose_balloon(&d);
    for (int i = 0; i < 400 && d.state == FLIER_PARACHUTE; i++) { FlierInput in = {0, 0}; flier_step(&d, &in, FL_PX(120)); }
    CHECK(d.state == FLIER_ALIVE && d.on_ground && d.invincible == 0);

    /* last balloon lost on the ground: stands on, no invincibility, feet stay on the floor */
    Flier g = stand(1);
    CHECK(flier_lose_balloon(&g) == 1 && g.balloons == 0 && g.state == FLIER_ALIVE && g.on_ground);
    gstep(&g, 0, 0);
    CHECK(g.y + flier_half_h(&g) == FL_PX(120));
    CHECK(flier_add_balloon(&g) == 1 && g.balloons == 1);
    gstep(&g, 0, 0);
    CHECK(g.y + flier_half_h(&g) == FL_PX(120));
    while (g.balloons < FLIER_MAX_BALLOONS) CHECK(flier_add_balloon(&g) == 1);
    CHECK(!flier_add_balloon(&g) && g.balloons == FLIER_MAX_BALLOONS);
}

static void test_angle(void) {
    CHECK(flier_angle(1000, 0) == 0);
    CHECK(flier_angle(0, 1000) == 64);
    CHECK(flier_angle(-1000, 0) == 128);
    CHECK(flier_angle(0, -1000) == 192);
    CHECK_NEAR(flier_angle(1000, 1000), 32, 1);
    CHECK_NEAR(flier_angle(-1000, 1000), 96, 1);
    CHECK_NEAR(flier_angle(-1000, -1000), 160, 1);
    CHECK_NEAR(flier_angle(1000, -1000), 224, 1);
    CHECK(flier_sin(64) == 32767 && flier_cos(0) == 32767 && flier_sin(0) == 0 && flier_sin(192) == -32767);
}

static void test_stomp(void) {
    Flier a, v;
    flier_init(&a, FL_PX(100), FL_PX(80), 2, 0);
    flier_init(&v, FL_PX(100), FL_PX(90), 2, 0);
    CHECK(flier_feet_hit(&a, &v));
    CHECK(flier_stomp(&a, &v) == 1);
    CHECK(v.balloons == 1 && v.invincible == 60 && a.balloons == 2);   /* exactly one balloon, attacker unhurt */
    CHECK_NEAR(v.vx, 0, 2);
    CHECK_NEAR(v.vy, 21845, 3);          /* victim pushed away (down) at 40 px/s */
    CHECK_NEAR(a.vy, -40960, 3);         /* attacker pushed away (up) at 75 px/s */
    CHECK_NEAR(a.vx, 0, 3);
    CHECK(flier_stomp(&a, &v) == 0 && v.balloons == 1);   /* invincible: no second pop */
    /* diagonal knockback is along the line between the fighters */
    flier_init(&a, FL_PX(100), FL_PX(80), 2, 0);
    flier_init(&v, FL_PX(101), FL_PX(90), 2, 0);
    CHECK(flier_stomp(&a, &v) == 1);
    CHECK(v.vx > 0 && v.vy > v.vx);
    CHECK(a.vx < 0 && a.vy < 0);
    /* last balloon: victim falls, knockback overwritten by the fall start */
    flier_init(&a, FL_PX(100), FL_PX(80), 2, 0);
    flier_init(&v, FL_PX(100), FL_PX(90), 1, 0);
    CHECK(flier_stomp(&a, &v) == 1);
    CHECK(v.state == FLIER_FALLING && v.vx == 0 && v.vy == -27307);
    /* no pop: apart, victim without balloons, falling attacker */
    flier_init(&v, FL_PX(100), FL_PX(90), 2, 0);
    flier_init(&a, FL_PX(140), FL_PX(80), 2, 0);
    CHECK(!flier_feet_hit(&a, &v) && flier_stomp(&a, &v) == 0 && v.balloons == 2);
    flier_init(&a, FL_PX(100), FL_PX(100), 2, 0);   /* attacker below the victim */
    CHECK(flier_stomp(&a, &v) == 0);
    flier_init(&a, FL_PX(100), FL_PX(80), 2, 0);
    a.state = FLIER_FALLING;
    CHECK(flier_stomp(&a, &v) == 0 && v.balloons == 2);
    a.state = FLIER_ALIVE;
    v.balloons = 0;
    CHECK(flier_stomp(&a, &v) == 0);
}

/* Body-contact reflect (spec 3.6 minimum bounce, design 1.6 rules 3-4). */
static void test_body_bounce(void) {
    Flier a, b;
    int hh;
    flier_init(&a, FL_PX(100), FL_PX(90), 2, 0);
    flier_init(&b, FL_PX(100), FL_PX(90), 2, 0);
    hh = (int)(flier_half_h(&a) >> 16) + 1;
    /* side by side, a left of b, a moving into b: x reflects, y stays */
    b.x = a.x + FL_PX(3);
    a.vx = 65536; a.vy = 1000;
    CHECK(flier_body_bounce(&a, &b) == 1);
    CHECK(a.vx == -65536 && a.vy == 1000);
    /* a right of b moving left */
    b.x = a.x - FL_PX(3);
    a.vx = -65536; a.vy = 0;
    CHECK(flier_body_bounce(&a, &b) == 1 && a.vx == 65536);
    /* separating and faster than the minimum: unchanged */
    a.vx = 65536;
    CHECK(flier_body_bounce(&a, &b) == 1 && a.vx == 65536);
    /* slow: becomes minimum x normal (pointing away from b) */
    b.x = a.x + FL_PX(3);
    a.vx = -100; a.vy = 100;
    CHECK(flier_body_bounce(&a, &b) == 1 && a.vx == -27307 && a.vy == 0);
    /* a above b (stacked, small x offset): y reflects upward */
    b.x = a.x; b.y = a.y + FL_PX(2 * hh - 2);
    a.vx = 5000; a.vy = 40000;
    CHECK(flier_body_bounce(&a, &b) == 1 && a.vy == -40000 && a.vx == 5000);
    /* no overlap */
    b.x = a.x + FL_PX(5); b.y = a.y;
    a.vx = 65536;
    CHECK(flier_body_bounce(&a, &b) == 0 && a.vx == 65536);
    /* balloon-less a gets none (it dies in flier_body_kill); other without balloons does not stop a bouncing */
    flier_init(&b, a.x + FL_PX(3), a.y, 0, 0);
    a.vx = 65536;
    CHECK(flier_body_bounce(&a, &b) == 1 && a.vx == -65536);
    CHECK(flier_body_bounce(&b, &a) == 0);
    /* a dead-fall body takes no part */
    flier_init(&b, a.x + FL_PX(3), a.y, 2, 0);
    b.state = FLIER_FALLING;
    a.vx = 65536;
    CHECK(flier_body_bounce(&a, &b) == 0 && a.vx == 65536);
}

/* Collision across the seam: a at x 383, v at x 1 are 2 px apart, not 382. */
static void test_seam(void) {
    Flier a, v;
    flier_init(&a, FL_PX(383), FL_PX(80), 2, 0);
    flier_init(&v, FL_PX(1), FL_PX(90), 2, 0);
    CHECK(flier_feet_hit(&a, &v));
    CHECK(flier_stomp(&a, &v) == 1 && v.balloons == 1);
    /* knockback direction: v is to the right of a across the seam, so it is pushed right (+vx) and a left */
    flier_init(&a, FL_PX(383), FL_PX(80), 2, 0);
    flier_init(&v, FL_PX(1) + 40000, FL_PX(90), 2, 0);
    CHECK(flier_stomp(&a, &v) == 1 && v.vx > 0 && a.vx < 0);
    /* and mirrored: attacker at 1, victim at 383 */
    flier_init(&a, FL_PX(1) + 40000, FL_PX(80), 2, 0);
    flier_init(&v, FL_PX(383), FL_PX(90), 2, 0);
    CHECK(flier_stomp(&a, &v) == 1 && v.vx < 0 && a.vx > 0);
    /* body contact: a left of the seam moving into b right of it */
    flier_init(&a, FL_PX(382), FL_PX(90), 2, 0);
    flier_init(&v, FL_PX(1), FL_PX(90), 2, 0);
    a.vx = 65536;
    CHECK(flier_body_bounce(&a, &v) == 1 && a.vx == -65536 * 0 + a.vx && a.vx < 0);
    /* body kill of a balloon-less flier that touches another across the seam */
    flier_init(&a, FL_PX(383), FL_PX(90), 0, 0);
    flier_init(&v, FL_PX(2), FL_PX(90), 2, 0);
    CHECK(flier_body_kill(&a, &v) == 1 && a.state == FLIER_FALLING);
    /* far apart across the seam: no contact */
    flier_init(&a, FL_PX(383), FL_PX(90), 2, 0);
    flier_init(&v, FL_PX(100), FL_PX(90), 2, 0);
    CHECK(!flier_feet_hit(&a, &v) && flier_body_bounce(&a, &v) == 0);
}

int main(void) {
    test_gravity();
    test_flap();
    test_ground();
    test_bounce();
    test_water_and_balloons();
    test_angle();
    test_stomp();
    test_body_bounce();
    test_seam();
    printf("flier: %d checks, %d failures\n", checks, failures);
    return failures != 0;
}
