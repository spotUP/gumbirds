#include "bg_scroll.h"

uint32_t bg_plane_offset(uint32_t cam_px, uint32_t k) { return (cam_px * k) >> 4; }

int bg_plane_x(uint32_t cam_px, uint32_t k) { return -(int)bg_plane_offset(cam_px, k); }
