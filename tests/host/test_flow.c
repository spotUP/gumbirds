/* Host tests for the screen flow: name entry (nameentry.c) and flow state machine (flow.c). */
#include <stdio.h>
#include <string.h>
#include "../../src/core/flow.h"

static int failures;
static int checks;
#define CHECK(c) do { checks++; if (!(c)) { failures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

/* ---- name entry ---- */

static void ne_press(NameEntry *e, uint8_t bits)
{
    nameentry_step(e, bits);
    nameentry_step(e, 0);
}

/* Regression: a stuck or held button must not block the name entry timeout. */
static void test_nameentry_stuck_button(void)
{
    NameEntry e;
    int i;
    nameentry_init(&e);
    for (i = 0; i < NAME_TIMEOUT_FRAMES + 2 && !e.done; i++) {
        nameentry_step(&e, IN_UP);
    }
    CHECK(e.done);
}

static void test_nameentry(void)
{
    NameEntry e;
    int i;

    /* symbol table */
    CHECK(nameentry_symbol_char(0) == 'A' && nameentry_symbol_char(25) == 'Z');
    CHECK(nameentry_symbol_char(26) == '0' && nameentry_symbol_char(35) == '9');
    CHECK(nameentry_symbol_char(36) == ' ' && nameentry_symbol_char(37) == '.');
    CHECK(nameentry_symbol_char(NAME_SYMBOL_END) == 0 && NAME_SYMBOLS == 39);

    /* edit: C, then back and redo, then digit, space, dot, END */
    nameentry_init(&e);
    ne_press(&e, IN_UP); ne_press(&e, IN_UP);
    CHECK(e.sym[0] == 2 && e.pos == 0);
    ne_press(&e, IN_A);
    CHECK(e.pos == 1 && e.name[0] == 'C');
    ne_press(&e, IN_DOWN);                      /* wraps from A to END */
    CHECK(e.sym[1] == NAME_SYMBOL_END);
    ne_press(&e, IN_B);                         /* back: erases C, cursor on 0 */
    CHECK(e.pos == 0 && e.name[0] == ' ' && !e.done);
    ne_press(&e, IN_B);                         /* back at 0 stays */
    CHECK(e.pos == 0);
    ne_press(&e, IN_DOWN);                      /* C -> B */
    ne_press(&e, IN_A);
    CHECK(e.name[0] == 'B' && e.pos == 1);
    for (i = 0; i < 27; i++) ne_press(&e, IN_UP); /* END -> A -> ... -> 0 digit */
    CHECK(nameentry_symbol_char(e.sym[1]) == '0' && e.sym[1] == 26);
    ne_press(&e, IN_A);
    for (i = 0; i < 36; i++) ne_press(&e, IN_UP); /* A -> space */
    CHECK(nameentry_symbol_char(e.sym[2]) == ' ');
    ne_press(&e, IN_UP);
    CHECK(nameentry_symbol_char(e.sym[2]) == '.');
    ne_press(&e, IN_A);
    ne_press(&e, IN_UP); ne_press(&e, IN_UP); ne_press(&e, IN_UP); 
    CHECK(e.sym[3] == 3);
    ne_press(&e, IN_DOWN); ne_press(&e, IN_DOWN); ne_press(&e, IN_DOWN); ne_press(&e, IN_DOWN); /* wraps to END */
    CHECK(e.sym[3] == NAME_SYMBOL_END);
    ne_press(&e, IN_A);
    CHECK(e.done && memcmp(e.name, "B0.     ", 8) == 0);
    { NameEntry copy = e; nameentry_step(&e, IN_UP); nameentry_step(&e, IN_A);
      CHECK(memcmp(&copy, &e, sizeof e) == 0); }  /* frozen when done */

    /* a held button is not a new press */
    nameentry_init(&e);
    for (i = 0; i < 50; i++) nameentry_step(&e, IN_A);
    CHECK(e.pos == 1);

    /* 8th character finishes, no END needed */
    nameentry_init(&e);
    for (i = 0; i < 8; i++) { CHECK(!e.done); ne_press(&e, IN_UP); ne_press(&e, IN_A); }
    CHECK(e.done && memcmp(e.name, "BBBBBBBB", 8) == 0);

    /* END at the first position: default name */
    nameentry_init(&e);
    ne_press(&e, IN_DOWN); ne_press(&e, IN_A);
    CHECK(e.done && memcmp(e.name, NAME_ENTRY_DEFAULT, 8) == 0);

    /* auto repeat: first step at once, next after NAME_REPEAT_DELAY, then every RATE */
    nameentry_init(&e);
    nameentry_step(&e, IN_UP);
    CHECK(e.sym[0] == 1);
    for (i = 1; i <= NAME_REPEAT_DELAY - 1; i++) nameentry_step(&e, IN_UP);
    CHECK(e.sym[0] == 1);
    nameentry_step(&e, IN_UP);                  /* held frame number DELAY */
    CHECK(e.sym[0] == 2);
    for (i = 0; i < NAME_REPEAT_RATE - 1; i++) nameentry_step(&e, IN_UP);
    CHECK(e.sym[0] == 2);
    nameentry_step(&e, IN_UP);
    CHECK(e.sym[0] == 3);
    nameentry_step(&e, 0);                      /* release resets the hold */
    nameentry_step(&e, IN_DOWN);
    CHECK(e.sym[0] == 2);
    for (i = 0; i < 3 * NAME_REPEAT_DELAY; i++) nameentry_step(&e, IN_DOWN);
    CHECK(e.sym[0] != 2);

    /* timeout keeps what was confirmed */
    nameentry_init(&e);
    ne_press(&e, IN_UP); ne_press(&e, IN_A);
    ne_press(&e, IN_UP); ne_press(&e, IN_UP); ne_press(&e, IN_A);   /* "BC" */
    for (i = 0; i < NAME_TIMEOUT_FRAMES - 2; i++) nameentry_step(&e, 0);
    CHECK(!e.done);
    nameentry_step(&e, 0);
    nameentry_step(&e, 0);
    CHECK(e.done && memcmp(e.name, "BC      ", 8) == 0);
    /* activity restarts the timeout */
    nameentry_init(&e);
    for (i = 0; i < 3 * NAME_TIMEOUT_FRAMES; i++) nameentry_step(&e, (i % 100 == 0) ? IN_UP : 0);
    CHECK(!e.done || NAME_TIMEOUT_FRAMES <= 100);
    /* timeout with nothing confirmed: default */
    nameentry_init(&e);
    for (i = 0; i < NAME_TIMEOUT_FRAMES; i++) nameentry_step(&e, 0);
    CHECK(e.done && memcmp(e.name, NAME_ENTRY_DEFAULT, 8) == 0);
}

