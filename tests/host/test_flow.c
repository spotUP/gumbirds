/* Host tests for the screen flow: name entry (nameentry.c) and flow state machine (flow.c). */
#include <stdio.h>
#include <string.h>
#include "../../src/core/flow.h"
#include "stomp_assist.h"

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
    CHECK(nameentry_seconds_left(&e) == 0);
    /* seconds left counts down with idle frames, rounded up, and restarts on a press */
    nameentry_init(&e);
    for (i = 0; i < NAME_TIMEOUT_FRAMES; i++) {
        unsigned want = (unsigned)(NAME_TIMEOUT_FRAMES - i + 59) / 60u;
        if (nameentry_seconds_left(&e) != want) { CHECK(nameentry_seconds_left(&e) == want); break; }
        nameentry_step(&e, 0);
    }
    nameentry_init(&e);
    for (i = 0; i < 120; i++) nameentry_step(&e, 0);
    ne_press(&e, IN_UP);
    CHECK(nameentry_seconds_left(&e) == (NAME_TIMEOUT_FRAMES + 59) / 60);
}

/* ---- flow ---- */

typedef struct {
    Flow f;
    uint32_t frame;
    uint8_t backup[SCORE_IMAGE_SIZE];
    int have_backup;
    uint32_t saves;     /* sentinel: incremented only by the save path below */
} Rig;

/* The platform layer: run a frame, then write backup RAM when the flow says dirty. */
static void rig_tick(Rig *r, uint8_t in, uint8_t start)
{
    r->frame++;
    flow_step(&r->f, in, start, r->frame);
    if (r->f.dirty) {
        CHECK(score_serialise(&r->f.tables, r->backup, sizeof r->backup) == SCORE_IMAGE_SIZE);
        r->have_backup = 1;
        r->saves++;
        r->f.dirty = 0;
    }
}

/* Begin a real game from an attract screen: one start press (a taken credit) begins the highlighted mode. seed 0 keeps the frame. */
static void rig_begin(Rig *r, uint32_t seed)
{
    if (seed) r->frame = seed - 1;
    rig_tick(r, 0, 1);
    CHECK(r->f.state == FLOW_PLAYING);
}

static void rig_ticks(Rig *r, uint8_t in, int n)
{
    while (n-- > 0) rig_tick(r, in, 0);
}

