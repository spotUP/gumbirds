-- Shared by ring_check.lua and camera_check.lua: keeps the computer fliers out of contact with the hero (test side only, no game hook).
-- Every PLAYING frame each live computer flier slot is written to the hero's y and to x = hero x + offsets[(i % #offsets) + 1], wrapped on the ring.
-- The game derives the pool sprites from game.cpu (src/main.c pool_sync_cpus), so these writes are what the draw path shows.
-- flay is the flier_probe.c layout (cpu_count idx 13, cpu[0].x idx 17, cpu[0].y idx 18, cpu[1].x idx 20, hero x idx 6, hero y idx 7).
return function(mem, flow_addr, flay, arena_w)
  local O_X, O_Y, O_CPUN, O_C0X, O_C0Y, O_C1X = flay[6], flay[7], flay[13], flay[17], flay[18], flay[20]
  local stride = O_C1X - O_C0X
  return function(hero_x_px, offsets)
    for i = 0, mem:read_u8(flow_addr + O_CPUN) - 1 do
      mem:write_u32(flow_addr + O_C0X + i * stride, ((hero_x_px + offsets[(i % #offsets) + 1]) % arena_w) << 16)
      mem:write_u32(flow_addr + O_C0Y + i * stride, mem:read_u32(flow_addr + O_Y))
    end
  end
end
