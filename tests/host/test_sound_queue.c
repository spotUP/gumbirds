/* Host tests for the sound command queue (sound_queue.c) and the game-to-sound event edges (sound_events.c). */
#include <stdio.h>
#include <string.h>
#include "../../src/core/sound_queue.h"
#include "../../src/core/sound_events.h"

static int failures, checks;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

int main(void)
{
    SoundQueue q;
    uint8_t c = 0;
    int i;
    sq_init(&q);
    CHECK(!sq_pop(&q, &c));
    CHECK(sq_push(&q, 5) && sq_push(&q, 6) && sq_push(&q, 7));
    CHECK(sq_pop(&q, &c) && c == 5);
    CHECK(sq_pop(&q, &c) && c == 6);
    CHECK(sq_pop(&q, &c) && c == 7);
    CHECK(!sq_pop(&q, &c));
    /* wraparound and overflow: newest dropped, oldest kept, drops counted */
    for (i = 0; i < SQ_CAP; i++) CHECK(sq_push(&q, (uint8_t)(10 + i)));
    CHECK(!sq_push(&q, 99) && q.dropped == 1);
    CHECK(sq_pop(&q, &c) && c == 10);
    CHECK(sq_push(&q, 77));
    for (i = 1; i < SQ_CAP; i++) CHECK(sq_pop(&q, &c) && c == 10 + i);
    CHECK(sq_pop(&q, &c) && c == 77);
    CHECK(!sq_pop(&q, &c));

    {   /* coin_drain: one coin blip per call, the rest stay pending; no coin, no blip */
        uint8_t pending = 0;
        CHECK(coin_drain(&pending) == 0 && pending == 0);
        pending = 2;
        CHECK(coin_drain(&pending) == 1 && pending == 1);
        CHECK(coin_drain(&pending) == 1 && pending == 0);
        CHECK(coin_drain(&pending) == 0 && pending == 0);
    }

    {   /* events */
        SoundEvents e;
        Game g;
        FlowView v;
        memset(&g, 0, sizeof g);
        memset(&v, 0, sizeof v);
        v.game = &g;
        se_init(&e);
        v.state = FLOW_ATTRACT_DEMO;
        g.flaps = 3;
        CHECK(se_step(&e, &v) == 0);                       /* demo is silent */
        v.state = FLOW_PLAYING; g.flaps = 0;
        CHECK(se_step(&e, &v) == SE_START);
        CHECK(se_step(&e, &v) == 0);
        g.flaps = 1;
        CHECK(se_step(&e, &v) == SE_FLAP);
        CHECK(se_step(&e, &v) == 0);                       /* no new press edge */
        g.flaps = 2;
        CHECK(se_step(&e, &v) == SE_FLAP);
        v.state = FLOW_GAME_OVER;
        CHECK(se_step(&e, &v) == SE_GAME_OVER);
        CHECK(se_step(&e, &v) == 0);
    }
    {   /* Gum Trip hit sound: SE_HIT once on each frame whose trip_events carries TRIP_EV_HIT, only while playing */
        SoundEvents e;
        Game g;
        FlowView v;
        memset(&g, 0, sizeof g);
        memset(&v, 0, sizeof v);
        v.game = &g;
        se_init(&e);
        v.state = FLOW_PLAYING;
        CHECK(se_step(&e, &v) == SE_START);
        g.trip_events = TRIP_EV_HIT;
        CHECK(se_step(&e, &v) == SE_HIT);
        CHECK(se_step(&e, &v) == SE_HIT);                  /* a level, not an edge: Game.trip_events is per frame, a new hit sets it again */
        g.trip_events = TRIP_EV_PICKUP;
        CHECK(se_step(&e, &v) == 0);                       /* a pickup does not play the hit sample */
        g.trip_events = 0;
        CHECK(se_step(&e, &v) == 0);
        v.state = FLOW_ATTRACT_DEMO; g.trip_events = TRIP_EV_HIT;
        se_init(&e);
        CHECK(se_step(&e, &v) == 0);                       /* demo is silent */
    }
    {   /* death sounds: per flier edges. die = last balloon lost (not by the hazard), fall = fall starts, splosh/spike/sizzle = hazard line crossed */
        SoundEvents e;
        Game g;
        FlowView v;
        int i;
        memset(&g, 0, sizeof g);
        memset(&v, 0, sizeof v);
        v.game = &g; v.state = FLOW_PLAYING;
        g.cpu_count = 2;
        g.flier.balloons = 2;
        for (i = 0; i < 2; i++) g.cpu[i].balloons = 2;
        se_init(&e);
        CHECK(se_step(&e, &v) == SE_START);
        CHECK(se_step(&e, &v) == 0 && !e.n_die && !e.n_fall && !e.n_splosh && !e.n_spike);
        g.flier.balloons = 1;                              /* a pop that leaves a balloon is not a death */
        CHECK(se_step(&e, &v) == 0);
        g.flier.balloons = 0; g.flier.state = FLIER_FALLING;   /* player stomped to death */
        CHECK(se_step(&e, &v) == (SE_DIE | SE_FALL) && e.n_die == 1 && e.n_fall == 1);
        CHECK(se_step(&e, &v) == 0 && !e.n_die && !e.n_fall);  /* once per death */
        g.cpu[0].balloons = 0; g.cpu[0].state = FLIER_FALLING;  /* two rivals die in one frame: both counted */
        g.cpu[1].balloons = 0; g.cpu[1].state = FLIER_FALLING;
        CHECK(se_step(&e, &v) == (SE_DIE | SE_FALL) && e.n_die == 2 && e.n_fall == 2);
        CHECK(se_step(&e, &v) == 0);
        g.cpu[0].state = FLIER_DROWNED;                    /* a dead body crossing the line is no new event */
        CHECK(se_step(&e, &v) == 0);

        memset(&g, 0, sizeof g);                           /* parachute: dies, does not fall */
        g.flier.balloons = 1; g.cpu_count = 0;
        se_init(&e); se_step(&e, &v); se_step(&e, &v);
        g.flier.balloons = 0; g.flier.state = FLIER_PARACHUTE;
        CHECK(se_step(&e, &v) == SE_DIE && e.n_fall == 0);

        {   /* hazard line: the sound follows the hazard kind; no die or fall for a hazard death */
            static const uint8_t kinds[4] = { HZ_SPIKES, HZ_FIRE, HZ_WATER, HZ_LAVA };
            static const uint16_t want[4] = { SE_SPIKE, SE_SIZZLE, SE_SPLOSH, SE_SPLOSH };
            for (i = 0; i < 4; i++) {
                memset(&g, 0, sizeof g);
                g.hazard_kind = kinds[i]; g.cpu_count = 2;
                g.flier.balloons = 2; g.cpu[0].balloons = 2; g.cpu[1].balloons = 2;
                se_init(&e); se_step(&e, &v); se_step(&e, &v);
                g.flier.x = 111 << 16; g.cpu[1].x = 222 << 16;
                g.flier.state = FLIER_DROWNED; g.flier.balloons = 0;
                g.cpu[1].state = FLIER_DROWNED; g.cpu[1].balloons = 0;
                CHECK(se_step(&e, &v) == want[i]);
                CHECK(e.n_die == 0 && e.n_fall == 0);
                CHECK(e.n_splosh == (want[i] == SE_SPLOSH ? 2 : 0) && e.n_spike == (want[i] == SE_SPIKE ? 2 : 0));
                CHECK(want[i] != SE_SPLOSH || e.splosh_x == 222);   /* splash x: world x of the last liquid crossing (rival 1 after the player) */
                CHECK(se_step(&e, &v) == 0);
            }
        }
        {   /* a popped flier falling through the liquid: one splosh from liquid_hit, none for spikes or fire */
            static const uint8_t kinds2[4] = { HZ_SPIKES, HZ_FIRE, HZ_WATER, HZ_LAVA };
            for (i = 0; i < 4; i++) {
                int arcade;
                for (arcade = 0; arcade < 2; arcade++) {
                    int slot = arcade ? CPU_MAX : 0;
                    Flier *f;
                    memset(&g, 0, sizeof g);
                    g.hazard_kind = kinds2[i]; g.cpu_count = arcade ? CPU_MAX + 1 : 0;
                    if (arcade) g.mode = GAME_MODE_ARCADE;
                    f = arcade ? &g.cpu[slot] : &g.flier;
                    f->balloons = 2; f->x = 77 << 16;
                    se_init(&e); se_step(&e, &v); se_step(&e, &v);
                    f->balloons = 0; f->state = FLIER_FALLING;
                    se_step(&e, &v);
                    f->liquid_hit = 1;
                    se_step(&e, &v);
                    CHECK(e.n_splosh == ((kinds2[i] == HZ_WATER || kinds2[i] == HZ_LAVA) ? 1 : 0));
                    CHECK(e.n_splosh == 0 || e.splosh_x == 77);
                    f->liquid_hit = 0;
                    se_step(&e, &v);
                    CHECK(e.n_splosh == 0);
                }
            }
        }
        {   /* rivals outside cpu_count are ignored; Gum Trip rivals count when active */
            memset(&g, 0, sizeof g);
            g.cpu_count = 1; g.cpu[1].balloons = 2; g.flier.balloons = 2; g.cpu[0].balloons = 2;
            se_init(&e); se_step(&e, &v); se_step(&e, &v);
            g.cpu[1].balloons = 0; g.cpu[1].state = FLIER_FALLING;
            CHECK(se_step(&e, &v) == 0);
            g.mode = GAME_MODE_TRIP;
            g.trip_rivals.r[0].active = 1; g.trip_rivals.r[0].f.balloons = 1;
            se_step(&e, &v);
            g.trip_rivals.r[0].f.balloons = 0; g.trip_rivals.r[0].f.state = FLIER_FALLING;
            CHECK(se_step(&e, &v) == (SE_DIE | SE_FALL));
        }
        {   /* pop: every balloon burst (also the non-final), once per burst per flier; the Trip player pops at gum 0 only */
            memset(&g, 0, sizeof g);
            g.cpu_count = 2; g.flier.balloons = 2; g.cpu[0].balloons = 2; g.cpu[1].balloons = 2;
            se_init(&e); se_step(&e, &v); se_step(&e, &v);
            CHECK(e.n_pop == 0);
            g.flier.balloons = 1;
            CHECK(se_step(&e, &v) == 0 && e.n_pop == 1);          /* non-final burst: pop, no die */
            CHECK(se_step(&e, &v) == 0 && e.n_pop == 0);
            g.flier.balloons = 0; g.flier.state = FLIER_FALLING;
            CHECK(se_step(&e, &v) == (SE_DIE | SE_FALL) && e.n_pop == 1 && e.n_die == 1);   /* last burst: pop then die */
            g.cpu[0].balloons = 1; g.cpu[1].balloons = 1;
            se_step(&e, &v);
            CHECK(e.n_pop == 2);                                   /* two rivals in one frame */
            g.cpu[0].balloons = 0; g.cpu[0].state = FLIER_DROWNED; /* hazard death: no pop */
            se_step(&e, &v);
            CHECK(e.n_pop == 0);

            memset(&g, 0, sizeof g);
            g.mode = GAME_MODE_TRIP; g.trip.gum = 40; g.flier.balloons = 3;
            se_init(&e); se_step(&e, &v); se_step(&e, &v);
            g.trip.gum = 20; g.flier.balloons = 2;                 /* balloons follow the gum: no pop */
            se_step(&e, &v);
            CHECK(e.n_pop == 0);
            g.trip.gum = 0; g.flier.balloons = 0; g.flier.state = FLIER_FALLING;
            se_step(&e, &v);
            CHECK(e.n_pop == 1);                                   /* gum 0: once */
            se_step(&e, &v);
            CHECK(e.n_pop == 0);

            memset(&g, 0, sizeof g);                           /* attract demo: silent */
            g.flier.balloons = 2; v.state = FLOW_ATTRACT_DEMO;
            se_init(&e); se_step(&e, &v);
            g.flier.balloons = 1;
            se_step(&e, &v);
            CHECK(e.n_pop == 0);
            v.state = FLOW_PLAYING;
        }
        memset(&g, 0, sizeof g);                           /* not PLAYING: silent (demo, title) */
        g.flier.balloons = 2;
        v.state = FLOW_ATTRACT_DEMO;
        se_init(&e); se_step(&e, &v);
        g.flier.balloons = 0; g.flier.state = FLIER_FALLING;
        CHECK(se_step(&e, &v) == 0 && !e.n_die);
        v.state = FLOW_ATTRACT_TITLE; v.game = 0;
        CHECK(se_step(&e, &v) == 0 && !e.n_fall);
    }
    printf("%s: %d checks, %d failures\n", failures ? "FAIL" : "PASS", checks, failures);
    return failures != 0;
}