/* ---- flow ---- */

typedef struct {
    Flow f;
    uint32_t frame;
    uint8_t backup[HISCORE_IMAGE_SIZE];
    int have_backup;
    uint32_t saves;     /* sentinel: incremented only by the save path below */
} Rig;

/* The platform layer: run a frame, then write backup RAM when the flow says dirty. */
static void rig_tick(Rig *r, uint8_t in, uint8_t start)
{
    r->frame++;
    flow_step(&r->f, in, start, r->frame);
    if (r->f.dirty) {
        CHECK(hiscore_serialise(&r->f.table, r->backup, sizeof r->backup) == HISCORE_IMAGE_SIZE);
        r->have_backup = 1;
        r->saves++;
        r->f.dirty = 0;
    }
}

static void rig_ticks(Rig *r, uint8_t in, int n)
{
    while (n-- > 0) rig_tick(r, in, 0);
}

static void rig_until(Rig *r, FlowState s, uint8_t in, int limit)
{
    while (r->f.state != s && limit-- > 0) rig_tick(r, in, 0);
}

static void rig_press(Rig *r, uint8_t bits)
{
    rig_tick(r, bits, 0);
    rig_tick(r, 0, 0);
}

/* Row a score would take in a table, computed independently of hiscore_insert. */
static int expect_row(const HiscoreTable *t, uint32_t s)
{
    int n = 0, i;
    if (s == 0) return -1;
    for (i = 0; i < HISCORE_ENTRIES; i++) if (t->score[i] >= s) n++;
    return n < HISCORE_ENTRIES ? n : -1;
}

