#!/usr/bin/env python3
"""Gum leak (air jet + hole) sprite set: assets/gum_leak/gum_leak_sheet.png + .json -> build/gen/gumleak.c1/.c2, gumleak_sprites.h/.c, gumleak_tables.h.
Usage: $PYTHON -I tools/build_gumleak_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py. The frame sequence (cell, dx, dy, ticks) is in the json tables."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("gumleak", "assets/gum_leak/gum_leak_sheet.png", "assets/gum_leak/gum_leak_sheet.json")
