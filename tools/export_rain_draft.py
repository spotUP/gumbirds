#!/usr/bin/env python3
"""One-off export of the owner-approved storm rain draft v3 (thoughts/shared/drafts/2026-11-20-rain-v3/draw_rain_v3.py) to
assets/rain/rain_data.json: the hand-typed grids and tables exactly as drawn. Code here only runs the draft's own cut() over
the loop to list which tile cells each (kind, x phase, y phase) uses; it draws and invents nothing.
Usage: python3.14 -I tools/export_rain_draft.py <draft v3 dir> assets/rain/rain_data.json   (needs numpy, PIL)"""
import json, sys
sys.dont_write_bytecode = True
src, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, src)
import draw_rain_v3 as D

for m in ('arena', 'trip', 'stadium'):
    for _ in D.sim('heavy', m, range(D.LOOP), scroll=0.75 if m == 'trip' else 0.0, islands=D.BF.ISLANDS if m == 'arena' else ()):
        pass
assert len(D.TILES) == 60, len(D.TILES)
ids = {t: i for t, (i, _) in D.TILES.items()}
kinds = [('far', 'lull'), ('far', 'steady'), ('far', 'gale'), ('near', 'lull'), ('near', 'steady'), ('near', 'gale')]
cuts = []
for k in sorted(D.CUTS, key=lambda q: (kinds.index(q[0]), q[1], q[2])):
    cuts.append([kinds.index(k[0]), k[1], k[2], [[dc, dr, ids[t]] for dc, dr, t in D.CUTS[k]]])
json.dump(dict(
    palette={k: list(v) for k, v in D.PAL.items()}, burst_palette={k: list(v) for k, v in D.BURST.items()}, key_order='HBTFe',
    tiles=[list(t) for t, _ in sorted(D.TILES.items(), key=lambda q: q[1][0])], kinds=['%s %s' % k for k in kinds],
    move=[list(D.MOVE[k]) for k in kinds], streak_height=[len(D.STREAK[k]) for k in kinds], cuts=cuts,
    spawn={'%s %s %s' % k: [list(e) for e in v] for k, v in D.SPAWN.items()},
    burst_spawn=[list(e) for e in D.BURST_SPAWN], gusts=[list(g) for g in D.GUSTS], loop=D.LOOP, tab=D.TAB, near_tab=D.NEAR_TAB,
    hud_rows={m: sorted(v) for m, v in D.R1.HUD_ROWS.items()}, flash0=D.FLASH0), open(out, 'w'), separators=(',', ':'))
print('[OK] %d tiles, %d cuts' % (len(D.TILES), len(cuts)))
