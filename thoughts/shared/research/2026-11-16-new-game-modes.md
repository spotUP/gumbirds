---
date: 2026-11-16
author: agent (game design research, read-only on source)
status: draft
topic: New funny game modes that reuse the Gumbirds engine
---

# New game modes for Gumbirds (draft)

Ten mode ideas, ranked best fun-per-cost first. The top 3 are marked RECOMMENDED.
All are original to this game; none copies a mode, name or character of another game.

## What the engine already gives (read from headers, not run)

- Modes: `GameMode` in `src/core/game.h:47` (ARENA, TRIP, ARCADE). `game_set_mode` seeds a mode, `game_step`
  dispatches. The arena step (`game_step_arena`, `game.c:439`) also runs arcade.
- Fliers: `Flier` with `balloons`, `has_parachute`, `no_wrap`, `kill_y` (per flier, settable) in `flier.h`.
  Pair rules: `flier_stomp`, `flier_pair_apply` (POP_A / POP_B / BOUNCE), `flier_body_kill`, `flier_body_bounce`,
  `flier_lose_balloon`, `flier_add_balloon`, `flier_spawn_protect`.
- Rivals: up to `STAGE_SPAWN_COUNT` 6 slots (`g->cpu[]`, `g->ai[]`), arena cap `CPU_MAX` 3, arcade 3..6 by layout.
  `ai_step(a, rng, self, target, out)` takes ANY flier as target, so "who chases whom" is one argument.
- Arcade parts: stage table and ranks (`arcade.h`), rival pump-up window (`ArcPump`, `arc_pump_progress` 0..4),
  lives and continue (`ArcLives`), bonus bubbles (`ArcBonus`, `arc_bonus_step` pops bubbles against a rectangle,
  pool of 4), stage elements (`arc_elements.h`: smog vent, gum flipper, drain grabber, updraft grate, with
  `arc_elements_kill` / `_bounce` / `_lift` / `_avoid_dir`).
- Stage: 12 arena layouts + 12 arcade layouts + bonus layout 24 (`stage.c`, `stage_select`), `stage_floor_y`,
  three island looks. Hazards: 4 kinds, `game_set_hazard` switches kind and every kill line at once.
- Round framing: ROUND / GO freeze, round end hold and camera pan, and `game_round_start_text` (two free text
  lines at round start, used today for the bonus announcement).
- Gum Trip: `Trip` (gum, streak, speed ramp `trip_speed_at`, density `trip_density_at`), `trip_pickup`, `trip_hit`,
  chunk generator, three rival variants (`trip_rival.h`).
- Two players: co-op exists in ARCADE and its bonus only (`game_join_p2`, friendly stomps on, camera follows the
  midpoint). P2 Start is ignored in Arena and Gum Trip by owner decision (todos.md line 4923).
- Budgets: `SB_GAMEPLAY_PER_LINE` 14 sprites for fliers (`sprite_budget.h:15`); a flier costs 2 strips; measured
  arena peak 8; arcade worst is hero + 4 rivals on one line.

## Cost every new mode shares (decide once, not per mode)

1. Title mode list: three entries today, drawn on fix rows 23-24 (`src/main.c` near line 942,
   `title_mode_select` in `flow.c:104` hard-codes the ARENA..ARCADE wrap). A fourth entry needs the list layout
   reworked.
2. Score tables: one `HiscoreTable` per `GameMode` (`score_table.h`). A new table changes the backup image
   (the arcade table did: "backup image v3, old saved scores reset", todos.md line 2807).
3. Attract demo rotation (`flow.c:22`) also hard-codes the three modes.

Cheapest route (recommended, owner decision): ONE new title entry, "PARTY", with a `party_rule` byte in `Game`
that picks the rule set, changed per round or per credit. Party modes share one new score table or keep no
table. That is one menu row, one table, one demo slot for all modes below, instead of one each.
Sharing one table across different rules is unfair between rules; showing the session best only avoids that.

## Ranking

