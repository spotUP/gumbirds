#!/usr/bin/env python3
"""Arcade hazard/particle sprite set: assets/arcade/arcade_sheet.png + .json -> build/gen/arcade.c1/.c2, arcade_sprites.h/.c.
Usage: $PYTHON -I tools/build_arcade_sprites.py [--out build/gen] [--no-verify]
All logic (incl. the pixel-exact decode check) is in tools/sprite_pipeline.py; the sheet is the draft strips from
thoughts/spot/drafts/2026-11-12-arcade-art/ stacked unchanged (picks: thoughts/spot/2026-11-12-arcade-art-final.md)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("arcade", "assets/arcade/arcade_sheet.png", "assets/arcade/arcade_sheet.json")
