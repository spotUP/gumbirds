# PARTY modes: implementation plan (Hot Gum, Roost Rule, Rule of the Round, then Gum Games)

Status: plan only, nothing built. Input: thoughts/shared/research/2026-11-16-new-game-modes.md (owner decisions at its end).

Line numbers are from the feature/arena-2p worktree (.claude/worktrees/agent-a4e2bd501c4804541, HEAD 8c9bf33 plus uncommitted
game.c/game.h/main.c edits, in progress). The checkout at /Users/spot/Code/ArcadeGame (feature/small-sootlings) has NO co-op code
(no input2, no game_join_p2), so it is not a base for this work. Re-grep after arena-2p lands; numbers will move.
Paths below are relative to the worktree root. Base branch for all PARTY work: feature/arena-2p once merged to integ/beta1.

## Verified facts

1. Buttons B/C/D reach the core. src/main.c:991 pad_to_core swaps nibbles of bios_p1current (P1) and bios_p2current (P2, main.c:1785
   into Game.input2); IN_A..IN_D are 0x01..0x08 (game.h:28-31). Nothing masks them. No play code reads B/C/D today (grep IN_B/C/D:
   only flow.c:210 title back and nameentry.c). B/C/D = free in play. The Start-ends-result hack (main.c, `in |= IN_A`) is A only.
   Caveat (unverified): P2 button A..D bit order on real hardware is the same swap as P1; only MAME keyboard checked by nobody.
2. Hard-coded three-mode sites (all must change for a fourth title entry):
   - flow.c:23 demo rotation `demo_mode == GAME_MODE_ARCADE ? ARENA : +1`.
   - flow.c:31 `rounds = !demo && mode != GAME_MODE_TRIP`.
   - flow.c:187-188 title_mode_select wrap ARENA..ARCADE (Down/Up).
   - main.c:1165-1170 title list rows (TITLE_SELECT_ROW, +1, +2; ">" marker + label), rows 23-24 area per research.
   - main.c:1024-1025 score table heading ("GUM TRIP/ARCADE/ARENA SCORES") and g_table_mode_draws index.
   - main.c:409 slots (ARCADE gets STAGE_SPAWN_COUNT, else CPU_MAX 3), main.c:958 pool_sync_p2 gate, main.c:1447 p2hud gate,
     main.c:1807 and :1878 `playing`/`arena` gates (ARENA||ARCADE), main.c:243/368/956/1859-1902 TRIP tests.
   - score_table.h:28 SCORE_MODES 3 (index = GameMode), :31 SCORE_IMAGE_SIZE 370, :26 SCORE_VERSION 3, header layout comment; score_table.c:58
     score_tables_defaults (one *_defaults per table), :149-186 read_tables/score_load (v3 and v2 paths), flow.c:69/200/219-220 use
     f->last_mode and f->mode as the table index.
   - tests/mame/vblank_check.lua:42 demo_mode per mode arena/trip/arcade (K_ARENA etc. from attract_probe.c).
   - Best design: add `party_rule` byte to Game, and make PARTY a GameMode value 3 (GAME_MODE_PARTY) that the arena step treats as ARENA
     with rule hooks; table index 3 = new SCORE v4 (image 370 + 120 + 0 = 490 bytes; old v3 images must load with PARTY defaults).
3. ai_step can target any flier: ai.h:38 `ai_step(a, r, self, target, out)`, only reads target->x/y (ai.c:44-99). Callers: game.c:675
   passes ai_nearest(...); flow.c:140 demo pilot. A parked dummy Flier works as a point target (Roost Rule island point). Hot Gum carrier
   chase = pass the nearest/any flier; cool rivals fleeing the carrier = pass carrier as target, but ai_decide (ai.c:44-49) flees only
   when d2 < AI_FLEE_DIST^2 and self is not above target by AI_ABOVE_MARGIN; otherwise it chases. So "cool rival flees carrier at any
   range" is NOT free: needs an ai_step flag or a new AiState bias (new small code). AI cannot hold a position: no stand/land state;
   chase aims at target and flaps toward it (ai.c:55-99); a rival over a point target will hover/oscillate around it, not land.
   Island holding therefore needs a new AI hold state (see Roost Rule phase). UNVERIFIED by running; read from code only.
