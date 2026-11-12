#!/usr/bin/env python3
"""Host test for tools/dbxtool.py. Run: python3 -I tests/host/test_dbxtool.py
Needs the installed ngdevkit nsstool/furtool (dbxtool imports them). Does not read the trial song."""
from __future__ import annotations
import copy, json, os, re, struct, sys, zlib
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import dbxtool as d

FAILS: list = []


def check(ok: bool, msg: str) -> None:
    print(("[OK]   " if ok else "[FAIL] ") + msg)
    if not ok:
        FAILS.append(msg)


def raises(fn, needle: str) -> bool:
    try:
        fn()
    except d.DbxError as e:
        return needle in str(e)
    return False


EMPTY = {"note": 0, "instrument": 0, "volume": 0, "effTyp": 0, "eff": 0, "effTyp2": 0, "eff2": 0}


def row(**kw) -> dict:
    r = dict(EMPTY)
    r.update(kw)
    return r


def fm_ins(iid: int) -> dict:
    op = {"enabled": True, "am": 0, "ar": 31, "dr": 5, "mult": 1, "rr": 7, "sl": 3, "tl": 20, "rs": 0, "dt": 0,
          "d2r": 2, "ssg": 0, "kvs": 2}
    return {"id": iid, "name": "Test FM", "furnace": {"algorithm": 4, "feedback": 3, "ams": 0, "fms": 0,
                                                      "operators": [dict(op) for _ in range(4)]}}


def ssg_ins(iid: int, noise: bool = False) -> dict:
    macros = [{"code": 0, "type": 0, "data": [15, 10, 5], "loop": -1, "release": -1, "mode": 0},
              {"code": 3, "type": 0, "data": [1, 1, 1], "loop": 1, "release": -1, "mode": 0}]
    if noise:
        macros.append({"code": 2, "type": 0, "data": [4, 8], "loop": -1, "release": -1, "mode": 0})
    return {"id": iid, "name": "Test SSG", "furnace": {"macros": macros}}


def tiny_song() -> dict:
    nrows = 4
    chans = [{"rows": [row() for _ in range(nrows)]} for _ in range(8)]
    chans[0]["rows"][0] = row(note=13, instrument=1)
    chans[0]["rows"][2] = row(note=97)
    chans[0]["rows"][3] = row(effTyp=12, eff=32)
    chans[4]["rows"][0] = row(note=25, instrument=2, effTyp=0, eff=0x37)
    chans[4]["rows"][2] = row(note=26)
    return {"format": "devilbox-song", "version": "test", "metadata": {"name": "Tiny", "author": "Tester"},
            "bpm": 125, "patterns": [{"channels": chans}], "patternOrder": [0, 0],
            "instruments": [fm_ins(1), ssg_ins(2)]}


def pack(song: dict, version: int = 1) -> bytes:
    raw = json.dumps(song).encode()
    return d.MAGIC + bytes([version]) + struct.pack("<I", len(raw)) + zlib.compress(raw)


def test_container() -> None:
    s = tiny_song()
    check(d.decode_dbx(pack(s)) == s, "container: DVBZ round trip")
    check(d.decode_dbx(json.dumps(s).encode()) == s, "container: raw JSON accepted")
    check(raises(lambda: d.decode_dbx(pack(s, 2)), "version 2"), "container: unknown version is an error")
    bad = bytearray(pack(s))
    bad[5] ^= 1
    check(raises(lambda: d.decode_dbx(bytes(bad)), "header says"), "container: size mismatch is an error")
    check(raises(lambda: d.decode_dbx(b'{"format":"x"}'), "not a devilbox-song"), "container: wrong format is an error")
    check(raises(lambda: d.decode_dbx(b"DVBZ\x01"), "shorter"), "container: truncated header is an error")


def test_mapping() -> None:
    check(d.nss_note_from_dbx(1) == 0 and d.nss_note_from_dbx(49) == 48, "note: 1 = C-0 maps to NSS 0")
    freq, tb = d.tempo_byte(125)
    check(freq == 50.0 and tb == 187, "tempo: 125 bpm = 50 Hz = Timer B 187")
    check(raises(lambda: d.tempo_byte(0), "bad bpm"), "tempo: bpm 0 is an error")
    check(raises(lambda: d.tempo_byte(1), "outside"), "tempo: bpm out of Timer B range is an error")


