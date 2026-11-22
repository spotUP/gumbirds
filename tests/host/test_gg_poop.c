#include <string.h>
/* test_gg_poop.c - Gum Games Poop the Man: flap physics, drop cooldown, walker and pavement death, respawn, head hit scoring (hat x2, bald x3, combo cap x4), pavement miss, umbrella bounce, shoe stun,
 * 60 s timer and result, 2P, flow wiring. */
#include <stdio.h>
#include "gg_poop.h"
#include "game.h"
#include "flow.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

/* Fresh event with no walkers, the spawn clock parked just after a spawn so the test controls every object. */
static void clean(GgPoop *p)
{
    int i;
    gm_init(p, 7, 0);
    p->timer = 1;
    for (i = 0; i < PM_WALKERS; i++) p->w[i].live = 0;
}

/* A walker standing still on the screen (its own speed cancels the street scroll). */
static void walker(GgPoop *p, int slot, int kind, int x)
{
    PmWalker *w = &p->w[slot];
    w->live = 1; w->kind = (uint8_t)kind; w->st = PM_WALK; w->x8 = (int16_t)(x * 8); w->dx8 = PM_SCROLL * 8;
    w->umb_prone = 0; w->umb = 0; w->t = 0; w->owner = 0;
}

/* A poop falling straight onto (x, y) on the next step. */
static void poop_at(GgPoop *p, int k, int x, int y)
{
    PmPoop *o = &p->poop[0];
    o->live = 1; o->st = PM_POOP_FALL; o->t = 0; o->owner = (uint8_t)k; o->vx16 = 0; o->vy16 = 0;
    o->x16 = (int32_t)x * 16; o->y16 = (int32_t)y * 16;
}

