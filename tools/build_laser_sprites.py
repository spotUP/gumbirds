#!/usr/bin/env python3
"""Overheat bar sprite set (name "heat"): assets/laser/heat_sheet.png + .json -> build/gen/heat.c1/.c2,
heat_sprites.h/.c. Usage: $PYTHON -I tools/build_laser_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py; the sheet is drawn by tools/draw_heat_sheet.py. The beam and the
hit flash are the hero set's "laser" and "hit_flash" animations (assets/hero/guard_sheet.json)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("heat", "assets/laser/heat_sheet.png", "assets/laser/heat_sheet.json")