| Rank | Mode | Size | Players | Recommended |
|------|------|------|---------|-------------|
| 1 | No Stomping Please | S | 1P, 2P co-op | yes |
| 2 | Hot Gum | S-M | 1P, 2P | yes |
| 3 | Roost Rule | S | 1P, 2P | yes |
| 4 | Gum Rush | S-M | 1P, 2P | |
| 5 | Very Important Bird | M | 1P, 2P co-op | |
| 6 | Rule of the Round | M (S for the cheap subset) | 1P, 2P | |
| 7 | Grudge Match | M | 2P only | |
| 8 | No Flap Zone | M | 1P | |
| 9 | Sugar Rush | S-M | 1P | |
| 10 | High Water | L | 1P, 2P | no (breaks the budget rules) |

Sizes: S = under about 80 lines of core logic plus a host test; M = 80 to 250 lines, touches HUD or flow;
L = touches the view, VRAM writes or the budget model.

---

## 1. No Stomping Please (RECOMMENDED)

Pitch: you may not pop anyone; clear the stage by tricking the rivals into the vents, the grabber and the hazard.

Why it is funny: the game's one verb is forbidden. The player becomes bait, hovering over a smog vent and
stepping aside at the last tick. A reflex stomp costs points and flashes "SORRY!", so the habit the other modes
taught becomes the joke.

Rules:
- Arcade stage layouts with elements (vents, grabber, flippers, grates). Rivals chase the player as usual.
- A rival killed by an element or by the hazard strip pays the rank defeat score times a chain multiplier
  (chain resets when the player loses a balloon).
- A player stomp still pops (physics unchanged) but subtracts points and resets the chain. Bounces are free and
  are the main tool: bump a rival into the plume.
- Rivals do NOT avoid elements in this mode.
- Stage clear when all rivals are gone; arcade lives apply.

Reuses: `game_step_arena` arcade path, `arc_elements_kill`, `arc_elements_bounce`, `flier_body_bounce`,
`arc_rank`, `ArcLives`, arcade layouts 12..23, `banner.c` for "SORRY!".

New code (S): one rule flag; skip the `arc_elements_avoid_dir` call for rivals; score branch in the stomp path
and in the element-kill path (`score_add`); chain counter; one banner text.

Risks: none for sprites or vblank (same scene as arcade). Design risk: stages with few elements (early arcade
stages) give no way to win, so the stage list for this mode must be the element-rich layouts only. The rivals'
pump-up window (`ArcPump`) pays a bump as a defeat today; decide whether that counts as "stomping".
Not checked: which of the 12 arcade stages carry which elements.

Players: 1P; 2P co-op works as arcade co-op does (friendly stomps make the second player a hazard too).

## 2. Hot Gum (RECOMMENDED)

Pitch: one bird carries a swelling gum bubble on a fuse; touching another bird passes it, and whoever holds it
when it bursts loses a balloon.

Why it is funny: chase and flee swap in an instant. The carrier lunges at everyone while the others scatter, and
the pass happens through the same bump that normally just bounces. The swelling gum makes the panic visible.

Rules:
- Arena layout, player plus 3 rivals. One flier is "hot"; a fuse counts down (for example 8 seconds, shorter
  each round).
- Any pair contact (stomp or level bounce) involving the hot flier passes the gum to the other. Stomps do not
  pop in this mode; only the fuse pops.
- Fuse end: the carrier loses one balloon (`flier_lose_balloon`), then the gum jumps to a random survivor and the
  fuse restarts. A short pass cooldown stops ping-pong on one contact.
- Last bird flying wins the round; score for each pass made and each round survived.

Reuses: `flier_pair_apply` results as the pass event, `flier_lose_balloon`, `ai_step` with the target argument
(hot rival targets the nearest flier; cool rivals get the carrier as target and the existing flee logic,
`AI_FLEE_DIST`), blink (`FLIER_BLINK_HALF_PERIOD`) or the pump-up frames (`arc_pump_progress`) as the "hot"
look, round framing, `Rng`.

New code (S-M): `hot` index, fuse timer, pass rule in the pair loop, target choice per rival, fuse readout in
the HUD (one fix-layer number or the blink rate alone).

