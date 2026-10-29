"""Query overlap_pairs.json. python query.py <regex> [min_fF=1]  (matches either net)
python query.py --sig [min_fF]  : signal-to-signal pairs only (no PGND/GND/AGND/VBUS/+5V/+3V3/+3V3A plane nets)"""
import os, sys, json, re
HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(HERE, 'overlap_pairs.json')))
PLANE = {'PGND', 'GND', 'AGND', 'VBUS'}
arg = sys.argv[1]; mn = float(sys.argv[2]) / 1000 if len(sys.argv) > 2 else 0.001
if arg == '--sig':
    sel = [r for r in rows if r['na'] not in PLANE and r['nb'] not in PLANE]
else:
    rx = re.compile(arg)
    sel = [r for r in rows if rx.search(r['na']) or rx.search(r['nb'])]
sel = [r for r in sel if max(r['c_int'], r['c_blt']) >= mn]
sel.sort(key=lambda r: -max(r['c_int'], r['c_blt']))
print(f"{'Li-Lj':6s} {'net A':24s} {'net B':24s} {'mm2':>7s} {'int fF':>8s} {'blt fF':>8s}  centroid")
for r in sel:
    print(f"L{r['li']}-L{r['lj']}  {r['na'][:24]:24s} {r['nb'][:24]:24s} {r['area']:7.3f} {r['c_int']*1e3:8.1f} {r['c_blt']*1e3:8.1f}  ({r['cx']:.1f},{r['cy']:.1f})")
