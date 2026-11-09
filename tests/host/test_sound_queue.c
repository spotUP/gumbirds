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

    {   /* events */
        SoundEvents e;
        Game g;
        FlowView v;
        memset(&g, 0, sizeof g);
        memset(&v, 0, sizeof v);
        v.game = &g;
        se_init(&e);
        v.state = FLOW_ATTRACT_DEMO;
        g.hero_h = 100; g.shots = 3;
        CHECK(se_step(&e, &v) == 0);                       /* demo is silent */
        v.state = FLOW_PLAYING; g.hero_h = 0; g.shots = 0; g.hits = 0;
        CHECK(se_step(&e, &v) == SE_START);
        CHECK(se_step(&e, &v) == 0);
        g.hero_h = 256;
        CHECK(se_step(&e, &v) == SE_JUMP);
        CHECK(se_step(&e, &v) == 0);                       /* still airborne */
        g.hero_h = 0; g.shots = 1; g.hits = 1;
        CHECK(se_step(&e, &v) == (SE_LASER | SE_HIT));
        v.state = FLOW_GAME_OVER;
        CHECK(se_step(&e, &v) == SE_GAME_OVER);
        CHECK(se_step(&e, &v) == 0);
    }
    printf("%s: %d checks, %d failures\n", failures ? "FAIL" : "PASS", checks, failures);
    return failures != 0;
}
