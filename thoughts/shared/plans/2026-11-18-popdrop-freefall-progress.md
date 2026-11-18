# Pop Drop free fall: progress

Done: sprite assets (a2ff4e2), logic + game wiring + host test (65cd3e6, host test passes), main.c view + MAME probe/Lua (c5d702e, gmake builds).

Open:
1. MAME not verified. `make test-gum-pop-drop` stalls in the "start" phase (Flow.state stays 0 after 17000 frames), and `make test-gum-fling` (untouched code) gives "no result". Both fail the same way, so find out first whether the ROM boots at all in this worktree (CROM size / popdrop tile base overflow? run the same targets on feature/gum-games for a baseline) or whether it is the local MAME/UniBIOS setup (sm1/sfix checksum warnings).
2. Visuals unchecked: platform piece order/flip, bird anim choice (fall/lean/bonk/crash by hits), shield and pop sprite position, gum candy y offset (PdGum.y treated as centre), streak tiles not drawn.
3. Shield pop (POPDROP_ANIM_POP) frame step uses pop_t>>3.
4. Run one more gum MAME test after (1) is fixed; `git checkout -- cfg/neogeo.cfg` after each run.