def test_errors(tools: d.Tools) -> None:
    def compile_with(edit) -> None:
        s = tiny_song()
        edit(s)
        d.compile_song(s, tools)

    r = lambda s: s["patterns"][0]["channels"][0]["rows"]
    check(raises(lambda: compile_with(lambda s: r(s)[1].update(effTyp=15, eff=3)), "pattern 0 row 1 channel 0"),
          "error: unsupported effect names pattern/row/channel")
    check(raises(lambda: compile_with(lambda s: r(s)[0].update(instrument=9)), "instrument 9"),
          "error: unknown instrument")
    check(raises(lambda: compile_with(lambda s: r(s)[0].update(instrument=0)), "before any instrument"),
          "error: note before any instrument")
    check(raises(lambda: compile_with(lambda s: s["patterns"][0]["channels"][7]["rows"][1].update(note=5)), "channel 7"),
          "error: data on channel 8")
    check(raises(lambda: compile_with(lambda s: s["instruments"][0]["furnace"]["operators"][2].update(enabled=False)),
                 "disabled"), "error: disabled operator")
    check(raises(lambda: compile_with(lambda s: s["instruments"][0]["furnace"]["operators"][1].update(tl=200)), "tl"),
          "error: operator range")
    s = tiny_song()
    s["instruments"][1] = ssg_ins(2, noise=True)
    warned: list = []
    d.compile_song(s, tools, True, warned.append)
    check(len(warned) == 1 and "dropped" in warned[0], "noise macro dropped with a warning under --drop-noise-macro")
    warned = []
    d.compile_song(s, tools, False, warned.append)
    check(warned == [], "noise macro compiles without --drop-noise-macro")
    check(raises(lambda: compile_with(lambda s: s.update(patternOrder=[5])), "patternOrder[0]"),
          "error: bad order entry")


def test_compile(tools: d.Tools) -> None:
    mod, channels, streams, table, tb, _ = d.compile_song(tiny_song(), tools)
    check(channels == [0, 4] and len(table) == 2 and tb == 187, "compile: channels, instruments, tempo")
    nss, size = d.write_nss(tools, mod, channels, streams, "nss_tiny")
    ins = d.write_instruments(tools, mod, table, "instruments_tiny", "build/samples.inc")
    check("nss_tiny::" in nss and "nss_tiny_f1::" in nss and "nss_tiny_s1::" in nss and "nss_tiny_end::" in nss,
          "compile: NSS labels")
    check((";;; NSS size: %d" % size) in nss, "compile: NSS size header")
    check("instruments_tiny::" in ins and "instr_00_test_fm:" in ins and "macro_01_test_ssg:" in ins
          and "macro_01_load_func:" in ins, "compile: instrument labels")
    check(".dw     0x0011" in nss, "compile: channel mask F1 + S1")
    check(d.write_nss(tools, mod, channels, streams, "nss_tiny")[0] == nss, "compile: output is deterministic")


def compiled(tools: d.Tools, song: dict, **kw):
    warned: list = []
    mod, channels, streams, table, tb, _ = d.compile_song(song, tools, warn=warned.append, **kw)
    nss, _ = d.write_nss(tools, mod, channels, streams, "nss_t")
    ins = d.write_instruments(tools, mod, table, "instruments_t", "build/samples.inc")
    return nss, ins, warned, table


def ssg_only(rows_ch4: list, rows_ch5: list | None = None, instruments=None, bpm: float = 125) -> dict:
    n = len(rows_ch4)
    chans = [{"rows": [row() for _ in range(n)]} for _ in range(8)]
    chans[4]["rows"] = rows_ch4
    if rows_ch5:
        chans[5]["rows"] = rows_ch5
    return {"format": "devilbox-song", "bpm": bpm, "patterns": [{"channels": chans}], "patternOrder": [0],
            "instruments": instruments or [ssg_ins(2)]}


def macro_ins(iid: int, *macros: dict) -> dict:
    return {"id": iid, "name": "M", "furnace": {"macros": list(macros)}}


def mac(code: int, data: list, **kw) -> dict:
    m = {"code": code, "type": 0, "data": data, "loop": -1, "release": -1, "mode": 0}
    m.update(kw)
    return m


