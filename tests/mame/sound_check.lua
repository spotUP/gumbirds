-- Sound driver reachability (make test-sound). Real boot path: coin, start, flap (A press edge), walk off the island and drown until game over.
-- Proves three links of the chain for each game sound event:
--   1. 68k:  g_sound_sent / g_sound_last (src/sound.c) move and the command byte is the expected SND_* id.
--   2. Z80:  audiocpu io taps (port 0x00 read for commands 1-3, port 0x0C ack for queued commands, see the taps)
--            see the same byte sequence; the 68k sequence must be the tail of the Z80 sequence (the BIOS may send first).
--   3. YM2610: io write taps on ports 4-7 (ADPCM-A key-on = port B reg 0x00, bit7 clear, mask = channel bits;
--            FM/SSG register writes on port A) show the driver acted: every SFX command is followed by the key-on
--            of its channel (bit from build/snd_commands.inc, i.e. sample-map.yaml channel - 1), the music command by
--            port A writes.
-- Ids come from build/snd_commands.h. Env: BRAWL_FLOW_ADDR (hex), BRAWL_HIT_LAYOUT (first value = flow
-- state offset), BRAWL_RESULT. Symbols from nm on build/rom.elf as in vblank_check.lua.
local flow_addr = tonumber(os.getenv("BRAWL_FLOW_ADDR"), 16)
local result    = os.getenv("BRAWL_RESULT")
local lay = {}
for v in (os.getenv("BRAWL_HIT_LAYOUT") or ""):gmatch("%d+") do lay[#lay + 1] = tonumber(v) end
local O_STATE = lay[1]
local FLOW_PLAYING, FLOW_GAME_OVER = 3, 4
local WATCHDOG = 6000
local KEYON_WINDOW = 40      -- frames from a command read by the Z80 to the key-on of its channel
local MUSIC_WINDOW = 90
local MUSIC_MIN_WRITES = 20

local function read_ids()
  local base, ids = 4, {}
  for line in io.lines("build/snd_commands.h") do
    local n, off = line:match("#define (SND_[A-Z_]+) %(_SND_CMD_BASE_GENERATED %+ (%d+)%)")
    if n then ids[n] = base + tonumber(off) end
  end
  return ids
end
local ids = read_ids()
-- A flap plays the jump sample (SE_FLAP in src/core/sound_events.c); the hit sound has no game event in the arena.
local ID_MUSIC, ID_JUMP, ID_OVER, ID_COIN =
  ids.SND_MUSIC_INGAME, ids.SND_SFX_JUMP, ids.SND_SFX_GAME_OVER, ids.SND_SFX_COIN
-- ADPCM-A key-on bit per SFX, read from the driver's own generated table (build/snd_commands.inc, line
-- ".db 0xNN ; channel (bit)" after "sfx_<name>_data:"). soundtool's yaml channel is 1-based (bit = 1 << (channel-1)).
local function read_masks()
  local m, cur = {}, nil
  for line in io.lines("build/snd_commands.inc") do
    cur = line:match("^sfx_([%w_]+)_data:") or cur
    local bit = line:match("%.db%s+0x(%x+)%s*; channel %(bit%)")
    if cur and bit then
      local id = ids["SND_SFX_" .. cur:upper()]
      if id then m[id] = tonumber(bit, 16) end
      cur = nil
    end
  end
  return m
end
local MASK = read_masks()
local NAME = { [ID_MUSIC] = "music", [ID_JUMP] = "flap", [ID_OVER] = "game_over", [ID_COIN] = "coin", [2] = "stop", [3] = "reset" }

local function sym_addrs()
  local gcc
  for line in io.lines("config.mk") do gcc = gcc or line:match("^M68KGCC=(.*)$") end
  local nm = (gcc or "m68k-neogeo-elf-gcc"):gsub("gcc$", "nm")
  local t = {}
  local h = io.popen(nm .. " build/rom.elf")
  for line in h:lines() do
    local a, name = line:match("^(%x+) %a (%S+)$")
    if a then t[name] = tonumber(a, 16) end
  end
  h:close()
  return t
end
local syms = sym_addrs()
local A_SENT, A_LAST, A_FRAME = syms.g_sound_sent, syms.g_sound_last, syms.g_frame_counter
local A_RE = syms.g_round_end_s   -- u16 round_end, round_timer, round_start, flier visible (src/main.c): the ROUND nn / GO! hold ignores input

local mem   = manager.machine.devices[":maincpu"].spaces["program"]
local zio   = manager.machine.devices[":audiocpu"].spaces["io"]
local ports = manager.machine.ioport.ports
local function field(tag, name)
  local p = ports[tag]
  if not p then return nil end
  for fname, f in pairs(p.fields) do if fname == name then return f end end