/* Earn score through the real arena path: stomp computer balloons (stomp_assist) until the score passes min. */
static void earn_score(Rig *r, uint32_t min)
{
    int i;
    for (i = 0; i < 600 && r->f.game.score <= min; i++) {
        stomp_assist(&r->f.game);
        rig_tick(r, 0, 0);
    }
    CHECK(r->f.game.score > min && r->f.game.stomps > 0);
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
        uint8_t img[SCORE_IMAGE_SIZE];
        ScoreTables st;
        score_tables_defaults(&st);
        st.t[0] = *pre;
        score_serialise(&st, img, sizeof img);
        flow_init(&r.f, img, sizeof img);
    } else {
        flow_init(&r.f, NULL, 0);
    }
    before = r.f.tables.t[0];
    CHECK(r.f.state == FLOW_ATTRACT_TITLE);

    rig_ticks(&r, 0, 10);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE);
    rig_begin(&r, 424242);                      /* seed = frame counter at the second start press */
    CHECK(r.f.state == FLOW_PLAYING && !r.f.demo);
    /* Arena slice: put the flier over the gap between islands (x 100 has no platform below) so it drowns. */
    earn_score(&r, 1500);                       /* stomps give the points; the table minimum is 1000 */
    r.f.game.flier.x = FL_PX(120);
    r.f.game.flier.y = FL_PX(100);
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
    CHECK(r.f.tables.t[0].score[row] == learned_score);
    CHECK(memcmp(r.f.tables.t[0].name[row], want_name, strlen(want_name)) == 0);
    CHECK(r.f.tables.t[0].name[row][strlen(want_name)] == ' ');
    /* rows above unchanged, rows below shifted down by one */
    for (i = 0; i < row; i++) CHECK(r.f.tables.t[0].score[i] == before.score[i]);
    for (i = row + 1; i < HISCORE_ENTRIES; i++) CHECK(r.f.tables.t[0].score[i] == before.score[i - 1]);

    rig_ticks(&r, 0, REMINDER_FRAMES);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE);       /* BG1: the reminder goes straight to the title */
    flow_view(&r.f, &v);
    CHECK(v.highlight == row);
    CHECK(r.saves == 1);
    rig_ticks(&r, 0, ATTRACT_TITLE_FRAMES);
    CHECK(r.f.state == FLOW_ATTRACT_TABLE && r.f.highlight == -1);   /* the title timeout clears the highlight */
    /* BG4: start in the table opens mode select on the title */
    rig_tick(&r, IN_A, 0);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.f.select_open);
    rig_ticks(&r, 0, ATTRACT_TITLE_FRAMES);
    CHECK(r.f.state == FLOW_ATTRACT_TABLE && !r.f.select_open);   /* an unpaid browse select still falls back to attract */
    rig_ticks(&r, 0, ATTRACT_TABLE_FRAMES);
    CHECK(r.f.state == FLOW_ATTRACT_DEMO);
    CHECK(r.f.highlight == -1);

    /* second boot: fresh flow from the saved image */
    {
        Flow g;
        uint32_t saves_before = r.saves;
        flow_init(&g, r.backup, sizeof r.backup);
        CHECK(memcmp(&g.tables, &r.f.tables, sizeof g.tables) == 0);
        CHECK(g.tables.t[0].score[row] == learned_score);
        CHECK(memcmp(g.tables.t[0].name[row], want_name, strlen(want_name)) == 0);
        CHECK(g.state == FLOW_ATTRACT_TITLE && !g.dirty);
        CHECK(r.saves == saves_before);
        /* corrupt image: defaults */
        r.backup[20] ^= 0x01;
        flow_init(&g, r.backup, sizeof r.backup);
        { ScoreTables d; score_tables_defaults(&d); CHECK(memcmp(&g.tables, &d, sizeof d) == 0); }
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
            uint8_t img[SCORE_IMAGE_SIZE];
            ScoreTables st;
            score_tables_defaults(&st);
            st.t[0] = t;
            score_serialise(&st, img, sizeof img);
            flow_init(&r.f, img, sizeof img);
        }
        rig_begin(&r, 424242);
        earn_score(&r, 1500);
        r.f.game.flier.x = FL_PX(120);
        r.f.game.flier.y = FL_PX(100);
        rig_until(&r, FLOW_GAME_OVER, IN_A, 60000);
        rig_ticks(&r, 0, GAMEOVER_FRAMES);
        CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.saves == 0 && r.f.new_row == -1);
    }
}

static void test_cycle_and_demo(void)
{
    Rig r;
    HiscoreTable before;
    int saw_table = 0, saw_demo = 0, saw_title_again = 0, i, run;
    memset(&r, 0, sizeof r);
    flow_init(&r.f, NULL, 0);
    before = r.f.tables.t[0];
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
    r.f.game.score = 900000u;
    for (i = 0; i < 20 * (ATTRACT_DEMO_FRAMES + ATTRACT_TITLE_FRAMES + ATTRACT_TABLE_FRAMES); i++) {
        rig_tick(&r, 0, 0);
        if (r.f.state == FLOW_ATTRACT_TABLE) saw_table = 1;
        if (r.f.state == FLOW_ATTRACT_DEMO) saw_demo = 1;
        if (r.f.state == FLOW_ATTRACT_TITLE) saw_title_again = 1;
        CHECK(r.f.state != FLOW_PLAYING && r.f.state != FLOW_NAME_ENTRY && r.f.state != FLOW_GAME_OVER);
        /* ME8: the demo never enters the round end or round start phases and its flier is always drawable */
        CHECK(r.f.game.round_end == RE_NONE && r.f.game.round_start == RS_NONE && game_flier_visible(&r.f.game));
    }
    CHECK(saw_table && saw_demo && saw_title_again);
    CHECK(r.saves == 0 && !r.f.dirty);
    CHECK(memcmp(&before, &r.f.tables.t[0], sizeof before) == 0);
    CHECK(r.f.last_score == 0 && r.f.new_row == -1);

    /* the demo actually plays: input moves the game */
    rig_until(&r, FLOW_ATTRACT_DEMO, 0, 100000);
    rig_ticks(&r, 0, 300);
    CHECK(r.f.state == FLOW_ATTRACT_DEMO || r.f.state == FLOW_ATTRACT_TITLE);
    if (r.f.state == FLOW_ATTRACT_DEMO) CHECK(r.f.game.frame >= 300 && r.f.game.flier_steps > 0);

    /* the demo flier survives the whole demo window: 12 demos from different start frames (the seed is the frame counter) each
     * end with it alive. The demo pilot cannot dodge computer fliers, so this guards DEMO_HOVER_Y / DEMO_SWEEP_FRAMES. */
    for (run = 0; run < 12; run++) {
        rig_until(&r, FLOW_ATTRACT_TITLE, 0, 100000);
        rig_until(&r, FLOW_ATTRACT_DEMO, 0, 100000);
        for (i = 0; i < ATTRACT_DEMO_FRAMES - 1 && r.f.state == FLOW_ATTRACT_DEMO; i++) rig_tick(&r, 0, 0);
        CHECK(r.f.state == FLOW_ATTRACT_DEMO && !r.f.game.over && r.f.game.flier.state == FLIER_ALIVE && r.f.game.flier_steps > 0);
    }

    /* BG4 (changed by the coin item): a taken credit during the demo starts a game at once, no second press */
    rig_until(&r, FLOW_ATTRACT_DEMO, 0, 100000);
    rig_tick(&r, 0, 1);
    CHECK(r.f.state == FLOW_PLAYING && !r.f.demo && r.f.game.frame == 0 && r.f.game.rounds == 1);
    /* a real run that dies still saves nothing without a rank (table full of big scores) */
}

