#!/usr/bin/env python3
"""Builds index.html for the SFX-MAX preview: old placeholder vs new effect, ADPCM-A size per effect and total.
New WAVs go in new/<name>.wav (mono 16-bit 18500 Hz). Usage: python3.11 -I build_page.py (run in this folder)."""
import html, os, wave

HERE = os.path.dirname(os.path.abspath(__file__))
BUDGET = 384 * 1024
RATE = 18500
# name, old sample (or ""), game event, target ms, layers (FM transient + noise + pitch move, then master FX)
FX = [
 ("flap_a", "jump", "flap press (SE_FLAP), variant 1 of 3", 110, "FM alg 4 soft thump 220>140 Hz, 30 ms SSG noise puff (wing air), high-pass feel; saturation light"),
 ("flap_b", "jump", "flap variant 2", 110, "as flap_a, start 240 Hz, noise 5 ms later"),
 ("flap_c", "jump", "flap variant 3", 110, "as flap_a, start 200 Hz, shorter noise"),
 ("pop_a", "pop", "balloon burst / gum at 0 / bonus bubble / result vanish, variant 1 of 3", 140, "FM alg 7 click (fb 7, TL 0, 2 ms), noise burst 25 ms, sine drop 1800>300 Hz in 60 ms; compressor hard, 40 ms room"),
 ("pop_b", "pop", "pop variant 2", 140, "as pop_a, drop from 2200 Hz, wetter slap tail"),
 ("pop_c", "pop", "pop variant 3", 140, "as pop_a, drop from 1500 Hz, double click 8 ms apart"),
 ("hit", "hit", "Gum Trip hit (SE_HIT)", 260, "FM alg 0 metallic knock (ratio 1:3.5), noise slap, body drop 400>90 Hz; saturation, compressor"),
 ("die", "die", "last balloon lost, not by hazard (SE_DIE)", 420, "two FM voices a minor second apart sliding 600>150 Hz with 4xy vibrato, noise tick at start; short echo"),
 ("fall", "fall", "flier starts falling (SE_FALL); now also a walker without a balloon dropping off an island", 700, "FM sine whistle 1400>180 Hz (2xx), fms vibrato growing via chip LFO, quiet octave copy one row late"),
 ("splosh", "splosh", "water or lava kill line (SE_SPLOSH)", 520, "low FM thump 120>50 Hz, SSG noise swell with falling volume macro, 3 FM droplet blips 900-1500 Hz at 120/200/300 ms; EQ low shelf up, 80 ms room"),
 ("sizzle", "sizzle", "fire kill line (SE_SIZZLE)", 520, "SSG noise with period sweep (crackle grains via volume macro), FM fb-7 hiss layer, low whump at start; saturation"),
 ("spike", "spike", "spike kill line (SE_SPIKE)", 180, "FM alg 4 bright ping 2.4 kHz + inharmonic 3.1 kHz, noise tick, fast decay; compressor"),
 ("coin", "coin", "coin inserted (BIOS coin vector)", 420, "FM bell alg 5 two notes B5>E6 (ratio 1:3.5 modulator), SSG square octave sparkle, short echo copy"),
 ("game_over", "game_over", "run ends (SE_GAME_OVER). Preview only, not in the ROM: the music jingle owns this event", 2200, "4 FM voices: descending minor phrase with brass patch, SSG arpeggio under it, last chord 12xx filter close; plate 300 ms"),
 ("start", "", "start pressed / run begins (SE_START), with the arena music", 700, "rising FM arpeggio C-E-G-C with bell patch, noise swell into last note"),
 ("round_go", "", "stage or round begins (banner out)", 600, "two FM stabs (fifth), SSG snare-like noise on second"),
 ("banner_in", "", "round / clear banner slides in", 500, "noise whoosh (SSG noise period sweep up), FM stamp thud 150>70 Hz at the end"),
 ("pump_a", "", "arcade rival pumps gum (ARC_PUMP_PUMPING), step low", 160, "FM squeak rising 300>520 Hz with fb 5, breath noise"),
 ("pump_b", "", "pump step high (alternates with pump_a, later stages)", 160, "as pump_a 420>700 Hz"),
 ("rival_launch", "", "pump done, rival takes off (ARC_PUMP_FLYING)", 300, "FM rise 400>1200 Hz, noise puff at start"),
 ("bump", "", "flier bounces off flier or island underside", 150, "FM rubber boing 260>180>240 Hz (1xx/2xx), no noise"),
 ("chute", "", "parachute opens (FLIER_PARACHUTE)", 260, "noise flutter (volume macro 3 pulses), FM soft whoomp 300>200 Hz"),
 ("defeat", "", "rival defeated on the ground / parachute finish scored", 300, "FM 3-note up blip E-G-B bell, pop click on first"),
 ("vent_warn", "", "smog vent telegraph (tick 144..215)", 600, "SSG noise rising volume hiss, FM low rumble 60 Hz with fb 6"),
 ("vent_burst", "", "smog vent launch (ARC_VENT_LAUNCH)", 650, "FM fb-7 blast 200>80 Hz, loud noise burst then falling hiss; saturation heavy, compressor"),
 ("flipper", "", "gum flipper bounce", 220, "FM alg 4 spring twang 500>900>650 Hz, click transient"),
 ("grab_rise", "", "drain grabber hand comes up (29 ticks)", 450, "bubbling: 5 FM blips rising 200-500 Hz, wet noise under"),
 ("grab_bite", "", "drain grabber bite (frames 5..7)", 300, "FM metallic snap alg 0 + noise slap, drop 700>120 Hz"),
 ("grate", "", "flier enters updraft grate", 600, "SSG noise whoosh with period sweep up, FM airy sine 500>900 Hz under"),
 ("bubble_puff", "", "bonus nozzle releases a bubble (16 frame puff)", 180, "soft FM bloop 350>600 Hz, tiny noise breath"),
 ("stage_clear", "", "arcade stage clear (ARC_CLEAR) / ALL POPPED banner. Preview only, not in the ROM: the round clear music owns this event", 1600, "4 FM voices fanfare, SSG arpeggio, ends on major chord with 12xx open; plate 250 ms"),
 ("perfect", "", "bonus perfect box (RES_EV_JINGLE)", 1800, "FM bell run up two octaves, sparkle SSG arpeggio 00C, final chord; plate 300 ms"),
 ("tally_tick", "", "result tally step (RES_EV_TICK)", 45, "FM click + 1.6 kHz blip 30 ms"),
 ("tally_bonus", "", "perfect bonus added (RES_EV_BONUS)", 500, "FM bell chord hit + noise crash short"),
 ("pickup", "", "Gum Trip gum pickup (TRIP_EV_PICKUP)", 220, "FM bloop up 500>1000 Hz + bell ping an octave above"),
 ("pickup_streak", "", "pickup with streak 3 and up", 240, "as pickup a fourth higher with a third added"),
 ("rival_warn", "", "Gum Trip rival enters (TRIP_RIV_EV_SPAWN)", 350, "two FM buzz notes (fb 6) minor second, 60 ms each, gap 40 ms"),
 ("gum_low", "", "Gum Trip gum low warning", 300, "two FM soft beeps 880 Hz, tremolo"),
 ("life_lost", "", "arcade life lost (arc_lose_life)", 700, "descending FM three notes + noise fall"),
 ("continue_tick", "", "continue countdown second (ARC_LIFE_CONTINUE)", 180, "FM clock tick + low 220 Hz tone 100 ms"),
 ("continue_yes", "", "continue accepted", 600, "rising FM arpeggio, brighter than start"),
 ("ne_move", "", "name entry letter change / menu move", 50, "FM tick 1.2 kHz 30 ms"),
 ("ne_confirm", "", "name entry letter set / menu confirm", 150, "FM two-step blip 800>1200 Hz"),
 ("ne_done", "", "name entered / new high score", 900, "FM bell fanfare 5 notes, echo copy"),
]