static uint32_t learned_score;

/* Drive attract -> start -> play -> game over -> name entry -> reminder -> table. */
static void scenario_full(const HiscoreTable *pre, const char *want_name)
{
    Rig r;
    HiscoreTable before;
    int row, i;
    FlowView v;
    memset(&r, 0, sizeof r);
    if (pre) {
        uint8_t img[HISCORE_IMAGE_SIZE];
        hiscore_serialise(pre, img, sizeof img);
        flow_init(&r.f, img, sizeof img);
    } else {
        flow_init(&r.f, NULL, 0);
    }
    before = r.f.table;
    CHECK(r.f.state == FLOW_ATTRACT_TITLE);

    rig_ticks(&r, 0, 10);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE);
    r.frame = 424242 - 1;                       /* seed = frame counter at start press */
    rig_tick(&r, 0, 1);
    CHECK(r.f.state == FLOW_PLAYING && !r.f.demo);
    rig_until(&r, FLOW_GAME_OVER, IN_A, 60000);
    CHECK(r.f.state == FLOW_GAME_OVER);
    CHECK(r.f.game.over && r.f.last_score == r.f.game.score && r.f.last_score > 0);
    CHECK(r.saves == 0);                        /* nothing saved before the entry */
    learned_score = r.f.last_score;
    row = expect_row(&before, r.f.last_score);
    CHECK(row >= 0);

    rig_ticks(&r, 0, GAMEOVER_FRAMES);
    CHECK(r.f.state == FLOW_NAME_ENTRY);
    for (i = 0; want_name[i]; i++) {
        int k, target = want_name[i] - 'A';
        for (k = 0; k < target; k++) rig_press(&r, IN_UP);
        rig_press(&r, IN_A);
    }
    rig_press(&r, IN_DOWN);                     /* END */
    rig_press(&r, IN_A);
    CHECK(r.f.state == FLOW_SAVE_REMINDER);
    CHECK(r.saves == 1 && r.have_backup);
    flow_view(&r.f, &v);
    CHECK(v.state == FLOW_SAVE_REMINDER && v.highlight == row && v.score == learned_score);
    CHECK(r.f.table.score[row] == learned_score);
    CHECK(memcmp(r.f.table.name[row], want_name, strlen(want_name)) == 0);
    CHECK(r.f.table.name[row][strlen(want_name)] == ' ');
    /* rows above unchanged, rows below shifted down by one */
    for (i = 0; i < row; i++) CHECK(r.f.table.score[i] == before.score[i]);
    for (i = row + 1; i < HISCORE_ENTRIES; i++) CHECK(r.f.table.score[i] == before.score[i - 1]);

    rig_ticks(&r, 0, REMINDER_FRAMES);
    CHECK(r.f.state == FLOW_ATTRACT_TABLE);
    flow_view(&r.f, &v);
    CHECK(v.highlight == row && v.table->score[row] == learned_score);
    CHECK(r.saves == 1);
    rig_ticks(&r, 0, ATTRACT_TABLE_FRAMES);
    CHECK(r.f.state == FLOW_ATTRACT_DEMO);
    CHECK(r.f.highlight == -1);

    /* second boot: fresh flow from the saved image */
    {
        Flow g;
        uint32_t saves_before = r.saves;
        flow_init(&g, r.backup, sizeof r.backup);
        CHECK(memcmp(&g.table, &r.f.table, sizeof g.table) == 0);
        CHECK(g.table.score[row] == learned_score);
        CHECK(memcmp(g.table.name[row], want_name, strlen(want_name)) == 0);
        CHECK(g.state == FLOW_ATTRACT_TITLE && !g.dirty);
        CHECK(r.saves == saves_before);
        /* corrupt image: defaults */
        r.backup[20] ^= 0x01;
        flow_init(&g, r.backup, sizeof r.backup);
        { HiscoreTable d; hiscore_defaults(&d); CHECK(memcmp(&g.table, &d, sizeof d) == 0); }
    }
}

