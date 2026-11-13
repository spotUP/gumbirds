-- 68k sound command ids from build/snd_commands.h (generated from sample-map.yaml); shared by sound_check.lua and flier_check.lua.
local base, ids = 4, {}
for line in io.lines("build/snd_commands.h") do
  local n, off = line:match("#define (SND_[A-Z_]+) %(_SND_CMD_BASE_GENERATED %+ (%d+)%)")
  if n then ids[n] = base + tonumber(off) end
end
return ids
