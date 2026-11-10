-- Shared input driver for the MAME checks that need a run to end: walk the flier right off the middle island, then
-- steer it back over the gap (left + flap until vx <= 0) so it drops into the water (same sequence as flier_check.lua).
-- Usage: local drive = dofile("tests/mame/flier_drive.lua")(mem, flow_addr, lay, abtn, lbtn, rbtn)
--        drive()  -- once per frame while PLAYING
-- lay = BRAWL_FLIER_LAYOUT numbers (tests/mame/flier_probe.c): X at lay[6], VX at lay[8], on_ground at lay[12].
return function(mem, flow_addr, lay, abtn, lbtn, rbtn)
  local O_X, O_VX, O_GROUND = lay[6], lay[8], lay[12]
  local function s32(v) return v >= 0x80000000 and v - 0x100000000 or v end
  local steering, tick = false, 0
  return function()
    local fx = s32(mem:read_u32(flow_addr + O_X)) / 65536
    local vx = s32(mem:read_u32(flow_addr + O_VX)) / 65536
    local on_ground = mem:read_u8(flow_addr + O_GROUND)
    -- A computer flier can bump the player back onto the island (body-contact reflect): walk off again.
    if steering and on_ground == 1 then steering = false end
    if not steering and (on_ground == 1 or fx < 212) then
      rbtn:set_value(1); abtn:set_value(0); lbtn:set_value(0)
      return
    end
    steering = true
    if vx <= 0 then
      abtn:set_value(0); rbtn:set_value(0); lbtn:set_value(0)
    else
      rbtn:set_value(0); lbtn:set_value(1)
      abtn:set_value((tick % 6) < 2 and 1 or 0)
      tick = tick + 1
    end
  end
end