4. Per-flier hooks: kill_y is per Flier (flier.h:102), set by flier_set_hazard (game.c:26-28) and game_set_hazard (game.c:109-117) for
   hero[] and cpu[]; Roost Rule/Hot Gum need no kill_y change. arc_bonus_step (arcade.h:112) takes a catcher rectangle per call; game.c:559
   calls it for h == 0 only and a second catcher uses the follow-on test (arcade.h:113). arc_elements_* take cx,cy,half sizes
   (game.c:421-442, 677), gated to ARCADE stages; they are not called in ARENA. So per-flier is available for all three, but none of
   the new modes needs them. Pair loop is game.c:728-775: act via flier_pair, flier_pair_apply at :757/:761. Hot Gum hooks here: pass
   the gum on FLP_POP_A/B/BOUNCE contact instead of apply (replace the apply call when party_rule == HOT).
   Arena scoring in this loop already supports human stomps (versus, game.c:769-773).
5. Sprite budget: SB_GAMEPLAY_PER_LINE 14 (sprite_budget.h:15); arena measured peak 8 (4 fliers x 2 strips); budget table
   src/core/sprite_budget.c:25-44, SB_LIMIT 90. One extra marker/bubble over the roost = 1 or 2 sprites; GUM_COUNT is 2
   (sprite_slots.h:51, "gum bubble" entry 0..224, always counted, sprite_budget.c:39). Reuse that gum bubble sprite for the Hot Gum
   carrier would collide with the player's own gum meter slot: needs its own slot range (new entry in SPRITE_BUDGET, all lines 0..224
   or per-line 2) plus a sprite_slots.h/vram_layout.h change. Fliers worst case 4 on one island line = 8 strips + marker 2 = 10 < 14, but
   total line count must be re-measured with `make test-sprite-peak` and tests/host/test_sprite_budget.c (it iterates SPRITE_BUDGET, so
   a new entry is checked automatically; a hard-coded SB_LIMIT 90 total is the real limit; headroom number UNVERIFIED, not run).
   Hot Gum can avoid a sprite entirely: blink/palette on the carrier (no budget cost).
6. Vblank: tests/mame/vblank_check.lua:39 LOGIC_LIMIT 224. Latest measured demo arena logic end 219.6 (handoffs/2026-11-16_night-merges.md:18),
   NOT 205-208; headroom is ~4 line units. Any per-frame party logic must be near zero cost, or the check goes red. Real-game (non-demo)
   arena logic end: UNVERIFIED (not run); read it from the last vblank check artifact before starting.

## Shared phase 0: PARTY plumbing (blocks everything)

Smallest: no rules, PARTY behaves as Arena with a different table and title row.
- game.h: GAME_MODE_PARTY = 3, `uint8_t party_rule` (PARTY_NONE, PARTY_HOT, PARTY_ROOST, PARTY_ROUND), per-rule state union (small).
- game.c: game_set_mode / game_reset seed party_rule; game_step dispatches PARTY to game_step_arena (same as ARCADE). Arena join rules
  (game_can_join_p2 game.c:82) use `mode == GAME_MODE_ARENA` -> widen to ARENA||PARTY (game.c:84, :97, main.c:958, :1447, :1807, :1878).
- flow.c: title list wrap to PARTY (187-188), demo rotation (23), rounds flag (31, PARTY gets rounds).
- main.c: fourth title row (1165-1170), table heading (1024), TITLE_SELECT_ROW layout re-check (static asserts at main.c ~992 area).
- score_table.*: SCORE_MODES 4, SCORE_VERSION 4, image size 490, loader keeps v3 (arena/trip/arcade, PARTY default), v2, v1.
- Files: src/core/game.h, game.c, flow.c, score_table.h/.c, src/main.c, tests/host/test_score_table.c, test_flow.c, test_core.c,
  tests/mame/score_check.lua + score_probe.c, vblank_check.lua (add K_PARTY demo bucket), attract_probe.c.
