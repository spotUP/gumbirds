#ifndef GFX_H
#define GFX_H
/*
 * The only place that writes the LSPC VRAM registers and palette RAM. Everything else calls gfx_*
 * (RAM only, see core/vram_queue.h); gfx_flush runs in the vblank callback and stops before its estimated time
 * (vq_cost) passes GFX_FLUSH_BUDGET_US, so the writes stay inside vblank (make test-vblank).
 */
#include <ngdevkit/neogeo.h>

/* Flush time per vblank in microseconds. Vblank is 40 lines of 64 us = 2560 us from the interrupt ack; the flush
 * starts about 30 us after it. 2000 us leaves about 8 lines of margin for cost estimate error
 * (thoughts/shared/research/2026-11-09_vblank-writes.md). */
#define GFX_FLUSH_BUDGET_US 2000u

void gfx_init(void);                /* forget the hardware state (boot, BIOS resume) */
#include "core/vram_queue.h"
extern VramQueue g_gfx_q;
void gfx_word_push(u16 addr, u16 val); /* gfx_word without the dedupe test */
/* SCB2/SCB3/SCB4 word, written only when it changes. Inline: the main loop calls it about a hundred times per
 * frame and most words are unchanged; a call per word was the largest part of the frame logic (PC profile,
 * thoughts/shared/research/2026-11-09_test-laser-hit-fix.md, section Loop 60 Hz fix). */
static inline void gfx_word(u16 addr, u16 val) { if (!vq_scb_same(&g_gfx_q, addr, val)) gfx_word_push(addr, val); }
void gfx_scb1_word(u16 sprite, u16 val);
void gfx_strip(u16 sprite, const u16 *tiles, u16 base, u8 rows, u16 attr);
void gfx_pal(u16 idx, u16 val);
void gfx_text(u8 x, u8 y, u8 pal, const char *s);
void gfx_center_text(u8 y, u8 pal, const char *s);
void gfx_cls(void);
void gfx_commit(void);              /* fold the fix layer changes into the queue (end of the frame's logic) */
void gfx_wait_vblank(void);         /* park until the next vblank; the vblank callback flushes the queue */
void gfx_flush(void);               /* runs only from the vblank callback in gfx.c */
void gfx_drain(void);               /* init only: wait vblank and flush until the queue is empty */
u16 gfx_last_flush_us(void);         /* estimated time of the last flush */

extern volatile u16 g_gfx_flush_max; /* longest estimated flush time (us) since boot (test sentinel) */

/* One sprite block of `cols` columns at hardware sprite `first`: column strips, then size and position on the first, sticky
 * (SCB3 bit 6) followers. `tiles` is column-major (cols x rows) tile numbers relative to `base`. */
void gfx_sprite_block(u16 first, u8 cols, u8 rows, const u16 *tiles, u16 base, u16 attr, int left, int top);
#endif
