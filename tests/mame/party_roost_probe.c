/* Compiled with the 68000 compiler (-S) by make test-party-roost; tests/mame/party_roost_check.lua reads the Roost Rule state from RAM with these
 * values (target ABI: int is 32 bit). Order is fixed:
 * 1 flow state, 2 Game.players, 3 Game.mode, 4 Game.party_rule, 5 Game.score, 6 Game.cpu_count, 7 Roost.idx, 8 Roost.timer,
 * 9 Roost.ticks[0], 10 hero[0].x, 11 hero[0].y, 12 hero[0].vx, 13 hero[0].vy, 14 sizeof(StagePlatform), then FLOW_PLAYING,
 * GAME_MODE_ARENA, PARTY_ROOST, ROOST_ROUND_FRAMES, STAGE_PLATFORM_COUNT (15..19), then Flow.mode, Flow.party_rule, GAME_MODE_PARTY (20..22), cpu[0].y offset and sizeof(Flier) (23, 24). */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(players), G(mode), G(party_rule), G(score), G(cpu_count), G(roost) + offsetof(Roost, idx),
    G(roost) + offsetof(Roost, timer), G(roost) + offsetof(Roost, ticks), G(hero) + offsetof(Flier, x), G(hero) + offsetof(Flier, y),
    G(hero) + offsetof(Flier, vx), G(hero) + offsetof(Flier, vy), sizeof(StagePlatform),
    FLOW_PLAYING, GAME_MODE_ARENA, PARTY_ROOST, ROOST_ROUND_FRAMES, STAGE_PLATFORM_COUNT,
    offsetof(Flow, mode), offsetof(Flow, party_rule), GAME_MODE_PARTY, G(cpu) + offsetof(Flier, y), sizeof(Flier),
};
