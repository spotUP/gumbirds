#include <ngdevkit/ng-video.h>
#include <ngdevkit/ng-fix.h>
#include "gfx.h"
#include "core/vram_queue.h"

VramQueue g_gfx_q; /* extern in gfx.h for the inline gfx_word dedupe test */
static u16 g_last_us;
volatile u16 g_gfx_flush_max;
volatile u16 g_gfx_backlog_max; /* most queue ops left over after a flush (test sentinel; init drains count too) */

void gfx_init(void) { vq_init(&g_gfx_q); }

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
void gfx_scb1_word(u16 sprite, u16 val) { RETRY(vq_vram_word(&g_gfx_q, (u16)(ADDR_SCB1 + sprite * 64), val)); }
void gfx_strip(u16 sprite, const u16 *tiles, u16 base, u8 rows, u16 attr) { RETRY(vq_strip(&g_gfx_q, sprite, tiles, base, rows, attr)); }
void gfx_scb_run(u16 addr, u16 mod, const u16 *vals, u8 n) { RETRY(vq_scb_run(&g_gfx_q, addr, mod, vals, n)); }
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
    const VqOp *op = &q->ops[head];
    volatile u16 *const vaddr = REG_VRAMADDR, *const vrw = REG_VRAMRW, *const vmod = REG_VRAMMOD;
    *vmod = 1;
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
        } else {
            MMAP_PALBANK1[op->a] = op->b;
        }
        op++;
        if (++head == VQ_CAP) { head = 0; op = q->ops; }
    }
    q->head = head;
    q->count = count;
    u16 us = (u16)(GFX_FLUSH_BUDGET_US - left);
    g_last_us = us;
    if (us > g_gfx_flush_max) g_gfx_flush_max = us;
    if (count > g_gfx_backlog_max) g_gfx_backlog_max = count;
}

u16 gfx_last_flush_us(void) { return g_last_us; }
