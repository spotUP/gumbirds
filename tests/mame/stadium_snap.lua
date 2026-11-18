-- Optional stadium snapshot hook for the Gum Games check scripts (Big Blow, Burst Race, Gum Fling).
-- Env: STADIUM_MOOD (0 moon, 1 dusk, 2 storm), STADIUM_MOOD_OFF (offsetof(Flow, game.mood), tests/mame/stadium_mood_probe.c),
-- STADIUM_NAME (snapshot file name, saved in MAME's -snapshot_directory). Without STADIUM_MOOD the hook does nothing.
return function(mem, flow_addr)
  local mood, off = tonumber(os.getenv("STADIUM_MOOD") or ""), tonumber(os.getenv("STADIUM_MOOD_OFF") or "")
  local name = os.getenv("STADIUM_NAME")
  local H = { on = mood ~= nil and off ~= nil and name ~= nil }
  function H.poke() if H.on then mem:write_u8(flow_addr + off, mood) end end   -- the match start picks its own mood; the next frame shows this one
  function H.shot() if H.on then manager.machine.screens[":screen"]:snapshot(name) end end
  return H
end
