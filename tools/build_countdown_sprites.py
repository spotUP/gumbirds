#!/usr/bin/env python3
"""Countdown GET SET / GO! sprite set (A2): assets/countdown/countdown_sheet.png + .json -> build/gen/countdown.c1/.c2, countdown_sprites.h/.c, countdown_tables.h.
Usage: $PYTHON -I tools/build_countdown_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py. Palette 0 = Pink Gum, extra palette "hot" = Hot Gum swap (same tiles)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("countdown", "assets/countdown/countdown_sheet.png", "assets/countdown/countdown_sheet.json")