Risks: sprites unchanged (4 fliers, peak 8). Whether the pump-up gum frames exist for the player bird is not
checked; blink is the fallback and needs no art. The AI has no "run away from a target" call as such: flee is a
state inside `ai_step`, so cool rivals may need a small bias. Input: none new.

Players: 1P; 2P is natural once P2 is allowed outside arcade (needs the join rule widened, see mode 7).

## 3. Roost Rule (RECOMMENDED)

Pitch: only the bird standing on the marked island scores, and the mark jumps to another island every few
seconds.

Why it is funny: a flying game where the goal is to stop flying. Everyone crowds one small island, shoving each
other off its edges on foot, then the mark moves and the whole flock scrambles.

Rules:
- Arena layout. One platform index is the roost; it changes every 10 seconds (never the same twice,
  `Rng`), with a 1 second warning.
- Each frame a flier STANDS on the roost alone it gains a point tick; shared roost pays nobody.
- Stomps and bounces work as in the arena; a popped bird respawns by parachute after a delay so nobody is
  eliminated. First to a target score, or highest after 90 seconds, takes the round.

Reuses: `stage_platforms[]`, `stage_floor_y` (which platform a flier stands on), rivals with a target that is a
dummy `Flier` parked on the roost (`ai_step` target argument), parachute respawn (the 2P join spawn,
`FLIER_START_JOIN_Y`), round timer fields, one bonus bubble sprite (`ArcBubble` art) hovering over the roost as
the marker.

New code (S): roost index and timer, standing test, score tick, dummy target, marker placement.

Risks: marker adds 1 sprite on the roost's lines; fliers crowding one island put up to 4 fliers (8 strips) plus
marker on the same lines: 9, under 14. The island art has no highlight state; the hovering bubble avoids new art.
Rivals standing still on an island is not something the AI does today (it flies at its target): expect them to
hop on and off, which may be fine or may need a "land here" bias. Not checked.

Players: 1P; 2P versus or co-op works once P2 may join outside arcade.

## 4. Gum Rush

Pitch: the bonus-stage bubbles rise through a live arena fight, and the rivals want them as badly as you do.

Why it is funny: greed against safety. Bubbles drift up through the brawl, rivals abandon the chase to snap one
up, and reaching for a bubble is exactly when you get stomped.

Rules:
- Arena or arcade layout plus the bubble stream (20 bubbles, at most 4 alive). A caught bubble pays the bonus
  value; a rival that catches one grows back a balloon (`flier_add_balloon`).
- Round ends when the stream ends; most bubbles wins, perfect bonus if the player takes all 20.

Reuses: `arc_bonus_init`, `arc_bonus_step` (called once per flier rectangle), `arc_bonus_value`,
`arc_bonus_perfect`, bubble sprites and pop effect, `ai_step` with a dummy target at the nearest bubble.

New code (S-M): run the bonus pool inside play instead of only in `ARC_BONUS`; bubble spawn x without nozzles
(random column at the hazard line, or keep the nozzle x values); per-rival catch test; nearest-bubble target.

Risks: sprites: 4 bubbles + 4 fliers x 2 strips = 12 on one line in the worst case, under 14 but the tightest of
the cheap modes; keep rivals at 3. The bonus view code assumes the bonus layout (floor strip, nozzle puffs in
`main.c`); how much of it is tied to that layout is not checked.

Players: 1P; 2P co-op in arcade layouts (bonus already supports per-catcher boxes, todos.md line 4919).

## 5. Very Important Bird

Pitch: escort a clueless, slow bird with one balloon; every rival wants it, and it wanders straight at the vents.

Why it is funny: the bodyguard job with the worst possible client. The escorted bird drifts happily toward
danger while the player bounces it out of plumes with body bumps.

Rules:
- One computer slot is the escort: one balloon, not hostile, flies a lazy hover pattern. Rivals target the
  escort, not the player.
- The round is lost when the escort drowns or loses its balloon; it is won when all rivals are popped or a timer
  runs out. Score for time survived and for each rival popped near the escort.
- The player's own stomp on the escort is ignored (friendly), bumps still move it.

