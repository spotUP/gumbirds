#include <ngdevkit/ng-video.h>
#include <ngdevkit/ng-fix.h>
#include "gfx.h"
#include "core/vram_queue.h"

VramQueue g_gfx_q; /* extern in gfx.h for the inline gfx_word dedupe test */
static u16 g_last_us;
volatile u16 g_gfx_flush_max;

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
void gfx_pal(u16 idx, u16 val) { RETRY(vq_pal(&g_gfx_q, idx, val)); }

void gfx_text(u8 x, u8 y, u8 pal, const char *s) {
    for (; *s && x < VQ_FIX_COLS; s++, x++) vq_fix_put(&g_gfx_q, x, y, (u16)((pal << 12) | (SROM_TXT_TILE_OFFSET + (u8)*s)));
}

void gfx_center_text(u8 y, u8 pal, const char *s) {
    u8 n = 0;
    while (s[n]) n++;
    gfx_text((u8)((VQ_FIX_COLS - n) / 2), y, pal, s);
}

void gfx_cls(void) { vq_fix_fill(&g_gfx_q, SROM_EMPTY_TILE); }

void gfx_commit(void) { RETRY(vq_fix_commit(&g_gfx_q)); }

void gfx_sprite_block(u16 first, u8 cols, u8 rows, const u16 *tiles, u16 base, u16 attr, int left, int top) {
    for (u8 c = 0; c < cols; c++) gfx_strip((u16)(first + c), &tiles[c * rows], base, rows, attr);
    gfx_word((u16)(ADDR_SCB2 + first), 0xFFF);
    gfx_word((u16)(ADDR_SCB3 + first), (u16)((((496 - top) & 0x1FF) << 7) | rows));
    gfx_word((u16)(ADDR_SCB4 + first), (u16)((left & 0x1FF) << 7));
    for (u8 c = 1; c < cols; c++) {
        gfx_word((u16)(ADDR_SCB2 + first + c), 0xFFF);
        gfx_word((u16)(ADDR_SCB3 + first + c), 1 << 6);
    }
}

/* Runs in the vblank interrupt. Kept tight (inline queue access, locals only): per-op overhead is most of the
 * vblank time an op takes, see vq_cost and GFX_FLUSH_BUDGET_US. */
void gfx_flush(void) {
    const VqOp *op;
    u16 next = 0xFFFF;
    u16 us = 0;
    *REG_VRAMMOD = 1;
    while ((op = vq_peek(&g_gfx_q)) != 0 && us + vq_cost(op) <= GFX_FLUSH_BUDGET_US) {
        us = (u16)(us + vq_cost(op));
        if (op->kind == VQ_PAL) {
            MMAP_PALBANK1[op->a] = op->b;
        } else {
            u16 a = op->kind == VQ_STRIP ? (u16)(ADDR_SCB1 + op->a * 64) : op->a;
            if (next != a) *REG_VRAMADDR = a;
            if (op->kind == VQ_STRIP) {
                const u16 *t = op->tiles;
                u16 base = op->b, attr = op->c;
                for (u8 r = op->rows; r; r--) {
                    *REG_VRAMRW = (u16)(base + *t++);
                    *REG_VRAMRW = attr;
                }
                next = (u16)(a + 2 * op->rows);
            } else {
                *REG_VRAMRW = op->b;
                next = (u16)(a + 1);
            }
        }
        vq_pop(&g_gfx_q);
    }
    g_last_us = us;
    if (us > g_gfx_flush_max) g_gfx_flush_max = us;
}

u16 gfx_last_flush_us(void) { return g_last_us; }
