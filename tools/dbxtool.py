#!/usr/bin/env python3
"""DEViLBOX .dbx song -> nullsound Z80 assembler (stage 1b).
Usage: $PYTHON -I tools/dbxtool.py --nss OUT.s --instruments OUT.s --name NAME [--drop-noise-macro] [--no-macro-resample] SONG.dbx
Writes the two files that `nsstool.py -z` (NSS stream) and `furtool.py --instruments` (instrument table) write from a .fur.
The opcode table, the pass pipeline and both assembler writers are the installed ngdevkit tools, imported at run time
(directory: --ngdevkit-bin, then $NGDEVKIT_BIN, then nsstool.py on PATH, then /opt/homebrew/opt/ngdevkit/libexec/bin).
No opcode number is copied here; a missing tool is a hard error. Anything the song holds that nullsound cannot play is an
error naming pattern, row, channel or instrument; nothing is dropped silently.
Notes: .dbx = "DVBZ" + u8 version(1) + u32le size + zlib(JSON) (DEViLBOX src/lib/projectCompression.ts); JSON = SongExport
(src/lib/export/exporters.ts:272). Channels 0-3 = FM1-4, 4-6 = SSG1-3, higher channels must be empty. Stage 1b
(thoughts/spot/2026-11-12-dbxtool-stage1b-results.md): DEViLBOX answers applied, macros resampled 60 Hz -> song tick rate, SSG
noise period carried on state offset 1 and loaded into register 0x06 by the generated load function."""
from __future__ import annotations
import argparse, importlib, io, json, math, os, re, shutil, struct, sys, zlib
from fractions import Fraction
sys.dont_write_bytecode = True

DEFAULT_BIN = "/opt/homebrew/opt/ngdevkit/libexec/bin"
MAGIC = b"DVBZ"
NSS_FM_CHANNELS = 4
NSS_CHANNELS = 7
DEFAULT_SPEED = 6
NOISE_FREQ_MACRO = 2  # Furnace/DEViLBOX SSG macro slot 2 = noise frequency (DEViLBOX opnbVoices.ts:80-91)
FURNACE_ENV_MACRO = 6  # furtool maps this code to state offset 0 and load bit BIT_LOAD_REGS; carries the noise data (see move_noise_to_slot1)
MACRO_CODES = {0: "volume", 1: "arpeggio", 2: "noise frequency", 3: "waveform"}
MACRO_HZ = 60  # DEViLBOX steps macros at 60 Hz (FurnaceDispatch.worklet.js:71)
NOISE_MAX = 31  # YM2610 SSG register 0x06 holds a 5 bit period
NOISE_STATE_OFFSET = 1  # nullsound SSG state byte "envelope fine", never read by the driver (nss-ssg.s:107-110)
NOISE_REG = 0x06
STOCK_ENV_FINE_REG = 0x0b  # what furtool's load function writes for state offset 1
EXTRA_EFFECT_COLUMNS = 8
DBX_NOTE_OFF = 97
DBX_NOTE_MAX = 96
DBX_VOL_MIN, DBX_VOL_MAX = 0x10, 0x50
DBX_VOLUME_STEPS = 64
EFFECT_ARPEGGIO, EFFECT_SET_VOLUME = 0, 12


class DbxError(Exception):
    """A song feature that cannot be compiled; the message names where it is."""


class Tools:
    """The installed ngdevkit modules, imported once."""
    def __init__(self, nsstool, furtool, directory: str) -> None:
        self.ns, self.ft, self.directory = nsstool, furtool, directory


def find_tools_dir(explicit: str | None) -> str:
    candidates = [explicit, os.environ.get("NGDEVKIT_BIN")]
    candidates.append(DEFAULT_BIN)
    found = shutil.which("nsstool.py")  # on PATH this is a shell wrapper; the Python module is in ../libexec/bin
    if found:
        base = os.path.dirname(os.path.realpath(found))
        candidates += [os.path.join(base, "..", "libexec", "bin"), base]
    for c in candidates:
        if c and os.path.isfile(os.path.join(c, "nsstool.py")) and os.path.isfile(os.path.join(c, "furtool.py")):
            return c
    raise DbxError("nsstool.py / furtool.py not found (tried --ngdevkit-bin, $NGDEVKIT_BIN, PATH, %s)" % DEFAULT_BIN)


