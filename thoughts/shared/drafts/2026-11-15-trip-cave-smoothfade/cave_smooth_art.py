"""TRIP-CAVE smooth fade: hand-typed data for the sloped fade under/over the curve pieces.
The fade pixels themselves are the hand-typed rows of ../2026-11-15-trip-cave-fade/cave_fade_art.py; build_smooth.py moves each pixel
column down by the lip offset typed below (assembly), then stamps the hand-typed seam patches of this file on top."""

# Lip offset per pixel column, piece drawn rising to the right (first gum row below the piece top). Typed from the v3 heights.json;
# S32 columns 27/28 were 13,14 in the art (one pixel bump of the lip outline) and are typed 14,13 here so the bands never step backwards.
PROFILE = {
 'S16': [18, 18, 18, 17, 17, 17, 17, 16, 16, 15, 15, 15, 15, 15, 14, 14,
         14, 13, 13, 12, 12, 11, 10, 10, 9, 8, 7, 7, 7, 6, 6, 6,
         5, 5, 5, 4, 4, 4, 4, 3, 3, 3, 3, 3, 2, 2, 2, 2],
 'S32': [34, 33, 33, 32, 32, 31, 31, 30, 30, 29, 29, 28, 28, 27, 27, 26,
         25, 25, 23, 22, 22, 20, 19, 18, 18, 16, 15, 14, 13, 12, 11, 10,
         9, 9, 8, 8, 7, 7, 6, 6, 5, 5, 4, 4, 3, 3, 2, 2],
}

# Seam patches: (rows, x, y) in block pixels, '.' keeps the pixel below. Floor block: y = 0 is the piece top row.
# Roof block: y = 0 is 32 px above the piece top row.
# View pass 1. Floor: the fade line cuts fill lumps in half; each cut lump is finished by hand in the dim fade tones (it sinks into the fade)
# or, where only a three pixel streak was left, taken out.
FLOOR_FIX = {
 'S16': [(["222",
           ".2."], 11, 45)],
 'S32': [(["4102",
           "2002",
           "222."], 32, 38),
         (["..1",
           ".1.",
           "1.."], 26, 42),
         (["3002",
           "4102",
           "2002",
           "222."], 16, 53)],
}
# Roof: the fade line slices the lit rim boulders on a diagonal, so their brightest tones met the dark outline directly.
# Each cut row now ends in a hand-typed taper (the right-hand shade the uncut boulders have).
ROOF_FIX = {
 'S16': [(["43"], 5, 33), (["54"], 7, 34), (["654"], 36, 46), (["6543"], 40, 47)],
 'S32': [(["23"], 1, 33), (["54"], 3, 34), (["765"], 4, 35), (["654"], 6, 36), (["543"], 8, 37), (["432"], 10, 38),
         (["543"], 22, 49), (["654"], 23, 50), (["654"], 24, 51)],
}

# View pass 2. Floor: the fade lumps that the per-column shift sheared into slanted smears are re-typed upright,
# as dim diamonds (tone 2 around a tone 0 core), the same lump shape the flat fill uses.
FLOOR_FIX['S16'] += [
    (["1121111"], 15, 47),
    (["1222111"], 15, 48),
    (["2202211"], 15, 49),
    (["11222111"], 14, 50),
    (["1121111"], 15, 51),
    (["112111",
      "122211",
      "220221",
      "122211",
      "112111"], 31, 55),
]
FLOOR_FIX['S32'] += [
    (["111211",
      "112221",
      "122022",
      "112221",
      "111211"], 30, 43),
    (["112111",
      "122211",
      "220221",
      "122211",
      "112111",
      "111111"], 15, 57),
    (["11011"], 13, 63),
    (["1211"], 10, 68),
    (["12021"], 10, 69),
    (["11211"], 10, 70),
]