/* ATTRACT-DEMOS1: each pass through the demo phase plays the next mode (arena, Gum Trip, arcade, arena ...). The order of the attract
 * phases stays title, table, demo. The demo never moves the mode highlighted on the title and leaves no run state behind. */
static void test_demo_modes(void)
{
    static const uint8_t want[6] = { GAME_MODE_ARENA, GAME_MODE_TRIP, GAME_MODE_ARCADE, GAME_MODE_ARENA, GAME_MODE_TRIP, GAME_MODE_ARCADE };
    Rig r;
    int c, i;
    memset(&r, 0, sizeof r);
    flow_init(&r.f, NULL, 0);
    r.f.mode = GAME_MODE_TRIP;                  /* the title highlight must survive every demo */
    for (c = 0; c < 6; c++) {
        int saw_table = 0, steps = 0;
        FlowState prev = (FlowState)r.f.state;
        while (r.f.state != FLOW_ATTRACT_DEMO && steps++ < 100000) {
            rig_tick(&r, 0, 0);
            if (r.f.state == FLOW_ATTRACT_TABLE) saw_table = 1;
            if (r.f.state == FLOW_ATTRACT_DEMO) CHECK(prev == FLOW_ATTRACT_TABLE && saw_table); /* title, table, demo */
            prev = (FlowState)r.f.state;
        }
        CHECK(r.f.state == FLOW_ATTRACT_DEMO && r.f.game.mode == want[c] && r.f.mode == GAME_MODE_TRIP);
        for (i = 0; i < 200 && r.f.state == FLOW_ATTRACT_DEMO; i++) rig_tick(&r, 0, 0);
        CHECK(r.f.game.frame > 0 && r.f.mode == GAME_MODE_TRIP);
        while (r.f.state == FLOW_ATTRACT_DEMO) rig_tick(&r, 0, 0);
        CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.f.mode == GAME_MODE_TRIP && !r.f.demo);
    }
    /* a coin during any demo goes to the title with the list open, in every mode */
    for (c = 0; c < 3; c++) {
        rig_until(&r, FLOW_ATTRACT_DEMO, 0, 100000);
        rig_ticks(&r, 0, 30);
        flow_coin(&r.f);
        CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.f.select_open && !r.f.demo && r.f.mode == GAME_MODE_TRIP);
    }
    /* an arcade demo leaves no run state: the next real game, arena or arcade, starts clean */
    for (c = 0; c < 2; c++) {
        rig_until(&r, FLOW_ATTRACT_DEMO, 0, 100000);
        for (i = 0; i < 3 && r.f.game.mode != GAME_MODE_ARCADE; i++) { r.f.state = FLOW_ATTRACT_TABLE; r.f.timer = ATTRACT_TABLE_FRAMES; rig_until(&r, FLOW_ATTRACT_DEMO, 0, 100000); }
        rig_ticks(&r, 0, 120);
        r.f.game.score = 777; r.f.game.lives.lives = 1; r.f.game.arc.stage = 5;
        r.f.mode = c ? GAME_MODE_ARCADE : GAME_MODE_ARENA;
        rig_tick(&r, 0, 1);
        CHECK(r.f.state == FLOW_PLAYING && !r.f.demo && r.f.game.mode == r.f.mode && r.f.game.score == 0 && r.f.game.frame == 0);
        if (c) CHECK(r.f.game.arc.stage == 1 && r.f.game.lives.lives == ARC_LIVES_START);
        r.f.state = FLOW_ATTRACT_TABLE; r.f.timer = ATTRACT_TABLE_FRAMES; r.f.demo = 0;
    }
}