Reuses: `g->cpu[]` slot with a different pilot (the attract hover pilot, `DEMO_HOVER_Y` / `DEMO_SWEEP_FRAMES` in
`tuning.h`), `ai_step` target argument, `flier_pair_apply` with POP against the escort filtered out, P2 palette
swap (`SOOT_P2_PAL_SLOT`) to mark the escort.

New code (M): escort slot flag, pilot hook, pair filter, lose condition, HUD marker.

Risks: sprites as arcade (5 fliers worst). The hover pilot lives in the demo path; whether it can drive a `cpu`
slot without the demo flag is not checked. Balance: too easy if rivals are slow, hopeless at rank 3.

Players: 1P; 2P co-op (two bodyguards) in arcade.

## 6. Rule of the Round

Pitch: every round starts with a surprise rule card: "MIRROR STICK", "WINDY", "ONE GUM EACH", "HAZARD ROULETTE".

Why it is funny: the announcement itself is the punchline, and the first seconds of each round are everyone
(rivals included) coping badly.

Rules: arena rounds; before GO a rule is drawn from a table (no repeat) and shown on the two round-start text
lines. Cheap rule set:
- Mirror Stick: left and right swapped for the human.
- Windy: a constant sideways push on every flier, direction flips mid-round.
- One Gum Each: everyone starts with one balloon.
- Hazard Roulette: `game_set_hazard` switches kind every 10 seconds.
- Crowded Sky: `CPU_MAX` rivals from round 1.
- Slow Thinkers / Quick Thinkers: rival rank forced to 1 or 3 (`ai_init` rank).

Reuses: `game_round_start_text`, `match_start`, `game_set_hazard`, `ai_init`, `flier_init`, `Rng`.

New code: S for the list above (input bit swap in `game_step`, a vx delta in `arena_flier_step`, start values).
M if gravity or flap strength rules are wanted: those are `#define`s in `flier.h` / `tuning.h` and would have to
become per-game values read in `flier_step`, which costs cycles in the hottest function.

Risks: Hazard Roulette changes the strip art mid-round: how much VRAM that writes is not checked; it may need the
round-end freeze to hide it, which would make it a per-round rule instead. Mirror Stick must not reach the name
entry or menus.

Players: 1P; 2P wherever P2 is allowed.

## 7. Grudge Match

Pitch: two players duel, and every time you pop your friend a computer bird joins THEIR side to get revenge.

Why it is funny: winning makes your life worse. The leader ends up chased by a flock while the loser coasts
behind hired help, so rounds swing back and forth and the trash talk writes itself.

Rules:
- 2P only, arena layout, best of 5 rounds. Friendly stomps on (already the co-op rule).
- Each pop of the other player spawns one rival (up to 3) that targets the popper only.
- Round ends when one player drowns; the survivor takes the round.

Reuses: co-op data model and input (`game_join_p2`, P2 palette, midpoint camera), `ai_step` target argument,
`stage_spawns`, round framing, `matches_won` style counters.

New code (M): P2 allowed at start in this mode, per-rival owner/target, round win per player, two win counters in
the HUD, result text.

Risks: sprites: 2 humans + 3 rivals = 5 fliers, 10 strips, plus parachutes at join: within 14 but measure.
Credit handling for a 2P start outside arcade was left unchecked on MVS BIOS / UniBIOS / MiSTer in the co-op plan
(todos.md line 4878); this mode reopens it. Owner decided P2 is ignored in Arena; this is a new mode, so it
needs a fresh decision.

Players: 2P only.

## 8. No Flap Zone

Pitch: your wings are tired: no flapping, so the only way up is to bounce off rivals, flippers and updraft grates.

Why it is funny: the rivals become trampolines. The player falls with dignity, lands on a head, and rides the
bounce to the next one; a missed bounce is a slow, sad sink into the water.

Rules:
- The A button does nothing in the air (ground jump stays). Height comes from stomp bounces, gum flippers and
  updraft grates. Rivals respawn so there is always something to bounce on.
- Score is time alive plus a chain bonus for consecutive stomps without landing.

