/* Compiled with the 68000 compiler (-S) by make test-laser; tests/mame/laser_check.lua reads the game
 * state from RAM with these offsets (target ABI, not the host one). Order is fixed:
 * flow_state, frame, bonus, heat, lockout, chain, kills, shots, kill_x, kill_y, kill_frame,
 * bolts, sizeof(Bolt), MAX_BOLTS, Bolt x, y, active, then obstacle offsets as in layout_probe.c,
 * then lives, hero_h, hero_vy, invuln. */
#include <stddef.h>
#include "../../src/core/flow.h"
#define G(m) (offsetof(Flow, game) + offsetof(Game, m))
unsigned int probe[] = {
    offsetof(Flow, state), G(frame), G(bonus), G(heat), G(lockout), G(chain), G(kills), G(shots),
    G(kill_x), G(kill_y), G(kill_frame), G(bolts), sizeof(Bolt), MAX_BOLTS,
    offsetof(Bolt, x), offsetof(Bolt, y), offsetof(Bolt, active),
    G(obs), sizeof(Obstacle), MAX_OBSTACLES,
    offsetof(Obstacle, x), offsetof(Obstacle, y), offsetof(Obstacle, w), offsetof(Obstacle, h),
    offsetof(Obstacle, type), offsetof(Obstacle, active),
    G(lives), G(hero_h), G(hero_vy), G(invuln),
};