static void test_operator_reset(void)
{
    Rig r;
    ScoreTables def;
    int i;
    FlowView v;
    memset(&r, 0, sizeof r);
    score_tables_defaults(&def);
    flow_init(&r.f, NULL, 0);
    hiscore_insert(&r.f.tables.t[0], "MINE", 50000);
    CHECK(r.f.tables.t[0].score[0] == 50000);

    rig_ticks(&r, FLOW_RESET_COMBO, RESET_HOLD_FRAMES - 1);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.saves == 0 && r.f.tables.t[0].score[0] == 50000);
    flow_view(&r.f, &v);
    CHECK(v.reset_progress > 90 && v.reset_progress < 100);
    rig_tick(&r, 0, 0);                         /* released one frame short: counter resets */
    flow_view(&r.f, &v);
    CHECK(v.reset_progress == 0);
    rig_ticks(&r, FLOW_RESET_COMBO & ~IN_D, RESET_HOLD_FRAMES + 20); /* three buttons: nothing */
    CHECK(r.saves == 0 && r.f.tables.t[0].score[0] == 50000);
    rig_tick(&r, 0, 0);
    r.f.timer = 0;                              /* stay on the title screen for the next hold */

    /* start while the combo is held is ignored */
    rig_tick(&r, FLOW_RESET_COMBO, 1);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE);
    rig_tick(&r, 0, 0);
    r.f.timer = 0;

    rig_ticks(&r, FLOW_RESET_COMBO, RESET_HOLD_FRAMES);
    CHECK(r.saves == 1 && r.have_backup);
    CHECK(memcmp(&r.f.tables, &def, sizeof def) == 0);
    flow_view(&r.f, &v);
    CHECK(v.reset_progress == 100 && v.reset_flash);
    /* keeps holding: fires only once */
    rig_ticks(&r, FLOW_RESET_COMBO, 50);
    CHECK(r.saves == 1);
    /* the saved image is the defaults */
    {
        Flow g;
        flow_init(&g, r.backup, sizeof r.backup);
        CHECK(memcmp(&g.tables, &def, sizeof def) == 0);
    }
    /* release, change the table, hold again: fires again */
    rig_tick(&r, 0, 0);
    r.f.timer = 0;
    hiscore_insert(&r.f.tables.t[0], "AGAIN", 77777);
    rig_ticks(&r, FLOW_RESET_COMBO, RESET_HOLD_FRAMES);
    CHECK(r.saves == 2 && memcmp(&r.f.tables, &def, sizeof def) == 0);

    /* the combo does nothing on the table screen */
    memset(&r, 0, sizeof r);
    flow_init(&r.f, NULL, 0);
    hiscore_insert(&r.f.tables.t[0], "KEEP", 60000);
    rig_until(&r, FLOW_ATTRACT_TABLE, 0, 10000);
    for (i = 0; i < RESET_HOLD_FRAMES + 5 && r.f.state == FLOW_ATTRACT_TABLE; i++) rig_tick(&r, FLOW_RESET_COMBO, 0);
    CHECK(r.saves == 0 && r.f.tables.t[0].score[0] == 60000);
}

