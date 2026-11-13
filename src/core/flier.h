/*
 * flier.h - balloon fighter physics (pure C, host tested in tests/host/test_flier.c, no hardware, no float,
 * no libm). Numbers come from thoughts/shared/research/2026-11-09_flier-reference-spec.md (the "spec");
 * section numbers below point into it.
 *
 * - Position and velocity are int32_t 16.16 fixed point, pixels per frame at 60 Hz, 320x224 screen (arena 384 wide, wrapping: arena.h), reference
 *   scale 0.5 (spec 2.1, 2.2). (x, y) is the centre of the body box.
 * - Every lerp weight is shift-add; no `/` or `%` and no 32x32 multiply on any path (68000: no hardware
 *   divide, no 32-bit multiply). Multiplies are int16 x int16.
 * - Physics only: the caller supplies the floor under the fighter each frame (level data, spec NIR-15) and
 *   routes input and fighter pairs here.
 */
#ifndef BRAWL_FLIER_H
#define BRAWL_FLIER_H

#include <stdint.h>
#include "tuning.h"

#define FL_PX(n) ((int32_t)(n) * 65536) /* whole pixels to 16.16 */

/* ---- Constants. Each line: name, reference value, spec section. Raw = 16.16. ---- */
/* Flight model, user decisions 2026-11-11 (additive impulse flight): every flap ADDS a fixed upward impulse to vy
 * (FLIER_FLAP_IMPULSE, tuning.h) and, with a direction held, a fixed sideways thrust to vx (FLIER_FLAP_THRUST_X); a
 * flap needs FLIER_FLAP_COOLDOWN frames since the last one; fall and rise speed are capped (FLIER_FALL_MAX,
 * FLIER_RISE_MAX); no air drag. Those five are knobs in tuning.h. Values below that the decision did not name keep their
 * old ratio to the decided ones (derived, not decided): gravity without gum = with-gum gravity x 5/3 (user decision 2026-11-12);
 * parachute gravity = with-gum gravity x 182/1092; ground walk = top air speed x 5/6 (54613/65536); ground jump = one
 * flap impulse, 2 x that without gum (old ratio 2.0). */
#define FLIER_GRAVITY_BALLOON      2048     /* with gum: 0.03125 px/frame^2 (decided) */
#define FLIER_GRAVITY_NO_BALLOON   (FLIER_GRAVITY_BALLOON * 5 / 3) /* 3413: 5/3 x with-gum gravity (user decision 2026-11-12) */
#define FLIER_TOP_AIR_SPEED        109227   /* 1.6667 px/frame (decided) */
#define FLIER_TOP_LAND_SPEED       91022    /* 5/6 of top air speed (old ratio 54613/65536; derived) */
#define FLIER_GROUND_JUMP_VY       (-FLIER_FLAP_IMPULSE)     /* two gum: one flap impulse (derived) */
#define FLIER_GROUND_JUMP_VY_ONE   (-FLIER_FLAP_IMPULSE_ONE_GUM) /* one gum: one one-gum flap impulse (derived) */
#define FLIER_GROUND_JUMP_VY_NOBAL (-2 * FLIER_FLAP_IMPULSE) /* no gum: twice that, old ratio 2.0 (derived) */
#define FLIER_FALL_START_VY        (-27307) /* 50 px/s up when a fall starts (3.5) */
#define FLIER_PARACHUTE_GRAVITY    1024     /* half the with-gum gravity (user decision 2026-11-12) */
#define FLIER_PARACHUTE_SWAY       17476    /* 32 px/s sway amplitude (3.5) */
/* Lerp weights (parachute sway 0.1) is the shift-add function in flier.c. */
#define FLIER_INVINCIBLE_POP       FLIER_HIT_COOLDOWN /* frames of immunity after losing a balloon (4.2; tuning.h, was 60) */
#define FLIER_INVINCIBLE_PARACHUTE 30       /* 500 ms when the last balloon goes and a parachute opens (4.2) */
#define FLIER_SWAY_PERIOD          30       /* sway target changes every 500 ms = 30 frames (3.5) */
#define FLIER_SWAY_PHASE_STEP      10430    /* one radian in 8.8 table indices: 256 / 2pi x 256 (3.5, sin(n)) */
#define FLIER_MAX_BALLOONS         2        /* art has two pods (user decision 2026-11-10); NIR-5 default was 3 */

