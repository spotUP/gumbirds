#!/usr/bin/env python3.14
"""Poop the Man draft v2, 2026-11-20: bigger walkers (32x48 cell), richer shading, umbrella carried in front.
Every shape is a hand-placed pixel grid. The code only assembles the grids (sprite parts on a walker rig,
16x16 tiles on a tilemap), snaps colours to Neo Geo 5 bits and counts tiles and sprites per scanline.
Run: python3.14 -I draw_poop_the_man.py"""
from PIL import Image
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PLANES = os.path.join(HERE, "..", "2026-11-10-backgrounds-final")
MOODS = ("dusk", "moon", "storm")
BG = (52, 56, 70)
ERR = []

def G(name, rows, w=16, h=None):
    if h is not None and len(rows) != h: ERR.append(f"{name}: {len(rows)} rows, want {h}")
    for i, r in enumerate(rows):
        if len(r) != w: ERR.append(f"{name} row {i}: {len(r)} wide, want {w}: {r}")
    return rows

def P(rows):
    """walker part grid: rows are left-aligned, padded right to the widest row"""
    w = max(len(r) for r in rows)
    return [r.ljust(w, ".") for r in rows]

def snap(hx):
    v = [int(hx[i:i + 2], 16) for i in (1, 3, 5)]
    return tuple(round(round(c * 31 / 255) * 255 / 31) for c in v)

def PAL(name, **kw):
    assert len(kw) <= 15, (name, len(kw))
    return {k: snap(v) for k, v in kw.items()}

# ---------------------------------------------------------------- palettes
# roles: k outline, s S h skin, R red (angry flush + accent), a A b B main cloth ramp, c C d second ramp, e E third, W white
WPAL = {
    "hat": PAL("hat", k="#101028", s="#983c30", S="#e08858", h="#ffc898", R="#e83838", a="#1c2458", A="#30488c", b="#4874c0",
               B="#80b4e8", c="#2c2448", C="#58487c", d="#8c7cb0", e="#5c2c1c", E="#b87030", W="#ffffff"),
    "bald": PAL("bald", k="#181020", s="#a84430", S="#f09868", h="#ffd8a8", R="#e84030", a="#a05010", A="#d89018", b="#f8d030",
                B="#fff490", c="#103c38", C="#20705c", d="#58b888", e="#5c5c78", E="#c0c0d8", W="#ffffff"),
    "woman": PAL("woman", k="#180820", s="#983c38", S="#d88060", h="#ffc8a8", R="#f04870", a="#701050", A="#b82888", b="#e858b0",
                 B="#ffa0d8", c="#281840", C="#503078", d="#8858b0", e="#086868", E="#30d0c0", W="#ffffff"),
    "kid": PAL("kid", k="#101030", s="#983c30", S="#e08858", h="#ffc898", R="#e83030", a="#1840a0", A="#3078e8", b="#88b8f8",
               B="#f0f8ff", c="#202060", C="#4058b8", e="#901020", E="#ff7858", g="#186830", G="#50d048"),
}
ITEMS = PAL("items", k="#101020", W="#ffffff", w="#e8e8c0", g="#a8b078", G="#687840", o="#582810", O="#a85820", t="#e8c078",
            p="#b01870", P="#f04898", l="#ff98c8", r="#701050", n="#187838", N="#58d048", y="#fff060")
UMB = {
    "red": PAL("ur", k="#101020", u="#801020", U="#d02838", V="#ff6858", W="#ffffff", m="#505868", M="#b8c0d0"),
    "yellow": PAL("uy", k="#101020", u="#a06008", U="#e8b010", V="#fff058", W="#ffffff", m="#505868", M="#b8c0d0"),
    "teal": PAL("ut", k="#101020", u="#085868", U="#10a0a8", V="#60e8d8", W="#ffffff", m="#505868", M="#b8c0d0"),
}
GROUND = {
    "dusk": PAL("gd", k="#180828", q="#48284c", Q="#683858", r="#904860", R="#c06860", j="#301838", e="#785070", E="#d89078",
                a="#201030", A="#302044", b="#504068", y="#b07828", Y="#f0c048", o="#402040", O="#583058"),
    "moon": PAL("gm", k="#080818", q="#202858", Q="#303c78", r="#4858a0", R="#7088c8", j="#101838", e="#485890", E="#98b8e8",
                a="#0c1028", A="#182040", b="#303c68", y="#607090", Y="#b0c8e0", o="#182048", O="#283468"),
    "storm": PAL("gs", k="#040c10", q="#10282c", Q="#183c40", r="#285858", R="#407878", j="#081820", e="#305050", E="#70a098",
                 a="#081418", A="#102428", b="#284044", y="#586850", Y="#a8b888", o="#0c3038", O="#58a8a0"),
}
SHOP = {
    "dusk": PAL("sd", k="#180820", w="#502040", W="#783050", x="#a85058", t="#382038", T="#c07850", g="#283058", G="#405890",
                l="#e89030", L="#ffe070", s="#b03028", S="#ffd8a0", c="#103850", C="#1c6078", n="#ff60b0"),
    "moon": PAL("sm", k="#080818", w="#1c2458", W="#2c3880", x="#4860a8", t="#141838", T="#6880b8", g="#182848", G="#305080",
                l="#d8a030", L="#fff088", s="#403098", S="#c0c8f0", c="#281848", C="#483078", n="#58f0e0"),
    "storm": PAL("ss", k="#040c10", w="#142c30", W="#204448", x="#386460", t="#0c1c20", T="#588078", g="#0c2030", G="#1c4050",
                 l="#b8b840", L="#f0ffa0", s="#701828", S="#a8b8a8", c="#181830", C="#303058", n="#ff5080"),
}
FIX = PAL("fix", k="#101020", W="#ffffff", w="#e8e8c0", g="#a8b078", G="#687840", d="#303048", p="#b01870", P="#f04898",
          l="#ff98c8", r="#701050", N="#58d048", c="#7088a8", C="#c8e0f0", y="#fff060")

# ---------------------------------------------------------------- walker parts (32x48 cell, face right; H flip for left)
HAT_TOP = [
    "......kkkkkkk",
    ".....kEEEEEEEk",
    "....kEEEEEEEsek",
    "....kEEEEsEsesk",
    "....kEEEsEsseek",
    "....kRRRRRRRRRk",
    "..kkkesesseeeekkkk",
    ".kEEEEEEsEsesseeek",
    "..kkkkkkkkkkkkkkk"]
BALD_TOP = [".....kkkkkk"]
WOMAN_TOP = [
    ".....kkkkkk",
    "...kkCCCCddkk",
    "..kCCCCCdCdddk",
    ".kcCCCCdCdddCdk"]
KID_TOP = [
    "....kkkkkkk",
    "..kkRRRREEEkk",
    ".kRRRRRREEEEEk",
    "keRRRRRRRREEEEk",
    "keeRRRRRRRRRRRkkkk",
    "keeeRRRRRkkkkREEEk"]
