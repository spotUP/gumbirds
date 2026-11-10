#!/usr/bin/env python3
"""Floating island sprite set: assets/islands/island_sheet.png + .json -> build/gen/island.c1/.c2, island_sprites.h/.c, island_tables.h.
Usage: $PYTHON -I tools/build_island_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py; the sheet is imported by tools/import_islands_sheet.py."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("island", "assets/islands/island_sheet.png", "assets/islands/island_sheet.json")
