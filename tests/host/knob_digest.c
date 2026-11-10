/* Prints one digest of a long scripted run. run.sh builds this once per tuning knob with a
 * -D override and checks the digest differs from the baseline. Input comes from its own
 * generator so it does not depend on the game RNG. */
#include <stdio.h>
#include "../../src/core/flow.h"
#include "stomp_assist.h"

static uint32_t h = 2166136261u;
static void mix(uint32_t v)
{
    int i;
    for (i = 0; i < 4; i++) { h ^= (v >> (8 * i)) & 0xFFu; h *= 16777619u; }
}

/* Flow part: a long scripted session driven only by the flow's public state. Covers attract
 * cycles, demo play, real runs, name entry (held direction, idle timeout, END) and the
 * operator reset, so every flow knob has a visible effect on the digest. */
static void flow_digest(void)
{
    static Flow f;
    uint32_t fr, title_visits = 0, entry_visits = 0, entry_frame = 0, in_state = 4242u;
    uint8_t prev_state = 255;
    int i, gapped = 0;
    uint32_t want_stomps = 0;
    flow_init(&f, 0, 0);
    for (fr = 1; fr <= 120000u; fr++) {
        uint8_t in = 0, start = 0;
        in_state = in_state * 1664525u + 1013904223u;
        if (f.state != prev_state) {
            if (f.state == FLOW_ATTRACT_TITLE) title_visits++;
            if (f.state == FLOW_NAME_ENTRY) { entry_visits++; entry_frame = 0; }
            if (f.state == FLOW_PLAYING && !f.demo) {
                /* Arena: stomp a few computer balloons (real score path), then drop over the gap so the run ends. */
                gapped = 0;
                want_stomps = 3u + ((in_state >> 20) & 3u);
            }
            prev_state = f.state;
        }
        switch (f.state) {
        case FLOW_ATTRACT_TITLE:
            if (title_visits % 5 == 1 && f.timer < 250) in = FLOW_RESET_COMBO;
            else if (title_visits % 5 == 3 && f.timer == 60) start = 1;
            break;
        case FLOW_ATTRACT_TABLE:
            if (f.timer == 30 && (in_state >> 28) < 3) start = 1;
            break;
        case FLOW_PLAYING:
            if (!f.demo) {
                if (f.game.stomps < want_stomps && f.game.frame < 600u) stomp_assist(&f.game);
                else if (!gapped) { f.game.flier.x = FL_PX(100); f.game.flier.y = FL_PX(100); gapped = 1; }
            }
            /* Arena: random flaps (1 in 16 frames) and steering so the flier eventually leaves the islands and drowns. */
            if (f.game.frame < 40u && ((in_state >> 8) & 15u) == 0u) in |= IN_A;   /* flaps only early, so the run ends */
            if (((in_state >> 20) & 3u) == 0u) in |= IN_LEFT;
            else if (((in_state >> 20) & 3u) == 1u) in |= IN_RIGHT;
            break;
        case FLOW_NAME_ENTRY:
            entry_frame++;
            if (entry_visits % 2 == 0) {            /* mash: hold up, confirm, down to END */
                if (entry_frame < 70) in = IN_UP;
                else if (entry_frame == 72) in = IN_A;
                else if (entry_frame == 75) in = IN_DOWN;
                else if (entry_frame == 78) in = IN_A;
            } else if (entry_frame == 5) {         /* one letter, then idle until timeout */
                in = IN_A;
            }
            break;
        default:
            break;
        }
        flow_step(&f, in, start, fr);
        if (f.dirty) { mix(0xD1u); f.dirty = 0; }
        mix(f.state); mix(f.timer); mix(f.game.score); mix(f.game.flier_steps); mix(f.game.flaps); mix((uint32_t)f.game.flier.x); mix((uint32_t)f.game.flier.y); mix((uint32_t)game_camera_px(&f.game)); mix((uint32_t)f.highlight);
        mix(f.reset_hold);
        for (i = 0; i < NAME_LEN; i++) mix((uint32_t)f.entry.name[i]);
        mix(f.entry.pos); mix(f.entry.sym[0]);
    }
    for (i = 0; i < HISCORE_ENTRIES; i++) {
        int k;
        mix(f.table.score[i]);
        for (k = 0; k < HISCORE_NAME_LEN; k++) mix((uint32_t)f.table.name[i][k]);
    }
    mix(title_visits); mix(entry_visits);
#ifdef KNOB_DEBUG
    fprintf(stderr, "title %u entry %u last %u\n", (unsigned)title_visits, (unsigned)entry_visits, (unsigned)f.last_score);
#endif
}

/* Arena part: computer fliers and matches. The player is kept alive; every 400 frames all computer fliers lose
 * their balloons (balloon-less AI states), every 1500 frames the rest are removed so the match is won and the next
 * one (one more flier, up to the cap) starts. */
static void arena_digest(void)
{
    static Game g;
    uint32_t f, in_state = 31337u;
    int i;
    game_reset(&g, 4242);
    for (f = 1; f <= 12000u; f++) {
        uint8_t in = 0;
        in_state = in_state * 1664525u + 1013904223u;
        if (((in_state >> 20) & 7u) < 2u) in |= IN_A;
        if (((in_state >> 12) & 3u) == 0u) in |= IN_LEFT;
        else if (((in_state >> 12) & 3u) == 1u) in |= IN_RIGHT;
        if (g.flier.state >= FLIER_FALLING) flier_init(&g.flier, FL_PX(FLIER_START_X), FL_PX(FLIER_START_Y), FLIER_START_BALLOONS, 0);
        g.over = 0;
        if (f % 700u < 40u) stomp_assist(&g);
        if (f % 400u == 0u) for (i = 0; i < g.cpu_count; i++) { g.cpu[i].invincible = 0; while (flier_lose_balloon(&g.cpu[i])) { g.cpu[i].invincible = 0; } if (g.cpu[i].state == FLIER_FALLING) { g.cpu[i].state = FLIER_ALIVE; g.cpu[i].vy = 0; } }
        if (f % 1500u == 0u) for (i = 0; i < g.cpu_count; i++) g.cpu[i].state = FLIER_GONE;
        game_step_arena(&g, in);
        mix(g.stomps); mix(g.score); mix(g.distance); mix(g.matches_won); mix(g.cpu_count); mix(g.cpu_alive);
        for (i = 0; i < g.cpu_count; i++) { mix((uint32_t)g.cpu[i].x); mix((uint32_t)g.cpu[i].y); mix(g.cpu[i].state); mix(g.cpu[i].balloons); mix(g.ai[i].thinks); mix(g.ai[i].state); }
        mix((uint32_t)g.flier.x); mix(g.flier.balloons); mix((uint32_t)game_camera_px(&g));
    }
}

int main(void)
{
    flow_digest();
    arena_digest();
    printf("%08x\n", (unsigned)h);
    return 0;
}