HEAD = {
 "hat": {"n": P(HAT_TOP + [
    "....kcSShhhhhhk",
    "....kcSShhWkhhk",
    "....ksSShhhhhhhk",
    "....ksSSShhhhhk",
    ".....ksSSSSkkk",
    ".....kssSSShhk",
    "......kkssSkk"]),
  "a": P(HAT_TOP + [
    "....kcRRkkSSSSk",
    "....kcRRRSkkSSk",
    "....ksRRSSWkSSSk",
    "....ksRRRSSSSSk",
    ".....ksRRkkkkk",
    ".....kssRksskk",
    "......kkssRkk"])},
 "bald": {"n": P(BALD_TOP + [
    "...kkSShhhhkk",
    "..kSShhhWWhhhk",
    ".kSSShhhhWhhhhk",
    ".kSSShhhhhhhhhk",
    ".kSSSShhhhhhhhk",
    ".ksSSShhhkkhhhk",
    "kSsSSSShhWkhhhhk",
    "kSssSSShhhhhhhhk",
    ".kksSSSShhhhhSk",
    "..ksSSSeEEEEEEk",     # owner fix: walrus moustache juts past the face front, with a closed mouth line under it (was a bare bar that read as a mouth)
    "..kssSSSeeeeeek",
    "...kssSSkkhhk",
    "....kkssSSkk"]),
  "a": P(BALD_TOP + [
    "...kkRRSSSSkk",
    "..kRRSSSWWSSSk",
    ".kRRRSSSSWSSSSk",
    ".kRRRSSSSSSSSSk",
    ".kRRRRSSSSSSSSk",
    ".ksRRRkkSSSSSSk",
    "kSsRRRRRkkSSSSSk",
    "kSssRRRSSWkSSSSk",
    ".kksRRRRSSSSSRk",
    "..ksRRReEEEEEk",
    "..kssRRkkkkkk",
    "...kssRksskk",
    "....kkssRkk"])},
 "woman": {"n": P(WOMAN_TOP + [
    ".kcCCCCCdddhhdk",
    "kccCCCCdhhhhhhk",
    "kccCCCShhhkkhhk",
    "kccCCSShhWkhhhk",
    "kcccCSShhhhhhhhk",
    "kcccCsSShhhRhhk",
    ".kccCsSSShRRhk",
    ".kcccksSSShhk",
    "..kkk.kssSkk",
    "......kssSk"]),
  "a": P(WOMAN_TOP + [
    ".kcCCCCCdddSSdk",
    "kccCCCCdSSSSSSk",
    "kccCCCRkkSSSSSk",
    "kccCCRRRSkkSSSk",
    "kcccCRRSSWkSSSSk",
    "kcccCsRRSSSSSSk",
    ".kccCsRRkkkkSk",
    ".kcccksRksskk",
    "..kkk.kssRkk",
    "......kssSk"])},
 "kid": {"n": P(KID_TOP + [
    ".kkkkkkkkShhkkkkk",
    ".kcCShhhhhhhhk",
    ".kcSShhhBkhhhk",
    ".kSsSShhBkhhhhk",
    "..ksSShhhhhhhk",
    "..ksSSShhkkhk",
    "...kssSSShhk",
    "....kkkssSk"]),
  "a": P(KID_TOP + [
    ".kkkkkkkkSSSkkkkk",
    ".kcCRRkkSSSSSk",
    ".kcRRRRRkkSSSk",
    ".kSsRRRSBkSSSSk",
    "..ksRRRSSSSSSk",
    "..ksRRRkkkkSk",
    "...kssRksskk",
    "....kkkssSk"])},
}
TORSO = {
 "hat": P([                      # long belted coat, shirt and red tie
    "......kssSk",
    "....kkBBWRWkk",
    "...kAbBBBWRBbk",
    "..kaAbBBBBRBBbk",
    "..kaAAbBBBBBBbk",
    "..kaAAbbBBBBbbk",
    "..kaaAbAbBBBbbk",
    "..kaaAAbAbBBbAk",
    "..kaaAAAbBkBbAk",
    "..kaaAAAbbBBbAk",
    "..kcccCcCCdCdck",
    "..kaaAAAbbBBbAk",
    "..kaaAAAAbBkbAk",
    ".kaaaAAAAbbBbAAk",
    ".kaaaAAAbAbBBbAk",
    ".kaaaAAAAbbBBbAk",
    ".kaaAaAAAbbBBbAk",
    ".kaaaAAAAAbbBbAk",
    ".kkaaaAAAAbbbAkk",
    "..kkkkkkkkkkkkk"]),
 "bald": P([                     # round belly, shirt with red braces
    "......kssSk",
    "....kkAbBBBkk",
    "...kaAbRBBBRBk",
    "..kaAAbRBBBBRBk",
    "..kaAAbRbBBBBRBk",
    "..kaAAbbRBBBBBRBk",
    "..kaaAbbRbBBBBBRk",
    "..kaaAAbbRBbBBBBBk",
    "..kaaAAbbbRBBBBBBk",
    "..kaaaAAbbbBbBBBbk",
    "..kaaaAAAbbbBBBbbk",
    "...kaaaAAAbbbbbbk",
    "...kkaaaAAAAbbkk",
    "....kcckkkkkkCdk",
    "....kcCCCCCCCCdk"]),
 "woman": P([                    # scarf, fitted dress, flared skirt
    ".......kEEEEk",
    ".....kkEEeEEEkk",
    "....kAbkeEEekBbk",
    "...kaAbBkEekBBbk",
    "...kaAbBBkEkBBbk",
    "...kaAAbBkEkBbbk",
    "....kaAbBBkBBbk",
    "....kaAAbBBBbk",
    ".....kaAbBBbk",
    ".....kaAAbBbk",
    "....kaAAbBBBbk",
    "...kaaAbAbBBBbk",
    "..kaaAAbAbBBBBbk",
    "..kaaAAAbAbBBBbk",
    ".kaaaAAbAbbBBBBbk",
    ".kaaAaAAbAbBbBBbk",
    ".kkaakAAbkbbBkbkk",
    "...kk.kkk.kkk.k"]),
 "kid": P([                      # striped shirt, backpack, shorts
    ".....ksSk",
    ".kkkkBBBBBkk",
    "kGGGkAAAAAbBk",
    "kGgGkBBBBBBBk",
    "kGggkAAAAAbbk",
    "kgggkBBBBBBBk",
    "kgggkaAAAAbbk",
    ".kkkkCCCCCCCk",
    "....kcCCCCCCk",
    "....kcCCkCCCk"]),
}
BAG = P([                        # woman's handbag: strap from the shoulder, bag on the rear hip
    "......kE",
    ".....kEk",
    ".....kEk",
    "....kEk",
    "....kEk",
    "...kEk",
    "...kEk",
    "..kEkk",
    ".kkkkkkkk",
    "kEEEEEEeek",
    "kEWEEEeeek",
    "kEEEEeeeek",
    "kEeEeeeeek",
    "keeeeeeeek",
    ".kkkkkkkk"])