def load_tools(explicit: str | None = None) -> Tools:
    directory = find_tools_dir(explicit)
    if directory not in sys.path:
        sys.path.insert(0, directory)
    try:
        ns = importlib.import_module("nsstool")
        ft = importlib.import_module("furtool")
    except Exception as exc:  # any import failure is fatal
        raise DbxError("cannot import ngdevkit tools from %s: %s" % (directory, exc))
    ns.register_nss_ops()
    for name in ("fm_note", "fm_stop", "s_note", "s_stop", "fm_instr", "s_macro", "fm_vol", "s_vol", "arpeggio", "tempo",
                 "call", "jmp", "nss_end", "nss_ret", "nss_label", "wait_n", "row_actions", "compact_nss_stream"):
        if not hasattr(ns, name):
            raise DbxError("nsstool in %s has no %s: version mismatch" % (directory, name))
    # nsstool keeps per-run state in module globals
    ns.tempo_injected, ns.ext_fm2, ns.ext_fm2_injected, ns.VERBOSE = False, False, False, False
    return Tools(ns, ft, directory)


# ---------------------------------------------------------------- container

def decode_dbx(data: bytes) -> dict:
    """DVBZ container, or plain JSON, to the song dict."""
    if data[:4] == MAGIC:
        if len(data) < 9:
            raise DbxError("DVBZ container shorter than its 9 byte header")
        version, size = data[4], struct.unpack("<I", data[5:9])[0]
        if version != 1:
            raise DbxError("DVBZ container version %d, only 1 is known" % version)
        try:
            raw = zlib.decompress(data[9:])
        except zlib.error as exc:
            raise DbxError("DVBZ payload is not zlib data: %s" % exc)
        if len(raw) != size:
            raise DbxError("DVBZ payload is %d bytes, header says %d" % (len(raw), size))
    else:
        raw = data
    try:
        song = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise DbxError("song is not JSON: %s" % exc)
    if not isinstance(song, dict) or song.get("format") != "devilbox-song":
        raise DbxError("not a devilbox-song (format=%r)" % (song.get("format") if isinstance(song, dict) else None))
    return song


REQUIRED_FIELDS = (("patterns", list), ("patternOrder", list), ("instruments", list), ("bpm", (int, float)))


def validate_song(song: dict) -> None:
    """Named fields must exist (unknown ones are ignored). speed (default 6) and restartPosition (default 0) are optional:
    the trial song has neither."""
    for name, typ in REQUIRED_FIELDS:
        if name not in song:
            raise DbxError("song has no field %r" % name)
        if not isinstance(song[name], typ) or isinstance(song[name], bool):
            raise DbxError("song field %r has the wrong type" % name)
    for i, p in enumerate(song["patterns"]):
        if not isinstance(p, dict) or not isinstance(p.get("channels"), list):
            raise DbxError("pattern %d has no channels list" % i)
        for c, ch in enumerate(p["channels"]):
            if not isinstance(ch, dict) or not isinstance(ch.get("rows"), list):
                raise DbxError("pattern %d channel %d has no rows list" % (i, c))


def read_dbx(path: str) -> dict:
    with open(path, "rb") as f:
        return decode_dbx(f.read())


# ---------------------------------------------------------------- mapping

def nss_note_from_dbx(note: int) -> int:
    """DEViLBOX 1..96 (1 = C-0) to NSS note (0 = C-0). Octave base is a guess, see findings."""
    return note - 1


def tempo_byte(bpm: float) -> tuple[float, int]:
    """Row tick rate (Hz) and Timer B value. Tick = 2.5 / bpm s (TrackerReplayer.ts:3230); formula as nsstool.py."""
    if not isinstance(bpm, (int, float)) or bpm <= 0:
        raise DbxError("bad bpm %r" % (bpm,))
    freq = bpm / 2.5
    tb = round(256 - 4000000 / (1152 * freq))
    if not 0 <= tb <= 255:
        raise DbxError("bpm %s gives Timer B value %d, outside 0..255" % (bpm, tb))
    return freq, tb


def asm_ident(x: str) -> str:
    """Same identifier rule as furtool.read_instrument (a nested function there)."""
    return re.sub(r"\W|^(?=\d)", "_", x).lower()


def where(pidx: int, row: int, ch: int) -> str:
    return "pattern %d row %d channel %d" % (pidx, row, ch)


