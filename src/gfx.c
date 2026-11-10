#include <ngdevkit/ng-video.h>
#include <ngdevkit/ng-fix.h>
#include "gfx.h"
#include "core/vram_queue.h"

VramQueue g_gfx_q; /* extern in gfx.h for the inline gfx_word dedupe test */
static u16 g_last_us;
volatile u16 g_gfx_flush_max;
volatile u16 g_pal_words_frame_max; /* most palette words written in one flush (test sentinel) */
volatile u16 g_gfx_backlog_max; /* most queue ops left over after a flush (test sentinel; init drains count too) */

void gfx_init(void) { vq_init(&g_gfx_q); }

/* The mode register is written by the next gfx_flush, so like every LSPC write it lands inside vblank (tests/mame/
 * vblank_check.lua counts register writes outside it). Timer interrupt off. */
static volatile u16 g_lspc_mode;
static volatile u8 g_lspc_mode_dirty;
volatile u8 g_autoanim_frames = GFX_AUTOANIM_DEFAULT_FRAMES;
void gfx_autoanim_speed(u8 frames_per_step) {
    g_autoanim_frames = frames_per_step;
    g_lspc_mode = (u16)((frames_per_step - 1) << 8);
    g_lspc_mode_dirty = 1;
}

/* Bank swap: two hidden-twin strips, one shown. A strip is shown by its head SCB3 word (height and y) and hidden by
 * 0 there. When the 3 bit animation counter (REG_LSPCMODE bits 2..0, read) is about to wrap to 0 the flush shows the other
 * strip: bank 0 holds the animation steps 0..7 of its 16 frames and bank 1 the steps 8..15. The words go straight to
 * VRAM inside the flush (vblank), never through the queue. Armed once per match by the hazard module. */
static volatile u16 g_swap_head[2], g_swap_show;
static volatile u8 g_swap_on, g_swap_prev, g_swap_vis, g_swap_run;
void gfx_swap_arm(u16 head0, u16 head1, u16 show_word) {
    g_swap_on = 0;
    g_swap_head[0] = head0; g_swap_head[1] = head1; g_swap_show = show_word;
    g_swap_prev = 0xFF; /* only a run of reads of 7 that began after a read of 6 is trusted */
    g_swap_run = 0;
    g_swap_vis = 1;     /* the first swap shows bank 0 */
    g_swap_on = 1;
}
void gfx_swap_disarm(void) { g_swap_on = 0; }
volatile u16 g_swap_count;

/* A full queue only happens while loading (video_init); wait for vblank, write, retry. */
/* The BIOS vblank handler calls rom_callback_VBlank first and then its own SYSTEM_IO routine, which runs for
 * about the whole 40 line vblank. A main loop woken by a flag set in the callback therefore resumes at the END of
 * vblank and every flush write lands on visible lines. So the flush runs inside the callback, at the start of
 * vblank, while the main thread is parked in gfx_wait_vblank (it then touches no queue state). When the main
 * thread is not parked (the frame logic overran) the callback skips the flush: the queue keeps its ops for the
 * next vblank. This replaces the ngdevkit callback and ng_wait_vblank. */
static volatile u8 g_vb_flag;
static volatile u8 g_parked;

void rom_callback_VBlank(void) {
    if (g_parked) gfx_flush();
    g_vb_flag = 1;
}

void gfx_wait_vblank(void) {
    g_vb_flag = 0;
    g_parked = 1;
    while (!g_vb_flag) { }
    g_parked = 0;
}

void gfx_drain(void) {
    while (vq_pending(&g_gfx_q)) gfx_wait_vblank();
}

#define RETRY(call) do { while (!(call)) gfx_drain(); } while (0)

void gfx_word_push(u16 addr, u16 val) { RETRY(vq_scb_word_push(&g_gfx_q, addr, val)); }
void gfx_strip(u16 sprite, const u16 *tiles, u16 base, u8 rows, u16 attr) { RETRY(vq_strip(&g_gfx_q, sprite, tiles, base, rows, attr)); }
void gfx_scb_run(u16 addr, u16 mod, const u16 *vals, u8 n) { RETRY(vq_scb_run(&g_gfx_q, addr, mod, vals, n)); }
void gfx_strip_attr(u16 sprite, const u16 *pairs, u16 base, u8 rows) { RETRY(vq_strip_attr(&g_gfx_q, sprite, pairs, base, rows)); }
void gfx_pal(u16 idx, u16 val) { RETRY(vq_pal(&g_gfx_q, idx, val)); }

void gfx_text(u8 x, u8 y, u8 pal, const char *s) {
    vq_fix_text(&g_gfx_q, x, y, (u16)(pal << 12), SROM_TXT_TILE_OFFSET, s);
}

void gfx_center_text(u8 y, u8 pal, const char *s) {
    u8 n = 0;
    while (s[n]) n++;
    gfx_text((u8)((VQ_FIX_COLS - n) / 2), y, pal, s);
}

void gfx_cls(void) { vq_fix_fill(&g_gfx_q, SROM_EMPTY_TILE); }

void gfx_commit(void) { RETRY(vq_fix_commit(&g_gfx_q)); }

void gfx_sprite_block(u16 first, u8 cols, u8 rows, const u16 *tiles, u16 base, u16 attr, int left, int top) {
    gfx_sprite_strips(first, cols, rows, tiles, base, attr);
    gfx_sprite_place(first, cols, rows, left, top);
}

