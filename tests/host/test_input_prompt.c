/* INPUT-PROMPTS: phase -> prompt mapping of src/core/input_prompt.c (what caps and stick each event shows in each phase) and the cap animation. */
#include <stdio.h>
#include "../../src/core/input_prompt.h"
#include "../../src/core/game.h"
#include "../../src/core/gg_fling.h"
#include "../../src/core/gg_popdrop.h"
#include "../../src/core/gg_toss.h"

static int checks, failures;
#define CHECK(c) do { checks++; if (!(c)) { failures++; if (failures <= 10) printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static void expect(uint8_t ev, uint8_t phase, uint8_t buttons, uint8_t style, uint8_t stick, int line)
{
    InputPrompt p = input_prompt_for(ev, phase);
    checks++;
    if (p.buttons != buttons || p.style != style || p.stick != stick) { failures++; printf("FAIL line %d: event %u phase %u gives buttons %u style %u stick %u\n", line, ev, phase, p.buttons, p.style, p.stick); }
}
#define EXPECT(ev, ph, b, s, st) expect(ev, ph, b, s, st, __LINE__)

static void test_mapping(void)
{
    EXPECT(IP_BLOW, GG_BLOW_INTRO, 0, IP_STYLE_NONE, 0);
    EXPECT(IP_BLOW, GG_BLOW_PLAY, IN_A | IN_B, IP_STYLE_MASH, 0);
    EXPECT(IP_BLOW, GG_BLOW_BURST, 0, IP_STYLE_NONE, 0);
    EXPECT(IP_BLOW, GG_BLOW_RESULT, 0, IP_STYLE_NONE, 0);
    EXPECT(IP_RACE, GG_RACE_INTRO, 0, IP_STYLE_NONE, 0);
    EXPECT(IP_RACE, GG_RACE_PLAY, IN_A | IN_B, IP_STYLE_MASH, 0);
    EXPECT(IP_RACE, GG_RACE_RESULT, 0, IP_STYLE_NONE, 0);
    EXPECT(IP_DASH, IP_PHASE_PLAY, IN_A | IN_B, IP_STYLE_MASH, 0);
    EXPECT(IP_DASH, IP_PHASE_OFF, 0, IP_STYLE_NONE, 0);
    EXPECT(IP_GATHER, IP_PHASE_PLAY, IN_A, IP_STYLE_MASH, 1);
    EXPECT(IP_GATHER, IP_PHASE_OFF, 0, IP_STYLE_NONE, 0);
    EXPECT(IP_POP, PD_FALL, IN_B | IN_C, IP_STYLE_PRESS, 1);
    EXPECT(IP_POP, PD_CRASH, 0, IP_STYLE_NONE, 0);
    EXPECT(IP_POP, PD_RESULT, 0, IP_STYLE_NONE, 0);
    EXPECT(IP_FLING, GF_WINDUP, IN_A | IN_B, IP_STYLE_MASH, 0);    /* mash A and B until the clock ends */
    EXPECT(IP_FLING, GF_AIM, IN_A, IP_STYLE_PRESS, 0);             /* A locks the swinging angle */
    EXPECT(IP_FLING, GF_FLIGHT, IN_A | IN_B, IP_STYLE_MASH, 0);    /* mash to flap */
    EXPECT(IP_FLING, GF_LANDED, 0, IP_STYLE_NONE, 0);
    EXPECT(IP_FLING, GF_RESULT, 0, IP_STYLE_NONE, 0);
    EXPECT(IP_TOSS, GT_HOLD, IN_A | IN_B | IN_C, IP_STYLE_PRESS, 0);
    EXPECT(IP_TOSS, GT_FLIGHT, 0, IP_STYLE_NONE, 0);
    EXPECT(IP_TOSS, GT_BURST, 0, IP_STYLE_NONE, 0);
}

static void test_items(void)
{
    uint8_t k[IP_MAX_ITEMS + 1];
    InputPrompt p = input_prompt_for(IP_GATHER, IP_PHASE_PLAY);
    CHECK(input_prompt_items(&p, k) == 2 && k[0] == IP_ITEM_STICK && k[1] == IP_ITEM_CAP_A);
    p = input_prompt_for(IP_POP, PD_FALL);
    CHECK(input_prompt_items(&p, k) == 3 && k[0] == IP_ITEM_STICK && k[1] == IP_ITEM_CAP_B && k[2] == IP_ITEM_CAP_C);
    p = input_prompt_for(IP_TOSS, GT_HOLD);
    CHECK(input_prompt_items(&p, k) == 3 && k[0] == IP_ITEM_CAP_A && k[2] == IP_ITEM_CAP_C);
    p = input_prompt_for(IP_FLING, GF_AIM);
    CHECK(input_prompt_items(&p, k) == 1 && k[0] == IP_ITEM_CAP_A);
    p = input_prompt_for(IP_FLING, GF_LANDED);
    CHECK(input_prompt_items(&p, k) == 0);
    {   /* no event ever needs more than IP_MAX_ITEMS items */
        uint8_t ev, ph;
        for (ev = 0; ev < IP_EVENTS; ev++) for (ph = 0; ph < 8; ph++) { p = input_prompt_for(ev, ph); CHECK(input_prompt_items(&p, k) <= IP_MAX_ITEMS); }
    }
}

static void test_animation(void)
{
    InputPrompt mash = input_prompt_for(IP_FLING, GF_WINDUP), one = input_prompt_for(IP_GATHER, IP_PHASE_PLAY), press = input_prompt_for(IP_FLING, GF_AIM);
    uint16_t t;
    int a_down = 0, b_down = 0, both = 0, up_gap = 0;
    for (t = 0; t < 120; t++) {
        uint8_t a = input_prompt_state(&mash, IP_ITEM_CAP_A, t), b = input_prompt_state(&mash, IP_ITEM_CAP_B, t);
        a_down += a == IP_CAP_DOWN; b_down += b == IP_CAP_DOWN; both += a == IP_CAP_DOWN && b == IP_CAP_DOWN; up_gap += a == IP_CAP_UP && b == IP_CAP_UP;
    }
    CHECK(a_down == 60 && b_down == 60 && both == 0 && up_gap == 0);                               /* two caps alternate, one is always down */
    CHECK(input_prompt_state(&one, IP_ITEM_CAP_A, 0) == IP_CAP_UP && input_prompt_state(&one, IP_ITEM_CAP_A, 6) == IP_CAP_DOWN);   /* a single cap pulses */
    CHECK(input_prompt_state(&press, IP_ITEM_CAP_A, 0) == IP_CAP_GLOW && input_prompt_state(&press, IP_ITEM_CAP_A, 47) == IP_CAP_DOWN);
    CHECK(input_prompt_state(&one, IP_ITEM_STICK, 0) == IP_STICK_NEUTRAL && input_prompt_state(&one, IP_ITEM_STICK, 16) == IP_STICK_LEFT &&
          input_prompt_state(&one, IP_ITEM_STICK, 48) == IP_STICK_RIGHT);
    {   /* C with A and C set (rank counts only set buttons) */
        InputPrompt bc = input_prompt_for(IP_POP, PD_FALL);
        CHECK(input_prompt_state(&bc, IP_ITEM_CAP_B, 0) == IP_CAP_GLOW && input_prompt_state(&bc, IP_ITEM_CAP_C, 0) == IP_CAP_GLOW);
    }
}

int main(void)
{
    test_mapping();
    test_items();
    test_animation();
    printf("test_input_prompt: %d checks, %d failures\n", checks, failures);
    return failures != 0;
}
