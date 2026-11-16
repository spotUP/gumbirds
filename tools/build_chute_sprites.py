#!/usr/bin/env python3
"""Parachute sprite set: assets/chute/chute_sheet.png + .json -> build/gen/chute.c1/.c2, chute_sprites.h/.c.
Usage: $PYTHON -I tools/build_chute_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py. The sheet is made by tools/make_chute_sheet.py."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("chute", "assets/chute/chute_sheet.png", "assets/chute/chute_sheet.json")