/* ---- Gum Trip mode select on the title (T-B1) ---- */
static void test_mode_select(void)
{
    Rig r;
    int i;
    memset(&r, 0, sizeof r);
    flow_init(&r.f, NULL, 0);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.f.mode == GAME_MODE_ARENA);   /* default arena */
    /* three entries Arena, Gum Trip, Arcade: Down steps forward, Up back, both wrap */
    rig_press(&r, IN_DOWN);
    CHECK(r.f.mode == GAME_MODE_TRIP);
    rig_press(&r, IN_DOWN);
    CHECK(r.f.mode == GAME_MODE_ARCADE);
    rig_press(&r, IN_DOWN);
    CHECK(r.f.mode == GAME_MODE_ARENA);
    rig_press(&r, IN_UP);
    CHECK(r.f.mode == GAME_MODE_ARCADE);
    rig_press(&r, IN_UP);
    CHECK(r.f.mode == GAME_MODE_TRIP);
    rig_press(&r, IN_UP);
    CHECK(r.f.mode == GAME_MODE_ARENA);
    /* held stick: one step on the edge, none while held */
    rig_ticks(&r, IN_DOWN, 100);
    CHECK(r.f.mode == GAME_MODE_TRIP);
    rig_tick(&r, 0, 0);
    /* other buttons and left/right never step */
    rig_press(&r, IN_B); rig_press(&r, IN_LEFT); rig_press(&r, IN_RIGHT);
    CHECK(r.f.mode == GAME_MODE_TRIP);
    /* up and down together on one frame: one step forward */
    rig_press(&r, IN_UP | IN_DOWN);
    CHECK(r.f.mode == GAME_MODE_ARCADE);
    rig_press(&r, IN_DOWN);
    CHECK(r.f.mode == GAME_MODE_ARENA);
    /* the view carries the selection */
    {
        FlowView v;
        rig_press(&r, IN_DOWN);
        flow_view(&r.f, &v);
        CHECK(v.mode == GAME_MODE_TRIP);
    }
    /* Start begins the selected mode through the real path; the trip core runs (sentinel), the arena core does not */
    rig_begin(&r, 0);
    CHECK(r.f.state == FLOW_PLAYING && r.f.game.mode == GAME_MODE_TRIP && r.f.game.flier.no_wrap);
    for (i = 0; i < 30; i++) rig_tick(&r, 0, 0);
    /* the run-start hold (one chunk build per tick, at most 3, none in the Start tick) takes ticks without a trip step */
    CHECK(r.f.game.trip_hold >= 1 && r.f.game.trip_hold <= 3 && game_trip_ready(&r.f.game));
    CHECK(r.f.game.trip.steps == 30 - r.f.game.trip_hold && r.f.game.flier_steps == r.f.game.trip.steps && r.f.game.cpu_count == 0);
    /* game over returns to the title with the selection kept */
    r.f.game.flier.state = FLIER_GONE;
    rig_tick(&r, 0, 0);
    CHECK(r.f.state == FLOW_GAME_OVER);
    rig_until(&r, FLOW_ATTRACT_TITLE, 0, 3000);
    if (r.f.state == FLOW_NAME_ENTRY) rig_ticks(&r, 0, NAME_TIMEOUT_FRAMES + 5);
    rig_until(&r, FLOW_ATTRACT_TITLE, 0, 3000);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.f.mode == GAME_MODE_TRIP);
    /* leaving the title for the table and demo keeps it; the demo is always the arena */
    rig_until(&r, FLOW_ATTRACT_DEMO, 0, 3000);
    CHECK(r.f.state == FLOW_ATTRACT_DEMO && r.f.game.mode == GAME_MODE_ARENA && r.f.mode == GAME_MODE_TRIP);
    rig_until(&r, FLOW_ATTRACT_TITLE, 0, 3000);
    CHECK(r.f.mode == GAME_MODE_TRIP);
    /* Start with the arena selected begins the arena; the trip core never runs */
    rig_press(&r, IN_UP);
    CHECK(r.f.mode == GAME_MODE_ARENA);
    rig_begin(&r, 0);
    for (i = 0; i < 30 + ROUND_START_TEXT_FRAMES + ROUND_GO_TEXT_FRAMES; i++) rig_tick(&r, 0, 0);   /* round 1 starts frozen (ME18) */
    CHECK(r.f.state == FLOW_PLAYING && r.f.game.mode == GAME_MODE_ARENA && r.f.game.trip.steps == 0 && r.f.game.flier_steps == 30);
    CHECK(!r.f.game.flier.no_wrap);
    /* the reset combo still works and does not toggle the mode */
    memset(&r, 0, sizeof r);
    flow_init(&r.f, NULL, 0);
    rig_ticks(&r, FLOW_RESET_COMBO, RESET_HOLD_FRAMES);
    CHECK(r.saves == 1 && r.f.mode == GAME_MODE_ARENA);
    /* Start with ARCADE highlighted begins the arcade run through the real path */
    memset(&r, 0, sizeof r);
    flow_init(&r.f, NULL, 0);
    rig_press(&r, IN_UP);
    CHECK(r.f.mode == GAME_MODE_ARCADE);
    rig_begin(&r, 0);
    CHECK(r.f.state == FLOW_PLAYING && r.f.game.mode == GAME_MODE_ARCADE && r.f.game.arc.stage == 1);
}