Reuses: `flier_stomp` / `flier_pair_apply` bounce, `arc_elements_bounce`, `arc_elements_lift`, arcade layouts
with flippers and grates, rival respawn through `match_start` spawns.

New code (M): mask the flap bit while airborne, respawn loop, chain counter, likely a larger stomp rebound in
this mode only.

Risks: no hardware risk. Balance is the whole cost: whether today's stomp rebound gives enough height to reach
the next rival is not checked, and the mode is dull if it does not. Needs play tuning rounds with the owner.

Players: 1P.

## 9. Sugar Rush

Pitch: Gum Trip on a 60 second clock: every gum pickup makes the cave scroll faster, every hit slows it down, and
only distance counts.

Why it is funny: the player asks for more speed than they can handle. A long pickup streak turns the cave into a
blur and one coal lump brings the humiliating crawl.

Rules:
- Gum Trip course and rivals. Scroll speed = normal ramp plus a boost per streak step, capped at the present top
  speed; `trip_hit` drops the boost to zero.
- 60 second timer; no death by gum decay (decay off), wall kill still ends the run. Score = distance.

Reuses: `Trip.streak`, `trip_step`, `trip_speed_at`, `trip_pickup`, `trip_hit`, `tripgen_*`, trip view and HUD.

New code (S-M): boost term in the speed (capped so the generator and scroll never exceed speeds already proven),
timer, decay switch, timer readout.

Risks: the cap matters: the chunk ring (`TRIP_GEN_RING` 5) and the vblank cost of the cave were tuned for the
present top speed, so the boost must stay at or under it; then nothing new is loaded. Least "new" of the list:
it is a tuning variant, so it ranks low on fun.

Players: 1P.

## 10. High Water (not recommended)

Pitch: the hazard rises a little every few seconds until the fight is squeezed into the top of the screen.

Why it is funny: the islands vanish one by one under the lava while everybody fights for the last perch.

Rules: arena; the kill line climbs (per flier `kill_y` is already settable) until one bird is left.

Reuses: `Flier.kill_y`, `game_set_hazard`, arena rounds.

New code (L): the logic is small, but the drawn strip sits at `HAZARD_STRIP_TOP_Y` 192 and `hazard_kind.h`
exists so that the art and the kill line cannot drift apart. Moving the strip means moving its sprites every
step (VRAM writes in vblank) and stacking it on the island rows.

Risks: breaks two of the stated limits: extra vblank writes, and strip sprites sharing scanlines with islands
and fliers (the storm mood was already at 21 on its worst band, todos.md line 337). Listed so the idea is on
record with its cost; a fake version (kill line rises, art does not) would look like a bug.

Players: 1P, 2P.

---

## Owner addition: Gum Games (button-mashing event medley)

Not ranked with the ten above: it is a mini-game collection, a different kind of mode with a different cost.

Pitch: a five-event bird sports day where gum is the equipment: mash to pump, hold and release to launch, tap in
rhythm to sprint, and miss the qualifying mark to be sent home under a parachute.

Why it is funny: the birds take it very seriously and the equipment does not. Over-pumped gum bursts in the
athlete's face, a bad launch angle drops the bird straight into the hazard strip, and a failed qualifier floats
off slowly on a parachute while the banner reads "NOT TODAY".

All events, names, layouts and readouts below are invented for Gumbirds; nothing is taken from an existing
sports game. Every event plays on screens the engine already draws.

### Input scheme (Neo Geo A/B/C/D)

`IN_A`..`IN_D` already exist as bits (`game.h:28-31`); B, C and D are unused in play today, so no input work in
`main.c` beyond passing them through (not checked that play passes B/C/D to the core).

- A and B: the two "wings". Power comes from ALTERNATING A, B, A, B. Pressing the same button twice adds
  nothing, so one-button turbo does not help. Power = alternations in the last 32 frames, decayed each frame.
- C: the "action" button: hold to set an angle or a pressure, release to commit.
- D: unused (kept free so a cabinet with three buttons loses nothing).
- Stick: not needed in events 1 to 4; steers in event 5.

