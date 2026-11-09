#!/usr/bin/env python3
"""Obstacle sprite set: assets/obstacles/obstacle_sheet.png + .json -> build/gen/obs.c1/.c2,
obs_sprites.h/.c. Usage: $PYTHON -I tools/build_obstacle_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py; the sheet is drawn by tools/draw_obstacle_sheet.py."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("obs", "assets/obstacles/obstacle_sheet.png", "assets/obstacles/obstacle_sheet.json")