#define FLIER_WORLD_H              180      /* 360 ref px x 0.5 (3.6) */
#define FLIER_WATER_Y              180      /* layout bound and default kill line (3.6, 4.3 item 6); the real line is Flier.kill_y */
#define FLIER_ART_H                32       /* px, height of a drawn Sootling frame (main.c asserts every sheet frame fits); sprite top = feet bottom - this */
#define FLIER_REMOVE_FEET_Y        (SCREEN_H + FLIER_ART_H) /* a dead body is GONE when its feet bottom reaches this: the whole sprite is below the screen */
#define FLIER_NO_FLOOR             0x7FFFFFFF /* floor_y value meaning "no floor under the fighter" */
#define FLIER_FLOOR_TOL            65536    /* 1 px: a standing flier stays on the floor only while its feet are this close to the floor top */

/* Body box (4.4, ours = ref x 0.5; NIR-12: AABB of the capsule's bounding size), half extents in pixels. */
#define FLIER_HALF_W               2        /* 4 px wide */
#define FLIER_HALF_H16_BALLOON     360448   /* 11 px tall / 2, with balloons, 16.16 */
#define FLIER_HALF_H16_NOBAL       229376   /* 7 px tall / 2, without balloons, 16.16 */

/* Contact boxes follow the drawn Sootling art (user decisions 2026-11-10 and 2026-11-11: fliers must not pass through
 * enemy gum bubbles). Measured on assets/flier/sootling_sheet.png (24 x 32 frames; art column 12 is the flier x, art row 31
 * is the feet bottom = y + half height; thoughts/spot/2026-11-11-gum-contact-executor-brief.md has the table). All whole
 * pixels; a box is centred on x and measured upward from the feet bottom of the flier that owns it. Player and computer
 * share them. FLIER_HALF_W above is NOT a contact box: it places the sprite, standing width, islands and hazards.
 *   body: fur ball with tuft, 14 wide, 0..22 above the feet bottom (wings and beak are left out).
 *   gum:  bubbles above the body, 22..31 above the feet bottom; silhouette rim 18 wide with two gums, 10 wide with one.
 * The six tunable box numbers (FLIER_BODY_HALF_W, FLIER_BODY_TOP, FLIER_GUM_HALF_W2, FLIER_GUM_HALF_W1, FLIER_GUM_BOTTOM,
 * FLIER_PAIR_LEVEL_PX) live in tuning.h so the knob check can override them. */
#define FLIER_FEET_HALF_W          3        /* px, drawn feet; kept for the art assertions in main.c */
#define FLIER_FEET_H               3        /* px, ends at the feet bottom */
#define FLIER_GUM_TOP              31       /* px above the victim's feet bottom */
/* Widest horizontal reach of any pair contact in half pixels (x >> 15), for the broad phase in game.c: two wide gums. */
#define FLIER_PAIR_REACH_HALF      (2 * (FLIER_GUM_HALF_W2 + FLIER_GUM_HALF_W2))

typedef enum {
    FLIER_ALIVE = 0,    /* flying or standing (see on_ground) */
    FLIER_PARACHUTE,    /* last balloon lost in the air with a parachute (3.5) */
    FLIER_FALLING,      /* dead, falling, input ignored, collisions off (3.5) */
    FLIER_DROWNED,      /* touched the hazard (4.3 item 6): dead like FALLING and still moving, sinks behind a liquid or bounces once on spike tips; the caller scores it once on entry */
    FLIER_GONE          /* the whole sprite is below the screen (FLIER_REMOVE_FEET_Y), remove it */
} FlierState;

