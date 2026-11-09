/* rng.h - xorshift32 pseudo random numbers. Portable C99, no libc. */
#ifndef ROOFLINE_RNG_H
#define ROOFLINE_RNG_H
#include <stdint.h>

typedef struct {
    uint32_t s; /* never zero */
} Rng;

/* Seed the generator. The game passes the frame counter at start press. A zero seed is
 * replaced by a fixed non-zero constant because xorshift32 sticks at zero. */
void rng_seed(Rng *r, uint32_t seed);

/* Next 32-bit value. */
uint32_t rng_next(Rng *r);

/* Value in [0, n). Returns 0 when n is 0. Uses modulo; the bias is irrelevant for gameplay. */
uint32_t rng_range(Rng *r, uint32_t n);

#endif