Alternation counter, hold-and-release timer and a power bar are one shared helper (about 40 lines) used by every
event.

### Events

1. Big Blow (pump power). Alternate A/B to inflate a gum bubble; release nothing, just stop in time. The pressure
   climbs with each alternation and leaks slowly. Score = largest size held when the 8 second clock ends. Pump past
   the limit and it bursts: size zero for that attempt. Reuses the rival pump-up stages (`arc_pump_progress`
   0..4 frames) for the growing gum and the existing pop effect and sound event.
   Qualify: reach stage 3 of 4. Three attempts, best counts.

2. Flap Dash (sprint). A bird runs and flaps across the 384 px arena ring for 3 laps. Each A/B alternation is one
   flap impulse sideways (`FLIER_FLAP_THRUST_X`) with the top-speed cap lifted for this event; the camera follows
   as in the arena. Score = time. Reuses `flier_step`, the arena wrap, `camera_step`, the walk and flap frames.
   Qualify: under a mark time that tightens each loop of the medley.

3. Gum Fling (launch distance). Alternate A/B during a short run-up to build speed, then HOLD C: an angle needle
   sweeps 0 to 90 degrees while held, release to launch. The bird flies as a ballistic body with no flapping and
   lands in the Gum Trip cave scroll; distance is read where it touches down. Launch velocity from the existing
   tables (`flier_sin` / `flier_cos` with the angle). Reuses the Gum Trip scroll and chunk view as the landing
   field (course generated with hazards and pickups off), `Trip.px` as the distance counter, the splat
   (`trip_splat`) as the landing mark.
   Qualify: a distance mark. Three attempts, best counts. A launch below 15 or above 75 degrees is a foul
   (it lands in the hazard).

4. Pop Drop (stomp precision). The bird hangs under a parachute high over a row of rival balloons drifting past.
   No mashing: press C once to cut the chute and fall. A hit pops the balloon; the score is how close the feet land
   to the balloon centre (pixels off centre), five drops. Reuses `has_parachute` and the chute release (flap
   releases the chute in co-op), `flier_stomp` for the hit test, a rival on a fixed sideways drift as the target,
   `FLIER_PARACHUTE_SWAY` as the built-in difficulty.
   Qualify: 3 pops out of 5.

5. Bubble Gather (medley closer). The arcade bonus stage as an event: 20 bubbles from the four nozzles, 45
   seconds; A flaps and the stick steers as in normal play, and alternating A/B is not required. Score = bubbles
   caught. Reuses `ArcBonus`, `arc_bonus_step`, layout 24 and the result screen unchanged.
   Qualify: 12 of 20. This event is the rest between mashing events and costs almost nothing.

### Medley and qualifying rules

- Events run in the order 1 to 5. Each has a qualifying mark shown before the start (two round-start text lines,
  `game_round_start_text`).
- Miss a mark: one "retry ticket" per credit lets the player repeat the event once; a second miss ends the run.
- Each result converts to points (table per event) for one Gum Games score table. After event 5 the medley loops
  with tighter marks (loop counter as `ArcRun.loops`).
- A new best mark in an event shows "RECORD" on the result screen; event records are session only (no extra
  backup data) unless the owner wants them saved.

### Players

- 1P: as above.
- 2P alternating (recommended): players take the same event in turn, P1 then P2, each with own marks and score;
  a player who fails to qualify sits out and the other plays on. One bird on screen at a time, so the sprite cost
  is the lowest of any mode, and the co-op per-player score and HUD rows are reused.
- 2P simultaneous: fits events 1 and 5 only (two birds side by side; event 5 already supports two catchers).
  Events 2, 3 and 4 need one camera per player, which the engine does not have. Not recommended as a rule; could
  be a later option for those two events.

### Reused systems

`ArcPump` stages (gum growth), `flier_step` / `Flier` (run, fall, parachute), `flier_sin` / `flier_cos` (launch),
arena ring and `Camera` (dash), Gum Trip scroll and chunks (landing field), `ArcBonus` and layout 24 (gather),
`result.c` / `result_view.c` (event result), `banner.c` and round-start text (marks, "NOT TODAY"), co-op player
data (alternating 2P), `score_table.h` (one new table), `sound_events.c` (pop, flap, splat).

