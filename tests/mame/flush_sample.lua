-- Flush saturation sampler (measurement only). dofile'd by a check script: local fs = dofile("tests/mame/flush_sample.lua")(mem); call fs.frame() each
-- frame_done and fs.report(label) at the end. Env BRAWL_LASTUS_ADDR, BRAWL_DEFER_ADDR (g_gfx_defer_last), BRAWL_FLUSHN_ADDR (g_gfx_flush_n), hex.
return function(mem)
  local function a(n) return tonumber(os.getenv(n) or "", 16) end
  local A_US, A_DEF, A_N = a("BRAWL_LASTUS_ADDR"), a("BRAWL_DEFER_ADDR"), a("BRAWL_FLUSHN_ADDR")
  local S = { flushes = 0, sat = 0, eq1800 = 0, defer_max = 0, defer_sum = 0, us_max = 0, hist = {}, last_n = nil, first_sat = nil, frames = 0 }
  function S.frame()
    if not (A_US and A_DEF and A_N) then return end
    S.frames = S.frames + 1
    local n = mem:read_u16(A_N)
    if n == S.last_n then return end
    S.last_n = n
    local us, d = mem:read_u16(A_US), mem:read_u16(A_DEF)
    S.flushes = S.flushes + 1
    if us > S.us_max then S.us_max = us end
    if us == 1800 then S.eq1800 = S.eq1800 + 1 end
    local b = math.min(us // 200, 9); S.hist[b] = (S.hist[b] or 0) + 1
    if d > 0 then S.sat = S.sat + 1; S.defer_sum = S.defer_sum + d; S.first_sat = S.first_sat or S.frames end
    if d > S.defer_max then S.defer_max = d end
  end
  function S.report(label)
    local h = {}
    for i = 0, 9 do h[#h + 1] = string.format("%d-%d:%d", i * 200, i * 200 + 199, S.hist[i] or 0) end
    return string.format("FLUSH[%s] flushes %d, us==1800 %d, deferred-flushes %d (%.1f%%), defer max %d avg-when-sat %.1f, us max %d, hist %s",
      label, S.flushes, S.eq1800, S.sat, S.flushes > 0 and 100 * S.sat / S.flushes or 0, S.defer_max, S.sat > 0 and S.defer_sum / S.sat or 0, S.us_max, table.concat(h, " "))
  end
  return S
end
