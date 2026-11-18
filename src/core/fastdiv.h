#ifndef FASTDIV_H
#define FASTDIV_H
#include <stdint.h>

/* 68000 has no 32 bit divide: `/` and `%` on 32 bit values are libgcc calls (~1700 cycles). These use DIVU.W (~140 cycles); the
 * host build keeps plain C, so results are identical wherever the stated limits hold. */

/* a * b for operands that fit signed 16 bits (MULS.W, no __mulsi3). */
static inline int fd_mul16(int a, int b)
{
#ifdef __m68k__
    int r = a;
    __asm__("muls.w %1,%0" : "+d"(r) : "d"((int16_t)b) : "cc");
    return r;
#else
    return a * b;
#endif
}

/* a / b when the quotient fits 16 bits (a < 65536 * b). */
static inline uint16_t fd_div16(uint32_t a, uint16_t b)
{
#ifdef __m68k__
    uint32_t r = a;
    __asm__("divu.w %1,%0" : "+d"(r) : "d"(b) : "cc");
    return (uint16_t)r;
#else
    return (uint16_t)(a / b);
#endif
}

/* t % n for any 32 bit t, n in 1..65535: two DIVU.W on the high and low halves. */
static inline uint16_t fd_umod(uint32_t t, uint16_t n)
{
#ifdef __m68k__
    uint32_t r = t >> 16;
    __asm__("divu.w %1,%0\n\tclr.w %0" : "+d"(r) : "d"(n) : "cc");   /* r = (hi % n) << 16 */
    r |= t & 0xFFFF;
    __asm__("divu.w %1,%0\n\tclr.w %0\n\tswap %0" : "+d"(r) : "d"(n) : "cc"); /* r = t % n */
    return (uint16_t)r;
#else
    return (uint16_t)(t % n);
#endif
}

/* (t / ticks) % frames for a free-running clock; needs ticks * frames < 65536. */
static inline uint8_t fd_clock(uint32_t t, uint16_t ticks, uint16_t frames)
{
#ifdef __m68k__
    return (uint8_t)fd_div16(fd_umod(t, (uint16_t)(ticks * frames)), ticks);
#else
    return (uint8_t)((t / ticks) % frames);
#endif
}
#endif
