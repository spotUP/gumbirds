# Front face take A ("chick") in the game - implementation notes (2026-11-22)

Brief: thoughts/spot/2026-11-21-front-face-brief.md. Drafts: thoughts/shared/drafts/2026-11-21-front-face/.
Branch: worktree-agent-ad07b1215c40c83b6 (not pushed).

## What changed
- assets/flier/gum_mouth/frames_front.txt (new): the 7 take A grids copied verbatim from the draft frames.txt
  (A_stand_rest, A_stand_in, A_stand_blink, A_air_mid, A_air_blink, A_air_up, A_air_down). No pixel was redrawn.
- tools/import_gum_mouth_sheet.py: reads frames_front.txt too; two clips appended last so every older frame keeps
  its number: idle_front (clip 14, frames 100..107, 6 ticks each) and breathe_front (clip 15, frames 108..113,
  ticks 24,20,24,20,10,6 = the draft timing). gum_show = 0 on the front frames (no bubble on a gumless face).
- Regenerated assets/flier/gum_mouth/sheet/{frames.json,sheet.png} and assets/flier/sootling_sheet.{png,json}:
  114 frames, 16 clips. Palettes (player, cpu) and extra palettes (p2, distress1..3) are byte-identical, same slots.
- src/core/flier_view.c steady_clip(): on the ground a bird with 0 balloons plays breathe_front, with gum the old
  breathe. In the air / on the parachute a bird with 0 balloons already played the `idle` slot; src/main.c k_clips
  now puts SOOTLING_CLIP_IDLE_FRONT there. Walking stays side-on. One shared path, so hero, P2, computer fliers
  and rivals in every mode get it.
- src/core/flier_view.h: FlierClips gets a trailing field breathe_front.
- src/core/gum_view.h: GUM_VIEW_BIRD_FRAMES 100 -> 114 (the per frame gum tables grew with the sheet).
- Tests: tests/host/test_flier_view.c (front breathe 6 frames with sheet ticks, front idle 8 frames, counts 114 / 16),
  tests/host/knob_digest.c (clip table), tests/mame/flier_check.lua (standing with 0 balloons expects breathe_front).
- RULES.md flier art line updated.

## Numbers
- Unique 16x16 tiles of the Sootling sheet: 85 -> 104 (+19), counted on the player animation, matches the draft count.
- build/gen/sootling.c1 is 7168 bytes. All C1 sets together 355840 bytes; the build's own check
  (build.mk, over CROMSIZE 2097152 = error) passed.
- Text check against the draft grids: 0 pixel mismatches in player and cpu palettes; the old 100 frames unchanged.

## Gates
- cart build: OK. Host tests: all passed.
- MAME (headless): test-flier PASS, test-vblank PASS, test-coop PASS (P2 drops in on the parachute), test-arcade PASS.

## Not changed on purpose
- The old side-on `idle` clip stays in the sheet (frames 37..42, shares tiles with fly, zero tile cost) but is no
  longer played. Remove it only together with a renumbering of the pinned frame indices.
- A gumless bird that lands still plays the side-on `land` one-shot (8 ticks) before the front breathe.
- The pump window after a parachute landing still shows the side-on pump frames (the bird has gum again there).
- breathe_front holds come from the sheet ticks, not from the FLIER_BREATHE_HOLD_* knobs (those still drive the
  breathe with gum).

## Not verified
- No MAME check reads the clip of a standing or hovering gumless bird frame by frame; the host test covers the
  choice, MAME covers that the tiles draw and nothing regressed. Owner check on screen is still needed.
- Facing-left mirror of the front frames was not looked at.