# arms: name -> (shoulder column in the grid, shoulder row in the grid, grid)
ARMS = {
 "adult": {
  "mid": (6, 0, P([
    ".....kBBk",
    "....kAbBBk",
    "....kAbBBk",
    "....kAAbBk",
    "....kaAbBk",
    "....kaAbBk",
    "....kaAbbk",
    "....kaAAbk",
    "....kaAAbk",
    "....kkkkkk",
    "....ksShk",
    "....ksShk",
    ".....kkk"])),
  "fwd": (6, 0, P([
    ".....kBBk",
    "....kAbBBk",
    "....kAbBBBk",
    "....kaAbBBk",
    ".....kaAbBBk",
    ".....kaAAbBk",
    "......kaAbBBk",
    "......kaAAbBk",
    ".......kaAbbk",
    "........kkkSk",
    "........kSShk",
    ".........kkk"])),
  "back": (6, 0, P([
    ".....kBBk",
    "....kAbBBk",
    "...kAAbBBk",
    "...kaAbBk",
    "..kaAbBBk",
    "..kaAbBk",
    ".kaAAbBk",
    ".kaAbbk",
    "kaAAbk",
    "kkkkk",
    "ksShk",
    ".kkk"])),
  "hold": (6, 0, P([              # forearm level, hand in front of the body: grips the umbrella
    ".....kBBk",
    "....kAbBBk",
    "....kAbBBk",
    "....kaAbBk",
    "....kaAbBkkkkkkk",
    "....kaAbBBBBBBBkkk",
    "....kaAAbbbbbbbkShk",
    ".....kaAAAAAAAAkShk",
    "......kkkkkkkkkkkk"])),
  "fist1": (6, 13, P([
    "..........kkkk",
    ".........khhShk",
    ".........kSSSsk",
    ".........kkkkk",
    "..........kBbk",
    "..........kBbk",
    ".........kBbAk",
    ".........kBbAk",
    "........kBBbAk",
    ".......kBBbAk",
    "......kBBbAk",
    ".....kBBbAk",
    "....kABbAk",
    "....kAbBk"])),
  "fist2": (6, 15, P([
    ".........kkkk",
    "........khhShk",
    "........kSSSsk",
    "........kkkkk",
    ".........kBbk",
    ".........kBbk",
    ".........kBbk",
    ".........kBbAk",
    ".........kBbAk",
    "........kBBbAk",
    "........kBbAk",
    ".......kBBbAk",
    "......kBBbAk",
    ".....kBBbAk",
    "....kABbAk",
    "....kAbBk"])),
  "throw": (7, 10, P([
    ".kkkk",
    "khhShk",
    "kSSSsk",
    ".kkkkk",
    "..kbBk",
    "..kAbBk",
    "...kAbBk",
    "...kaAbBk",
    "....kaAbBk",
    ".....kaAbBk",
    ".....kaAbBk"])),
  "far": (0, 0, P([               # far arm's fist showing in front of the body
    ".kkkkkkk",
    "kaaAAkShk",
    "kaaaAksSk",
    ".kkkkkkk"])),
 },
 "kid": {
  "mid": (3, 0, P([
    "..kBk",
    ".kAbBk",
    ".kAbBk",
    ".kaAbk",
    ".kaAbk",
    ".kkkkk",
    ".ksShk",
    "..kkk"])),
  "fwd": (3, 0, P([
    "..kBk",
    ".kAbBk",
    ".kAbBBk",
    "..kaAbBk",
    "...kaAbk",
    "....kkSk",
    "....kShk",
    ".....kk"])),
  "back": (4, 0, P([
    "...kBk",
    "..kAbBk",
    ".kAAbBk",
    ".kaAbk",
    "kaAbk",
    "kkkk",
    "ksSk",
    ".kk"])),
  "hold": (3, 0, P([
    "..kBk",
    ".kAbBk",
    ".kAbBkkkkkkk",
    ".kaAbBBBBBBkkk",
    ".kaAAbbbbbbbkShk",
    "..kkkkkkkkkkkkk"])),
  "fist1": (3, 9, P([
    ".......kkk",
    "......khShk",
    "......kSSsk",
    ".......kkk",
    ".......kBk",
    "......kBbk",
    ".....kBbAk",
    "....kBbAk",
    "..kkBbAk",
    ".kAbBAk"])),
  "fist2": (3, 10, P([
    "......kkk",
    ".....khShk",
    ".....kSSsk",
    "......kkk",
    "......kBk",
    "......kBbk",
    "......kBbk",
    ".....kBbAk",
    "....kBbAk",
    "..kkBbAk",
    ".kAbBAk"])),
  "throw": (6, 7, P([
    ".kkk",
    "khShk",
    "kSSsk",
    ".kkk",
    ".kbBk",
    "..kAbBk",
    "...kaAbBk",
    "....kaAbk"])),
  "far": (0, 0, P([
    ".kkkkk",
    "kaAAkSk",
    ".kkkkk"])),
 },
}
# one leg per grid, hip at the top. Poses: 0 contact forward, 1 bearing, 2 support, 3 push off, 4 lifted behind, 5 swing through
LEGS = {
 "adult": [P(g) for g in ([
    "....kCCCCdk",
    "....kCCCCdk",
    "....kcCCCdk",
    "....kcCCCCdk",
    ".....kcCCCdk",
    ".....kcCCCCdk",
    "......kcCCCdk",
    "......kcCCCdk",
    ".......kcCCdk",
    ".......kcCCCdk",
    "........kcCCdk",
    "........kcCCdk",
    "........kcCCdkk",
    "........kEEEEEEk",
    "........keeEEEEk",
    ".........kkkkkk"], [
    "....kCCCCdk",
    "....kCCCCdk",
    "....kcCCCdk",
    "....kcCCCCdk",
    ".....kcCCCdk",
    ".....kcCCCdk",
    ".....kcCCCdk",
    ".....kcCCdk",
    ".....kcCCdk",
    ".....kcCCdk",
    ".....kcCCdk",
    ".....kcCCdk",
    ".....kcCCdkk",
    ".....kEEEEEEk",
    ".....keeeEEEEk",
    "......kkkkkkk"], [
    "....kCCCCdk",
    "....kCCCCdk",
    "....kcCCCdk",
    "....kcCCCdk",
    "....kcCCCdk",
    "....kcCCCdk",
    "....kcCCdk",
    "....kcCCdk",
    "....kcCCdk",
    "....kcCCdk",
    "....kcCCdk",
    "....kcCCdk",
    "....kcCCdkk",
    "....kEEEEEEk",
    "....keeeEEEEk",
    ".....kkkkkkk"], [
    "....kCCCCdk",
    "....kCCCCdk",
    "....kcCCCdk",
    "...kcCCCdk",
    "...kcCCCdk",
    "..kcCCCdk",
    "..kcCCCdk",
    "..kcCCdk",
    ".kcCCdk",
    ".kcCCdk",
    ".kcCdk",
    "kcCCdk",
    "kEEdk",
    "keEEk",
    "keeEEk",
    ".kkkkk"], [
    "....kCCCCdk",
    "....kCCCCdk",
    "....kcCCCdk",
    "....kcCCCdk",
    "...kcCCCCdk",
    "...kcCCCdk",
    "...kcCCCdk",
    "..kkcCCdk",
    ".kcCcCdk",
    "kcCCkkk",
    "kEEk",
    "kEeEk",
    "keeek",
    ".kkk"], [
    "....kCCCCdk",
    "....kCCCCdk",
    "....kcCCCdk",
    "....kcCCCCdk",
    ".....kcCCCdk",
    ".....kcCCCCdk",
    "......kcCCCdk",
    "......kcCCdk",
    ".....kcCCdk",
    ".....kcCCdk",
    "....kcCCdk",
    "....kEEEdkk",
    "....keeEEEEk",
    ".....kkkkkk"])],
 "woman": [P(g) for g in ([
    "....kSShk",
    "....kSShk",
    ".....kSShk",
    ".....kSShk",
    "......kSShk",
    "......kSShk",
    ".......kShk",
    ".......kSShk",
    "........kShk",
    "........kShk",
    "........kShkk",
    "........kAAAAk",
    "........kakaAAk",
    ".........k.kkk"], [
    "....kSShk",
    "....kSShk",
    "....kSShk",
    ".....kSShk",
    ".....kSShk",
    ".....kSShk",
    ".....kShk",
    ".....kShk",
    ".....kShk",
    ".....kShk",
    ".....kShkk",
    ".....kAAAAk",
    ".....kakaAAk",
    "......k.kkk"], [
    "....kSShk",
    "....kSShk",
    "....kSShk",
    "....kSShk",
    "....kSShk",
    "....kSShk",
    "....kShk",
    "....kShk",
    "....kShk",
    "....kShk",
    "....kShkk",
    "....kAAAAk",
    "....kakaAAk",
    ".....k.kkk"], [
    "....kSShk",
    "....kSShk",
    "...kSShk",
    "...kSShk",
    "..kSShk",
    "..kSShk",
    "..kShk",
    ".kSShk",
    ".kShk",
    ".kShk",
    "kShk",
    "kaAk",
    "kaAAk",
    ".kkkk"], [
    "....kSShk",
    "....kSShk",
    "....kSShk",
    "...kSShk",
    "...kSShk",
    "..kkShk",
    ".kSSShk",
    "kSSkkk",
    "kAk",
    "kaAk",
    ".kk"], [
    "....kSShk",
    "....kSShk",
    ".....kSShk",
    ".....kSShk",
    "......kSShk",
    "......kShk",
    ".....kShk",
    ".....kShk",
    "....kShk",
    "....kAAkk",
    "....kaAAAk",
    ".....kkkk"])],
 "kid": [P(g) for g in ([
    "...kSShk",
    "...kSShk",
    "....kSShk",
    "....kSShk",
    ".....kShk",
    ".....kShkk",
    ".....kRRBBk",
    ".....kRRRBk",
    "......kkkk"], [
    "...kSShk",
    "...kSShk",
    "...kSShk",
    "...kSShk",
    "...kShk",
    "...kShkk",
    "...kRRBBk",
    "...kRRRBk",
    "....kkkk"], [
    "...kSShk",
    "..kSShk",
    "..kSShk",
    ".kSShk",
    ".kShk",
    "kShk",
    "kRBk",
    "kRRBk",
    ".kkkk"], [
    "...kSShk",
    "....kSShk",
    "....kSShk",
    "...kShkk",
    "...kRRBBk",
    "...kRRRBk",
    "....kkkk"])],
}
FARMAP = {"adult": {"d": "C", "C": "c", "E": "e"}, "woman": {"h": "S", "S": "s", "A": "a"}, "kid": {"h": "S", "S": "s", "B": "b", "R": "e"}}
TYPES = ("hat", "bald", "woman", "kid")
# rig: part positions in the 32x48 cell. sh = near shoulder, far = far fist grid, top = first head row
RIG = {
 "hat":   dict(head=(4, 0), torso=(5, 16), legs=(5, 32), sh=(12, 18), far=(16, 23), top=0, legset="adult"),
 "bald":  dict(head=(5, 8), torso=(4, 20), legs=(5, 32), sh=(12, 23), far=(16, 28), top=8, legset="adult"),
 "woman": dict(head=(5, 6), torso=(3, 20), legs=(7, 34), sh=(12, 22), far=(16, 27), top=6, legset="woman", bag=(4, 22)),
 "kid":   dict(head=(5, 18), torso=(5, 31), legs=(8, 39), sh=(13, 32), far=(18, 35), top=18, legset="kid"),
}
# walk cycle: (near leg pose, far leg pose, body bob, near arm). Arm swings against the near leg.
WALK = {"adult": [(0, 3, 0, "back"), (1, 4, 1, "back"), (2, 5, 0, "mid"), (3, 0, 0, "fwd"), (4, 1, 1, "fwd"), (5, 2, 0, "mid")],
        "kid": [(0, 2, 0, "back"), (1, 3, 1, "mid"), (2, 0, 0, "fwd"), (3, 1, 1, "mid")]}
WALK["woman"] = WALK["adult"]

# ---------------------------------------------------------------- umbrella
CLOSED = G("umb_closed", [       # rolled umbrella held upright in front of the walker, grip at row 21
    "...kk...", "...kk...", "..kVUk..", "..kVUk..", "..kWVUk.", "..kVVUk.", ".kWVUuk.", ".kVVUuk.", ".kVVUuk.", ".kVUUuk.",
    ".kVVUuk.", ".kVUUuk.", ".kVVUuk.", ".kVUUuk.", ".kVVUuk.", ".kVUuuk.", ".kVUUuk.", "..kVUuk.", "..kUUuk.", "..kkkkk.",
    "...kMk..", "...kMk..", "...kMk..", "...kmk..", "...kmkk.", "...kmmmk", "....kkmk", ".....kk."], w=8, h=28)
OPEN = G("umb_open", [
    "...............kk...............",
    "...........kkkkVVkkkk...........",
    "........kkkVVVVVUUUUUkkk........",
    "......kkWVVVVkVVUUUkUUUUkk......",
    "....kkWWVVVVkVVVUUUUkUUUUukk....",
    "...kWWVVVVVkVVVVUUUUUkUUUuuuk...",
    "..kWVVVVVVkVVVVUUUUUUkUUUUuuuk..",
    ".kWVVVVVVVkVVVUVUUUUUUkUUUuUuuk.",
    ".kVVVVVVVkVVVVVUUUUUUUkUUUUuuuk.",
    "kVVVUVVVVkVVVUVUUUUuUUUkUUuUuuuk",
    "kVVkkkVVVkVVkkkkUUkkkkUkUkkkuuuk",
    ".kk...kkk.kk....kk....k.k...kkk."], w=32, h=12)
HALF = G("umb_half", [
    ".......kk.......",
    "......kVUk......",
    ".....kWVUUk.....",
    "....kWVVUUuk....",
    "....kVVkUUuk....",
    "...kWVVkUUUuk...",
    "...kVVVkUUUuk...",
    "..kWVVkVUUkUuk..",
    "..kVVVkVUUkUuk..",
    ".kVVVVkVUUkUuuk.",
    ".kVVUVkVUUkUuuk.",
    "kVVkkVkVUkkkUuuk",
    ".kk..kk.kk..kkk."], w=16, h=13)
