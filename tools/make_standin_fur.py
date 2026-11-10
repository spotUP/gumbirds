#!/usr/bin/env python3
"""Writes a minimal Furnace module (format v213, Neo Geo YM2610) used as stand-in music until the
DEViLBOX .fur export replaces it. One SSG channel plays a short arpeggio; every other channel is empty.
Usage: make_standin_fur.py OUT.fur   (original content, no third-party music)."""
import struct
import sys
import zlib

CHANNELS = 14
PATTERN_LEN = 16
SSG_CHANNEL = 4


def s(text):
    return text.encode("ascii") + b"\0"


def pattern(channel, rows):
    body = struct.pack("<BBH", 0, channel, 0) + s("")
    first = True
    for note in rows:
        if note is None:
            body += bytes([0x00])
        elif first:
            body += bytes([0b11, note, 0])  # note + instrument 0
            first = False
        else:
            body += bytes([0b01, note])
    body += bytes([0xFF])
    return b"PATN" + struct.pack("<I", len(body)) + body


def build():
    rows = [60, None, 64, None, 67, None, 72, None, 67, None, 64, None, 60, None, None, None]
    pats = [pattern(c, rows if c == SSG_CHANNEL else []) for c in range(CHANNELS)]
    chips = bytes([0xA5]) + bytes(31)
    info = bytes([1, 6, 6, 1]) + struct.pack("<f", 60.0)
    info += struct.pack("<HH", PATTERN_LEN, 1) + bytes([4, 16])
    info += struct.pack("<HHHI", 1, 0, 0, CHANNELS)
    info += chips + bytes([64]) + bytes(31) + bytes(32) + bytes(128)
    info += s("Bubblegum Brawl stand-in") + s("generated")
    info += struct.pack("<f", 440.0) + bytes(20)
    ptr_pos = len(info)
    info += bytes(4 * (CHANNELS + 1))  # instrument pointer + pattern pointers, patched below
    info += bytes(CHANNELS)  # orders: 1 order, pattern 0 per channel
    info += bytes([1]) * CHANNELS + bytes(CHANNELS) * 2  # fx columns, hide, collapse
    info += b"".join(s("") for _ in range(2 * CHANNELS))
    info += s("") + struct.pack("<f", 1.0) + bytes(28) + struct.pack("<HH", 1, 1)
    info += s("") + s("") + bytes([0]) + bytes(3)
    info += s("Neo Geo MVS") + s("Bubblegum Brawl") + s("") * 4 + bytes(12)
    info += struct.pack("<I", 0) + bytes([0]) + bytes(8) + bytes([1, 6])
    head_len = 32 + 8 + len(info)
    ins = b"INS2" + struct.pack("<IHH", 4 + 2 + 2 + len(s("lead")), 213, 6) + b"NA" + struct.pack("<H", len(s("lead"))) + s("lead")
    ins = b"INS2" + struct.pack("<I", len(ins) - 8) + ins[8:]
    off, ptrs = head_len, [head_len]
    off += len(ins)
    for p in pats:
        ptrs.append(off)
        off += len(p)
    info = info[:ptr_pos] + struct.pack("<%dI" % (CHANNELS + 1), *ptrs) + info[ptr_pos + 4 * (CHANNELS + 1):]
    out = b"-Furnace module-" + struct.pack("<HHI", 213, 0, 32) + bytes(8)
    out += b"INFO" + struct.pack("<I", len(info)) + info + ins + b"".join(pats)
    return zlib.compress(out)


if __name__ == "__main__":
    open(sys.argv[1], "wb").write(build())
