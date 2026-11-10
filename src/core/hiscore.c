#include "hiscore.h"

static void copy(void *dst, const void *src, size_t n)
{
    uint8_t *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;
    while (n--) {
        *d++ = *s++;
    }
}

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

static void set_name(char *dst, const char *name)
{
    size_t i = 0;
    if (name) {
        for (; i < HISCORE_NAME_LEN && name[i]; i++) {
            dst[i] = name[i];
        }
    }
    for (; i < HISCORE_NAME_LEN; i++) {
        dst[i] = ' ';
    }
}

void hiscore_defaults(HiscoreTable *t)
{
    int i;
    for (i = 0; i < HISCORE_ENTRIES; i++) {
        set_name(t->name[i], "GUMBRAWL");
        t->score[i] = (uint32_t)(HISCORE_ENTRIES - i) * 1000u;
    }
}

size_t hiscore_serialise(const HiscoreTable *t, uint8_t *buf, size_t cap)
{
    int i;
    uint8_t *p;
    if (cap < HISCORE_IMAGE_SIZE) {
        return 0;
    }
    put32(buf, HISCORE_MAGIC);
    buf[4] = (uint8_t)(HISCORE_VERSION >> 8);
    buf[5] = (uint8_t)HISCORE_VERSION;
    p = buf + 6;
    for (i = 0; i < HISCORE_ENTRIES; i++) {
        copy(p, t->name[i], HISCORE_NAME_LEN);
        put32(p + HISCORE_NAME_LEN, t->score[i]);
        p += HISCORE_NAME_LEN + 4;
    }
    put32(p, fnv1a(buf, HISCORE_IMAGE_SIZE - 4));
    return HISCORE_IMAGE_SIZE;
}

int hiscore_load(HiscoreTable *t, const uint8_t *buf, size_t len)
{
    int i;
    const uint8_t *p;
    if (len < HISCORE_IMAGE_SIZE || get32(buf) != HISCORE_MAGIC ||
        (((uint32_t)buf[4] << 8) | buf[5]) != HISCORE_VERSION ||
        get32(buf + HISCORE_IMAGE_SIZE - 4) != fnv1a(buf, HISCORE_IMAGE_SIZE - 4)) {
        hiscore_defaults(t);
        return 0;
    }
    p = buf + 6;
    for (i = 0; i < HISCORE_ENTRIES; i++) {
        copy(t->name[i], p, HISCORE_NAME_LEN);
        t->score[i] = get32(p + HISCORE_NAME_LEN);
        p += HISCORE_NAME_LEN + 4;
    }
    return 1;
}

int hiscore_insert(HiscoreTable *t, const char *name, uint32_t score)
{
    int row, i;
    if (score == 0) {
        return -1;
    }
    for (row = 0; row < HISCORE_ENTRIES; row++) {
        if (score > t->score[row]) {
            break;
        }
    }
    if (row >= HISCORE_ENTRIES) {
        return -1;
    }
    for (i = HISCORE_ENTRIES - 1; i > row; i--) {
        copy(t->name[i], t->name[i - 1], HISCORE_NAME_LEN);
        t->score[i] = t->score[i - 1];
    }
    set_name(t->name[row], name);
    t->score[row] = score;
    return row;
}