# ---------------------------------------------------------------- items, fix tiles, street (unchanged from v1)
SHOE = [G("shoe0", ["................", "................", "................", "................", "...kkk..........", "..kOOOk.........",
                    "..kOoOkkk.......", "..kOOWOOOkkk....", "..koOOWOOOOOk...", "..kttttttttttk..", "...kkkkkkkkkk...", "................",
                    "................", "................", "................", "................"], h=16),
        G("shoe1", ["................", "................", "....kkkkkk......", "...kOOOoOtk.....", "...kOoOOOtk.....", "...kkOWOOtk.....",
                    ".....kWOOtk.....", ".....kOOOtk.....", ".....kOOOtk.....", ".....kOOOtk.....", ".....kOOOtk.....", "......kOOtk.....",
                    ".......kkk......", "................", "................", "................"], h=16),
        G("shoe2", ["................", "................", "................", "................", "................", "...kkkkkkkkkk...",
                    "..kttttttttttk..", "...kOOOOOWOOok..", "....kkkOOOWOOk..", ".......kkkOoOk..", ".........kOOOk..", "..........kkk...",
                    "................", "................", "................", "................"], h=16),
        G("shoe3", ["................", "................", "................", "......kkk.......", ".....ktOOk......", ".....ktOOOk.....",
                    ".....ktOOOk.....", ".....ktOOOk.....", ".....ktOOOk.....", ".....ktOOWk.....", ".....ktOOWOkk...", ".....ktOOOoOk...",
                    ".....ktOoOOOk...", "......kkkkkk....", "................", "................"], h=16)]
POOP = [G("poop0", ["...kk...", "..kWwk..", "..kWwk..", ".kWWwgk.", ".kWWwgk.", ".kWwwGk.", "..kwgk..", "...kk..."], w=8, h=8),
        G("poop1", ["...k....", "..kWk...", "..kWwk..", "..kWwgk.", ".kWWwgk.", ".kWwgGk.", ".kwwgk..", "..kkk..."], w=8, h=8)]
SPLAT_HEAD = [
 G("sh0", ["......W.........", "..W....W...W....", "....kWWWWk......", ".W.kWWWWWWk..W..", "...kWWwWWwk.....", "..kWWWwwWWWk....",
           "..kwWWWWWWgk....", "...kkkkkkkk....."], h=8),
 G("sh1", ["................", "................", "................", ".....kkkkk......", "...kkWWWWWkk....", "..kWWWwWWWWwk...",
           "..kwWWWWwWWgk...", "...kwk....kgk..."], h=8),
 G("sh2", ["................", "................", "................", "................", "....kkWWWkk.....", "..kkWWWwWWWkk...",
           "..kwWWWWWWwgk...", "..kWk.kwk..kgk.."], h=8)]
SPLAT_PAVE = [
 G("sp0", ["................", "................", "..W...W....W....", "....W..WW..W....", ".W..kWWWWWk..W..", "...kWWWwWWWk....",
           ".kkWWwWWWWwWkk..", "..kkkkkkkkkkk..."], h=8),
 G("sp1", ["................", "................", "................", "................", "................", "....kkkkkkk.....",
           ".kkWWWWwWWWWkk..", "kWWwWWWWWWwWWgk."], h=8),
 G("sp2", ["................", "................", "................", "................", "................", "................",
           "..kkWWWwWWWkk.W.", ".kWwWWWWWwWWgk.."], h=8)]
BOUNCE = [
 G("b0", ["................", "................", "................", "................", "......kkkk......", "....kkWWWwkk....",
          "...kWWWwWWWgk...", "....kkkkkkkk...."], h=8),
 G("b1", ["................", "..kk......kk....", ".kWwk....kWgk...", "..kk..kk..kk....", ".....kWwk.......", "..W...kk....W...",
          "................", "................"], h=8),
 G("b2", ["kk...........kk.", "Wwk.........kWk.", "kk.....k.....k..", "......kWk.......", ".......k........", "................",
          "................", "................"], h=8)]
BERRY = G("berry", [
    "................", ".......kk.......", "......kNNk.kk...", ".....kNnnkkNNk..", "......knnkNNnk..", "....kkkkkknnk...",
    "...kPllPkkkkk...", "..kPlWlPPkPllk..", "..kPPlPPpkPWlPk.", "..kpPPPprkPlPPk.", "...kppprkkpPPpk.", "...kkrrkPlkpprk.",
    "..kPllkkPWlkrk..", "..kPWPpkPPPpk...", "..kpPprkpPprk...", "...kkkk.kkkk...."], h=16)
SPARK = G("spark", ["..y..", "..y..", "yyWyy", "..y..", "..y.."], w=5, h=5)
# fix layer (8x8)
PIP_ON = POOP[0]
PIP_OFF = G("pip_off", ["...kk...", "..kddk..", "..kddk..", ".kddddk.", ".kddddk.", ".kddddk.", "..kddk..", "...kk..."], w=8, h=8)
BERRY_ICON = G("berry_icon", ["...kNk..", "..kkkk..", ".kPllPk.", "kPlWlPPk", "kPPlPPpk", "kpPPPprk", ".kppprk.", "..kkkk.."], w=8, h=8)
RAIN = [G("rain1", ["......c.", ".....c..", "....C...", "........", "........", ".c......", "c.......", "........"], w=8, h=8),
        G("rain2", ["........", "...c....", "..c.....", ".C......", "........", ".......c", "......c.", "........"], w=8, h=8)]
RAIN_MAP = G("rain_map", ["1..2...1.2..1...2..1..2.1...2..1.2...1.2", ".2...1.2...1..2.1...2..1..2.1...2..1.2..",
                          "..1.2...1.2..1...2.1..2...1.2..1...2..1.", "2..1...2..1.2...1.2...1.2..1...2.1..2..1"], w=40)
DIGIT = {"x": ["...", "W.W", ".W.", "W.W", "..."], "0": [".W.", "W.W", "W.W", "W.W", ".W."], "2": ["WW.", "..W", ".W.", "W..", "WWW"],
         "3": ["WW.", "..W", ".W.", "..W", "WW."], "6": [".WW", "W..", "WW.", "W.W", ".W."]}

# ---------------------------------------------------------------- street tiles (16x16), shop palette
FASCIA = G("fascia", ["TTTTTTTTTTTTTTTT", "tTttTtttTttTtttT", "kkkkkkkkkkkkkkkk", "cccccccccccccccc", "cCccccccCccccccc", "cccccccccccccccc",
                      "ccccCccccccccCcc", "cccccccccccccccc", "cCcccccccCcccccc", "cccccccccccccccc", "kkkkkkkkkkkkkkkk", "tttttttttttttttt",
                      "SSSSssssSSSSssss", "SSSSssssSSSSssss", "SSSSssssSSSSssss", "SSSsSsssSSSsSsss"], h=16)
AWN = G("awn", ["SSSsSsssSSSsSsss", "SSsSssssSSsSssss", "SsSsssssSsSsssss", "sSsssssssSssssss", "kSSSssskkSSSsssk", "kkSssskkkkSssskk",
                "kkkkkkkkkkkkkkkk"], h=7)
WIN_L1 = AWN + G("winL1", ["wttttttttttttttt", "wtkkkkkkkkkkkkkk", "wtkgGGLLLLLLLLLL", "wtkGGLLLLLLlLLLL", "wtkGLLLLLlLLLLlL",
                           "wtkLLLLlLLLLlLLl", "wtkLLlLLLlLLLlLl", "wtkLlLLlLLlLlLll", "wtklLlLLlLlLllLl"], h=9)
WIN_M1 = AWN + G("winM1", ["tttttttttttttttt", "kkkkkkkkkkkkkkkk", "LLLLLLLLLLLLLLLL", "LLLLlLLLLLLLLlLL", "LLlLLLLLlLLLLLLL",
                           "LLLLLlLLLLLlLLLl", "lLLlLLLlLLLLLlLL", "LlLLlLlLLlLlLLlL", "lLlLlLLlLlLLlLlL"], h=9)
WIN_R1 = AWN + G("winR1", ["tttttttttttttttw", "kkkkkkkkkkkkkktw", "LLLLLLLLLLGGgktw", "LLLlLLLLLLLGGktw", "LLLLLLlLLLLLGktw",
                           "LlLLLLLLlLLLLktw", "LLLlLLlLLLLlLktw", "lLlLLlLLlLLlLktw", "LlLlLLlLlLlLlktw"], h=9)
DOOR1 = AWN + G("door1", ["wttttttttttttttw", "wtkkkkkkkkkkkktw", "wtkgGGgGGgGGgktw", "wtkGGgGGgGGgGktw", "wtkkkkkkkkkkkktw",
                          "wtkTTTTTTTTTTktw", "wtkTtttttttTtktw", "wtkTtgGGGGgTtktw", "wtkTtGGlLGGTtktw"], h=9)
BASE4 = ["WWxWWWwWWWxWWWwW", "kkkkkkkkkkkkkkkk", "wWWWxWWWwWWWxWWW", "wwwwwwwwwwwwwwww", "kkkkkkkkkkkkkkkk"]
WIN_L2 = G("winL2", ["wtkLlllLllLlllll", "wtklkklllkkllkkl", "wtkkTTkllkTklTTk", "wtkkTtkgkTTTktTk", "wtkkttklkTtTkttk", "wtkkkkkkkkkkkkkk",
                     "wtkglgGgglgGGglg", "wtkgGgGGgGgGGGgG", "wtkkkkkkkkkkkkkk", "TTTTTTTTTTTTTTTT", "tttttttttttttttt"] + BASE4, h=16)
WIN_M2 = G("winM2", ["lLllLlllLlllllLl", "llkkllllkkklllkl", "lkTTklkkTTTkkkTk", "lkTtkkTkTtTkTkTk", "lkttkktkTttktktk", "kkkkkkkkkkkkkkkk",
                     "gglgGgglgGgGglgg", "GgGGgGgGGgGGgGGg", "kkkkkkkkkkkkkkkk", "TTTTTTTTTTTTTTTT", "tttttttttttttttt"] + BASE4, h=16)
WIN_R2 = G("winR2", ["lLlllLllLlllLktw", "lkkllllkkllllktw", "kTTklkkTTkklkktw", "kTtkkTkTtkTkTktw", "kttkktkttktktktw", "kkkkkkkkkkkkkktw",
                     "glgGgglgGgGglktw", "gGGgGgGGgGGgGktw", "kkkkkkkkkkkkkktw", "TTTTTTTTTTTTTTTw", "tttttttttttttttw"] + BASE4, h=16)