int main(void)
{
    GgPoop p;
    int i;

    CHECK(gm_kind_mult(PM_HAT) == 2 && gm_kind_mult(PM_BALD) == 3 && gm_kind_mult(PM_WOMAN) == 1 && gm_kind_mult(PM_KID) == 1);

    /* head hits: hat 200, then bald with streak 2 = 100*3*2, streak caps at x4 */
    clean(&p);
    walker(&p, 0, PM_HAT, 200);
    poop_at(&p, 0, 200, 170);
    gm_step(&p, 0, 0);
    CHECK(p.b[0].score == 200 && p.b[0].streak == 1 && p.last_hit_pts_ev == 1 && p.w[0].st == PM_HIT);
    walker(&p, 1, PM_BALD, 100);
    poop_at(&p, 0, 100, 180);   /* bald top = 216 - 40 = 176 */
    gm_step(&p, 0, 0);
    CHECK(p.b[0].score == 200 + 600 && p.b[0].streak == 2);
    p.b[0].streak = 4; walker(&p, 2, PM_WOMAN, 150);
    poop_at(&p, 0, 150, 176);   /* woman top 174 */
    gm_step(&p, 0, 0);
    CHECK(p.b[0].score == 800 + 400 && p.b[0].streak == 5);   /* x4 cap, counter keeps counting */

    /* pavement miss: no score, streak ends */
    clean(&p);
    p.b[0].streak = 3;
    poop_at(&p, 0, 40, PM_PAVE_Y);
    gm_step(&p, 0, 0);
    CHECK(p.b[0].score == 0 && p.b[0].streak == 0 && p.poop[0].live && p.poop[0].st == PM_POOP_SPLAT && p.splat_n == 1);
    {   /* the pavement splat scrolls with the street, holds PM_SPLAT_FRAMES, then clears */
        int32_t x0 = p.poop[0].x16;
        for (int i = 0; i < (int)PM_SPLAT_FRAMES - 2; i++) gm_step(&p, 0, 0);
        CHECK(p.poop[0].live && p.poop[0].x16 < x0);
        gm_step(&p, 0, 0); gm_step(&p, 0, 0);
        CHECK(!p.poop[0].live);
    }

    /* umbrella bounce: no score, streak ends, the walker stays unhit */
    clean(&p);
    walker(&p, 0, PM_HAT, 96); p.w[0].umb_prone = 1; p.w[0].umb = 1;   /* bird at x 96 keeps it open */
    p.b[0].streak = 2;
    poop_at(&p, 0, 96, 158);   /* hat top 168, umbrella band 156..164 */
    gm_step(&p, 0, 0);
    CHECK(p.b[0].score == 0 && p.b[0].streak == 0 && p.poop[0].st == PM_POOP_BOUNCE && p.w[0].st == PM_WALK && (p.sfx & PM_SFX_BOUNCE));

    /* shoe that reaches a bird stuns it 45 frames and ends the streak */
    clean(&p);
    p.b[0].streak = 3;
    p.shoe[0].live = 1; p.shoe[0].x = p.b[0].x; p.shoe[0].y = (int16_t)(p.b[0].y + 4); p.shoe[0].vx = 0; p.shoe[0].vy = 0;
    gm_step(&p, 0, 0);
    CHECK(p.b[0].stun == PM_STUN && p.b[0].streak == 0 && !p.shoe[0].live);
    {
        int16_t x0 = p.b[0].x;
        gm_step(&p, IN_B, 0);
        CHECK(p.b[0].x == x0 && p.b[0].drop_t == 0);   /* stunned: no move, no drop */
        for (i = 0; i < (int)PM_STUN; i++) gm_step(&p, 0, 0);
        CHECK(p.b[0].stun == 0);
    }

    /* no ammo: drops are limited only by the cooldown */
    clean(&p);
    {
        int drops = 0;
        for (i = 0; i < 120; i++) {
            p.b[0].y = 60; p.b[0].vy16 = 0;
            gm_step(&p, (i & 1) ? 0 : IN_B, 0);
            if (p.b[0].drop_t == 1) drops++;
        }
        CHECK(drops >= 8 && drops <= 120 / (int)PM_DROP_CD + 1);   /* far past the old 5 shots, never faster than the cooldown */
        clean(&p); p.b[0].y = 60;
        gm_step(&p, IN_B, 0); gm_step(&p, 0, 0); gm_step(&p, IN_B, 0);   /* second press 2 frames later: inside the cooldown */
        CHECK(p.b[0].drop_t == 3);
        for (i = 0; i < (int)PM_DROP_CD; i++) gm_step(&p, 0, 0);
        p.b[0].y = 60; gm_step(&p, IN_B, 0);
        CHECK(p.b[0].drop_t == 1);
    }

    /* gravity: no flap = it falls; a flap press rises; stick up does not lift */
    clean(&p);
    {
        int16_t y0 = p.b[0].y;
        for (i = 0; i < 10; i++) gm_step(&p, 0, 0);
        CHECK(p.b[0].y > y0);
        p.b[0].y = 100; p.b[0].yf = 0; p.b[0].vy16 = 0;
        gm_step(&p, IN_A, 0);
        CHECK(p.b[0].vy16 < 0 && (p.sfx & PM_SFX_FLAP));
        for (i = 0; i < 6; i++) gm_step(&p, 0, 0);
        CHECK(p.b[0].y < 100);
        p.b[0].y = 100; p.b[0].vy16 = 0;
        gm_step(&p, IN_UP, 0);
        CHECK(p.b[0].vy16 > 0);
    }

    /* walker touch kills: streak ends, score kept, input ignored while dead, respawn mid-height with invulnerability */
    clean(&p);
    p.b[0].score = 300; p.b[0].streak = 3;
    walker(&p, 0, PM_KID, p.b[0].x + PM_SCROLL);
    p.b[0].y = 180;
    gm_step(&p, 0, 0);
    CHECK(p.b[0].dead == PM_DEAD_FRAMES && p.b[0].streak == 0 && p.b[0].score == 300 && (p.sfx & PM_SFX_DEAD));
    p.w[0].live = 0;
    {
        int16_t y0 = p.b[0].y;
        for (i = 0; i < 50; i++) gm_step(&p, IN_A | IN_B, 0);   /* the death kick rises a few frames, then it falls; input is ignored */
        CHECK(p.b[0].y > y0 && p.b[0].drop_t == 0 && p.b[0].vy16 > 0);
        for (i = 0; i < (int)PM_DEAD_FRAMES - 50; i++) gm_step(&p, 0, 0);
        CHECK(p.b[0].dead == 0 && p.b[0].y == PM_SPAWN_Y && p.b[0].inv == PM_INV_FRAMES);
        walker(&p, 1, PM_HAT, p.b[0].x + PM_SCROLL); p.b[0].y = 170;   /* invulnerable: a walker does not kill */
        gm_step(&p, 0, 0);
        CHECK(p.b[0].dead == 0);
        p.w[1].live = 0;
        for (i = 0; i < (int)PM_INV_FRAMES; i++) { p.b[0].y = 60; gm_step(&p, 0, 0); }
        CHECK(p.b[0].inv == 0);
    }
    /* falling onto the pavement kills too */
    clean(&p);
    p.b[0].y = PM_FEET_Y - PM_BIRD_HALF_H - 1;
    p.b[0].vy16 = PM_FALL_MAX;
    gm_step(&p, 0, 0); gm_step(&p, 0, 0);
    CHECK(p.b[0].dead);

    /* timer, result, done; record points = score */
    clean(&p);
    p.timer = 0; p.b[0].score = 700;
    for (i = 0; i < (int)PM_CLOCK; i++) gm_step(&p, 0, 0);
    CHECK(p.phase == PM_RESULT && p.seq.best[0] == p.b[0].score);
    for (i = 0; i < (int)PM_RESULT_FRAMES - 1; i++) CHECK(gm_step(&p, 0, 0) == 0);
    CHECK(gm_step(&p, 0, 0) == 1 && p.phase == PM_DONE && p.done);

    /* 2P: each bird scores on its own */
    clean(&p);
    gm_add_p2(&p);
    walker(&p, 0, PM_HAT, 220);
    poop_at(&p, 1, 220, 170);
    gm_step(&p, 0, 0);
    CHECK(p.b[1].score == 200 && p.b[0].score == 0);

    /* flow: Up from Big Blow picks Poop the Man, Start runs it, the best score is the record */
    {
        Flow f;
        flow_init(&f, 0, 0);
        f.mode = GAME_MODE_PARTY;  /* merged PARTY list: sub_i 0 = Rule of the Round, 4 = Big Blow ... 10 = Poop the Man */
        flow_coin(&f);
        flow_step(&f, IN_A, 0, 0); flow_step(&f, 0, 0, 0);
        flow_step(&f, IN_UP, 0, 0); flow_step(&f, 0, 0, 0);
        CHECK(f.gg_event == GG_POOP_MAN);
        f.tables.gg_record[GG_POOP_MAN] = 20;
        flow_step(&f, 0, 1, 1);
        CHECK(f.state == FLOW_PLAYING && f.game.gg_poop);
        f.game.poop.b[0].score = 900; f.game.poop.timer = PM_CLOCK - 1;
        for (i = 0; i < (int)GGCD_SET_FRAMES + (int)PM_RESULT_FRAMES + (int)GG_CARD_FRAMES + 400 && !f.game.res.active; i++) {
            flow_step(&f, 0, 0, 0);
            CHECK(f.state == FLOW_PLAYING);   /* minigame ends on the result screen, never GAME OVER or the title first (owner 2026-11-22) */
        }
        CHECK(f.game.res.active && f.game.res.ev && strcmp(flow_menu_name((uint8_t)(f.game.res.ev - 1)), "POOP THE MAN") == 0);
        for (i = 0; i < 600; i++) flow_step(&f, 0, 0, 0);
        CHECK(f.state == FLOW_PLAYING && f.game.res.active);   /* it holds until a press */
        flow_step(&f, IN_A, 0, 0);
        CHECK(f.state != FLOW_PLAYING && f.state != FLOW_GAME_OVER && f.ended);   /* A leaves it for name entry or the title, never GAME OVER */
        CHECK(f.tables.gg_record[GG_POOP_MAN] >= 900);
    }

    if (fails) { printf("test_gg_poop: %d FAILED\n", fails); return 1; }
    printf("test_gg_poop: all passed\n");
    return 0;
}