def check_range(value: int, lo: int, hi: int, what: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not lo <= value <= hi:
        raise DbxError("%s = %r, must be %d..%d" % (what, value, lo, hi))
    return value


def song_order(song: dict) -> list[int]:
    order = song.get("patternOrder")
    pats = song.get("patterns")
    if not isinstance(order, list) or not order or not isinstance(pats, list):
        raise DbxError("song has no patternOrder / patterns")
    for i, p in enumerate(order):
        if not isinstance(p, int) or not 0 <= p < len(pats):
            raise DbxError("patternOrder[%d] = %r is not a pattern index" % (i, p))
    return order


def pattern_rows(song: dict, pidx: int, ch: int) -> list[dict]:
    chans = song["patterns"][pidx].get("channels", [])
    return chans[ch]["rows"] if ch < len(chans) else []


def effect_columns() -> list[tuple[str, str]]:
    return [("effTyp", "eff")] + [("effTyp%d" % n, "eff%d" % n) for n in range(2, EXTRA_EFFECT_COLUMNS + 1)]


def row_is_empty(r: dict) -> bool:
    return not (r.get("note") or r.get("instrument") or r.get("volume")
                or any(r.get(t) or r.get(e) for t, e in effect_columns()))


def active_channels(song: dict, order: list[int]) -> list[int]:
    """Channel numbers 0..6 that hold any row data; a higher channel with data is an error."""
    used = set()
    for pidx in sorted(set(order)):
        for ch, c in enumerate(song["patterns"][pidx].get("channels", [])):
            for ri, r in enumerate(c["rows"]):
                if row_is_empty(r):
                    continue
                if ch >= NSS_CHANNELS:
                    raise DbxError("%s holds data but only channels 0-6 (FM1-4, SSG1-3) exist; "
                                   "ADPCM channels are not supported" % where(pidx, ri, ch))
                used.add(ch)
    return sorted(used)


def lengths_ok(song: dict, order: list[int]) -> None:
    for pidx in sorted(set(order)):
        chans = song["patterns"][pidx].get("channels", [])
        lens = {len(c["rows"]) for c in chans}
        if len(lens) > 1:
            raise DbxError("pattern %d channels differ in length %s" % (pidx, sorted(lens)))


def is_fm(ch: int) -> bool:
    return ch < NSS_FM_CHANNELS


def effects_of(r: dict, loc: str) -> list[tuple[int, int]]:
    out = []
    for tk, ek in effect_columns():
        t, v = r.get(tk, 0) or 0, r.get(ek, 0) or 0
        if t or v:  # effTyp 0 with eff 0 is no effect; effTyp 0 with eff != 0 is arpeggio 0xy
            out.append((t, v))
    types = [t for t, _ in out]
    if len(set(types)) != len(types):
        raise DbxError("%s: two effects of the same type" % loc)
    return out


def volume_level(r: dict, loc: str) -> int | None:
    """Row volume 0..64 or None. Cxx (0..0x40, larger clamps) wins over the volume column (0x10..0x50 = 0..64, other
    values ignored), as DEViLBOX: cellSetVolumeLevel(row) ?? decodeVolumeColumn(row.volume) (TrackerReplayer.ts routeRowToChip)."""
    level = None
    v = r.get("volume", 0) or 0
    if DBX_VOL_MIN <= v <= DBX_VOL_MAX:
        level = v - DBX_VOL_MIN
    for t, e in effects_of(r, loc):
        if t == EFFECT_SET_VOLUME:
            level = min(DBX_VOLUME_STEPS, check_range(e, 0, 255, "%s: Cxx" % loc))
    return level


def volume_ops(factory, ch: int, r: dict, loc: str) -> list:
    """One volume op for the row. On a row with a note it is that note's velocity, without a note the channel volume at
    once; nullsound has one op for both (the velocity then persists until the next volume: UNVERIFIED difference).
    Linear scale 0..64 to the chip range (guess)."""
    top = 0x7f if is_fm(ch) else 0x0f
    level = volume_level(r, loc)
    return [] if level is None else [factory.vol(round(level * top / DBX_VOLUME_STEPS))]


def fx_ops(ns, r: dict, loc: str) -> list:
    out = []
    for t, e in effects_of(r, loc):
        if t == EFFECT_SET_VOLUME:
            continue
        if t == EFFECT_ARPEGGIO and e:
            out.append(ns.arpeggio(check_range(e, 1, 255, "%s: 0xy" % loc)))
        else:
            raise DbxError("%s: effect type %d (0x%02x) parameter 0x%02x is not supported; only arpeggio 0xy and Cxx volume "
                           "are mapped to nullsound (slides, vibrato, chip commands and the song-steering Fxx/Bxx/Dxx/E6x "
                           "are not)" % (loc, t, t, e))
    return out


def row_ops(tools: Tools, factory, ch: int, r: dict, loc: str, cur: dict, ins_index: dict) -> list:
    """NSS opcodes for one row, in the order nsstool uses: ctx, ins, vol, fx, note."""
    ns = tools.ns
    ra = ns.row_actions()
    if row_is_empty(r):
        return []
    ra.ctx = factory.ctx()
    iid = r.get("instrument", 0)
    if iid:
        key = (iid, "fm" if is_fm(ch) else "ssg")
        if key not in ins_index:
            raise DbxError("%s: instrument %d unknown" % (loc, iid))
        ra.ins.append(factory.instr(ins_index[key]))
        cur["ins"] = iid
    ra.vol = volume_ops(factory, ch, r, loc) or None
    ra.fx = fx_ops(ns, r, loc)
    note = r.get("note", 0)
    if note == DBX_NOTE_OFF:
        ra.note.append(factory.note_off())
    elif note:
        check_range(note, 1, DBX_NOTE_MAX, "%s: note" % loc)
        if "ins" not in cur:
            raise DbxError("%s: note before any instrument on this channel" % loc)
        ra.note.append(factory.note_on(nss_note_from_dbx(note)))
    return ra.to_nss_list()


# ---------------------------------------------------------------- instruments

def find_instrument(song: dict, iid: int) -> dict:
    for ins in song.get("instruments", []):
        if ins.get("id") == iid:
            return ins
    raise DbxError("instrument %d is used but not in the song" % iid)


def used_instruments(song: dict, order: list[int], channels: list[int]) -> list[tuple[int, str]]:
    keys = set()
    for pidx in sorted(set(order)):
        for ch in channels:
            for ri, r in enumerate(pattern_rows(song, pidx, ch)):
                if r.get("instrument"):
                    keys.add((r["instrument"], "fm" if is_fm(ch) else "ssg"))
    return sorted(keys)


def build_fm(tools: Tools, ins: dict, name: str, warn=lambda s: None):
    ft = tools.ft
    fz = ins.get("furnace")
    ops = fz.get("operators") if isinstance(fz, dict) else None
    if not ops or len(ops) != 4:
        raise DbxError("instrument %r (id %s) used on an FM channel has no 4 FM operators" % (ins.get("name"), ins.get("id")))
    what = "instrument %r" % ins.get("name")
    if fz.get("fms2") or fz.get("ams2"):
        raise DbxError("%s: fms2/ams2 are not supported" % what)
    out = ft.fm_instrument(name=name,
                           algorithm=check_range(fz.get("algorithm", 0), 0, 7, what + " algorithm"),
                           feedback=check_range(fz.get("feedback", 0), 0, 7, what + " feedback"),
                           am_sense=check_range(fz.get("ams", 0), 0, 3, what + " ams"),
                           fm_sense=check_range(fz.get("fms", 0), 0, 7, what + " fms"))
    # DEViLBOX storage order is operator 1, 3, 2, 4 (index 0..3), the same as Furnace's slots and the OP1-OP3-OP2-OP4 order
    # of the furtool table, so the list is passed through in the order given.
    dts = []
    for i, op in enumerate(ops):
        w = "%s operator slot %d" % (what, i)
        if not op.get("enabled", True):
            raise DbxError("%s is disabled; nullsound has no operator mute" % w)
        dt = check_range(op.get("dt", 0), -3, 3, w + " dt")
        dts.append(dt)
        out.ops.append(ft.fm_operator(
            detune=dt if dt >= 0 else abs(dt) + 4,
            multiply=check_range(op.get("mult", 0), 0, 15, w + " mult"),
            total_level=check_range(op.get("tl", 0), 0, 127, w + " tl"),
            key_scale=check_range(op.get("rs", 0), 0, 3, w + " rs"),
            attack_rate=check_range(op.get("ar", 0), 0, 31, w + " ar"),
            am_on=1 if op.get("am") else 0,
            decay_rate=check_range(op.get("dr", 0), 0, 31, w + " dr"),
            kvs=check_range(op.get("kvs", 0), 0, 3, w + " kvs"),
            sustain_rate=check_range(op.get("d2r", 0), 0, 31, w + " d2r"),
            sustain_level=check_range(op.get("sl", 0), 0, 15, w + " sl"),
            release_rate=check_range(op.get("rr", 0), 0, 15, w + " rr"),
            ssg_eg=check_range(op.get("ssg", 0), 0, 15, w + " ssg")))
    if any(dts):
        warn("%s: operator dt %s is not 0; the encoding (negative = 4 + |dt|) is UNVERIFIED against DEViLBOX" % (what, dts))
    return out


def resample_steps(data: list[int], loop: int, tick_hz: Fraction) -> tuple[list[int], int]:
    """60 Hz macro steps to song ticks: console tick t reads source step floor(t * 60 / tick_hz). The loop point maps the
    same way (first tick that reads a step at or after the loop step). loop is -1 for none."""
    ratio = Fraction(MACRO_HZ) / tick_hz
    n = math.ceil(len(data) / ratio)
    out = [data[int(t * ratio)] for t in range(n)]
    new_loop = -1 if loop < 0 else min(n - 1, math.ceil(loop / ratio))
    return out, new_loop


def macro_block(macros: list[dict], what: str, drop_noise: bool, warn, tick_hz: Fraction | None = None) -> tuple[bytes, dict]:
    """Furnace macro section (as read by furtool.read_macro_data) for the supported macros, plus an info dict
    (noise: noise macro present, ticks: longest macro in ticks, looping: any macro loops)."""
    body = bytearray()
    info = {"noise": False, "ticks": 0, "looping": False}
    for m in macros:
        code = m.get("code")
        if code is None:
            code = m.get("type")  # DEViLBOX: slot = m.code ?? m.type
        data = m.get("data")
        w = "%s macro %s" % (what, MACRO_CODES.get(code, code))
        if code not in MACRO_CODES:
            raise DbxError("%s: unknown or unsupported macro code" % w)
        if code == NOISE_FREQ_MACRO and drop_noise:
            warn("%s dropped (--drop-noise-macro): noise period stays at its default" % w)
            continue
        if m.get("mode", 0) not in (0, None):
            raise DbxError("%s: only sequence macros (mode 0) are supported (mode %r)" % (w, m.get("mode")))
        if m.get("release", -1) not in (-1, None):
            raise DbxError("%s: release point %r is not supported (the nullsound driver has no release)" % (w, m.get("release")))
        if m.get("delay") not in (None, 0):
            raise DbxError("%s: macro delay %r is not supported" % (w, m.get("delay")))
        speed = 1 if m.get("speed") is None else check_range(m.get("speed"), 1, 255, w + " speed")
        if not isinstance(data, list) or not data:
            raise DbxError("%s: needs at least one step" % w)
        loop = m.get("loop", -1)
        loop = -1 if loop in (-1, None) else check_range(loop, 0, len(data) - 1, w + " loop")
        if code == 1:
            lo, hi = -128, 127
        elif code == NOISE_FREQ_MACRO:
            lo, hi = 0, NOISE_MAX
        else:
            lo, hi = 0, 255
        for v in data:
            check_range(v, lo, hi, w + " value")
        data = [v for v in data for _ in range(speed)]  # macro tick divider: each step lasts `speed` 60 Hz ticks
        loop = loop * speed if loop >= 0 else -1
        if tick_hz is not None:
            data, loop = resample_steps(data, loop, tick_hz)
        if code == 1 and loop < 0 and data[-1] != 0:
            data.append(0)  # arpeggio off at the end of a non-looping arpeggio macro (state offset 5 = 0)
        if len(data) > 255:
            raise DbxError("%s: %d steps after resampling, the limit is 255" % (w, len(data)))
        info["ticks"] = max(info["ticks"], len(data))
        info["looping"] = info["looping"] or loop >= 0
        fcode = code
        if code == NOISE_FREQ_MACRO:
            info["noise"] = True
            fcode = FURNACE_ENV_MACRO  # furtool carries it on key 0; move_noise_to_slot1 re-keys it to offset 1
        vals = bytes(v & 0xff for v in data)
        body += bytes([fcode, len(vals), 255 if loop < 0 else loop, 255, 0, 0, 0, 1]) + vals
    return struct.pack("<H", 8) + bytes(body), info


def decode_macro_prog(prog: list[int]) -> list[dict]:
    """Inverse of furtool.compile_macro_sequence: prog -> per step {absolute state offset: value}."""
    body, steps, i = prog[:-1], [], 0
    while i < len(body):
        off, step = 0, {}
        while body[i] != 255:
            key = off + body[i]
            step[key] = body[i + 1]
            off, i = key + 1, i + 2
        i += 1
        steps.append(step)
    return steps


def encode_macro_prog(steps: list[dict]) -> list[int]:
    prog = []
    for step in steps:
        off = 0
        for key in sorted(step):
            prog += [key - off, step[key]]
            off = key + 1
        prog.append(255)
    return prog + [255]


def move_noise_to_slot1(mac) -> None:
    """furtool put the noise data on state offset 0 (its Furnace code 6 'env' key). Re-key to offset 1, the unused 'envelope
    fine' byte. Load bits are unchanged (both are BIT_LOAD_REGS). The steps are decoded and re-encoded with furtool's own
    scheme; encode(decode(prog)) must reproduce prog before the move (structural self check)."""
    steps = decode_macro_prog(mac.prog)
    if encode_macro_prog(steps) != mac.prog:
        raise DbxError("internal: macro program does not round-trip through decode/encode")
    for st in steps:
        if 1 in st:
            raise DbxError("internal: macro program already uses state offset 1")
        if 0 in st:
            st[NOISE_STATE_OFFSET] = st.pop(0)
    mac.prog = encode_macro_prog(steps)
    mac.keys = sorted({k for st in steps for k in st})
    mac.offset = [v if i == 0 else mac.keys[i] - mac.keys[i - 1] - 1 for i, v in enumerate(mac.keys)]


def build_ssg(tools: Tools, ins: dict, name: str, drop_noise: bool, warn, tick_hz: Fraction | None = None):
    """SSG macro via furtool.read_ssg_macro on a synthesised Furnace macro block (same defaults, merge, load bits, offsets as
    stock). The noise period (macro slot 2) is carried on furtool's key 0 and re-keyed to state offset 1."""
    ft = tools.ft
    fz = ins.get("furnace")
    macros = fz.get("macros", []) if isinstance(fz, dict) else []
    what = "instrument %r" % ins.get("name")
    block, info = macro_block(macros, what, drop_noise, warn, tick_hz)
    mac = ft.read_ssg_macro(len(block), ft.binstream(block))
    if info["noise"]:
        move_noise_to_slot1(mac)
    mac.noise_slot = info["noise"]
    mac.span_ticks = None if info["looping"] else info["ticks"]
    return mac


def build_instrument_table(tools: Tools, song: dict, keys: list[tuple[int, str]], drop_noise: bool, warn,
                           tick_hz: Fraction | None = None) -> tuple[list, dict]:
    table, index = [], {}
    for n, (iid, kind) in enumerate(keys):
        ins = find_instrument(song, iid)
        label = asm_ident(("instr_%02x_%s" if kind == "fm" else "macro_%02x_%s") % (n, ins.get("name", "")))
        if kind == "fm":
            table.append(build_fm(tools, ins, label, warn))
        else:
            mac = build_ssg(tools, ins, label, drop_noise, warn, tick_hz)
            mac.name = label
            mac.load_name = asm_ident("macro_%02x_load_func" % n)
            mac.loop_name = asm_ident("macro_%02x_loop" % n)
            table.append(mac)
        index[(iid, kind)] = n
    return table, index


# ---------------------------------------------------------------- streams

def build_pattern_blocks(tools: Tools, song: dict, order: list[int], ch: int, ins_index: dict) -> list:
    """Raw stream for one channel: order calls, loop jump, then the pattern bodies (as nsstool.raw_nss_stream)."""
    ns = tools.ns
    factory = (ns.channel_nss_factory.fm_factory if is_fm(ch) else ns.channel_nss_factory.ssg_factory)(ch)
    cname = ns.channel_name(ch)
    cur: dict = {}
    seen, blocks, stream = set(), [], []
    for oidx, pidx in enumerate(order):
        rows = pattern_rows(song, pidx, ch)
        pid = "%s_%02x_%02x" % (cname, pidx, len(rows))
        if pid not in seen:
            body = []
            for ri, r in enumerate(rows):
                body += row_ops(tools, factory, ch, r, where(pidx, ri, ch), cur, ins_index) + [ns.wait_n(1)]
            blocks += [ns.nss_label(pid)] + body + [ns.nss_ret()]
            seen.add(pid)
        else:  # re-walk for the instrument-before-note check only
            for ri, r in enumerate(rows):
                if r.get("instrument"):
                    cur["ins"] = r["instrument"]
        call = ns.call(-1, -1)
        call.pat = pid
        stream += [ns.nss_label("order_%02x" % oidx), call]
    restart = song.get("restartPosition", 0) or 0
    check_range(restart, 0, len(order) - 1, "restartPosition")
    loop = ns.jmp(-1, -1)
    loop.pat = "order_%02x" % restart
    loop.desc = "back to %s" % loop.pat
    return stream + [loop] + blocks


def noise_overlap_warnings(song: dict, order: list[int], channels: list[int], speed: int, noisy: dict) -> list[str]:
    """The three SSG channels share one noise generator. Warn on each row where 2+ channels sound a noise instrument.
    noisy maps instrument id to the macro length in ticks (None = loops, sounds until note off or a new note).
    A note sounds from its note-on to a note-off, a new note, or ceil(ticks / speed) rows."""
    ssg = [c for c in channels if not is_fm(c)]
    cur = {c: 0 for c in ssg}  # instrument per channel
    alive = {c: 0 for c in ssg}  # rows left; -1 = until note off
    warns, seen = [], set()
    for pidx in order:
        rows = {c: pattern_rows(song, pidx, c) for c in ssg}
        for ri in range(max([len(v) for v in rows.values()] or [0])):
            for c in ssg:
                r = rows[c][ri] if ri < len(rows[c]) else {}
                if r.get("instrument"):
                    cur[c] = r["instrument"]
                note = r.get("note", 0)
                if note == DBX_NOTE_OFF:
                    alive[c] = 0
                elif note and cur[c] in noisy:
                    span = noisy[cur[c]]
                    alive[c] = -1 if span is None else max(1, -(-span // speed))
                elif note:
                    alive[c] = 0
            hot = [c for c in ssg if alive[c] != 0]
            if len(hot) >= 2 and (pidx, ri, tuple(hot)) not in seen:
                seen.add((pidx, ri, tuple(hot)))
                warns.append("pattern %d row %d: channels %s sound noise instruments together; the noise period is shared "
                             "and the last write wins" % (pidx, ri, ", ".join(str(c) for c in hot)))
            for c in ssg:
                if alive[c] > 0:
                    alive[c] -= 1
    return warns


class Module:
    """The fields of a Furnace module that nsstool's writers read."""
    def __init__(self, name: str, author: str, frequency: float, speeds: list[int]) -> None:
        self.name, self.author, self.frequency, self.speeds = name, author, frequency, speeds
        self.ext_fm = False


def compile_song(song: dict, tools: Tools, drop_noise: bool = False, warn=lambda s: print("[WARN] " + s, file=sys.stderr),
                 resample: bool = True):
    """Song dict to (module, channels, streams, instrument table, Timer B value, tick Hz). Macros are resampled from 60 Hz to
    the song tick rate unless resample is False."""
    ns, ft = tools.ns, tools.ft
    validate_song(song)
    order = song_order(song)
    lengths_ok(song, order)
    channels = active_channels(song, order)
    if not channels:
        raise DbxError("song has no notes on channels 0-6")
    speed = check_range(song.get("speed", DEFAULT_SPEED), 1, 255, "speed")
    freq, tb = tempo_byte(song["bpm"])
    meta = song.get("metadata", {})
    mod = Module(str(meta.get("name", "")), str(meta.get("author", "")), freq, [speed])
    keys = used_instruments(song, order, channels)
    tick_hz = Fraction(str(song["bpm"])) / Fraction(5, 2) if resample else None
    table, ins_index = build_instrument_table(tools, song, keys, drop_noise, warn, tick_hz)
    noisy = {iid: table[ins_index[(iid, kind)]].span_ticks for iid, kind in keys
             if kind == "ssg" and getattr(table[ins_index[(iid, kind)]], "noise_slot", False)}
    for w in noise_overlap_warnings(song, order, channels, speed, noisy):
        warn(w)
    ns.tempo_injected, ns.ext_fm2, ns.ext_fm2_injected = False, False, False
    raw = [build_pattern_blocks(tools, song, order, ch, ins_index) for ch in channels]
    streams = [ns.compact_nss_stream(s, mod, table, ch) for ch, s in zip(channels, raw)]
    return mod, channels, streams, table, tb, freq


def write_nss(tools: Tools, mod: Module, channels: list[int], streams: list, name: str) -> tuple[str, int]:
    ns = tools.ns
    channels, streams = ns.non_empty_nss_streams(channels, streams)
    size = 1 + 2 + 1 + len(mod.speeds) + 2 * len(streams) + sum(ns.stream_size_in_bytes(s) for s in streams)
    fd = io.StringIO()
    ns.asm_header(streams, mod, name, None, size, fd)
    ns.nss_compact_header(mod, channels, streams, name, fd)
    for ch, s in zip(channels, streams):
        ns.nss_to_asm(s, mod, ns.stream_name(name, ch), fd)
    ns.nss_footer(name, fd)
    return fd.getvalue(), size


def patch_noise_loads(text: str, table: list) -> str:
    """furtool writes the state offset 1 byte to register 0x0b inside each macro's load function. Offset 1 is the noise slot
    (move_noise_to_slot1), so in the noise macros' load functions that write goes to register 0x06 instead. Exactly one
    such write must exist in each."""
    for mac in table:
        if not getattr(mac, "noise_slot", False):
            continue
        head = mac.load_name + ":"
        a = text.find(head)
        if a < 0:
            raise DbxError("internal: load function %s not found" % mac.load_name)
        b = text.find("ret", a)
        blk = text[a:b]
        old = re.compile(r"ld(\s+)b,\s*#0x0b\b")
        if len(old.findall(blk)) != 1:
            raise DbxError("internal: load function %s has no single register 0x0b write to retarget" % mac.load_name)
        blk = old.sub(lambda m: "ld%sb, #0x%02x" % (m.group(1), NOISE_REG), blk)
        text = text[:a] + blk + text[b:]
    return text


def write_instruments(tools: Tools, mod: Module, table: list, name: str, samples_inc: str) -> str:
    fd = io.StringIO()
    tools.ft.generate_instruments(mod, samples_inc, name, None, table, fd)
    return patch_noise_loads(fd.getvalue(), table)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compile a DEViLBOX .dbx song to nullsound assembler (NSS stream + instruments)")
    ap.add_argument("song", help="DEViLBOX .dbx file")
    ap.add_argument("--nss", required=True, help="output NSS stream .s")
    ap.add_argument("--instruments", required=True, help="output instruments .s")
    ap.add_argument("--name", required=True, help="song name; labels nss_<name>, instruments_<name>")
    ap.add_argument("--samples-inc", default="build/samples.inc", help="ADPCM sample map include (as furtool -m)")
    ap.add_argument("--drop-noise-macro", action="store_true", help="downgrade the unsupported noise-frequency macro to a warning")
    ap.add_argument("--no-macro-resample", action="store_true",
                    help="keep macro steps as authored (DEViLBOX steps them at 60 Hz; default resamples to the song tick rate)")
    ap.add_argument("--ngdevkit-bin", help="directory holding nsstool.py and furtool.py")
    a = ap.parse_args(argv)
    try:
        tools = load_tools(a.ngdevkit_bin)
        song = read_dbx(a.song)
        mod, channels, streams, table, tb, freq = compile_song(song, tools, a.drop_noise_macro,
                                                                       resample=not a.no_macro_resample)
        nss_text, size = write_nss(tools, mod, channels, streams, "nss_" + a.name)
        ins_text = write_instruments(tools, mod, table, "instruments_" + a.name, a.samples_inc)
    except (DbxError, OSError) as exc:
        print("[ERROR] %s" % exc, file=sys.stderr)
        return 1
    with open(a.nss, "w") as f:
        f.write(nss_text)
    with open(a.instruments, "w") as f:
        f.write(ins_text)
    print("[OK] %s: %d bytes NSS (tempo 0x%02x = %.2f Hz, wanted %.2f Hz), %d instruments, channels %s, tools %s"
          % (a.song, size, tb, 4000000 / (1152 * (256 - tb)), freq, len(table), channels, tools.directory))
    return 0


if __name__ == "__main__":
    sys.exit(main())
