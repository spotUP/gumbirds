#!/usr/bin/env python3
"""Gum bubble sprite set: assets/gum/gum_sheet.png + .json -> build/gen/gum.c1/.c2, gum_sprites.h/.c.
Usage: $PYTHON -I tools/build_gum_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py (sheet facts: thoughts/spot/2026-11-12-gum-sheet-build.md)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("gum", "assets/gum/gum_sheet.png", "assets/gum/gum_sheet.json")