- Tests: host test_score_table (v3 -> v4 migration, checksum, defaults), test_flow (title wrap with 4 entries, demo rotation includes
  PARTY, P2 join allowed), test_core (PARTY == arena without rule). MAME: make test-vblank (demo bucket), test-reach (name entry saves into
  table 3), score_check (heading), boot_check. Reachability rule (RULES.md): a MAME run must enter via the title list and Start.
- Decision needed from owner: what PARTY title row looks like with rule choice (see open questions).

## Phase 1: Rule of the Round (smallest; no sprite, no AI change)

Goal lines (owner approved 2026-11-16; shown under the rule name on the title PARTY row and in the round-start freeze): RULE OF THE ROUND "A NEW TWIST EVERY ROUND" plus the twist name on the round banner; ROOST RULE "STAND ON THE GLOWING ISLAND TO SCORE"; HOT GUM "PASS THE HOT GUM BEFORE IT POPS"; HAZARD ROULETTE "NEW HAZARD EVERY ROUND".

Rule table drawn in match_start (game.c:234) before GO; shown through game_round_start_text (game.c:350: currently BONUS only, add
PARTY branch). Start with the cheap rules that need no per-frame cost:
- One Gum Each: balloons start value (flier_init arg game.c:36/102).
- Crowded Sky / Slow / Quick Thinkers: cpu_count and ai_init rank at match_start.
- Mirror Stick: swap IN_LEFT/IN_RIGHT in game_step_arena where `in.dir` is built (game.c:473-474, :547, :589 for P2) - core only,
  not in flow/nameentry, so menus unaffected.
- Windy: a vx delta in arena_flier_step (game.c:406) - one add per flier, negligible.
- Hazard Roulette: game_set_hazard (game.c:109) every 10 s; main.c hazard strip swap writes VRAM mid-round: UNVERIFIED cost; may need
  round-end swap only (open question).
Files: game.c, game.h, tests/host/test_arena.c (new test_party_round.c), main.c only if banner text lines need new strings.
Tests: host: each rule applied, no repeat in draw, deterministic with Rng seed, Mirror affects P1 and P2 inputs only in play; MAME: new
party_check.lua (title -> PARTY -> round start text readable via symbol, then round plays, make test-flier-style drive); test-vblank.
Risks: per-round hazard swap (above); Mirror Stick leaking into name entry (verify flow state gate); score table shared across rules.

## Phase 2: Roost Rule

Needs: roost index + timer + warning; stage_platforms[] (stage.h:17) for island rectangles; standing test = flier on_ground
(flier.h:90) within platform x-range; score tick; popped fliers respawn by parachute (join spawn path exists: FLIER_START_JOIN_Y,
game.c:102).
AI (hardest part, fact 3): rivals do not hold islands. Plan: add a hold state to ai.c (HOLD: steer to target.x, flap only to keep
altitude above the platform top; no flap once on_ground) keyed by a new Ai field; or accept hop-and-hover and tune. Needs new code in
ai.c plus tests/host/test_ai.c cases. Dummy Flier target parked at roost center (x, platform top - half height).
Marker: 1 sprite hovering (reuse bonus bubble ArcBubble art, new slot range + SPRITE_BUDGET entry + sprite_slots.h; fact 5) or
fix-layer arrow if the budget fails.
Files: game.c/h, ai.c/h, stage.c (read only), sprite_slots.h, vram_layout.h, sprite_budget.c, main.c (marker place/draw), result/score.
Tests: host: roost never repeats, sole standing scores, shared pays none, parachute respawn after pop, round ends on target or time;
test_ai: hold state converges and does not flap on_ground; test_sprite_budget with new entry; MAME: party_check (roost scores while
standing), test-sprite-peak, test-vblank, test-solid.
Risks: crowd of 4 on one island (8 strips) + marker; AI pile-ups; roost on a platform a flier cannot reach.

