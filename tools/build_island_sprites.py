#!/usr/bin/env python3
"""Floating island sprite set: assets/islands/island_sheet.png + .json -> build/gen/island.c1/.c2, island_sprites.h/.c, island_tables.h.
Usage: $PYTHON -I tools/build_island_sprites.py [--look garden|deck] [--out build/gen] [--no-verify]
--look builds the set island_<look> from assets/islands/island_<look>_sheet; without it the roof set "island".
All logic is in tools/sprite_pipeline.py; the sheet is imported by tools/import_islands_sheet.py."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    name = "island"
    if "--look" in sys.argv:
        k = sys.argv.index("--look")
        name = "island_" + sys.argv[k + 1]
        del sys.argv[k:k + 2]
    base = "assets/islands/%s_sheet" % name
    sprite_pipeline.main(name, base + ".png", base + ".json")
