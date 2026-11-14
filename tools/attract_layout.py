"""Attract how-to-play overlay layout (picked corner variant from the 2026-11-13 overlay drafts).

Fix-grid coordinates are (column, row) on the 40 x 28 fix layer. Read by tools/build_attract_icons.py.
"""

CAPTIONS = {  # two lines split at '|' for the corner variant
    "arena": "STOMP|RIVAL GUM",
    "gum trip": "FLY FAR|GRAB GUM",
    "arcade": "CLEAR THE|STAGES",
}

STATES = {  # name -> (lever frame, A frame, Start frame, active word)
    "flap": ("stick_neutral", "a_down", "start_up", "FLAP"),
    "steer right": ("stick_right", "a_up", "start_up", "STEER"),
}


def v_corner(state, cap):
    lever, a, start, act = STATES[state]
    l1, l2 = cap.split("|")
    return [
        # lower left, text left-aligned (owner 2026-11-13: lower left reads better than lower right)
        ("text", l1, 1, 21, "white"), ("text", l2, 1, 22, "white"),
        ("text", act, 1, 23, "gold"),
        ("icon", lever, 1, 25), ("icon", a, 6, 24), ("icon", start, 10, 25),
    ]