def test_stage1b(tools: d.Tools) -> None:
    # operator order: slot 0..3 reach the instrument in the order given (op1, op3, op2, op4)
    s = tiny_song()
    for i, tl in enumerate((10, 20, 30, 40)):
        s["instruments"][0]["furnace"]["operators"][i]["tl"] = tl
    nss, ins, _, _ = compiled(tools, s)
    check("0x0a, 0x14, 0x1e, 0x28   ; TL" in ins, "operator order: storage slots 0,1,2,3 are written as given (op1, op3, op2, op4)")
    # SSG defaults: no volume macro = [15], no waveform macro = [1]
    _, ins, _, tab = compiled(tools, ssg_only([row(note=13, instrument=2)], instruments=[macro_ins(2, mac(1, [3, 0]))]))
    ref = ssg_only([row(note=13, instrument=2)], instruments=[macro_ins(2, mac(0, [15]), mac(3, [1]), mac(1, [3, 0]))])
    _, ins2, _, _ = compiled(tools, ref)
    check(ins == ins2, "SSG defaults: missing volume macro is [15], missing waveform macro is [1]")
    # macro slot = code, falling back to type
    m = mac(0, [15, 8]); del m["code"]; m["type"] = 0
    _, ins3, _, _ = compiled(tools, ssg_only([row(note=13, instrument=2)], instruments=[macro_ins(2, m)]))
    _, ins4, _, _ = compiled(tools, ssg_only([row(note=13, instrument=2)], instruments=[macro_ins(2, mac(0, [15, 8]))]))
    check(ins3 == ins4, "macro slot: type is used when code is absent")
    # volume: column 0x10..0x50 = 0..64, Cxx 0..0x40 clamps, Cxx wins, other column values ignored
    def vols(**kw):
        n, _, _, _ = compiled(tools, ssg_only([row(note=13, instrument=2, **kw)]))
        return [int(x, 16) for x in re.findall(r"0x2a, (0x[0-9a-f]+)\s+; S_VOL", n)]
    check(vols(volume=0x50) == [15] and vols(volume=0x10) == [0], "volume column: 0x50 = full, 0x10 = silent")
    check(vols(volume=0x30) == [8], "volume column: 0x30 = 32 of 64 = half")
    check(vols(volume=0x0f) == vols() and vols(volume=0x60) == vols(), "volume column: values outside 0x10..0x50 are ignored")
    check(vols(effTyp=12, eff=0x40) == [15] and vols(effTyp=12, eff=0xff) == [15], "Cxx: 0x40 is full, larger clamps")
    check(vols(volume=0x10, effTyp=12, eff=0x40) == [15], "Cxx wins over the volume column, no error")
    n, _, _, _ = compiled(tools, ssg_only([row(note=13, instrument=2), row(effTyp=12, eff=0x20)]))
    check(re.findall(r"0x2a, (0x[0-9a-f]+)\s+; S_VOL", n) == ["0x0f", "0x08"], "Cxx without a note sets the channel volume")
    # arpeggio 0xy and unknown effects
    n, _, _, _ = compiled(tools, ssg_only([row(note=13, instrument=2, effTyp=0, eff=0x37)]))
    check("0x37" in n and "ARPEGGIO" in n, "effTyp 0 with a parameter is arpeggio 0xy")
    check(raises(lambda: compiled(tools, ssg_only([row(note=13, instrument=2, effTyp=1, eff=4)])), "not supported"),
          "unknown effect fails the build")
    check(raises(lambda: compiled(tools, ssg_only([row(note=13, instrument=2, effTyp3=4, eff3=1)])), "pattern 0 row 0"),
          "unknown effect in a later effect column fails the build")
    # macro resample
    steps = list(range(10))
    _, ins, _, tab = compiled(tools, ssg_only([row(note=13, instrument=2)], instruments=[macro_ins(2, mac(0, steps))], bpm=125))
    ticks125 = ins.count("; tick ")
    check(ticks125 == 9, "resample 60 -> 50 Hz: 10 steps become 9 ticks (got %d)" % ticks125)
    data, loop = d.resample_steps(steps, 4, d.Fraction(50))
    check(data == [0, 1, 2, 3, 4, 6, 7, 8, 9] or data == [0, 1, 2, 3, 4, 6, 7, 8, 9][:len(data)] and len(data) == 9,
          "resample 60 -> 50 Hz: tick t reads step floor(t * 1.2)")
    check(loop == 4, "resample: loop point maps to the first tick at or after it")
    data, loop = d.resample_steps(steps, 4, d.Fraction(60))
    check(data == steps and loop == 4, "resample at 60 Hz is the identity")
    _, ins150, _, _ = compiled(tools, ssg_only([row(note=13, instrument=2)], instruments=[macro_ins(2, mac(0, steps))], bpm=150))
    _, ins150n, _, _ = compiled(tools, ssg_only([row(note=13, instrument=2)], instruments=[macro_ins(2, mac(0, steps))], bpm=150),
                                resample=False)
    check(ins150 == ins150n and ins150.count("; tick ") == 10, "150 BPM (60 Hz) is the identity, same as --no-macro-resample")
    _, ins125n, _, _ = compiled(tools, ssg_only([row(note=13, instrument=2)], instruments=[macro_ins(2, mac(0, steps))]),
                                resample=False)
    check(ins125n.count("; tick ") == 10, "--no-macro-resample keeps the raw 10 steps at 125 BPM")
    # macro speed, delay, mode, release
    _, ins_sp, _, _ = compiled(tools, ssg_only([row(note=13, instrument=2)], instruments=[macro_ins(2, mac(0, [5, 6], speed=2))],
                                               bpm=150))
    check(ins_sp.count("; tick ") == 4, "macro speed 2 repeats every step twice")
    check(raises(lambda: compiled(tools, ssg_only([row(note=13, instrument=2)], instruments=[macro_ins(2, mac(0, [5], delay=3))])),
                 "delay"), "macro delay fails the build")
    check(raises(lambda: compiled(tools, ssg_only([row(note=13, instrument=2)], instruments=[macro_ins(2, mac(0, [5], mode=1))])),
                 "mode"), "macro mode other than 0 fails the build")
    check(raises(lambda: compiled(tools, ssg_only([row(note=13, instrument=2)], instruments=[macro_ins(2, mac(0, [5, 4], release=1))])),
                 "release"), "macro release point fails the build")
    # arpeggio macro ends with arpeggio off
    _, ins, _, _ = compiled(tools, ssg_only([row(note=13, instrument=2)], instruments=[macro_ins(2, mac(1, [4, 7]))], bpm=150))
    check(ins.count("; tick ") == 3 and ins.count("0x05, 0x00") >= 1, "arpeggio macro gets a final step writing 0 to the arpeggio byte")
    # noise macro: golden text, register 0x06, values 4 and 8, load bit set only while the noise steps run
    n, ins, w, tab = compiled(tools, ssg_only([row(note=13, instrument=2)], instruments=[macro_ins(2, mac(2, [4, 8]))], bpm=150))
    golden = (".dw     macro_00_load_func\n"
              "        ;; macro actions\n"
              "        .db     0x01, 0x04, 0x01, 0x0f, 0x00, 0x08, 0xff, 0x3a   ; tick 0\n"
              "        .db     0x01, 0x08, 0xff, 0x10                           ; tick 1\n")
    check(golden in ins, "noise macro: golden step text carries the period on state offset 1")
    lf = ins[ins.index("_load_func:"):]
    lf = lf[:lf.index("ret")]
    check("ld      b, #0x06" in lf and "#0x0b" not in lf, "noise macro: load function writes register 0x06, not 0x0b")
    check(w == [] and tab[0].noise_slot, "noise macro: no warning without overlap")
    check(raises(lambda: compiled(tools, ssg_only([row(note=13, instrument=2)], instruments=[macro_ins(2, mac(2, [4, 40]))])),
                 "noise frequency"), "noise period above 31 fails the build")
    # noise overlap warning
    noisy = [macro_ins(2, mac(2, [4, 8], loop=0))]
    _, _, w, _ = compiled(tools, ssg_only([row(note=13, instrument=2), row(), row(note=97)],
                                          [row(), row(note=13, instrument=2), row()], instruments=noisy))
    check(len(w) == 1 and "pattern 0 row 1" in w[0] and "channels 4, 5" in w[0], "noise overlap: pattern, row and channels named")
    _, _, w, _ = compiled(tools, ssg_only([row(note=13, instrument=2), row(note=97), row()],
                                          [row(), row(), row(note=13, instrument=2)], instruments=noisy))
    check(w == [], "noise overlap: no warning when the first noise ended")
    # dt warning, once per instrument
    s = tiny_song()
    s["instruments"][0]["furnace"]["operators"][0]["dt"] = 2
    s["instruments"][0]["furnace"]["operators"][1]["dt"] = 1
    _, _, w, _ = compiled(tools, s)
    check(len(w) == 1 and "UNVERIFIED" in w[0], "FM dt other than 0 warns once, encoding unverified")
    # container and required fields
    s = tiny_song()
    s["extra"] = {"anything": 1}
    check(compiled(tools, s)[0] != "", "unknown top-level fields are ignored")
    for key in ("patterns", "patternOrder", "instruments", "bpm"):
        s = tiny_song()
        del s[key]
        check(raises(lambda: compiled(tools, s), key), "missing field %s fails the build" % key)
    s = tiny_song()
    s["patternOrder"] = [0, 0]
    s["restartPosition"] = 1
    n, _, _, _ = compiled(tools, s)
    check("JMP back to order_01" in n, "restartPosition sets the loop point")
    s = tiny_song()
    s["speed"] = 3
    n, _, _, _ = compiled(tools, s)
    check(compiled(tools, tiny_song())[0] != n, "speed field is used")
    check(raises(lambda: d.decode_dbx(d.MAGIC), "shorter"), "container: magic alone is truncated")
    check(d.decode_dbx(b'{"format": "devilbox-song", "bpm": 1}')["bpm"] == 1, "container: raw JSON with the right format is accepted")


def main() -> int:
    test_container()
    test_mapping()
    try:
        tools = d.load_tools()
    except d.DbxError as e:
        check(False, "ngdevkit tools load: %s" % e)
        tools = None
    if tools:
        test_errors(tools)
        test_compile(tools)
        test_stage1b(tools)
    print("%d failure(s)" % len(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