/* ---- one score table per mode (rivals + scores plan S3) ---- */

/* Start a run of mode m from the title, end it at once with the given score, and tick to the table screen. */
static void run_mode_to_table(Rig *r, uint8_t m, uint32_t score)
{
    rig_until(r, FLOW_ATTRACT_TITLE, 0, 10000);
    for (int k = 0; k < 3 && r->f.mode != m; k++) rig_press(r, IN_DOWN);   /* Down steps forward through the three entries */
    CHECK(r->f.mode == m);
    rig_begin(r, 0);
    CHECK(r->f.state == FLOW_PLAYING && r->f.game.mode == m);
    r->f.game.score = score;
    r->f.game.over = 1;
    rig_tick(r, 0, 0);
    CHECK(r->f.state == FLOW_GAME_OVER && r->f.last_mode == m && r->f.last_score == score);
    rig_until(r, FLOW_NAME_ENTRY, 0, 3000);
    CHECK(r->f.state == FLOW_NAME_ENTRY);
    rig_ticks(r, 0, NAME_TIMEOUT_FRAMES + 5);
    rig_until(r, FLOW_ATTRACT_TABLE, 0, 3000);
    CHECK(r->f.state == FLOW_ATTRACT_TABLE);
}

static void test_score_modes(void)
{
    Rig r;
    ScoreTables def;
    FlowView v;
    uint8_t v1[HISCORE_IMAGE_SIZE];
    HiscoreTable h;
    int i;
    score_tables_defaults(&def);

    /* trip defaults: 3000 down to 300 step 300, name GUMTRIP */
    for (i = 0; i < HISCORE_ENTRIES; i++) {
        CHECK(def.t[1].score[i] == 3000u - 300u * (uint32_t)i);
        CHECK(memcmp(def.t[1].name[i], "GUMTRIP ", 8) == 0);
    }

    /* a trip run ranks into the trip table only, and the run's table is the one shown */
    memset(&r, 0, sizeof r);
    flow_init(&r.f, NULL, 0);
    run_mode_to_table(&r, GAME_MODE_TRIP, 5000);
    CHECK(r.saves == 1 && r.f.tables.t[1].score[0] == 5000 && r.f.new_row == 0);
    CHECK(memcmp(&r.f.tables.t[0], &def.t[0], sizeof def.t[0]) == 0);
    for (i = 1; i < HISCORE_ENTRIES; i++) CHECK(r.f.tables.t[1].score[i] == def.t[1].score[i - 1]);
    CHECK(r.f.last_mode == GAME_MODE_TRIP);
    /* the saved image round trips */
    { Flow g; flow_init(&g, r.backup, sizeof r.backup); CHECK(memcmp(&g.tables, &r.f.tables, sizeof g.tables) == 0 && !g.dirty); }
    /* table screen: arena for SWAP frames, trip for SWAP frames; the highlight shows only on the run's table */
    r.f.highlight = r.f.new_row;           /* the flow clears it on the title timeout (BG1); set it to test the view alone */
    r.f.state = FLOW_ATTRACT_TABLE;        /* BG1: the flow no longer reaches the table with a highlight; this checks the view function alone */
    r.f.timer = 0;                         flow_view(&r.f, &v); CHECK(v.table_mode == 0 && v.table == &r.f.tables.t[0] && v.highlight == -1);
    r.f.timer = SCORE_TABLE_SWAP_FRAMES - 1; flow_view(&r.f, &v); CHECK(v.table_mode == 0);
    r.f.timer = SCORE_TABLE_SWAP_FRAMES;     flow_view(&r.f, &v); CHECK(v.table_mode == 1 && v.table == &r.f.tables.t[1] && v.highlight == 0);
    r.f.timer = ATTRACT_TABLE_FRAMES - 1;    flow_view(&r.f, &v); CHECK(v.table_mode == 1);
    CHECK(ATTRACT_TABLE_FRAMES >= 2 * SCORE_TABLE_SWAP_FRAMES);

    /* an arena run ranks into the arena table only */
    run_mode_to_table(&r, GAME_MODE_ARENA, 900000);
    CHECK(r.f.tables.t[0].score[0] == 900000 && r.f.tables.t[1].score[0] == 5000 && r.f.last_mode == GAME_MODE_ARENA);
    CHECK(r.saves == 2);
    /* a trip score below the trip table's last row does not rank, even though it would in no other mode's table */
    {
        uint32_t saves = r.saves;
        rig_until(&r, FLOW_ATTRACT_TITLE, 0, 10000);
        rig_press(&r, IN_UP);
        rig_begin(&r, 0);
        r.f.game.score = 1; r.f.game.over = 1;
        rig_tick(&r, 0, 0);
        rig_until(&r, FLOW_ATTRACT_TITLE, 0, 3000);
        CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.saves == saves);
    }
    /* title shows the picked mode's table */
    flow_view(&r.f, &v);
    CHECK(v.table_mode == r.f.mode && v.table == &r.f.tables.t[r.f.mode]);
    rig_press(&r, IN_UP); flow_view(&r.f, &v); CHECK(v.table_mode == r.f.mode);
    rig_press(&r, IN_UP); flow_view(&r.f, &v); CHECK(v.table_mode == r.f.mode && v.table == &r.f.tables.t[r.f.mode]);

    /* operator reset wipes both tables */
    CHECK(memcmp(&r.f.tables, &def, sizeof def) != 0);
    rig_until(&r, FLOW_ATTRACT_TITLE, 0, 10000);
    { uint32_t saves = r.saves; rig_ticks(&r, FLOW_RESET_COMBO, RESET_HOLD_FRAMES);
      CHECK(r.saves == saves + 1 && memcmp(&r.f.tables, &def, sizeof def) == 0); }

    /* a version 1 image (arena rows only) loads: arena kept, trip at defaults, no dirty, no save at boot */
    memset(&r, 0, sizeof r);
    hiscore_defaults(&h);
    hiscore_insert(&h, "OLDV1", 424242);
    CHECK(hiscore_serialise(&h, v1, sizeof v1) == HISCORE_IMAGE_SIZE);
    flow_init(&r.f, v1, sizeof v1);
    CHECK(memcmp(&r.f.tables.t[0], &h, sizeof h) == 0 && memcmp(&r.f.tables.t[1], &def.t[1], sizeof def.t[1]) == 0);
    CHECK(r.f.dirty == 0);
    rig_ticks(&r, 0, 600);
    CHECK(r.saves == 0);
    /* the first new entry writes the version 2 image */
    run_mode_to_table(&r, GAME_MODE_TRIP, 4000);
    CHECK(r.saves == 1);
    { Flow g; flow_init(&g, r.backup, sizeof r.backup); CHECK(memcmp(&g.tables, &r.f.tables, sizeof g.tables) == 0 && g.tables.t[0].score[0] == 424242); }
}

