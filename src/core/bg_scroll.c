#include "bg_scroll.h"

/* n = floor(u * k / 16) for k a multiple of 4 up to 28, with shifts and adds only (a general u * k is a libgcc __mulsi3 call on the 68000). */
static uint32_t scaled(uint32_t u, uint32_t k) {
    uint32_t m = k >> 2, s = 0;
    if (m & 1) s += u;
    if (m & 2) s += u << 1;
    if (m & 4) s += u << 2;
    return s >> 2;
}

/* n mod period with one 16 bit divide. n <= 680447 and period >= 336 give a quotient <= 2025, so the 32/16 DIVU cannot overflow
 * (it needs quotient < 65536, i.e. period >= 11 for the largest n); a plain 32 bit % is a libgcc __umodsi3 call. */
static uint32_t mod_period(uint32_t n, uint32_t period) {
#ifdef __m68k__
    uint32_t r = n;
    __asm__("divu.w %1,%0\n\tswap %0" : "+d"(r) : "dmi"((uint16_t)period) : "cc");
    return r & 0xFFFF;
#else
    return n % period;
#endif
}

uint32_t bg_loop_offset(uint32_t u, uint32_t k, uint32_t period) { return mod_period(scaled(u, k), period); }

void bg_ramp(uint32_t off, uint32_t period, BgRamp *out) {
    uint32_t split = off >> 4;
    out->split = (uint8_t)split;
    out->v1 = VQ_SCB4_X(period - off);
    out->v2 = VQ_SCB4_X((split << 4) - off);
}

int bg_column_x(uint32_t off, uint32_t c, uint32_t period) {
    int x = (int)(c * BG_COL_PX) - (int)off;
    return x <= -BG_COL_PX ? x + (int)period : x;
}