### Cost

- Shared: alternation and hold-release helper, event sequencer (state, attempt count, mark table, points table),
  mark and result text: M.
- Per event: Big Blow S, Flap Dash S, Gum Fling M (ballistic step, angle needle, Gum Trip used as a field),
  Pop Drop S-M, Bubble Gather S.
- Whole mode: L in total, about the size of the arcade bonus work twice over, but it can ship in slices: helper +
  Big Blow + Bubble Gather first (S+M), then one event per step.
- New art, small: a power bar and an angle needle. Both can be fix-layer characters (the HUD already draws on
  the fix layer), so no sprites and no new sprite art. A hand-pixeled needle sprite would look better: 1 sprite.

### Risks

- Sprites per line: at most 1 or 2 birds plus up to 4 bubbles or 1 target: well under 14 everywhere.
- Vblank: the power bar redraws fix characters every frame while mashing; keep it to a changed-cells-only write
  (the fix commit budget was a problem before, `vq_fix_commit_room`, todos.md line 4452).
- Gum Fling switches between an arena-style run-up and the Gum Trip scroll inside one event. Cheaper variant:
  do the run-up inside the Gum Trip screen too (bird runs on an island chunk), so only one view is used. Whether
  the generator can emit a flat hazard-free course is not checked.
- Flap Dash lifts the speed cap: camera `CAM_MAX_STEP_PX` 2 px/frame is twice the human top speed, so the dash
  top speed must stay at or under 2 px/frame or the bird outruns the camera.
- Input: fast A/B alternation on real hardware and on MiSTer is fine at 60 Hz reads, but the mark values need
  tuning with a real stick, not a keyboard; marks set on a keyboard will be too easy or too hard on the cabinet.
- Cabinet wear and player fatigue: five mashing events in a row is too much, which is why only 1, 2 and the
  run-up of 3 mash.

## Recommendation

Build "PARTY" as one title entry with modes 1, 2 and 3 as its first three rules. All three are rule changes
inside `game_step_arena` with host tests, draw nothing new beyond one reused bubble sprite and one banner text,
and stay at or under the sprite peaks already measured. Mode 4 is the next cheapest once the bonus pool's tie to
the bonus layout is checked.

## Not checked (read headers and the ledger only; nothing built or run)

- Element mix per arcade stage (mode 1 stage list).
- Whether pump-up gum frames exist for the player bird (mode 2 look).
- Whether the AI can hold a position on an island (mode 3), and whether the demo hover pilot can drive a `cpu`
  slot (mode 5).
- Bubble sprite cost per bubble (assumed 1 sprite for the 16 px box) and the bonus view's dependence on layout 24
  (mode 4).
- Stomp rebound height (mode 8).
- All sizes are estimates from header reading, not from `game.c` bodies.

## Owner decisions (2026-11-16, session arcadegame-7)

- First build: Hot Gum, Roost Rule, Rule of the Round. No Stomping Please is not picked for now.
- Title: one new PARTY entry with a rule byte; one score table for all party modes.
- Gum Games: full medley (all 5 events, qualifying marks, retry tickets), not just the first slice.
- 2P: P2 may join in PARTY modes as in Arcade; Gum Games alternates turns. Arena and Gum Trip stay 1P.
- Next step: a plan doc (thoughts/shared/plans/) that resolves the unverified engine facts above (B/C/D reach the core, AI island holding, Gum Trip hazard-free course, sprite cost) before any agent builds.

### Owner addition 2026-11-16: event 6, Burst Race

Head-to-head pump race: both birds stand side by side, each alternates A/B to inflate its own gum bubble; the first gum to burst wins the heat. 1P races a computer bird (fixed pump rate per difficulty step). 2P is simultaneous (not alternating). Reuses the Big Blow pump helper, bubble art and burst animation. Pairs with Big Blow as its opposite (burst on purpose versus stop in time). Records: best winning time, saved with the other Gum Games records.