DOOR2 = G("door2", ["wtkTtGlLLlGTtktw", "wtkTtGGllGGTtktw", "wtkTtgGGGGgTtktw", "wtkTtttttttTtktw", "wtkTTTTTTTTTLktw", "wtkTtttttttTLktw",
                    "wtkTtTTTTTtTtktw", "wtkTtTttttTTtktw", "wtkTtTttttTTtktw", "wtkTtTTTTTtTtktw", "wtkTtttttttTtktw", "wtkkkkkkkkkkkktw",
                    "xxxxxxxxxxxxxxxx", "WWWWWWWWWWWWWWWW", "wwwwwwwwwwwwwwww", "kkkkkkkkkkkkkkkk"], h=16)
BRICK_A = G("brickA", ["WWWxWWWwWWWWxWWw", "WxWWWWWwWWxWWWWw", "WWWWxWWwWWWWWWxw", "wwwwwwwwwwwwwwww", "WWWwWWWWxWWwWWWW", "xWWwWWxWWWWwWxWW",
                       "WWWwWWWWWWxwWWWW", "wwwwwwwwwwwwwwww", "WxWWWWWwWWWWxWWw", "WWWWxWWwWxWWWWWw", "WWxWWWWwWWWWWxWw", "wwwwwwwwwwwwwwww",
                       "WWWwWxWWWWWwWWWx", "WxWwWWWWxWWwWWWW", "WWWwWWWxWWWwWxWW", "wwwwwwwwwwwwwwww"], h=16)
BRICK_PIPE = G("brickPipe", ["WWWxWkTTtkWWxWWw", "WxWWWkTTtkxWWWWw", "WWWWxkTTtkWWWWxw", "wwwwwkTTtkwwwwww", "WWWwWkTttkWwWWWW", "xWWwWkTTtkWwWxWW",
                             "WWWwkTTTttkwWWWW", "wwwwkkkkkkkwwwww", "WxWWWkTTtkWWxWWw", "WWWWxkTTtkWWWWWw", "WWxWWkTTtkWWWxWw", "wwwwwkTTtkwwwwww",
                             "WWWwWkTttkWwWWWx", "WxWwWkTTtkWwWWWW", "WWWwWkTTtkWwWxWW", "wwwwwkTTtkwwwwww"], h=16)
BRICK_POSTER = G("brickPoster", ["WWWxWWWwWWWWxWWw", "WxkkkkkkkkkkkkWw", "WWkLLLLLLLLLLkxw", "wwkLnnnLLnnnLkww", "WWkLnLnLLnLnLkWW", "xWkLnnnLLnnnLkWW",
                                 "WWkLLLLLLLLLLkWW", "wwkLcccccccCLkww", "WxkLcCcccccCLkWw", "WWkLccccCccCLkWw", "WWkLLLLLLLLLlkWw", "wwkkkkkkkkkklkww",
                                 "WWWwWxWWWWWwklWx", "WxWwWWWWxWWwWkWW", "WWWwWWWxWWWwWxWW", "wwwwwwwwwwwwwwww"], h=16)
BRICK_BASE = G("brickBase", ["WWWxWWWwWWWWxWWw", "WxWWWWWwWWxWWWWw", "WWWWxWWwWWWWWWxw", "wwwwwwwwwwwwwwww", "WWWwWWWWxWWwWWWW", "xWWwWWxWWWWwWxWW",
                             "WWWwWWWWWWxwWWWW", "wwwwwwwwwwwwwwww", "WxWWWWWwWWWWxWWw", "WWWWxWWwWxWWWWWw", "kkkkkkkkkkkkkkkk", "TTTTTTTTTTTTTTTT",
                             "tTttTtttTttTtttT", "tttttttttttttttt", "wwwwwwwwwwwwwwww", "kkkkkkkkkkkkkkkk"], h=16)
BRICK_PIPE_BASE = G("brickPipeBase", ["WWWxWkTTtkWWxWWw", "WxWWWkTTtkxWWWWw", "WWWWxkTTtkWWWWxw", "wwwwwkTTtkwwwwww", "WWWwWkTttkWwWWWW", "xWWwWkTTtkWwWxWW",
                                      "WWWwWkTTtkWwWWWW", "wwwwwkTTtkwwwwww", "WxWWWkTTtkWWxWWw", "WWWWxkTTtkWWWWWw", "kkkkkkTTtkkkkkkk", "TTTTTkTTtkTTTTTT",
                                      "tTttTkTTttkttttT", "tttttkkTTttktttt", "wwwwwwwkkkkkwwww", "kkkkkkkkkkkkkkkk"], h=16)
BRICK_TOP = G("brickTop", ["TTTTTTTTTTTTTTTT", "tTttTtttTttTtttT", "kkkkkkkkkkkkkkkk", "WWWwWWWWxWWwWWWW", "xWkkkkkkkkkkkkWW", "WWktttttttttTkWW",
                           "wwktgGGgktGLLkww", "WxktGGgGktLLlkWw", "WWktGgGGktLlLkWw", "WWktgGGgktlLlkWw", "wwktttttttttTkww", "WWkkkkkkkkkkkkWx",
                           "WxTTTTTTTTTTTTWW", "WWWwWWWxWWWwWxWW", "wwwwwwwwwwwwwwww", "WxWWWWWwWWWWxWWw"], h=16)
BRICK_TOP_PIPE = G("brickTopPipe", ["TTTTTTTTTTTTTTTT", "tTttTkkkkkkTtttT", "kkkkkkTTTtkkkkkk", "WWWwWkTTtkWwWWWW", "xWWwWkTTtkWwWxWW", "WWWwWkTTtkWwWWWW",
                                    "wwwwwkTTtkwwwwww", "WxWWWkTTtkWWxWWw", "WWWWxkTTtkWWWWWw", "WWxWWkTTtkWWWxWw", "wwwwwkTTtkwwwwww", "WWWwWkTttkWwWWWx",
                                    "WxWwWkTTtkWwWWWW", "WWWwkTTTttkwWxWW", "wwwwkkkkkkkwwwww", "WxWWWkTTtkWWxWWw"], h=16)
LETTER = {"G": [".nnnn", "n....", "n..nn", "n...n", ".nnn."], "U": ["n...n", "n...n", "n...n", "n...n", ".nnn."], "M": ["n...n", "nn.nn", "n.n.n", "n...n", "n...n"],
          "C": [".nnnn", "n....", "n....", "n....", ".nnnn"], "A": [".nnn.", "n...n", "nnnnn", "n...n", "n...n"], "F": ["nnnnn", "n....", "nnnn.", "n....", "n...."],
          "E": ["nnnnn", "n....", "nnnn.", "n....", "nnnnn"], "B": ["nnnn.", "n...n", "nnnn.", "n...n", "nnnn."], "K": ["n...n", "n..n.", "nnn..", "n..n.", "n...n"],
          "R": ["nnnn.", "n...n", "nnnn.", "n..n.", "n...n"], "Y": ["n...n", ".n.n.", "..n..", "..n..", "..n.."]}
# ground palette tiles
PAVE_A = G("paveA", ["jjjjjjjjjjjjjjjj", "QQqQQQQkQQQQqQQQ", "QqQQQrQkQQrQQQqQ", "QQQrQQQkQrQQQQQQ", "QQrQQQqkQQQQrQQq", "qQQQrQQkQQqQQQrQ",
                     "QQqQQQQkQrQQQqQQ", "qqQqqQqkqQqqQqqQ", "jjjjjjjjjjjjjjjj", "QrQkQQrQQQrQQQrQ", "rQQkQrQQrQQQrQQQ", "QQrkrQQrQQQrQQrQ",
                     "QrQkQQrQQrQQQrQQ", "rQQkQrQQrQQrQQQr", "QQrkQQQrQQQQrQrQ", "qQQkqQqQQqQqQQqQ"], h=16)
PAVE_B = G("paveB", ["jjjjjjjjjjjjjjjj", "QQQQqQQkQQqQQQQQ", "QqQQQQrkQQQQkQqQ", "QQQrQQQkQrQkQQQQ", "QQQQQqQkQQkjQrQq", "qQrQQQQkQQQkQQQQ",
                     "QQQQQrQkQrQQkqQQ", "qQqqQqqkqQqQqkqQ", "jjjjjjjjjjjjjkjj", "QrQkQQQrQQQrQQkQ", "rQQkQrQQQoooQQQr", "QQrkrQQQooqqoQrQ",
                     "QrQkQQrQoqqqoQQQ", "rQQkQQQrQoooQrQr", "QQrkQrQQQQQQrQQQ", "qQQkqQqQqQQqQqQq"], h=16)
PAVE_C = G("paveC", ["jjjjjjjjjjjjjjjj", "QQqQQQQkQQQQqQQQ", "QqQQooooooQQQQqQ", "QQooOOoOOOooQQQQ", "QoOOoooOOoOOoQQq", "qQooOOOoooOooQrQ",
                     "QQqQooooooooQqQQ", "qqQqqQqkqQqqQqqQ", "jjjjjjjjjjjjjjjj", "QrQkQQrQQQrQQQrQ", "rQQkQrQQrQoooQQQ", "QQrkrQQrooOOooQQ",
                     "QrQkQQrQoOOoOooQ", "rQQkQrQQQooooQQr", "QQrkQQQrQQQQrQrQ", "qQQkqQqQQqQqQQqQ"], h=16)
