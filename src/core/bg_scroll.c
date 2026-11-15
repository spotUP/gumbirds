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

uint16_t bg_fade_color(uint16_t c, uint8_t level)
{
    uint16_t r = (uint16_t)((((c >> 8) & 0xF) << 1) | ((c >> 14) & 1));
    uint16_t g = (uint16_t)((((c >> 4) & 0xF) << 1) | ((c >> 13) & 1));
    uint16_t b = (uint16_t)(((c & 0xF) << 1) | ((c >> 12) & 1));
    r = (uint16_t)(r * level / BG_FADE_MAX); /* 5 bit * 16 fits u16; the divisor is a power of two */
    g = (uint16_t)(g * level / BG_FADE_MAX);
    b = (uint16_t)(b * level / BG_FADE_MAX);
    return (uint16_t)((c & 0x8000) | ((r & 1) << 14) | ((g & 1) << 13) | ((b & 1) << 12) | ((r >> 1) << 8) | ((g >> 1) << 4) | (b >> 1));
}

void bg_fade_start(BgFade *f)
{
    if (f->phase == BGF_IDLE) f->level = BG_FADE_MAX;
    f->phase = BGF_OUT;
}

void bg_fade_abort(BgFade *f)
{
    if (f->phase == BGF_OUT) f->phase = BGF_IN;
}

void bg_fade_swapped(BgFade *f)
{
    if (f->phase == BGF_DARK) f->phase = BGF_IN;
}

uint8_t bg_fade_step(BgFade *f)
{
    if (f->phase == BGF_OUT) {
        if (f->level) f->level--;
        if (!f->level) { f->phase = BGF_DARK; return 1; }
    } else if (f->phase == BGF_IN && f->level < BG_FADE_MAX) {
        f->level++;
    }
    return 0;
}

void bg_fade_settle(BgFade *f, uint8_t synced)
{
    if (f->phase == BGF_IN && f->level == BG_FADE_MAX && synced) f->phase = BGF_IDLE;
}
