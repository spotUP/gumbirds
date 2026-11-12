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

#define GFX_AUTOANIM_DEFAULT_FRAMES 1 /* counter speed at boot and when no auto-animated strip is shown */
void gfx_autoanim_speed(u8 frames_per_step); /* LSPC auto-animation: counter steps every N video frames (REG_LSPCMODE bits 15..8 = N-1) */
extern volatile u8 g_autoanim_frames; /* frames per step last set (test sentinel) */
extern volatile u32 g_vq_ramp_ops;  /* VQ_RAMP ops written by gfx_flush since boot (test sentinel: the plane scroll ran through the generated path) */
extern volatile u16 g_swap_count;     /* bank swaps done by gfx_flush since boot (test sentinel) */
/* Show the strip whose head SCB3 address is head0 or head1, one at a time, swapping at each wrap of the animation
 * counter (see gfx_flush). show_word is the head SCB3 word of the shown strip. Both heads must be hidden (0). */
void gfx_swap_arm(u16 head0, u16 head1, u8 cols, u16 show_word); /* cols: SCB3 words per bank, the first at head */
void gfx_swap_disarm(void);
void gfx_init(void);                /* forget the hardware state (boot, BIOS resume) */
#include "core/vram_queue.h"
extern VramQueue g_gfx_q;
void gfx_word_push(u16 addr, u16 val); /* gfx_word without the dedupe test */
/* SCB2/SCB3/SCB4 word, written only when it changes. Inline: the main loop calls it about a hundred times per
 * frame and most words are unchanged; a call per word was the largest part of the frame logic (PC profile,
 * thoughts/shared/research/2026-11-09_test-laser-hit-fix.md, section Loop 60 Hz fix). */
static inline void gfx_word(u16 addr, u16 val) { if (!vq_scb_same(&g_gfx_q, addr, val)) gfx_word_push(addr, val); }
void gfx_strip(u16 sprite, const u16 *tiles, u16 base, u8 rows, u16 attr);
/* Strided SCB2..SCB4 run (vq_scb_run): vals[k] goes to addr + k * mod, one queue op for all changed words. For
 * per-frame words of many sprites at a fixed stride, e.g. the head SCB3/SCB4 of every pool object. */
void gfx_scb_run(u16 addr, u16 mod, const u16 *vals, u8 n);
static inline void gfx_scb_forget(u16 addr, u16 n) { vq_scb_forget(&g_gfx_q, addr, n); } /* see vq_scb_forget */
void gfx_scb_ramp(u16 addr, u8 n, u8 split, u16 v1, u16 v2);  /* VQ_RAMP: words generated in the flush (vram_queue.h) */
/* One column with a per-tile attribute: `pairs` = rows x {tile, attribute}; for init-time art that mixes palettes in a column. */
void gfx_strip_attr(u16 sprite, const u16 *pairs, u16 base, u8 rows);
void gfx_pal(u16 idx, u16 val);
void gfx_text(u8 x, u8 y, u8 pal, const char *s);
/* One fix cell: S-ROM tile number with palette pal (goes through the fix shadow, so an unchanged cell sends nothing). */
void gfx_fix_tile(u8 x, u8 y, u8 pal, u16 tile);
void gfx_text_backed(u8 x, u8 y, u8 pal, const char *s);
void gfx_text_tall(u8 x, u8 y, u8 pal, const char *s);
void gfx_text_tall_backed(u8 x, u8 y, u8 pal, const char *s);
void gfx_center_text(u8 y, u8 pal, const char *s);
void gfx_cls(void);
void gfx_commit(void);              /* fold the fix layer changes into the queue (end of the frame's logic) */
void gfx_wait_vblank(void);         /* park until the next vblank; the vblank callback flushes the queue */
void gfx_flush(void);               /* runs only from the vblank callback in gfx.c */
void gfx_drain(void);               /* init only: wait vblank and flush until the queue is empty */
u16 gfx_last_flush_us(void);         /* estimated time of the last flush */

extern volatile u16 g_gfx_flush_max;
extern volatile u16 g_pal_words_frame_max; /* most palette words written by one flush since boot (test sentinel) */
extern volatile u16 g_gfx_backlog_max; /* most ops still queued after a flush since boot (test sentinel) */ /* longest estimated flush time (us) since boot (test sentinel) */

/* One sprite block of `cols` columns at hardware sprite `first`: column strips, then size and position on the first, sticky
 * (SCB3 bit 6) followers. `tiles` is column-major (cols x rows) tile numbers relative to `base`. */
void gfx_sprite_block(u16 first, u8 cols, u8 rows, const u16 *tiles, u16 base, u16 attr, int left, int top);
/* The SCB2..4 half of gfx_sprite_block (shrink, height, position; chain for columns 1..cols-1) without the tile
 * strips: for a block whose SCB1 tiles are already in VRAM and only moved. The words dedupe in gfx_word. */
void gfx_sprite_place(u16 first, u8 cols, u8 rows, int left, int top);
/* The parts of gfx_sprite_block, for a caller that sends the head SCB3/SCB4 words itself (gfx_scb_run): the column
 * strips; SCB2 of every column plus the sticky SCB3 of columns 1..cols-1; the head SCB3 (height, y) and SCB4 (x). */
void gfx_sprite_strips(u16 first, u8 cols, u8 rows, const u16 *tiles, u16 base, u16 attr);
void gfx_sprite_chain(u16 first, u8 cols);
/* Full size (SCB2 0xFFF) for each column and no sticky SCB3 bit: every column is placed on its own (ring columns). */
void gfx_sprite_unchained(u16 first, u8 cols);
static inline u16 gfx_scb3_word(u8 rows, int top) { return (u16)((((496 - top) & 0x1FF) << 7) | rows); }
static inline u16 gfx_scb4_word(int left) { return VQ_SCB4_X(left); }
#endif