KERB = G("kerb", ["jjjjjjjjjjjjjjjj", "rQrQrrQkrQrrQrQr", "QrrQrQrkQrrQrrQr", "rrQrrRrkrrQrRrrQ", "rQrrRrrkrRrrrQrr", "rrRrrQrkrrrRrrRr",
                  "RrrRrrRkRrRrrRrr", "RRRRRRRRRRRRRRRR", "EEEEEEEEEEEEEEkE", "eEeeEeeeEeeEeekE", "eeeeeeeeeeeeeeke", "kkkkkkkkkkkkkkkk",
                  "aakaaaakaaakaaaa", "aAaaAaaaaAaaaaAa", "AaaAaAbaAaaAaAaa", "aAAaAAaAAaAAaAAa"], h=16)
ROAD = G("road", ["AAaAAAAaAAAbAAaA", "AaAAbAAAAaAAAAAA", "AAAAAaAAAAAAaAAb", "AbAAAAAAaAAAAAAA", "AAAaAAAbAAAAAaAA", "aAAAAAAAAAaAAAAA",
                  "AAaAAbAAAAAAAAaA", "aAAaAAAaAAbAAaAA"], h=8)
DASH = G("dash", ["AAaAAAAaAAAbAAaA", "AaAAbAAAAaAAAAAA", "AAAAAaAAAAAAaAAb", "AYYYYYYYYYYYYYAA", "yYYyYYYYyYYYYyYA", "ayyyyyyyyyyyyyaA",
                  "AAaAAbAAAAAAAAaA", "aAAaAAAaAAbAAaAA"], h=8)
# tilemap of the street ring: 21 columns (336 px), shop 4 / wall 2 / shop 4 / wall 3 / shop 4 / wall 2 / wall 2
SHOP_COLS = ([(FASCIA, WIN_L1, WIN_L2), (FASCIA, WIN_M1, WIN_M2), (FASCIA, WIN_R1, WIN_R2), (FASCIA, DOOR1, DOOR2)])
WALL2 = [(BRICK_TOP, BRICK_POSTER, BRICK_BASE), (BRICK_TOP_PIPE, BRICK_PIPE, BRICK_PIPE_BASE)]
WALL3 = [(BRICK_TOP, BRICK_A, BRICK_BASE), (BRICK_TOP_PIPE, BRICK_PIPE, BRICK_PIPE_BASE), (BRICK_TOP, BRICK_POSTER, BRICK_BASE)]
WALL2B = [(BRICK_TOP_PIPE, BRICK_PIPE, BRICK_PIPE_BASE), (BRICK_TOP, BRICK_A, BRICK_BASE)]
STREET_COLS = SHOP_COLS + WALL2 + SHOP_COLS + WALL3 + SHOP_COLS + WALL2 + WALL2B
SIGNS = ((0, "GUM"), (96, "CAFE"), (208, "BAKERY"))      # shop left edge x, word on the fascia
PAVE_ROW = {"dusk": "ABAABABAABAABABAABABA", "moon": "ABAABABAABAABABAABABA", "storm": "ACABACBAACABCABACABCA"}
ROAD_ROW = "DDRDDRDDRDDRDDRDDRDDR"
STREET_Y, STREET_W, STREET_H = 136, 336, 88

if ERR:
    print("\n".join(ERR)); sys.exit(1)

# ---------------------------------------------------------------- assembly helpers
def grid(w, h): return [["."] * w for _ in range(h)]

def gblit(cv, x, y, rows, flip=False):
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            if c == ".": continue
            xx = x + (len(r) - 1 - i if flip else i)
            if 0 <= y + j < len(cv) and 0 <= xx < len(cv[0]): cv[y + j][xx] = c


def remap(rows, m): return ["".join(m.get(c, c) for c in r) for r in rows]

def grip(tp):
    """umbrella grip point in the cell: the far fist (hit/fist/throw) and the 'hold' hand (umbrella walk) share it"""
    r = RIG[tp]; return r["far"][0] + (5 if tp == "kid" else 6), r["far"][1] + 1

def walker(tp, near, far, bob=0, head="n", arm="mid", fist=False):
    """one 32x48 walker cell from its hand-pixeled parts: far leg, near leg, torso, head, bag, far fist, near arm"""
    r = RIG[tp]; ls = r["legset"]; cv = grid(32, 48)
    def part(x, y, g):
        assert 0 <= x and x + len(g[0]) <= 32 and 0 <= y and y + len(g) <= 48, (tp, x, y, g[0])
        gblit(cv, x, y, g)
    lx, ly = r["legs"]
    part(lx + 2, ly, remap(LEGS[ls][far], FARMAP[ls]))
    part(lx, ly, LEGS[ls][near])
    part(r["torso"][0], r["torso"][1] + bob, TORSO[tp])
    arms = ARMS["kid" if tp == "kid" else "adult"]
    sc, sr, g = arms[arm]
    raised = arm in ("fist1", "fist2", "throw")
    if raised:   # owner fix 2026-11-20: the raised arm swings up behind the head (H flip, drawn under it), never across the face
        g = [row[::-1] for row in g]; sc = len(g[0]) - 1 - sc
        part(r["sh"][0] - sc, r["sh"][1] - sr + bob, g)
    part(r["head"][0], r["head"][1] + bob, HEAD[tp][head])
    if "bag" in r: part(r["bag"][0], r["bag"][1] + bob, BAG)
    if fist: part(r["far"][0], r["far"][1], arms["far"][2])
    if not raised: part(r["sh"][0] - sc, r["sh"][1] - sr + bob, g)
    return ["".join(row) for row in cv]

def frames_of(tp):
    ls = RIG[tp]["legset"]; st = 1 if ls == "kid" else 2
    def W(**kw): return walker(tp, st, st, fist=True, **kw)
    return {"walk": [walker(tp, n, f, b, "n", a) for n, f, b, a in WALK[ls]],
            "walk_umb": [walker(tp, n, f, b, "n", "hold") for n, f, b, a in WALK[ls]],
            "hit": [W(bob=2, head="n", arm="back"), W(bob=1, head="a", arm="mid"), W(head="a", arm="mid")],
            "fist": [W(head="a", arm="fist1"), W(bob=1, head="a", arm="fist2")],
            "throw": [W(bob=1, head="a", arm="throw"), W(head="a", arm="fist2"), W(head="a", arm="fist1")]}
FR = {tp: frames_of(tp) for tp in TYPES}
HIT_BOB = (2, 1, 0)

def put(im, x, y, rows, pal, flip=False):
    px = im.load()
    for j, r in enumerate(rows):
        for i, c in enumerate(r):
            if c == ".": continue
            xx = x + (len(r) - 1 - i if flip else i)
            if 0 <= xx < im.width and 0 <= y + j < im.height: px[xx, y + j] = pal[c]

