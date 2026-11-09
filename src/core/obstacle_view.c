#include "obstacle_view.h"
#include "game.h"

uint8_t obstacle_view_ticks(uint8_t type) {
    switch (type) {
    case OB_VENT:  return 12; /* slow lamp and grille flicker */
    case OB_CABLE: return 3;  /* fast sparks */
    case OB_DRONE: return 2;  /* rotor blur */
    case OB_BOT:   return 8;  /* tread shuffle */
    default:       return 0;
    }
}

uint8_t obstacle_view_frame(uint8_t type, uint32_t frame, uint8_t frame_count) {
    uint8_t t = obstacle_view_ticks(type);
    if (t == 0 || frame_count == 0) {
        return 0;
    }
    return (uint8_t)((frame / t) % frame_count);
}