typedef struct {
    int32_t x, y;        /* body centre, 16.16 pixels */
    int32_t vx, vy;      /* pixels per frame, 16.16 */
    int32_t sway_target; /* parachute horizontal target, 16.16 */
    uint16_t sway_phase; /* 8.8 sine table index, advances once per FLIER_SWAY_PERIOD */
    uint8_t state;       /* FlierState */
    uint8_t balloons;    /* 0..FLIER_MAX_BALLOONS: the life count (4.1) */
    uint8_t invincible;  /* frames left */
    uint16_t spawn_inv;  /* spawn protection frames left (FLIER_SPAWN_INVINCIBLE); players only; any left/right/flap input clears it */
    uint8_t on_ground;
    uint8_t flap_prev;   /* button level last frame, for the press edge */
    uint8_t flap_cd;     /* frames until the next flap is allowed (FLIER_FLAP_COOLDOWN after a flap or ground jump) */
    uint8_t has_parachute;
    uint8_t sway_tick;
    uint8_t liquid_hit;  /* 1 on the one step a dead FALLING body's feet cross the kill line (not spikes): the splash/sound signal, same as the DROWNED edge */
    uint8_t flapped;     /* 1 on the frame a flap impulse or ground jump was applied (view only, never read by the physics) */
    uint8_t facing;      /* 1 = right, 0 = left: the last non-zero input dir (view only, never read by the physics) */
    uint8_t no_wrap;     /* 1 = the side edges do not wrap (Gum Trip: the caller clamps x). 0 in the arena. */
    uint8_t rival;       /* 1 = computer flier: its top bounce line is FLIER_RIVAL_CEILING_DROP px lower (set by the game after flier_init) */
    uint8_t solid_kill;  /* 1 = the kill line is spike tips: a dead body bounces once on it (set by the game from the hazard kind; arena only) */
    uint8_t bounced;     /* 1 = the spike bounce has happened */
    int32_t kill_y;      /* 16.16 world y of the hazard kill line: death when y + half height reaches it (set by the game from the hazard kind) */
} Flier;

typedef struct {
    int8_t dir;          /* -1, 0, +1 */
    uint8_t flap;        /* button level this frame (the module finds the press edge) */
} FlierInput;

void flier_init(Flier *f, int32_t x, int32_t y, uint8_t balloons, uint8_t has_parachute);
/* One frame. floor_y is the 16.16 y of the surface under the fighter (feet land on it), or FLIER_NO_FLOOR. */
void flier_step(Flier *f, const FlierInput *in, int32_t floor_y);
/* Lowest allowed body centre y (16.16) when the whole flier, gum included, must stay below screen row top_px: feet bottom
 * FLIER_CEILING_FEET_Y rows under top_px, plus FLIER_RIVAL_CEILING_DROP when drop is set. The one ceiling rule, shared by flier_step
 * (top_px 0) and the Gum Trip window clamp (top_px win_top). */
int32_t flier_ceiling_y(const Flier *f, int top_px, int drop);
/* A solid platform box for flier_collide_solids, 16.16 pixels in the flier's own x frame (x16 is the left edge, y16 the top;
 * the box is w16 wide and h16 deep). The arena builds these from stage_solids_near, Gum Trip from trip_hit_solids. */
typedef struct { int32_t x16, y16, w16, h16; } FlierSolid;
/* Widest half width in whole pixels flier_collide_solids can use, for the broad phase of the solid lists. */
#define FLIER_SOLID_MAX_HALF_W (FLIER_GUM_HALF_W2 > FLIER_BODY_HALF_W ? FLIER_GUM_HALF_W2 : FLIER_BODY_HALF_W)
extern volatile uint16_t g_flier_solid_hits; /* bounces off a solid, counted by flier_collide_solids (test sentinel) */
/* Solid platforms (call right after flier_step with the position the flier had before it; flier_step is unchanged).
 * A live flier (not FALLING) whose box (body and gum, see flier_solid_box) overlaps a solid is pushed out of it along the axis it came from and the speed
 * component into the solid is reflected times FLIER_BOUNCE_RESTITUTION/256 (no minimum): from below the flier is put under the
 * solid and bounces down, from a side it is put beside it and bounces away. Landing on top stays flier_step's floor.
 * Wrap-aware on the arena ring (a flier with no_wrap set is not folded). Returns the number of solids bounced off. */
int flier_collide_solids(Flier *f, int32_t prev_x, int32_t prev_y, const FlierSolid *solids, int n);
/* Half width and height above the feet bottom (16.16) of the box flier_collide_solids tests: the whole drawn flier, gum included. */
void flier_solid_box(const Flier *f, int32_t *hw, int32_t *top);
/* Loses one balloon unless invincible (spec 4.2). Returns 1 if a balloon popped. */
int flier_lose_balloon(Flier *f);
/* Spawn protection (BR-D5): spawn_inv = FLIER_SPAWN_INVINCIBLE. Immune to balloon loss and pops (a pair against it bounces) until
 * it runs out or the first left/right/flap input arrives. The hazard kill line ignores it. */
void flier_spawn_protect(Flier *f);
/* Body contact (spec 4.3 item 3, design 1.6 rules 2-3): a standing or flying flier with no balloons that another live
 * body touches starts falling. Returns 1 if it did. */