static void test_full_flow(void)
{
    HiscoreTable t;
    int i;
    scenario_full(NULL, "ACE");                 /* defaults: score ranks last or near */
    /* craft a table so the same run ranks in the middle (row 3) */
    memset(&t, 0, sizeof t);
    for (i = 0; i < HISCORE_ENTRIES; i++) memcpy(t.name[i], "OLD     ", 8);
    t.score[0] = learned_score + 5000; t.score[1] = learned_score + 3000;
    t.score[2] = learned_score + 100;  t.score[3] = learned_score - 1;
    for (i = 4; i < HISCORE_ENTRIES; i++) t.score[i] = 100u - (uint32_t)i;
    scenario_full(&t, "ZED");
    /* tie ranks below the existing equal score (row 3 here) */
    t.score[2] = learned_score;
    scenario_full(&t, "TIE");
    /* a score that does not rank skips name entry and the save */
    {
        Rig r;
        memset(&r, 0, sizeof r);
        for (i = 0; i < HISCORE_ENTRIES; i++) { memcpy(t.name[i], "BIG     ", 8); t.score[i] = 900000u - (uint32_t)i; }
        {
            uint8_t img[HISCORE_IMAGE_SIZE];
            hiscore_serialise(&t, img, sizeof img);
            flow_init(&r.f, img, sizeof img);
        }
        r.frame = 424242 - 1;
        rig_tick(&r, 0, 1);
        rig_until(&r, FLOW_GAME_OVER, IN_A, 60000);
        rig_ticks(&r, 0, GAMEOVER_FRAMES);
        CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.saves == 0 && r.f.new_row == -1);
    }
}

static void test_cycle_and_demo(void)
{
    Rig r;
    HiscoreTable before;
    int saw_table = 0, saw_demo = 0, saw_title_again = 0, i;
    memset(&r, 0, sizeof r);
    flow_init(&r.f, NULL, 0);
    before = r.f.table;
    /* durations */
    rig_ticks(&r, 0, ATTRACT_TITLE_FRAMES - 1);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE);
    rig_tick(&r, 0, 0);
    CHECK(r.f.state == FLOW_ATTRACT_TABLE);
    rig_ticks(&r, 0, ATTRACT_TABLE_FRAMES - 1);
    CHECK(r.f.state == FLOW_ATTRACT_TABLE);
    rig_tick(&r, 0, 0);
    CHECK(r.f.state == FLOW_ATTRACT_DEMO && r.f.demo);
    /* push the demo score high so it would rank if the demo ever wrote */
    r.f.game.bonus = 900000u;
    for (i = 0; i < 20 * (ATTRACT_DEMO_FRAMES + ATTRACT_TITLE_FRAMES + ATTRACT_TABLE_FRAMES); i++) {
        rig_tick(&r, 0, 0);
        if (r.f.state == FLOW_ATTRACT_TABLE) saw_table = 1;
        if (r.f.state == FLOW_ATTRACT_DEMO) saw_demo = 1;
        if (r.f.state == FLOW_ATTRACT_TITLE) saw_title_again = 1;
        CHECK(r.f.state != FLOW_PLAYING && r.f.state != FLOW_NAME_ENTRY && r.f.state != FLOW_GAME_OVER);
    }
    CHECK(saw_table && saw_demo && saw_title_again);
    CHECK(r.saves == 0 && !r.f.dirty);
    CHECK(memcmp(&before, &r.f.table, sizeof before) == 0);
    CHECK(r.f.last_score == 0 && r.f.new_row == -1);

    /* the demo actually plays: input moves the game */
    rig_until(&r, FLOW_ATTRACT_DEMO, 0, 100000);
    rig_ticks(&r, 0, 300);
    CHECK(r.f.state == FLOW_ATTRACT_DEMO || r.f.state == FLOW_ATTRACT_TITLE);
    if (r.f.state == FLOW_ATTRACT_DEMO) CHECK(r.f.game.frame >= 300 && r.f.game.shots > 0);

    /* start during the demo starts a real game */
    rig_until(&r, FLOW_ATTRACT_DEMO, 0, 100000);
    rig_tick(&r, 0, 1);
    CHECK(r.f.state == FLOW_PLAYING && !r.f.demo && r.f.game.frame == 0);
    /* a real run that dies still saves nothing without a rank (table full of big scores) */
}

