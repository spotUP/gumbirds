#include "score_table.h"
#include "flow.h"

static void copy(void *dst, const void *src, size_t n)
{
    uint8_t *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;
    while (n--) {
        *d++ = *s++;
    }
}

/* Same FNV-1a as hiscore.c (that one is static there; not edited). */
static uint32_t fnv1a(const uint8_t *p, size_t n)
{
    uint32_t h = 2166136261u;
    size_t i;
    for (i = 0; i < n; i++) {
        h ^= p[i];
        h *= 16777619u;
    }
    return h;
}

static void put32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)(v >> 24);
    p[1] = (uint8_t)(v >> 16);
    p[2] = (uint8_t)(v >> 8);
    p[3] = (uint8_t)v;
}

static uint32_t get32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}

#define TABLE_BYTES (HISCORE_ENTRIES * (HISCORE_NAME_LEN + 4))

static void trip_defaults(HiscoreTable *t)
{
    int i;
    for (i = 0; i < HISCORE_ENTRIES; i++) {
        copy(t->name[i], "GUMTRIP ", HISCORE_NAME_LEN);
        t->score[i] = SCORE_TRIP_DEFAULT_TOP - (uint32_t)i * SCORE_TRIP_DEFAULT_STEP;
    }
}

static void arcade_defaults(HiscoreTable *t)
{
    int i;
    for (i = 0; i < HISCORE_ENTRIES; i++) {
        copy(t->name[i], "ARCADE  ", HISCORE_NAME_LEN);
        t->score[i] = SCORE_ARCADE_DEFAULT_TOP - (uint32_t)i * SCORE_ARCADE_DEFAULT_STEP;
    }
}

void score_tables_defaults(ScoreTables *s)
{
    hiscore_defaults(&s->t[0]);
    trip_defaults(&s->t[1]);
    arcade_defaults(&s->t[2]);
}

static int table_valid(const HiscoreTable *t)
{
    int i;
    for (i = 0; i < HISCORE_ENTRIES; i++) {
        if (t->score[i] > SCORE_CAP || (i > 0 && t->score[i] > t->score[i - 1])) {
            return 0;
        }
    }
    return 1;
}

int score_tables_valid(const ScoreTables *s)
{
    unsigned m;
    for (m = 0; m < SCORE_MODES; m++) {
        if (!table_valid(&s->t[m])) {
            return 0;
        }
    }
    return 1;
}

int score_qualifies(const ScoreTables *s, unsigned mode, uint32_t score)
{
    if (mode >= SCORE_MODES || score == 0) {
        return 0;
    }
    if (score > SCORE_CAP) {
        score = SCORE_CAP;
    }
    return score > s->t[mode].score[HISCORE_ENTRIES - 1];
}

int score_insert(ScoreTables *s, unsigned mode, const char *name, uint32_t score)
{
    if (mode >= SCORE_MODES) {
        return -1;
    }
    if (score > SCORE_CAP) {
        score = SCORE_CAP;
    }
    return hiscore_insert(&s->t[mode], name, score);
}

int score_entry(const ScoreTables *s, unsigned mode, unsigned row, char *name8, uint32_t *score)
{
    if (mode >= SCORE_MODES || row >= HISCORE_ENTRIES) {
        return 0;
    }
    if (name8) {
        copy(name8, s->t[mode].name[row], HISCORE_NAME_LEN);
    }
    if (score) {
        *score = s->t[mode].score[row];
    }
    return 1;
}

size_t score_serialise(const ScoreTables *s, uint8_t *buf, size_t cap)
{
    unsigned m;
    int i;
    uint8_t *p;
    if (cap < SCORE_IMAGE_SIZE) {
        return 0;
    }
    put32(buf, HISCORE_MAGIC);
    buf[4] = (uint8_t)(SCORE_VERSION >> 8);
    buf[5] = (uint8_t)SCORE_VERSION;
    p = buf + 6;
    for (m = 0; m < SCORE_MODES; m++) {
        for (i = 0; i < HISCORE_ENTRIES; i++) {
            copy(p, s->t[m].name[i], HISCORE_NAME_LEN);
            put32(p + HISCORE_NAME_LEN, s->t[m].score[i]);
            p += HISCORE_NAME_LEN + 4;
        }
    }
    put32(p, fnv1a(buf, SCORE_IMAGE_SIZE - 4));
    return SCORE_IMAGE_SIZE;
}

/* Read modes tables from p, then check them. The modes after them keep the defaults. */
static int read_tables(ScoreTables *s, const uint8_t *p, unsigned modes)
{
    unsigned m;
    int i;
    score_tables_defaults(s);
    for (m = 0; m < modes; m++) {
        for (i = 0; i < HISCORE_ENTRIES; i++) {
            copy(s->t[m].name[i], p, HISCORE_NAME_LEN);
            s->t[m].score[i] = get32(p + HISCORE_NAME_LEN);
            p += HISCORE_NAME_LEN + 4;
        }
    }
    return score_tables_valid(s);
}

int score_load(ScoreTables *s, const uint8_t *buf, size_t len)
{
    unsigned ver = 0;
    if (buf && len >= HISCORE_IMAGE_SIZE && get32(buf) == HISCORE_MAGIC) {
        ver = ((uint32_t)buf[4] << 8) | buf[5];
    }
    if (ver == SCORE_VERSION && len >= SCORE_IMAGE_SIZE &&
        get32(buf + SCORE_IMAGE_SIZE - 4) == fnv1a(buf, SCORE_IMAGE_SIZE - 4)) {
        if (read_tables(s, buf + 6, SCORE_MODES)) {
            return 1;
        }
    } else if (ver == SCORE_VERSION_2 && len >= SCORE_IMAGE_SIZE_2 &&
               get32(buf + SCORE_IMAGE_SIZE_2 - 4) == fnv1a(buf, SCORE_IMAGE_SIZE_2 - 4)) {
        if (read_tables(s, buf + 6, 2)) {
            return 3;
        }
    } else if (ver == HISCORE_VERSION) {
        HiscoreTable v1;
        if (hiscore_load(&v1, buf, len) && table_valid(&v1)) {
            score_tables_defaults(s);
            s->t[0] = v1;
            return 2;
        }
    }
    score_tables_defaults(s);
    return 0;
}

unsigned score_shown_mode(unsigned flow_state, unsigned highlighted, unsigned run_mode,
                          uint16_t timer, uint16_t swap_frames)
{
    unsigned t, two;
    if (flow_state == FLOW_ATTRACT_TITLE) {
        return highlighted < SCORE_MODES ? highlighted : 0;
    }
    if (flow_state == FLOW_ATTRACT_TABLE) {
        if (swap_frames == 0) {
            return 0;
        }
        t = timer;
        two = (unsigned)swap_frames * 2u;
        while (t >= two) {
            t -= two;
        }
        return t >= swap_frames ? 1u : 0u;
    }
    return run_mode < SCORE_MODES ? run_mode : 0;
}