void gfx_sprite_strips(u16 first, u8 cols, u8 rows, const u16 *tiles, u16 base, u16 attr) {
    u8 done;
    while ((done = vq_strips(&g_gfx_q, first, cols, rows, tiles, base, attr)) < cols) {
        gfx_drain(); /* queue full: same as RETRY, continue with the columns not queued yet */
        first = (u16)(first + done);
        cols = (u8)(cols - done);
        tiles += done * rows;
    }
}

void gfx_sprite_chain(u16 first, u8 cols) {
    gfx_word((u16)(ADDR_SCB2 + first), 0xFFF);
    for (u8 c = 1; c < cols; c++) {
        gfx_word((u16)(ADDR_SCB2 + first + c), 0xFFF);
        gfx_word((u16)(ADDR_SCB3 + first + c), 1 << 6);
    }
}

void gfx_sprite_place(u16 first, u8 cols, u8 rows, int left, int top) {
    gfx_word((u16)(ADDR_SCB3 + first), gfx_scb3_word(rows, top));
    gfx_word((u16)(ADDR_SCB4 + first), gfx_scb4_word(left));
    gfx_sprite_chain(first, cols);
}

/* Runs in the vblank interrupt. The queue head and count live in registers for the whole loop and are stored once
 * at the end: the u16 register writes may alias the queue (same type), so gcc reloaded and stored them on every op,
 * which with the 12-byte op indexing and a 32-bit budget compare cost about 370 cycles (31 us) per word op. Now the
 * op is walked by pointer and its cost is precomputed (vq_cost), so an op is a few compares plus its writes
 * (thoughts/shared/research/2026-11-09_object-pool.md, section Flush speed fix). REG_VRAMMOD stays 1 except
 * inside a VQ_RUN op. */
void gfx_flush(void) {
    VramQueue *const q = &g_gfx_q;
    u16 count = q->count, head = q->head, left = GFX_FLUSH_BUDGET_US;
    u16 pal_words = 0;
    const VqOp *op = &q->ops[head];
    volatile u16 *const vaddr = REG_VRAMADDR, *const vrw = REG_VRAMRW, *const vmod = REG_VRAMMOD;
    *vmod = 1;
    if (g_lspc_mode_dirty) { *REG_LSPCMODE = g_lspc_mode; g_lspc_mode_dirty = 0; }
    if (g_swap_on) {
        u8 ctr = (u8)(*REG_LSPCMODE & 7);
        /* The counter steps between the flush and the next frame, so a flush reads the value that was displayed in
         * the frame before it. The frames per step th flush in a row that reads 7 is the one right before the first
         * frame of step 0: swapping there shows the new bank from step 0 on, with no stray frame (measured in MAME:
         * a swap on the first read of 0 shows the old bank's step 0 for one extra frame, one flush earlier shows the
         * new bank's step 7 for one frame). */
        if (ctr != 7) g_swap_run = 0;
        else if (g_swap_run || g_swap_prev == 6) g_swap_run++;
        if (ctr == 7 && g_swap_run == g_autoanim_frames) {
            g_swap_vis ^= 1;
            *vaddr = (u16)(ADDR_SCB3 + g_swap_head[g_swap_vis]); *vrw = g_swap_show;
            *vaddr = (u16)(ADDR_SCB3 + g_swap_head[g_swap_vis ^ 1]); *vrw = 0;
            g_swap_count++;
        }
        g_swap_prev = ctr;
    }
    for (; count; count--) {
        u16 c = op->cost;
        if (c > left) break;
        left = (u16)(left - c);
        u8 kind = op->kind;
        if (kind == VQ_WORD) {
            *vaddr = op->a;
            *vrw = op->b;
        } else if (kind == VQ_RUN) {
            const u16 *s = op->tiles;
            u16 m = op->b;
            u8 r = op->rows;
            *vaddr = op->a;
            *vmod = m;
            do { *vrw = *s; s += m; } while (--r);
            *vmod = 1;
        } else if (kind == VQ_STRIP) {
            const u16 *t = op->tiles;
            u16 base = op->b, attr = op->c;
            u8 r = op->rows;
            *vaddr = (u16)(ADDR_SCB1 + op->a * 64);
            do { *vrw = (u16)(base + *t++); *vrw = attr; } while (--r);
        } else if (kind == VQ_STRIP_ATTR) {
            const u16 *t = op->tiles;
            u16 base = op->b;
            u8 r = op->rows;
            *vaddr = (u16)(ADDR_SCB1 + op->a * 64);
            do { *vrw = (u16)(base + t[0]); *vrw = t[1]; t += 2; } while (--r);
        } else {
            MMAP_PALBANK1[op->a] = op->b;
            pal_words++;
        }
        op++;
        if (++head == VQ_CAP) { head = 0; op = q->ops; }
    }
    q->head = head;
    q->count = count;
    u16 us = (u16)(GFX_FLUSH_BUDGET_US - left);
    g_last_us = us;
    if (us > g_gfx_flush_max) g_gfx_flush_max = us;
    if (pal_words > g_pal_words_frame_max) g_pal_words_frame_max = pal_words;
    if (count > g_gfx_backlog_max) g_gfx_backlog_max = count;
}

u16 gfx_last_flush_us(void) { return g_last_us; }