end
local coin  = field(":AUDIO_COIN", "Coin 1")
local start = field(":edge:joy:START", "1 Player Start")
local ss = dofile("tests/mame/start_seq.lua")(coin, start)
local rbtn  = field(":edge:joy:JOY1", "P1 Right")
local lbtn  = field(":edge:joy:JOY1", "P1 Left")
local abtn  = field(":edge:joy:JOY1", "P1 A")

local flay = {}
for v in (os.getenv("BRAWL_FLIER_LAYOUT") or ""):gmatch("%d+") do flay[#flay + 1] = tonumber(v) end
local drive = dofile("tests/mame/flier_drive.lua")(mem, flow_addr, flay, abtn, lbtn, rbtn)

local done = false
local n = 0
local function finish(ok, msg)
  if done then return end
  done = true
  local f = io.open(result, "w")
  f:write((ok and "PASS " or "FAIL ") .. msg .. "\n")
  f:close()
  print("BRAWL_TEST " .. (ok and "PASS " or "FAIL ") .. msg)
  manager.machine:exit()
end

-- Z80 and YM taps (globals: a collected handle stops firing)
local zcmds = {}               -- {frame, byte} for every read of port 0x00
local keyons = {}              -- {frame, mask}
local porta_writes = {}        -- frames of FM/SSG data writes
local addr_a, addr_b = 0, 0
rawb = {}
local zcpu = manager.machine.devices[":audiocpu"]
local wr_ports = {}
-- Z80 io is 16-bit: `in a,(n)` / `out (n),a` drive A8-A15 with register A, so the taps span the whole space
-- and decode the port from the low byte (taps limited to 0x00xx only saw accesses made while A was 0).
tap_dbg = zio:install_write_tap(0x0000, 0xffff, "dbg", function(offset, data, mask)
  local k = string.format("%02x", offset & 0xff); wr_ports[k] = (wr_ports[k] or 0) + 1
end)
-- One received command per NMI, decoded by nullsound's protocol (NMI handler at 0x66 / 0x159 in the M1):
-- commands 1-3 are dispatched inside the NMI after a single port 0x00 read; every other command is read a
-- second time, pushed into the driver FIFO and acked with (cmd | 0x80) on port 0x0C. So: a port 0x00 read of
-- 1-3, or a port 0x0C write with bit 7 set, is one command received (the second read is not counted twice).
tap_cmd = zio:install_read_tap(0x0000, 0xffff, "cmd", function(offset, data, mask)
  data = data & 0xff
  if (offset & 0xff) == 0x00 and data >= 1 and data <= 3 then zcmds[#zcmds + 1] = { n, data } end
end)
tap_ack = zio:install_write_tap(0x0000, 0xffff, "ack", function(offset, data, mask)
  data = data & 0xff
  if (offset & 0xff) == 0x0c and (data & 0x80) ~= 0 then zcmds[#zcmds + 1] = { n, data & 0x7f } end
end)
tap_ym = zio:install_write_tap(0x0000, 0xffff, "ym", function(offset, data, mask)
  local lo = offset & 0xff
  if lo < 0x04 or lo > 0x07 then return end
  local port = lo & 3
  data = data & 0xff
  if port == 0 then addr_a = data
  elseif port == 1 then porta_writes[#porta_writes + 1] = n
  elseif port == 2 then addr_b = data
  elseif port == 3 and #rawb < 120 then rawb[#rawb + 1] = string.format("%d:%02x=%02x", n, addr_b, data) end
  if port == 3 and addr_b == 0x00 and (data & 0x80) == 0 and (data & 0x3f) ~= 0 then
    keyons[#keyons + 1] = { n, data & 0x3f }
  end
end)

local sent_log = {}            -- 68k commands seen via the sentinel: {frame, byte}
local prev_sent = nil
local phase, phase_at = "boot", 0
local fc0

local function evaluate()
  -- 1. 68k sentinel
  if #sent_log == 0 then finish(false, "68k sentinel g_sound_sent never moved (sound_play_sfx not reached)") return end
  local seen = {}
  for _, e in ipairs(sent_log) do seen[e[2]] = (seen[e[2]] or 0) + 1 end
  for _, id in ipairs({ ID_COIN, ID_MUSIC, ID_JUMP, ID_OVER }) do
    if not seen[id] then finish(false, "68k never sent " .. NAME[id] .. " (id " .. id .. ")") return end
  end
  if not seen[2] then finish(false, "68k never sent stop_music at game over") return end
  -- 2. Z80 received the same sequence: sent_log must be the tail of zcmds
  local off = #zcmds - #sent_log
  if off < 0 then
    local zs, ss = {}, {}
    for _, e in ipairs(zcmds) do zs[#zs + 1] = e[1] .. ":" .. e[2] end
    for _, e in ipairs(sent_log) do ss[#ss + 1] = e[1] .. ":" .. e[2] end
    finish(false, string.format("Z80 read %d commands [%s], 68k sent %d [%s]; %d key-ons, %d FM/SSG writes", #zcmds, table.concat(zs, " "), #sent_log, table.concat(ss, " "), #keyons, #porta_writes) .. string.format(" Z80 pc=%04x", zcpu.state["PC"].value) .. (function() local s = "" for k, v in pairs(wr_ports) do s = s .. " w" .. k .. "=" .. v end return s end)())
    return
  end
  for i, e in ipairs(sent_log) do
    if zcmds[off + i][2] ~= e[2] then
      local zs, ss = {}, {}
      for _, z in ipairs(zcmds) do zs[#zs + 1] = z[1] .. ":" .. z[2] end
      for _, x in ipairs(sent_log) do ss[#ss + 1] = x[1] .. ":" .. x[2] end
      finish(false, string.format("command %d: 68k sent %d, Z80 read %d; Z80 [%s] 68k [%s]", i, e[2], zcmds[off + i][2], table.concat(zs, " "), table.concat(ss, " ")))
      return
    end
  end
  -- 3. YM2610 acted on each command
  for i, e in ipairs(sent_log) do
    local id, zf = e[2], zcmds[off + i][1]
    if MASK[id] then
      local ok = false
      for _, k in ipairs(keyons) do
        if k[1] >= zf and k[1] <= zf + KEYON_WINDOW and (k[2] & MASK[id]) ~= 0 then ok = true break end
      end
      if not ok then finish(false, string.format("no ADPCM-A key-on mask 0x%02x within %d frames of %s (Z80 frame %d) RAWB %s", MASK[id], KEYON_WINDOW, NAME[id], zf, table.concat(rawb, " "))) return end
    elseif id == ID_MUSIC then
      local cnt = 0
      for _, f in ipairs(porta_writes) do if f >= zf and f <= zf + MUSIC_WINDOW then cnt = cnt + 1 end end
      if cnt < MUSIC_MIN_WRITES then finish(false, string.format("only %d FM/SSG writes within %d frames of music start", cnt, MUSIC_WINDOW)) return end
    end
  end
  local names = {}
  for _, e in ipairs(sent_log) do names[#names + 1] = NAME[e[2]] or tostring(e[2]) end
  finish(true, string.format("68k sent %d (%s); Z80 read %d total; %d key-ons, %d FM/SSG writes", #sent_log, table.concat(names, ","), #zcmds, #keyons, #porta_writes))
end

emu.register_frame_done(function()
  if done then return end
  n = n + 1
  if n > WATCHDOG then finish(false, "watchdog in phase " .. phase) return end
  if not (coin and start and rbtn and abtn) then finish(false, "missing input field") return end
  if not (A_SENT and A_LAST and A_FRAME and O_STATE and ID_COIN and MASK[ID_JUMP] and MASK[ID_OVER] and MASK[ID_COIN]) then finish(false, "missing symbol, layout or ids") return end
  local sent = mem:read_u16(A_SENT)
  if prev_sent == nil then prev_sent = sent end
  -- the sentinel moves at most once per frame (sound_tick); log each step with the byte written
  if sent ~= prev_sent then
    if ((sent - prev_sent) & 0xffff) ~= 1 then finish(false, "sentinel jumped by more than 1 in a frame") return end
    sent_log[#sent_log + 1] = { n, mem:read_u8(A_LAST) }
    prev_sent = sent
  end
  local state = mem:read_u8(flow_addr + O_STATE)
  if phase == "boot" then
    local fc = mem:read_u32(A_FRAME)
    if fc ~= 0 then fc0 = fc0 or fc end
    if fc0 and fc - fc0 >= 30 then phase = "coin"; phase_at = n; ss.begin(n) end
  elseif phase == "coin" then
    if ss.step(n, state == FLOW_PLAYING) then phase = "settle"; phase_at = n end
  elseif phase == "settle" then
    if n >= phase_at + 60 and mem:read_u16(A_RE) == 0 and mem:read_u16(A_RE + 4) == 0 then phase = "flap"; phase_at = n; abtn:set_value(1) end
  elseif phase == "flap" then
    if n == phase_at + 3 then abtn:set_value(0) end
    if n >= phase_at + 60 then phase = "idle"; phase_at = n end
  elseif phase == "idle" then
    drive()   -- walk off the island and drown (tests/mame/flier_drive.lua)
    if state == FLOW_GAME_OVER then phase = "over"; phase_at = n end
  elseif phase == "over" then
    if n >= phase_at + 150 then evaluate() end
  end
end)