## Phase 3: Hot Gum (SUPERSEDED 2026-11-18 by TOSS-GUM, see below; kept for history)

Needs: `hot` flier index (humans 0..1, cpu offset), fuse timer, pass cooldown, per-contact pass in the pair loop (game.c:757-761:
suppress stomp pops, set hot = other, g->bounces++ as is), fuse end -> flier_lose_balloon (flier.h) on carrier, pick random survivor
(Rng), restart fuse (shorter per round). Score: pass made + round survived.
AI: carrier target = nearest (ai_nearest, ai.h:33; existing); cool rivals flee the carrier only inside AI_FLEE_DIST (fact 3). Needs a
cool-rival flee-at-any-range flag in ai_decide, or accept shorter flee range.
Look: carrier blink (FLIER_BLINK_HALF_PERIOD) or palette, no sprite (preferred); fuse readout on fix layer (changed-cells-only write,
vq_fix_commit_room, see research Gum Games risks) or blink rate only.
Files: game.c/h, ai.c (flag), flier.c only if blink is exposed, main.c (carrier look, fuse HUD), result.
Tests: host: pass on contact, cooldown, fuse pop removes one balloon, last bird wins round, no stomp pops in HOT; test_ai flag;
MAME: party_check hot rule (one pass observed, one fuse pop); test-vblank, test-sprite-peak.
Risks: ping-pong with 2P contact; 2P carrier chain; whether pump-up/blink frames exist for the player bird (UNVERIFIED, research listed
as not checked); AI flee tuning.

## Phase 4+: Gum Games (full medley, built after 1-3; owner decision: all 5 events)

Order of cost: shared helper (alternate A/B counter, hold-release on C, power bar) -> Bubble Gather (reuse arcade bonus: needs layout 24 and
ArcBonus; bonus lives under ARCADE gates, see game.c:559 and main.c:1865 `mode == GAME_MODE_ARCADE && state == ARC_BONUS`, to be widened)
-> Big Blow -> Flap Dash -> Pop Drop -> Gum Fling (largest: Gum Trip field). Gum Games is a PARTY rule value (or its own title row: open
question). 2P alternates turns, so no new input path: P1/P2 read from the existing input / input2 bytes in turn.
Facts needed first, still UNVERIFIED: Gum Trip generator can emit a flat hazard-free course (trip_gen.h not read here); fix-layer power
bar fits the vblank budget (fact 6, 4 line units headroom); B/C/D on real MiSTer stick (fact 1 caveat).
Tests: host per event (scoring, qualifying, retry ticket, alternation counter rejects repeated same button), MAME one script per event.
Each event is a separate plan phase and merge.

## Cross-cutting tests (each phase)

- make test (host + MAME suite) once per landing only; per change: test-vblank, test-sprite-peak (if sprites), test-score/score_check
  for table changes, party_check.lua. Run nice -n 19, one at a time (global rule), SDL_VIDEODRIVER=dummy, -window -nomaximize -video none.
- MAME targets reachable per phase: 0: boot_check, score_check, vblank, reach. 1-3: party_check (new), vblank, flier, solid; 2 adds
  sprite-peak. Gum Games: events + vblank + sound for new events.

## Risks (overall)

- Vblank margin ~4 line units (219.6/224 for demo arena): adding any per-frame work in PARTY demo may fail test-vblank. Measure first.
- feature/arena-2p is uncommitted and moving; PARTY join rule must be rebased on it. Do not start phase 0 before it merges.
- One score table shared across rules (open question) compares unequal rules.
- Backup image bump v4: players' saved scores must survive (load v3 path must be tested with an old image).

## Open questions for the owner (not decided here)

