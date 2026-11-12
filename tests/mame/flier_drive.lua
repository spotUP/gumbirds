-- Shared input driver for the MAME checks that need a run to end: walk the flier right off its island (R01: start island 0; MIDDLE below is island 2, whose edge 244 the walk never reaches, so the steer-back half is idle and the flier falls into the water), then
-- steer it back over the gap (left + flap until vx is under half a flap thrust) so it drops into the water (same sequence as flier_check.lua).
-- The island edge comes from the game's own stage table: the middle island (index 2 of stage_platforms, src/core/stage.c)
-- read from the ROM at BRAWL_STAGE_ADDR (nm symbol stage_platforms; StagePlatform = four int16 x, y, w, h). The flier is
-- past the edge once its centre is one flier width (4 px, FLIER_HALF_W * 2) beyond x + w.
-- Usage: local drive = dofile("tests/mame/flier_drive.lua")(mem, flow_addr, lay, abtn, lbtn, rbtn)
--        drive()  -- once per frame while PLAYING
-- lay = BRAWL_FLIER_LAYOUT numbers (tests/mame/flier_probe.c): X at lay[6], VX at lay[8], on_ground at lay[12].
return function(mem, flow_addr, lay, abtn, lbtn, rbtn)
  local O_X, O_VX, O_GROUND = lay[6], lay[8], lay[12]
  local function s32(v) return v >= 0x80000000 and v - 0x100000000 or v end
  local stage_addr = tonumber(os.getenv("BRAWL_STAGE_ADDR") or "", 16)
  assert(stage_addr, "flier_drive: BRAWL_STAGE_ADDR missing")
  local MIDDLE = 2
  local past_edge = mem:read_i16(stage_addr + 8 * MIDDLE) + mem:read_i16(stage_addr + 8 * MIDDLE + 4) + 4
  local steering, tick = false, 0
  return function()
    local fx = s32(mem:read_u32(flow_addr + O_X)) / 65536
    local vx = s32(mem:read_u32(flow_addr + O_VX)) / 65536
    local on_ground = mem:read_u8(flow_addr + O_GROUND)
    -- A computer flier can bump the player back onto the island (body-contact reflect): walk off again.
    if steering and on_ground == 1 then steering = false end
    if not steering and (on_ground == 1 or fx < past_edge) then
      rbtn:set_value(1); abtn:set_value(0); lbtn:set_value(0)
      return
    end
    steering = true
    -- Stop once vx is under half a flap's sideways thrust (FLIER_FLAP_THRUST_X 38229 = 0.583 px, src/core/tuning.h): from the
    -- walk speed 1.39 two flaps leave +0.22 and the flier sinks into the gap. Waiting for vx <= 0 took a third flap: -0.36
    -- plus its lift carried the flier back onto the middle island under the low gum gravity, and the drive looped until
    -- the watchdog (thoughts/spot/2026-11-12-test-flier-hazard-regression.md).
    if vx <= 38229 / 65536 / 2 then
      abtn:set_value(0); rbtn:set_value(0); lbtn:set_value(0)
    else
      rbtn:set_value(0); lbtn:set_value(1)
      abtn:set_value((tick % 6) < 2 and 1 or 0)
      tick = tick + 1
    end
  end
end