int flier_body_kill(Flier *victim, const Flier *other);
/* The test inside flier_body_kill without the effect: 1 when victim would start falling. The arena asks it first so the
 * platform block (flier_pair_blocked) is only evaluated for real body contacts. */
int flier_body_touching(const Flier *victim, const Flier *other);
/* Body-contact reflect (spec 4.3 item 3 bounce, spec 3.6, design 1.6 rules 3-4): a (alive, with balloons) touching a live
 * body b reverses its own velocity on each axis the two close on (vertical and horizontal independent) times FLIER_BOUNCE_RESTITUTION/256, no minimum; no closing axis, no bounce. A
 * balloon-less a gets no bounce (it dies by flier_body_kill); b having no balloons does not stop a bouncing. Evaluate
 * both orders per pair, before flier_body_kill. Returns 1 if a bounced. */
int flier_body_bounce(Flier *a, const Flier *b);
/* Adds a balloon up to FLIER_MAX_BALLOONS (NIR-8 pickup). Returns 1 if added. */
int flier_add_balloon(Flier *f);
/* Half height of the body box, 16.16. */
int32_t flier_half_h(const Flier *f);
/* Bounce reflection: -v times FLIER_BOUNCE_RESTITUTION/256, magnitude truncated. Used by pair bounces, platform bounces and the ceiling. */
int32_t flier_reflect(int32_t v);
/* Pair contact (gum, body): one decision per unordered pair, in a's point of view. Boxes are the FLIER_BODY_* and FLIER_GUM_*
 * constants above, edges exclusive, half pixel units. Both fliers must be ALIVE or PARACHUTE, else NONE. A bounce or pop also needs the pair to close on an axis (relative velocity), else NONE.
 *   level (feet bottoms differ by less than FLIER_PAIR_LEVEL_PX): body or gum meets, BOUNCE (nobody pops);
 *   otherwise the higher flier's body or gum against the lower flier's gum pops the lower one: POP_B when a is higher,
 *   POP_A when b is. A pop on an invincible victim is a BOUNCE. Body against body with no gum in play also bounces. */
typedef enum { FLP_NONE = 0, FLP_POP_A, FLP_POP_B, FLP_BOUNCE } FlierPairAct;
extern volatile uint32_t g_flier_pair_calls; /* flier_pair calls (test sentinel, read by MAME) */
FlierPairAct flier_pair(const Flier *a, const Flier *b);
/* Executes act for the pair: POP_B/POP_A pop one balloon of the lower flier, BOUNCE does not; both reflect each flier's own
 * velocity on every axis the pair closes on (vertical and horizontal independent) times FLIER_BOUNCE_RESTITUTION/256, no
 * minimum speed and no knockback (a balloon-less flier gets none). Returns 1 if a balloon popped. */
int flier_pair_apply(Flier *a, Flier *b, FlierPairAct act);
/* A solid platform between two fliers blocks their contact (pop, bounce, body kill; user decision 2026-11-11): 1 when the
 * straight segment between the two flier centres passes through the open interior of any of the n solid boxes (touching an
 * edge or corner does not block). wrap 1 = arena ring: b is taken at its copy nearest a and each box at its copy nearest the
 * segment midpoint, so the caller builds the list with stage_solids_near at that midpoint; wrap 0 = Gum Trip frame (no
 * folding; build the list at the midpoint, trip_hit_solids on a copy of a flier placed there). */
extern volatile uint32_t g_flier_ceiling_hits;       /* ceiling bounces in flier_step (test sentinel, read by MAME) */
extern volatile uint32_t g_flier_ceiling_rival_hits; /* of those, on the lowered computer flier line */
extern volatile uint32_t g_flier_pair_blocked; /* predicate returned 1 (test sentinel, read by MAME) */
int flier_pair_blocked(const Flier *a, const Flier *b, const FlierSolid *solids, int n, int wrap);
/* flier_pair(attacker, victim) == FLP_POP_B, then flier_pair_apply: pops one victim balloon. Returns 1 if a balloon popped. */
int flier_stomp(Flier *attacker, Flier *victim);
/* Unit vector from (dx, dy) as a 256-step angle (0 = +x, 64 = +y down); (0,0) gives 0. Binary search with
 * cross products, no divide. Exposed for tests. */
uint8_t flier_angle(int32_t dx, int32_t dy);
/* Q15 sine and cosine of a 256-step angle. */
int16_t flier_sin(uint8_t a);
int16_t flier_cos(uint8_t a);

#endif
