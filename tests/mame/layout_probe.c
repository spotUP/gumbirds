/* Compiled with the 68000 compiler (-S) by make test; the Lua script reads obstacle state from RAM
 * with these offsets, so the target ABI (2-byte alignment) is used, not the host one. */
#include <stddef.h>
#include "../../src/core/flow.h"
unsigned int probe[] = {
    offsetof(Flow, game) + offsetof(Game, obs), sizeof(Obstacle), MAX_OBSTACLES,
    offsetof(Obstacle, x), offsetof(Obstacle, y), offsetof(Obstacle, w), offsetof(Obstacle, h),
    offsetof(Obstacle, type), offsetof(Obstacle, active),
};