/* Menu buttons: A is a second Start on the attract screens (never begins a game by itself), B goes back to the title. */
static void test_menu_buttons(void)
{
    Rig r;
    memset(&r, 0, sizeof r);
    flow_init(&r.f, NULL, 0);
    /* title, select closed: A edge opens the select; a second A with the select open does nothing */
    rig_press(&r, IN_A);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.f.select_open);
    rig_press(&r, IN_A);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.f.select_open);
    /* B on the title does nothing */
    rig_press(&r, IN_B);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.f.select_open);
    /* a held A is one edge */
    flow_init(&r.f, NULL, 0);
    r.f.input_prev = IN_A;
    rig_tick(&r, IN_A, 0);
    CHECK(!r.f.select_open);
    /* table: A opens the select on the title, B returns to the title with it closed */
    rig_until(&r, FLOW_ATTRACT_TABLE, 0, 3000);
    CHECK(r.f.state == FLOW_ATTRACT_TABLE);
    rig_press(&r, IN_A);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.f.select_open);
    rig_until(&r, FLOW_ATTRACT_TABLE, 0, 3000);
    CHECK(r.f.state == FLOW_ATTRACT_TABLE);
    rig_press(&r, IN_B);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE && !r.f.select_open);
    /* demo: same two buttons, and the demo flag is cleared */
    rig_until(&r, FLOW_ATTRACT_DEMO, 0, 6000);
    CHECK(r.f.state == FLOW_ATTRACT_DEMO && r.f.demo);
    rig_press(&r, IN_A);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.f.select_open && !r.f.demo);
    rig_until(&r, FLOW_ATTRACT_DEMO, 0, 6000);
    CHECK(r.f.state == FLOW_ATTRACT_DEMO && r.f.demo);
    rig_press(&r, IN_B);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE && !r.f.select_open && !r.f.demo);
    /* A without a credit (no start) only opens the select, never a game */
    flow_init(&r.f, NULL, 0);
    rig_press(&r, IN_A); rig_press(&r, IN_A);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.f.select_open);
    /* COIN-TITLE: a coin in each attract phase lands on the title with the select open */
    flow_init(&r.f, NULL, 0);
    rig_until(&r, FLOW_ATTRACT_TABLE, 0, 100000);
    flow_coin(&r.f);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.f.select_open && r.f.timer == 0);
    rig_until(&r, FLOW_ATTRACT_DEMO, 0, 100000);
    flow_coin(&r.f);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE && r.f.select_open && !r.f.demo);
    /* CREDIT-START: with a credit and no press the title waits no longer than attract (no auto start from flow) */
    rig_ticks(&r, 0, 5);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE);
    /* START: a taken credit starts the highlighted mode at once, from title, table and demo */
    {
        int m;
        for (m = GAME_MODE_ARENA; m <= GAME_MODE_ARCADE; m++) {
            flow_init(&r.f, NULL, 0);
            r.f.mode = (uint8_t)m;
            rig_tick(&r, 0, 1);
            CHECK(r.f.state == FLOW_PLAYING && r.f.game.mode == m && !r.f.select_open);
        }
    }
    flow_init(&r.f, NULL, 0);
    rig_until(&r, FLOW_ATTRACT_TABLE, 0, 100000);
    rig_tick(&r, 0, 1);
    CHECK(r.f.state == FLOW_PLAYING && !r.f.demo);
    flow_init(&r.f, NULL, 0);
    rig_until(&r, FLOW_ATTRACT_DEMO, 0, 100000);
    rig_tick(&r, 0, 1);
    CHECK(r.f.state == FLOW_PLAYING && !r.f.demo);
    /* a coin during play does not move the flow */
    flow_coin(&r.f);
    CHECK(r.f.state == FLOW_PLAYING);
    /* the reset combo on the title takes no game and no select */
    flow_init(&r.f, NULL, 0);
    r.f.input_prev = 0;
    rig_tick(&r, FLOW_RESET_COMBO, 1);
    CHECK(r.f.state == FLOW_ATTRACT_TITLE && !r.f.select_open);
    /* no start and no credit: the title falls back to attract */
    flow_init(&r.f, NULL, 0);
    rig_press(&r, IN_A);
    rig_ticks(&r, 0, ATTRACT_TITLE_FRAMES);
    CHECK(r.f.state == FLOW_ATTRACT_TABLE);
}

/* NE1: Start confirms one letter in name entry, exactly like A. */
static void test_name_entry_start(void)
{
    Rig r;
    memset(&r, 0, sizeof r);
    flow_init(&r.f, NULL, 0);
    rig_until(&r, FLOW_ATTRACT_TITLE, 0, 10000);
    rig_begin(&r, 0);
    r.f.game.score = 9999999;
    r.f.game.over = 1;
    rig_tick(&r, 0, 0);
    rig_until(&r, FLOW_NAME_ENTRY, 0, 3000);
    CHECK(r.f.state == FLOW_NAME_ENTRY && r.f.entry.pos == 0);
    rig_tick(&r, 0, 1);
    rig_tick(&r, 0, 0);
    CHECK(r.f.entry.pos == 1);
}

int main(void)
{
    test_nameentry();
    test_nameentry_stuck_button();
    test_full_flow();
    test_cycle_and_demo();
    test_demo_modes();
    test_operator_reset();
    test_mode_select();
    test_menu_buttons();
    test_score_modes();
    test_name_entry_start();
    printf("test_flow: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
