/* test_score_table.c - per-mode score tables (plan T-B8). Standalone: see header of run.sh
 * flags; link hiscore.c + score_table.c. */
#include <stdio.h>
#include <string.h>
#include "score_table.h"
#include "flow.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

static uint32_t sc(const ScoreTables *s, unsigned m, unsigned r)
{
    uint32_t v = 0;
    score_entry(s, m, r, NULL, &v);
    return v;
}

int main(void)
{
    ScoreTables s, s2;
    uint8_t img[SCORE_IMAGE_SIZE + 8], v1[HISCORE_IMAGE_SIZE];
    char nm[8];
    unsigned i, a, b;
    uint32_t before[HISCORE_ENTRIES];

    score_tables_defaults(&s);
    CHECK(score_tables_valid(&s));
    CHECK(sc(&s, 0, 0) == 10000 && sc(&s, 1, 0) == 3000 && sc(&s, 1, 9) == 300);

    /* insert order, rank, name */
    CHECK(score_insert(&s, 1, "ABC", 1000) == 7); /* 3000..1200 then 1000 at row 7 */
    score_entry(&s, 1, 7, nm, NULL);
    CHECK(memcmp(nm, "ABC     ", 8) == 0);
    CHECK(score_insert(&s, 1, "TOP", 5000) == 0);
    CHECK(sc(&s, 1, 0) == 5000 && sc(&s, 1, 1) == 3000);
    /* tie keeps earlier above */
    CHECK(score_insert(&s, 1, "TIE", 5000) == 1);
    score_entry(&s, 1, 0, nm, NULL);
    CHECK(memcmp(nm, "TOP     ", 8) == 0);
    /* full table drops the last entry (300, 600 already dropped by two inserts) */
    CHECK(score_tables_valid(&s));
    CHECK(sc(&s, 1, 9) == 1000 && sc(&s, 1, 8) == 1200);
    CHECK(sc(&s, 1, 9) > 0);

    /* non-qualifying changes nothing */
    for (i = 0; i < HISCORE_ENTRIES; i++) before[i] = sc(&s, 1, i);
    a = (unsigned)sc(&s, 1, 9);
    CHECK(!score_qualifies(&s, 1, a));      /* tie with last: no */
    CHECK(score_qualifies(&s, 1, a + 1));
    CHECK(!score_qualifies(&s, 1, 0));
    CHECK(score_insert(&s, 1, "LOW", a) == -1);
    CHECK(score_insert(&s, 1, "LOW", 0) == -1);
    for (i = 0; i < HISCORE_ENTRIES; i++) CHECK(sc(&s, 1, i) == before[i]);
    CHECK(!score_qualifies(&s, 3, 99999) && score_insert(&s, 3, "X", 99999) == -1);

    /* modes never mix */
    score_tables_defaults(&s);
    CHECK(score_insert(&s, 1, "TRP", 9999) == 0);
    CHECK(sc(&s, 0, 0) == 10000 && sc(&s, 0, 9) == 1000);
    CHECK(score_insert(&s, 0, "ARN", 20000) == 0);
    CHECK(sc(&s, 1, 0) == 9999 && sc(&s, 1, 1) == 3000);
    CHECK(!score_qualifies(&s, 1, 1) && score_qualifies(&s, 0, 2001) && !score_qualifies(&s, 0, 2000));

    /* clamp at 999999, no wrap; two clamped scores tie, second ranks below */
    CHECK(score_insert(&s, 1, "BIG", 4000000000u) == 0);
    CHECK(sc(&s, 1, 0) == 999999);
    CHECK(score_insert(&s, 1, "BI2", 1000000u) == 1);
    CHECK(sc(&s, 1, 1) == 999999 && score_qualifies(&s, 1, 4000000000u));

    /* entry bounds */
    CHECK(!score_entry(&s, 0, 10, nm, NULL) && !score_entry(&s, 3, 0, nm, NULL));

    /* image round trip and size */
    CHECK(score_serialise(&s, img, SCORE_IMAGE_SIZE - 1) == 0);
    CHECK(score_serialise(&s, img, sizeof img) == SCORE_IMAGE_SIZE);
    CHECK(score_load(&s2, img, SCORE_IMAGE_SIZE) == 1);
    CHECK(memcmp(&s, &s2, sizeof s) == 0);

    /* corruption (every byte class) restores defaults */
    for (i = 0; i < SCORE_IMAGE_SIZE; i += 7) {
        uint8_t save = img[i];
        ScoreTables d;
        img[i] ^= 0x10;
        score_tables_defaults(&d);
        s2 = s;
        CHECK(score_load(&s2, img, SCORE_IMAGE_SIZE) == 0);
        CHECK(memcmp(&s2, &d, sizeof d) == 0);
        img[i] = save;
    }
    CHECK(score_load(&s2, img, SCORE_IMAGE_SIZE - 1) == 0);
    CHECK(score_load(&s2, NULL, 0) == 0);
    /* well formed checksum but unsorted rows is still rejected */
    score_tables_defaults(&s2);
    s2.t[1].score[3] = 5000;
    score_serialise(&s2, img, sizeof img);
    CHECK(!score_tables_valid(&s2) && score_load(&s2, img, sizeof img) == 0);
    CHECK(score_tables_valid(&s2) && sc(&s2, 1, 3) == 2100);

    /* v1 image: arena kept, trip defaults */
    {
        HiscoreTable h;
        ScoreTables d;
        hiscore_defaults(&h);
        hiscore_insert(&h, "OLD", 5555);
        CHECK(hiscore_serialise(&h, v1, sizeof v1) == HISCORE_IMAGE_SIZE);
        CHECK(score_load(&s2, v1, sizeof v1) == 2);
        score_tables_defaults(&d);
        CHECK(memcmp(&s2.t[0], &h, sizeof h) == 0 && memcmp(&s2.t[1], &d.t[1], sizeof h) == 0);
    }

    /* v2 image (250 bytes, two tables): loads as 3, third table gets defaults */
    {
        ScoreTables d;
        uint8_t v2[250];
        unsigned k;
        score_tables_defaults(&d);
        score_insert(&d, 0, "TWO", 99999);
        score_insert(&d, 1, "TRP", 4444);
        score_serialise(&d, img, sizeof img);
        for (k = 0; k < 246; k++) v2[k] = img[k];
        v2[4] = 0; v2[5] = 2;
        { uint32_t h = 2166136261u; for (k = 0; k < 246; k++) { h ^= v2[k]; h *= 16777619u; }
          v2[246] = (uint8_t)(h >> 24); v2[247] = (uint8_t)(h >> 16); v2[248] = (uint8_t)(h >> 8); v2[249] = (uint8_t)h; }
        score_tables_defaults(&s2);
        CHECK(score_load(&s2, v2, sizeof v2) == 3);
        CHECK(sc(&s2, 0, 0) == 99999 && sc(&s2, 1, 0) == 4444);
        score_tables_defaults(&d);
        CHECK(memcmp(&s2.t[2], &d.t[2], sizeof d.t[2]) == 0);
    }
    /* v3: arcade score lands in table 3 only, round trips */
    score_tables_defaults(&s);
    CHECK(SCORE_MODES == 3 && score_insert(&s, 2, "ARC", 123456) == 0);
    CHECK(sc(&s, 2, 0) == 123456 && sc(&s, 0, 0) != 123456 && sc(&s, 1, 0) != 123456);
    CHECK(score_serialise(&s, img, sizeof img) == SCORE_IMAGE_SIZE);
    CHECK(score_load(&s2, img, SCORE_IMAGE_SIZE) == 1 && memcmp(&s, &s2, sizeof s) == 0);

    /* shown mode */
    CHECK(score_shown_mode(FLOW_ATTRACT_TITLE, 0, 1, 5, 240) == 0);
    CHECK(score_shown_mode(FLOW_ATTRACT_TITLE, 1, 0, 5, 240) == 1);
    CHECK(score_shown_mode(FLOW_NAME_ENTRY, 0, 1, 5, 240) == 1);
    CHECK(score_shown_mode(FLOW_GAME_OVER, 1, 0, 5, 240) == 0);
    CHECK(score_shown_mode(FLOW_ATTRACT_TABLE, 1, 1, 0, 240) == 0);
    CHECK(score_shown_mode(FLOW_ATTRACT_TABLE, 1, 1, 239, 240) == 0);
    CHECK(score_shown_mode(FLOW_ATTRACT_TABLE, 0, 0, 240, 240) == 1);
    CHECK(score_shown_mode(FLOW_ATTRACT_TABLE, 0, 0, 479, 240) == 1);
    CHECK(score_shown_mode(FLOW_ATTRACT_TABLE, 0, 0, 480, 240) == 0);
    /* knob moves the result: same timer, other period */
    a = score_shown_mode(FLOW_ATTRACT_TABLE, 0, 0, 300, 240);
    b = score_shown_mode(FLOW_ATTRACT_TABLE, 0, 0, 300, 400);
    CHECK(a == 1 && b == 0);
    CHECK(score_shown_mode(FLOW_ATTRACT_TABLE, 0, 0, 300, 0) == 0);
    CHECK(score_shown_mode(FLOW_ATTRACT_TABLE, 0, 0, SCORE_TABLE_SWAP_FRAMES, SCORE_TABLE_SWAP_FRAMES) == 1);

    printf(fails ? "score_table: %d FAILED\n" : "score_table: all passed\n", fails);
    return fails != 0;
}
