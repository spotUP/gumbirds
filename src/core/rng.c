#include "rng.h"

void rng_seed(Rng *r, uint32_t seed)
{
    r->s = seed ? seed : 0x9E3779B9u;
}

uint32_t rng_next(Rng *r)
{
    uint32_t x = r->s;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    r->s = x;
    return x;
}

uint32_t rng_range(Rng *r, uint32_t n)
{
    if (n == 0) {
        return 0;
    }
    return rng_next(r) % n;
}