def adpcm_a_bytes(n_samples):
    b = (n_samples + 1) // 2            # 4 bits per sample
    return (b + 255) // 256 * 256       # ADPCM-A sample addresses are in 256 byte units

def wav_bytes(path):
    if not os.path.exists(path):
        return None
    with wave.open(path, "rb") as w:
        assert w.getnchannels() == 1 and w.getframerate() == RATE, path + ": must be mono 18500 Hz"
        return adpcm_a_bytes(w.getnframes())

rows, total_new, total_plan = [], 0, 0
for name, old, event, ms, layers in FX:
    plan = adpcm_a_bytes(RATE * ms // 1000)
    total_plan += plan
    newb = wav_bytes(os.path.join(HERE, "new", name + ".wav"))
    oldb = wav_bytes(os.path.join(HERE, "old", old + ".wav")) if old else None
    total_new += newb or 0
    def audio(sub, n, b):
        return ('<audio controls preload="none" src="%s/%s.wav"></audio><div class="sz">%d bytes</div>' % (sub, n, b)) if b else '<span class="none">none</span>'
    rows.append("<tr><th>%s</th><td>%s</td><td>%s</td><td>%s</td><td class='num'>%d ms<br>%d bytes</td><td>%s</td></tr>" % (
        name, html.escape(event), audio("old", old, oldb), audio("new", name, newb) if newb else '<span class="none">not rendered yet</span>', ms, plan, html.escape(layers)))
assert total_plan <= BUDGET and total_new <= BUDGET, "over the 384 KB effect budget"
page = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gumbirds sound effects</title><style>
:root{--bg:#14171c;--fg:#e6e9ee;--dim:#98a2b3;--line:#2b313b;--acc:#6fd3a8}
@media (prefers-color-scheme: light){:root{--bg:#ffffff;--fg:#1b1f26;--dim:#5b6472;--line:#d9dee6;--acc:#0b7a52}}
body{background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif;margin:0;padding:16px}
h1{font-size:22px;margin:0 0 4px}p{color:var(--dim);margin:4px 0 14px;max-width:80ch}
.wrap{overflow-x:auto}table{border-collapse:collapse;width:100%%;min-width:900px}
th,td{border-bottom:1px solid var(--line);padding:8px;text-align:left;vertical-align:top}
thead th{color:var(--dim);font-weight:600}tbody th{color:var(--acc);white-space:nowrap}
.num{white-space:nowrap}.sz,.none{color:var(--dim);font-size:13px}audio{height:32px;width:220px}
</style></head><body><h1>Gumbirds sound effects: old and new</h1>
<p>%d effects planned. Planned size %d of %d bytes (%d%%). Rendered so far: %d bytes. ADPCM-A, 18.5 kHz, 4 bits per sample, 256 byte steps. All new effects are rendered offline by tools/make_sfx.py (own synthesis: FM, square and noise layers with mastering baked in); the Layers column is the design, the script is the exact recipe.</p>
<div class="wrap"><table><thead><tr><th>Effect</th><th>Game event</th><th>Old</th><th>New</th><th>Planned length and size</th><th>Layers</th></tr></thead>
<tbody>%s</tbody></table></div></body></html>""" % (len(FX), total_plan, BUDGET, total_plan * 100 // BUDGET, total_new, "\n".join(rows))
open(os.path.join(HERE, "index.html"), "w").write(page)
print("effects", len(FX), "planned bytes", total_plan, "rendered bytes", total_new, "budget", BUDGET)
