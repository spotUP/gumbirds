/* Compiled with the 68000 compiler (-S) by make test-arcade; tests/mame/arcade_check.lua reads the arcade state from RAM with
 * these values (target ABI: int is 32 bit). Order is fixed:
 * 1 flow state, 2 Game.mode, 3 arc.stage, 4 arc.state, 5 lives.lives, 6 lives.state, 7 lives.countdown, 8 cpu_count,
 * 9 cpu[0].state, 10 sizeof(Flier), 11 player Flier.state, 12 score, 13 over, 14 lives.score,
 * then the enum and knob values the script compares with: 15 FLOW_PLAYING, 16 GAME_MODE_ARCADE, 17 ARC_PLAY, 18 ARC_CLEAR,
 * 19 ARC_LIFE_PLAY, 20 ARC_LIFE_CONTINUE, 21 ARC_LIVES_START, 22 ARC_CLEAR_FRAMES, 23 ARC_CONTINUE_FRAMES, 24 FLIER_GONE,
 * 25 ISLAND_SPRITE, 26 ISLAND_COUNT, 27 FLOW_GAME_OVER, 28 ARC_LIFE_ENDED, 29 ISLAND_TILE_BASE, 30 ISLAND_TILE_COUNT, 31 ISLAND_PAL_SLOT, 32 bonus.nlive, 33 ARC_BONUS, 34 bonus.timer (int16_t), 35 ARC_BONUS_LIVE_MAX, 36 res.active (u8). */
#include <stddef.h>
#include "../../src/core/flow.h"
#include "../../src/sprite_slots.h"
#include "../../src/vram_layout.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(mode), G(arc) + offsetof(ArcRun, stage), G(arc) + offsetof(ArcRun, state),
    G(lives) + offsetof(ArcLives, lives), G(lives) + offsetof(ArcLives, state), G(lives) + offsetof(ArcLives, countdown),
    G(cpu_count), G(cpu) + offsetof(Flier, state), sizeof(Flier), G(flier) + offsetof(Flier, state), G(score), G(over),
    G(lives) + offsetof(ArcLives, score),
    FLOW_PLAYING, GAME_MODE_ARCADE, ARC_PLAY, ARC_CLEAR, ARC_LIFE_PLAY, ARC_LIFE_CONTINUE, ARC_LIVES_START, ARC_CLEAR_FRAMES,
    ARC_CONTINUE_FRAMES, FLIER_GONE, ISLAND_SPRITE, ISLAND_COUNT, FLOW_GAME_OVER, ARC_LIFE_ENDED,
    ISLAND_TILE_BASE, ISLAND_TILE_COUNT, ISLAND_PAL_SLOT,
    G(bonus) + offsetof(ArcBonus, nlive), ARC_BONUS,
    G(bonus) + offsetof(ArcBonus, timer), ARC_BONUS_LIVE_MAX, G(res) + offsetof(Result, active),
};