def draw_walker(im, x, y, tp, cell, flip=False, umb=None, ucol="red", splat=None, bob=0, boxes=None):
    """walker instance: umbrella sprite behind (so the hand grips over the shaft), walker cell, splat sprite on the head"""
    r = RIG[tp]; gx, gy = grip(tp)
    def sub(ox, oy, rows, pal, box=None):
        w = len(rows[0]); xx = x + (32 - ox - w if flip else ox)
        put(im, xx, y + oy, rows, pal, flip)
        if boxes is not None and box != 0: boxes.append((xx, y + oy, w, box or len(rows)))
    if umb == "closed": sub(gx - 4, gy - 21, CLOSED, UMB[ucol])
    elif umb:
        can = OPEN if umb == "open" else HALF
        cy = r["top"] - (11 if umb == "open" else 9)
        sub(gx - 1, cy + len(can) - 2, ["Mm"] * (gy + 5 - cy - len(can)), UMB[ucol], box=0)   # shaft lies inside the canopy sprite columns
        sub(gx - len(can[0]) // 2 - (2 if umb == "open" else 0), cy, can, UMB[ucol], box=gy + 3 - cy)
    put(im, x, y, cell, WPAL[tp], flip)
    if boxes is not None: boxes.append((x, y + r["top"], 32, 48 - r["top"]))
    if splat is not None: sub(r["head"][0] + 1, r["top"] + bob - 4, SPLAT_HEAD[splat], ITEMS)

def street_grid(mood):
    cv = grid(STREET_W, STREET_H)
    for c, col in enumerate(STREET_COLS):
        for r, t in enumerate(col): gblit(cv, 16 * c, 16 * r, t)
        gblit(cv, 16 * c, 48, {"A": PAVE_A, "B": PAVE_B, "C": PAVE_C}[PAVE_ROW[mood][c]])
        gblit(cv, 16 * c, 64, KERB)
        gblit(cv, 16 * c, 80, DASH if ROAD_ROW[c] == "D" else ROAD)
    for x, word in SIGNS:
        cx = x + (64 - (6 * len(word) - 1)) // 2
        for ch in word:
            gblit(cv, cx, 4, LETTER[ch]); cx += 6
    return ["".join(r) for r in cv]

def street_img(mood):
    g = street_grid(mood)
    im = Image.new("RGB", (STREET_W, STREET_H))
    put(im, 0, 0, g[:48], SHOP[mood]); put(im, 0, 48, g[48:], GROUND[mood])
    return im

def tiles_of(frames, t=16):
    """unique non-empty t x t tiles of char frames; H flips count once (the hardware flips per tile)"""
    seen = set()
    for f in frames:
        h = -(-len(f) // t) * t; w = -(-len(f[0]) // t) * t
        f = [r.ljust(w, ".") for r in f] + ["." * w] * (h - len(f))
        for ty in range(0, h, t):
            for tx in range(0, w, t):
                tile = tuple(r[tx:tx + t] for r in f[ty:ty + t])
                if all(set(r) == {"."} for r in tile): continue
                fl = tuple(r[::-1] for r in tile)
                if tile not in seen and fl not in seen: seen.add(tile)
    return len(seen)

def scale(im, k): return im.resize((im.width * k, im.height * k), Image.NEAREST)

def save_gif(path, frames, ms, k=3):
    fs = [scale(f, k).quantize(colors=255, dither=Image.Dither.NONE) for f in frames]
    fs[0].save(path, save_all=True, append_images=fs[1:], duration=ms, loop=0)

# ---------------------------------------------------------------- birds (in-game Sootling sheet, fly clip)
def load_birds():
    j = json.load(open(os.path.join(REPO, "assets", "flier", "sootling_sheet.json")))
    sh = Image.open(os.path.join(REPO, "assets", "flier", "sootling_sheet.png")).convert("RGBA")
    p1 = [tuple(c) for c in j["palettes"]["player"]]; p2 = [tuple(c) for c in j["extra_palettes"]["p2"]]
    first = j["tables"]["clip_first"][j["defines"]["CLIP_FLY"]]
    out = []
    for n, swap in ((first + 2, None), (first + 6, p2)):
        b = j["animations"]["player"][n]
        fr = sh.crop((b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]))
        if swap:
            px = fr.load()
            for y in range(fr.height):
                for x in range(fr.width):
                    r, g, bl, a = px[x, y]
                    if a and (r, g, bl) in p1: px[x, y] = swap[p1.index((r, g, bl))] + (a,)
        out.append(fr)
    return out

def backdrop(mood):
    im = Image.new("RGB", (320, 224))
    for name, y in (("sky", 0), ("far", 48), ("midA", 80), ("midB", 112)):
        p = Image.open(os.path.join(PLANES, f"plane_{mood}_{name}_1x.png")).convert("RGB")
        mask = Image.eval(Image.frombytes("L", p.size, bytes(0 if px == (255, 0, 255) else 255 for px in p.get_flattened_data())), lambda v: v)
        im.paste(p, (0, y), mask)
    im.paste(street_img(mood), (0, STREET_Y))
    return im

PLANE_ROWS = ((0, 128, 20), (48, 128, 21), (80, 144, 21), (112, 176, 21), (STREET_Y, 224, 21))   # sky, far, midA, midB, street


def mock(mood, birds):
    im = backdrop(mood); bx = []
    Y = 156; storm = mood == "storm"
    def w(x, tp, cell, **kw): draw_walker(im, x, Y, tp, cell, boxes=bx, **kw)
    def it(x, y, g, h=None): put(im, x, y, g, ITEMS); bx.append((x, y, 16, h or len(g)))
    it(236, 194, SPLAT_PAVE[2])
    w(4, "hat", FR["hat"]["walk_umb" if storm else "walk"][0], umb="open" if storm else None, ucol="teal")
    w(56, "woman", FR["woman"]["walk_umb"][3], flip=True, umb="open" if storm else "closed", ucol="red")
    if storm: it(60, Y + RIG["woman"]["top"] - 17, BOUNCE[1])
    w(108, "bald", FR["bald"]["hit"][1], splat=1, bob=1, umb="closed" if storm else None, ucol="yellow")
    w(160, "kid", FR["kid"]["walk_umb" if storm else "walk"][2], flip=True, umb="open" if storm else None, ucol="yellow")
    w(212, "hat", FR["hat"]["throw"][1], splat=2, umb="closed" if storm else None, ucol="teal")
    w(264, "bald", FR["bald"]["fist"][0], splat=2, umb="closed" if storm else None, ucol="red")
    it(236, 116, SHOE[1])
    it(248, 56, BERRY); put(im, 259, 54, SPARK, ITEMS)
    it(92, 104, POOP[0], 16)
    for b, (x, y) in zip(birds, ((60, 50), (176, 82))):
        im.paste(b, (x, y), b); bx.append((x, y, 24, 32))
    if storm:
        for r in range(26):
            for c, ch in enumerate(RAIN_MAP[r % 4]):
                if ch != ".": put(im, 8 * c, 8 * r, RAIN[int(ch) - 1], FIX)
    for x0, n in ((16, 3), (264, 4)):
        put(im, x0 - 8, 16, BERRY_ICON, FIX)
        for i in range(5): put(im, x0 + 8 * i, 16, PIP_ON if i < n else PIP_OFF, FIX)
    for x0, s in ((60, "x3"), (153, "32"), (308, "x2")):
        for i, ch in enumerate(s): put(im, x0 + 4 * i, 18, DIGIT[ch], FIX)
    def line(y): return sum(n for a, b, n in PLANE_ROWS if a <= y < b) + sum(-(-wd // 16) for x, by, wd, h in bx if by <= y < by + h)
    return im, max((line(y), y) for y in range(224)), max((line(y), y) for y in range(144, 224))

def strip(cells, cw, ch, k, per=None, bg=BG):
    per = per or len(cells)
    im = Image.new("RGB", (cw * per, ch * -(-len(cells) // per)), bg)
    for i, fn in enumerate(cells): fn(im, cw * (i % per), ch * (i // per))
    return scale(im, k)

THROW = ((-12, -22, 3), (2, -30, 0), (8, -32, 1))      # shoe offset from the near shoulder + shoe frame, per throw frame

def main():
    birds = load_birds()
    for p in list(WPAL.values()) + list(UMB.values()) + list(GROUND.values()) + list(SHOP.values()) + [ITEMS, FIX]:
        assert len(p) <= 15 and all(c == round(round(c * 31 / 255) * 255 / 31) for rgb in p.values() for c in rgb)
    assert all(len(f) == 48 and all(len(r) == 32 for r in f) for tp in TYPES for fs in FR[tp].values() for f in fs)
    assert all(set("".join(f)) <= set(WPAL[tp]) | {"."} for tp in TYPES for fs in FR[tp].values() for f in fs)
    street = {m: street_img(m) for m in MOODS}
    for m in MOODS:
        scale(street[m], 2).save(os.path.join(HERE, f"street_{m}_2x.png")); street[m].save(os.path.join(HERE, f"street_{m}_1x.png"))
    # ---- sheets
    CW, CH, OX, OY = 56, 64, 12, 14
    for tp in TYPES:
        f = FR[tp]; sh = RIG[tp]["sh"]
        def D(c, **kw): return lambda im, x, y: draw_walker(im, x + OX, y + OY, tp, c, **kw)
        def thr(i):
            def fn(im, x, y):
                draw_walker(im, x + OX, y + OY, tp, f["throw"][i], splat=2, bob=1 if i == 0 else 0)
                put(im, x + OX + sh[0] + THROW[i][0], y + OY + sh[1] + THROW[i][1], SHOE[THROW[i][2]], ITEMS)
            return fn
        cells = [D(c) for c in f["walk"]] + [D(c, splat=i, bob=HIT_BOB[i]) for i, c in enumerate(f["hit"])]
        cells += [D(c, splat=2, bob=i) for i, c in enumerate(f["fist"])] + [thr(i) for i in range(3)]
        cells += [D(f["walk_umb"][0], umb="closed", ucol="yellow"), D(f["walk_umb"][2], umb="half", ucol="red"), D(f["walk_umb"][3], umb="open", ucol="teal"),
                  D(f["hit"][1], splat=1, bob=1, umb="closed", ucol="yellow"), D(f["fist"][0], splat=2, umb="closed", ucol="red"),
                  D(f["throw"][0], splat=2, bob=1, umb="closed", ucol="teal"), D(f["walk"][0], flip=True)]
        for k in (4, 1): strip(cells, CW, CH, k, per=-(-len(cells) // 2)).save(os.path.join(HERE, f"sheet_{tp}_{k}x.png"))
    it = [lambda im, x, y, g=g: put(im, x + 4, y + 4, g, ITEMS) for g in POOP]
    it += [lambda im, x, y, g=g: put(im, x, y + 4, g, ITEMS) for g in SPLAT_HEAD + SPLAT_PAVE + BOUNCE]
    it += [lambda im, x, y, g=g: put(im, x, y, g, ITEMS) for g in SHOE + [BERRY]]
    it += [lambda im, x, y: (put(im, x, y, BERRY, ITEMS), put(im, x + 11, y, SPARK, ITEMS))]
    it += [lambda im, x, y, g=g: put(im, x + 4, y + 4, g, FIX) for g in (PIP_ON, PIP_OFF, BERRY_ICON, RAIN[0], RAIN[1])]
    strip(it, 16, 16, 4).save(os.path.join(HERE, "sheet_items_4x.png"))
    um = [lambda im, x, y, s=s, ox=ox, c=c: put(im, x + ox, y + 2, s, UMB[c]) for c in UMB for s, ox in ((CLOSED, 16), (HALF, 12), (OPEN, 4))]
    strip(um, 40, 32, 4).save(os.path.join(HERE, "sheet_umbrella_4x.png"))
    # ---- GIFs on the dusk street (28 px of headroom above the plane for shoes and canopies)
    def stage(x0=96):
        im = Image.new("RGB", (64, 116), BG); im.paste(street["dusk"].crop((x0, 0, x0 + 64, 88)), (0, 28)); return im
    WX, WY = 16, 28 + 68 - 47
    def wf(tp, cell, **kw):
        im = stage(); draw_walker(im, WX, WY, tp, cell, **kw); return im
    for tp in TYPES:
        f = FR[tp]; r = RIG[tp]; gx, gy = grip(tp)
        save_gif(os.path.join(HERE, f"walk_{tp}_3x.gif"), [wf(tp, c) for c in f["walk"]], 110)
        hit = [wf(tp, f["walk"][0])]
        for i, dy in enumerate((-22, -11)):
            im = wf(tp, f["walk"][0]); put(im, WX + r["head"][0] + 5, WY + r["top"] + dy, POOP[i], ITEMS); hit.append(im)
        hit += [wf(tp, f["hit"][i], splat=i, bob=HIT_BOB[i]) for i in (0, 0, 1, 2, 2, 2)]
        save_gif(os.path.join(HERE, f"hit_{tp}_3x.gif"), hit, 90)
        save_gif(os.path.join(HERE, f"fist_{tp}_3x.gif"), [wf(tp, f["fist"][i], splat=2, bob=i) for i in (0, 1)], 130)
        thr = []
        for i, (dx, dy, sf) in enumerate(((-12, -22, 3), (-12, -22, 3), (2, -30, 0), (6, -40, 1), (9, -49, 2), (11, -57, 3), (13, -64, 0), (14, -70, 1))):
            im = wf(tp, f["throw"][0 if i < 2 else 1 if i == 2 else 2], splat=2, bob=1 if i < 2 else 0)
            put(im, WX + r["sh"][0] + dx, WY + r["sh"][1] + dy, SHOE[sf], ITEMS); thr.append(im)
        save_gif(os.path.join(HERE, f"throw_{tp}_3x.gif"), thr, 90)
        uf = [wf(tp, f["walk_umb"][i % len(f["walk"])], umb=u, ucol="red") for i, u in enumerate(("closed", "closed", "half", "open", "open", "open", "open", "open", "open"))]
        for i, b in ((5, 0), (6, 1), (7, 2)): put(uf[i], WX + gx - 10, WY + r["top"] - 17 - 3 * (i - 5), BOUNCE[b], ITEMS)
        save_gif(os.path.join(HERE, f"umbrella_{tp}_3x.gif"), uf, 110)
    def itemgif(name, grids, ms, y=60, pal=ITEMS, dys=None):
        fs = []
        for i, g in enumerate(grids):
            im = stage(160); put(im, 24, 28 + y + (dys[i] if dys else 0), g, pal); fs.append(im)
        save_gif(os.path.join(HERE, name), fs, ms, 4)
    itemgif("splat_pave_4x.gif", [POOP[0], POOP[1]] + SPLAT_PAVE + [SPLAT_PAVE[2]] * 3, 100, dys=[-30, -14, 0, 0, 0, 0, 0, 0])
    itemgif("poop_fall_4x.gif", [POOP[0], POOP[1]], 120, y=20)
    itemgif("shoe_spin_4x.gif", SHOE, 80, y=16)
    itemgif("splat_head_4x.gif", SPLAT_HEAD + [SPLAT_HEAD[2]] * 2, 110, y=30)
    itemgif("bounce_4x.gif", BOUNCE, 110, y=30)
    bf = []
    for i in range(4):
        im = stage(160); put(im, 24, 44 + (i % 2), BERRY, ITEMS)
        if i in (1, 2): put(im, 35, 42 + i, SPARK, ITEMS)
        bf.append(im)
    save_gif(os.path.join(HERE, "berry_4x.gif"), bf, 160, 4)
    # ---- mocks + numbers
    worst, wline = {}, {}
    for m in MOODS:
        im, worst[m], wline[m] = mock(m, birds)
        im.save(os.path.join(HERE, f"mock_{m}_1x.png")); scale(im, 3).save(os.path.join(HERE, f"mock_{m}_3x.png"))
    assert max(v[0] for v in worst.values()) <= 96, worst
    wt = {tp: tiles_of([c for k in FR[tp] for c in FR[tp][k]]) for tp in TYPES}
    wt_noumb = {tp: tiles_of([c for k in FR[tp] if k != "walk_umb" for c in FR[tp][k]]) for tp in TYPES}
    nframes = {tp: sum(len(v) for v in FR[tp].values()) for tp in TYPES}
    item_t = tiles_of(SPLAT_HEAD + SPLAT_PAVE + BOUNCE + SHOE + [BERRY]) + 2 + 1     # + 2 poop + berry sparkle frame
    umb_t = tiles_of([CLOSED, HALF, OPEN]) + 1
    sg = street_grid("storm"); sd = street_grid("dusk")
    street_t = tiles_of([sd[:48], sg[:48]]) + tiles_of([sd[48:], sg[48:]])
    fix_t = 5 + len(DIGIT)
    total = sum(wt.values()) + item_t + umb_t + street_t
    free = 96 - 42      # walker lines 144 to 175: midB 21 + street 21; below line 176 only the street (21)
    lines = [f"walker {tp}: 32x48 cell, {nframes[tp]} frames (walk {len(FR[tp]['walk'])}, umbrella walk {len(FR[tp]['walk_umb'])}, hit 3, fist 2, throw 3), "
             f"{wt[tp]} tiles 16x16 ({wt_noumb[tp]} without the umbrella walk)" for tp in TYPES]
    lines += [f"items (poop 2, head splat 3, pavement splat 3, umbrella bounce 3, shoe 4, berry 2): {item_t} tiles",
              f"umbrella (closed 8x28, half 16x13, open 32x12 + shaft): {umb_t} tiles", f"street plane (336 x 88 ring, all moods): {street_t} tiles",
              f"sprite tiles total: {total}", f"fix tiles 8x8 (pip on/off, berry icon, rain 2, combo/timer glyphs): {fix_t}",
              "palettes: walkers 4, items 1, umbrella 3 (colour swaps), street 2 per mood (shop, ground), fix 1; birds use the existing player and p2 palettes",
              "worst sprites per scanline in the mock (planes sky 20, far/midA/midB/street 21 each + objects): "
              + ", ".join(f"{m} {worst[m][0]} at line {worst[m][1]}" for m in MOODS) + " (limit 96)",
              "worst walker line (144 to 223) in the mock: " + ", ".join(f"{m} {wline[m][0]} at line {wline[m][1]}" for m in MOODS),
              f"walker cost per line: 2 sprites bare, 3 with closed umbrella, 4 with open umbrella, +1 head splat. Planes on walker lines: 42, so {free} free. "
              f"Max on one line: {free // 2} bare, {free // 3} with closed umbrella, {free // 5} with open umbrella and splat; "
              f"with 8 kept for birds, shoes, poop and berry: {(free - 8) // 2} / {(free - 8) // 3} / {(free - 8) // 5}. The 320 px screen holds about 7 walkers side by side.",
              "tight band stays lines 112 to 127 (four planes, 83 sprites): 13 free for birds, poop, shoes and berry; walkers and umbrellas start at line 145 and never enter it"]
    open(os.path.join(HERE, "numbers.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    h = ["<!doctype html><meta charset=utf-8><title>Poop the Man draft v2</title>",
         "<style>body{background:#14121c;color:#e8e6f0;font:15px system-ui;margin:24px;max-width:1200px}img{image-rendering:pixelated;margin:6px 8px 16px 0;max-width:100%;vertical-align:top}h2{margin-top:36px}pre{background:#1e1b2a;padding:12px;white-space:pre-wrap}</style>",
         "<h1>Poop the Man, visual draft v2, 2026-11-20</h1><p>Draft only, no game code. Bigger walkers: 32 x 48 cell (birds are 24 x 32). All grids hand-placed in draw_poop_the_man.py. "
         "Walkers face right; the left walk is the H flip (last cell of each sheet). v1 stays in ../2026-11-20-poop-the-man/.</p>",
         "<h2>Mock-ups</h2>"]
    for m in MOODS: h.append(f"<p>{m} (3x, then 1x)</p><img src='mock_{m}_3x.png'><br><img src='mock_{m}_1x.png'>")
    h.append("<h2>Walkers</h2><p>Sheet cells: walk cycle, hit 3 (splat is a separate 16 x 8 sprite), fist shake 2, shoe throw 3, umbrella closed / half / open, "
             "storm hit / fist / throw with the closed umbrella kept in the far fist, H flip.</p>")
    names = {"hat": "Hat man: tall, long coat (extra score)", "bald": "Bald man: short, round belly, braces (extra score)",
             "woman": "Woman: handbag, scarf, skirt", "kid": "Kid: small, cap, backpack"}
    for tp in TYPES:
        h.append(f"<h3>{names[tp]}</h3><img src='sheet_{tp}_4x.png'><br>" + "".join(f"<img src='{a}_{tp}_3x.gif' title='{a}'>" for a in ("walk", "hit", "fist", "throw", "umbrella")))
    h.append("<h2>Poop, splats, shoe, gum berry, ammo pips</h2><p>Unchanged from v1. Sprites, one shared items palette: poop fall 2, head splat 3, pavement splat 3, umbrella bounce 3, shoe spin 4, gum berry 2. "
             "Last five cells are fix-layer 8 x 8 tiles: ammo pip full / empty, berry icon, two rain tiles (storm).</p><img src='sheet_items_4x.png'><br>"
             + "".join(f"<img src='{g}_4x.gif' title='{g}'>" for g in ("poop_fall", "splat_head", "splat_pave", "bounce", "shoe_spin", "berry")))
    h.append("<h2>Umbrella</h2><p>Own sprite, three palette swaps. Closed: rolled, held upright in front of the walker, so a walker that can block always shows it, also in the hit, fist and throw poses. "
             "Open: 32 x 12 canopy over the head, shaft down to the same grip.</p><img src='sheet_umbrella_4x.png'>")
    h.append("<h2>Street plane</h2><p>Unchanged from v1: 336 x 88 ring at screen rows 136 to 223.</p>")
    for m in MOODS: h.append(f"<p>{m}</p><img src='street_{m}_2x.png'>")
    h.append("<h2>Numbers</h2><pre>" + "\n".join(lines) + "</pre>")
    open(os.path.join(HERE, "index.html"), "w").write("\n".join(h) + "\n")

if __name__ == "__main__":
    main()