1. Title: how is the rule chosen: auto-cycling per round, shown card then fixed per credit, or sub-select (Left/Right on the PARTY row)?
2. PARTY score table: all rules in one table with no per-rule label, or session best only (research suggests this to avoid unfairness)?
3. Is Rule of the Round a rule in the same cycle (random rule each round that can stack with Hot Gum/Roost) or one of the three rule sets?
4. Roost Rule AI: new hold state in ai.c (cost M) or accept hop-and-hover and tune?
5. Hot Gum: carrier look by blink only (no art) or a new gum bubble sprite (new slot, art, budget entry)?
6. Hazard Roulette: mid-round swap (cost unverified) or only at round end?
7. Hot Gum cool-rival flee at any range (ai_decide change) or the existing short flee range?
8. Gum Games: own title row or a PARTY rule? Where do event records live (session only vs saved)?
9. 2P: P2 uses same rule set every round, and does P2 join mid-round (arena-2p style, next round start) in PARTY? Confirm.
10. Hold Phase 0 until feature/arena-2p merges, or start now on top of the worktree?

## Owner decisions 2026-11-16

1. Rule pick: Left/Right on the PARTY title row changes the rule shown; Start begins it.
2. Score table: one saved PARTY table, each entry carries a short rule tag. Backup save v4 with a v3 loader path.
3. Rule of the Round is its own rule set (one of the three on the PARTY row), not stacked on the others.
4. Roost Rule: new hold state in ai.c (rivals contest the island).
5. Hot Gum carrier: hand-pixeled gum bubble sprite from the start (new slot range, budget table entry, 14 per line check). Visual drafts first, owner picks, then implement. Owner pick: draft B angry bubble (thoughts/shared/drafts/2026-11-16-gum-bubble/).
6. Hazard Roulette: hazards change only at round end, inside the existing fade transition.
7. Hot Gum: rivals without the gum flee the carrier at any range (ai_decide change).
8. Gum Games: own title row (not a PARTY rule); per-event records saved in the backup save. Supersedes "one PARTY entry" for Gum Games only.
9. 2P: P2 joins PARTY modes as in Arena 2P (Start banks join, P2 enters at next round start, one credit). Same rule all match.
10. Phase 0 waits until feature/arena-2p merges into beta1 (implementation default, not asked).

## Owner decisions 2026-11-16 (evening): how-to screens and twist announce

- PARTY how-to screen before round 1 of every PARTY match (after Start on a PARTY rule). Content: the rule name, 2-3 explaining text lines, and a live demo of computer birds playing that rule (reuse the attract demo path, party rule set, fixed seed). Runs about 8 s; any player's A or Start skips it.
- The demo source is the existing attract demo with computer birds, not recorded human inputs.
- Rule of the Round: every round announces its twist with a twist-specific explanation line (replaces the generic "A NEW TWIST EVERY ROUND" on the banner), held about 3 s with play frozen; A skips the hold. The explanation lines are drafted by the agent and approved by the owner before landing.

## Owner decisions 2026-11-18

These supersede the 2026-11-16 decisions where they conflict (decision 8 "Gum Games own title row", Phase 3 Hot Gum).

- MENU-MERGE: one PARTY entry on the title page, submenu SINGLE EVENT (pick one event vs a friend) or TOURNAMENT (every event once incl. Gum Trip, shuffled, one total score table).
- PARTY is 2 players only. No CPU-rival 1P party variants.
- GATHER-2P: Bubble Gather becomes 2P head to head for most bubbles.
- ROOST king of the hill: strong pulsing glow + arrow over the hot island; island moves every 10 s with a 2 s warning blink; points only while alone on it; CPU birds race to it and fight for it.
- 2P plan for games built 1P: Pop Drop and Bubble Gather on the same screen at the same time; Flap Dash and Gum Fling by turns; Gum Trip by turns now, co-op later. No split screen (report thoughts/spot/reports/split-screen-research.md).
- Pump rule: any new press of A or B counts as one pump in all mash games (gg_mash_step).
- Open: 1P Gum Games records/solo play (default: solo gum games leave the menu, saved records stay in save data).

