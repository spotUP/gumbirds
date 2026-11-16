# Hot Gum (PARTY phase 3) status, 2026-11-16

Branch `feature/hot-gum` (from `integ/beta1`).

## Rule as built
- One carrier holds the hot gum (angry bubble sprite above the bird, design B, tiles 5032..5039, slot 118 shared with the Roost marker; the two rules never run together).
- Fuse: HOT_FUSE_FRAMES 720, minus 90 per round won, minimum 360. At zero the carrier loses one balloon and a random bird still flying takes the gum with a fresh fuse.
- A touch hands the gum to the other bird after a 60 frame cooldown. A human carrier scores SCORE_HOT_PASS (200) per pass. Stomps never pop in this rule (every contact is a bounce).
- Rivals without the gum flee the carrier at any range (`Ai.flee` forces AI_FLEE with the carrier as target).
- Match end: normal arena round end (last bird flying wins the round). No target score. Chosen because the plan leaves it open and the fuse already removes balloons.
- Goal line "PASS THE HOT GUM BEFORE IT POPS"; how-to text rewritten to match; COMING SOON removed for Hot Gum only (Hazard Roulette keeps it).

## Tests
- Host: `tests/host/test_hot.c` (in `run.sh`), knob digest and knobs.txt cover the new tuning.
- MAME: `make test-party-hot` (`tests/mame/party_hot_check.lua`, probe `party_hot_probe.c`): fuse counts down and reloads in the real ROM.

## Not verified
- Sprite look in game (yellow core against the P2 bird, dusk and storm mood readability), bubble y offset (-34) on screen: no visual check done. The MAME check reads state, not the sprite.
- A touch on a rival still inside its stage-start pump window defeats it (existing pump rule), it does not pass the gum.
