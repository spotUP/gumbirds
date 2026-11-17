-- PROF temp: time from each g_prof_mark write to the next one, summed per mark value per frame (mark 1 starts a frame, 12 ends it)
local mem, addr = ...
local LINE_S = manager.machine.screens[":screen"].scan_period
local NAMES = {[1]="input",[2]="flow_pre",[3]="hazsel+view+sound",[4]="draw",[5]="hero_and_mode",[6]="hazard_step",[7]="arcade_elems",[8]="island_step",[9]="gum+splash",[10]="logo..trip",[11]="bg_update",
  [20]="ga_head",[21]="ga_elems_step",[22]="ga_player",[23]="cpu_pump",[24]="cpu_ai",[25]="cpu_avoid",[26]="cpu_flier",[27]="cpu_apply",[28]="broad",[29]="pairs",[30]="bodykill",[31]="ga_tail"}
local ORDER = {1,2,20,21,22,23,24,25,26,27,28,29,30,31,3,4,5,6,7,8,9,10,11}
local seq, P = {}, {}
local tap = mem:install_write_tap(addr & ~1, addr | 1, "prof", function(off, data, mask)
  local v
  if (addr & 1) == 0 then if (mask & 0xff00) == 0 then return end v = (data >> 8) & 0xff
  else if (mask & 0xff) == 0 then return end v = data & 0xff end
  if v == 1 then seq = {} end
  seq[#seq + 1] = { v, manager.machine.time:as_double() }
end)
local M = { tap = tap }
function M.frame(stage, steady, line)
  if not steady or #seq < 2 or seq[#seq][1] ~= 12 then return end
  local p = P[stage] or { n = 0, sum = {}, max = {}, worst = -1, wb = {} }
  P[stage] = p
  p.n = p.n + 1
  local d = {}
  for k = 1, #seq - 1 do local v = seq[k][1]; d[v] = (d[v] or 0) + (seq[k + 1][2] - seq[k][2]) / LINE_S end
  for v, x in pairs(d) do p.sum[v] = (p.sum[v] or 0) + x; if x > (p.max[v] or 0) then p.max[v] = x end end
  if line > p.worst then p.worst = line; p.wb = d end
end
function M.report()
  for st = 1, 12 do local p = P[st]
    if p then
      local a, w = {}, {}
      for _, v in ipairs(ORDER) do a[#a + 1] = string.format("%s %.1f/%.1f", NAMES[v], (p.sum[v] or 0) / p.n, p.max[v] or 0); w[#w + 1] = string.format("%s %.1f", NAMES[v], p.wb[v] or 0) end
      print(string.format("PROF stage %d n %d mean/max: %s", st, p.n, table.concat(a, ", ")))
      print(string.format("PROF stage %d worst %.1f: %s", st, p.worst, table.concat(w, ", ")))
    end
  end
end
return M