## Phase 3 (new): TOSS-GUM

Replaces Hot Gum in the PARTY list. 2 players + 2 CPU birds.
- Four birds stand still in an ellipse on the Gum Fling grass field (draft layout 1, thoughts/shared/drafts/2026-11-18-toss-gum/). No flying.
- Carrier tosses with seat-relative buttons: A = left neighbour, B = across, C = right neighbour; letter tag over each target while carrying.
- Fuse hidden; the gum swells and blinks faster near the end.
- Burst bird is out; a new gum goes to a random survivor with a shorter fuse; last bird wins.
- Look: hand-drawn side-view throw and catch poses (no front/back views); P2 gold and CPU2 violet palettes unless P2 already has a colour elsewhere.
- Status: pose drafts in thoughts/shared/drafts/2026-11-18-toss-gum/poses/, owner eye check before code.

## Phase (new): TUG-GUM

Owner decisions 2026-11-18. 2 players + 2 CPU birds.
- Teams of two on a gum strand: each player has a CPU partner behind them. Partners lean, strain and slide with their player but add zero force (looks only).
- Input: any new press of A, B or C is one pull (gg_mash_step style). D lets go: you slide back a little; if the other player pressed pull in the last ~0.25 s they stumble and their pulls count for nothing for ~0.6 s; otherwise you just lost ground. No heave.
- Win: the knot crosses a line, the strand snaps, the losing team gets slapped by the gum. Best of 3.
- Stage: stadium background (see STADIUM below) on the field.

Implementation (feature/tug-gum): PARTY_TUG after PARTY_TOSS; logic in src/core/gg_tug.c/.h (pure, tests/host/test_gg_tug.c); wiring copies Toss Gum (GgTug in Game, game_gg_start_tug, game_step_tug, flow start). Win line +/-32 px, pull 1.5 px, let go 3 px, D window 15 frames, stumble 36 frames, CPU rival presses every 8-13 frames. Remaining: art sheet from drafts/2026-11-20-tug-gum (partner marker, stronger pull0, thicker storm strand), main.c drawing, sprite_budget, make test-party-tug.

## STADIUM background (ground events)

Owner decisions 2026-11-18: ground events only (Toss Gum, Tug Gum, Gum Fling, Big Blow, Burst Race). Side stands behind the field at pitch level: sky with floodlight towers, far stands, near rail, grass. Bird crowd reacts to play (idle bob, cheer burst on score/burst/snap, each half in one team colour, win wave at result) plus a rolling stadium wave in calm moments. Moods dusk, moon, storm (floodlights at moon and storm, rain and umbrellas at storm). Drafts: thoughts/shared/drafts/2026-11-18-stadium/, owner pick before code.

## Owner decisions 2026-11-21: MENU-MERGE (one PARTY list)

- Title page: PARTY and GUM GAMES rows become one PARTY row. Title menu goes from 5 to 4 modes (ARENA, GUM TRIP, ARCADE, PARTY).
- PARTY opens one event list with all 11 events, party rules first: RULE OF THE ROUND, ROOST RULE, TOSS GUM, TUG GUM, BIG BLOW, BURST RACE, BUBBLE GATHER, POP DROP, FLAP DASH, GUM FLING, POOP THE MAN.
- Tournament (SINGLE EVENT / TOURNAMENT split from 2026-11-18) is NOT in this step. It comes later as its own task.
- Player count: each event keeps the player count it supports today. 1-player gum game records stay and stay visible. Nothing is removed.
- Look: same style as today's GUM GAMES submenu; the list scrolls if 11 rows do not fit. No visual draft first; owner checks it in the play build.
- Score tables: keep today's PARTY SCORES and GUM GAMES SCORES data; only the menu entry merges.
