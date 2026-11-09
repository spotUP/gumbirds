/* Prints one digest of a long scripted run. run.sh builds this once per tuning knob with a
 * -D override and checks the digest differs from the baseline. Input comes from its own
 * generator so it does not depend on the game RNG. Lives are topped up so the run reaches
 * deep into the difficulty ramp. */
#include <stdio.h>
#include "../../src/core/flow.h"
#include "../../src/core/hero_view.h"

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
    int i;
    flow_init(&f, 0, 0);
    for (fr = 1; fr <= 120000u; fr++) {
        uint8_t in = 0, start = 0;
        in_state = in_state * 1664525u + 1013904223u;
        if (f.state != prev_state) {
            if (f.state == FLOW_ATTRACT_TITLE) title_visits++;
            if (f.state == FLOW_NAME_ENTRY) { entry_visits++; entry_frame = 0; }
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
            in = IN_A;
            if (((in_state >> 12) & 31u) == 0u) in |= IN_B;
            if (((in_state >> 8) & 15u) < 3u) in |= IN_C;
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
        mix(f.state); mix(f.timer); mix(f.game.score); mix(f.game.lives); mix((uint32_t)f.highlight);
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
}

int main(void)
{
    Game g;
    uint32_t f, in_state = 99991u;
    int i;
    game_reset(&g, 777);
    mix(g.lives); mix((uint32_t)g.speed); mix(g.next_gap);
    for (f = 0; f < 40000; f++) {
        uint8_t in = 0;
        in_state = in_state * 1664525u + 1013904223u;
        if (((in_state >> 20) & 7u) < 5u) in |= IN_A;
        if (((in_state >> 12) & 31u) == 0u) in |= IN_B;
        if (((in_state >> 8) & 15u) < 3u) in |= IN_C;
        game_step(&g, in);
        if (g.lives < 2) g.lives = 50;
        g.over = 0;
        mix(g.score); mix(g.lives); mix((uint32_t)g.speed); mix(g.heat); mix(g.lockout);
        mix((uint32_t)g.hero_h); mix(g.spawned);
        { int vis; mix(hero_view_look(&g, &vis)); mix((uint32_t)vis); }
        { int hx, hy, hw, hh; game_hero_box(&g, &hx, &hy, &hw, &hh); mix((uint32_t)(hx + hy + hw + hh)); }
        for (i = 0; i < MAX_OBSTACLES; i++) if (g.obs[i].active) { mix((uint32_t)g.obs[i].x); mix(g.obs[i].type); mix((uint32_t)g.obs[i].y); }
        for (i = 0; i < MAX_BOLTS; i++) if (g.bolts[i].active) mix((uint32_t)g.bolts[i].x);
    }
    flow_digest();
    printf("%08x\n", (unsigned)h);
    return 0;
}