static void test_operator_reset(void)
{
    Rig r;
    HiscoreTable def;
    int i;
    FlowView v;
    memset(&r, 0, sizeof r);
    hiscore_defaults(&def);
    flow_init(&r.f, NULL, 0);
    hiscore_insert(&r.f.table, "MINE", 50000);
    CHECK(r.f.table.score[0] == 50000);

    rig_ticks(&r, FLOW_RESET_COMBO, RESET_HOLD_FRAMES - 1);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.saves == 0 && r.f.table.score[0] == 50000);
    flow_view(&r.f, &v);
    CHECK(v.reset_progress > 90 && v.reset_progress < 100);
    rig_tick(&r, 0, 0);                         /* released one frame short: counter resets */
    flow_view(&r.f, &v);
    CHECK(v.reset_progress == 0);
    rig_ticks(&r, FLOW_RESET_COMBO & ~IN_D, RESET_HOLD_FRAMES + 20); /* three buttons: nothing */
    CHECK(r.saves == 0 && r.f.table.score[0] == 50000);
    rig_tick(&r, 0, 0);
    r.f.timer = 0;                              /* stay on the title screen for the next hold */

    /* start while the combo is held is ignored */
    rig_tick(&r, FLOW_RESET_COMBO, 1);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE);
    rig_tick(&r, 0, 0);
    r.f.timer = 0;

    rig_ticks(&r, FLOW_RESET_COMBO, RESET_HOLD_FRAMES);
    CHECK(r.saves == 1 && r.have_backup);
    CHECK(memcmp(&r.f.table, &def, sizeof def) == 0);
    flow_view(&r.f, &v);
    CHECK(v.reset_progress == 100 && v.reset_flash);
    /* keeps holding: fires only once */
    rig_ticks(&r, FLOW_RESET_COMBO, 50);
    CHECK(r.saves == 1);
    /* the saved image is the defaults */
    {
        Flow g;
        flow_init(&g, r.backup, sizeof r.backup);
        CHECK(memcmp(&g.table, &def, sizeof def) == 0);
    }
    /* release, change the table, hold again: fires again */
    rig_tick(&r, 0, 0);
    r.f.timer = 0;
    hiscore_insert(&r.f.table, "AGAIN", 77777);
    rig_ticks(&r, FLOW_RESET_COMBO, RESET_HOLD_FRAMES);
    CHECK(r.saves == 2 && memcmp(&r.f.table, &def, sizeof def) == 0);

    /* the combo does nothing on the table screen */
    memset(&r, 0, sizeof r);
    flow_init(&r.f, NULL, 0);
    hiscore_insert(&r.f.table, "KEEP", 60000);
    rig_until(&r, FLOW_ATTRACT_TABLE, 0, 10000);
    for (i = 0; i < RESET_HOLD_FRAMES + 5 && r.f.state == FLOW_ATTRACT_TABLE; i++) rig_tick(&r, FLOW_RESET_COMBO, 0);
    CHECK(r.saves == 0 && r.f.table.score[0] == 60000);
}

int main(void)
{
    test_nameentry();
    test_nameentry_stuck_button();
    test_full_flow();
    test_cycle_and_demo();
    test_operator_reset();
    printf("test_flow: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
