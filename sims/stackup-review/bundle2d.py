"""2D cut across the analog bundle: per-mm capacitance of each analog trace to every other conductor, both stackups.
python bundle2d.py <axis y|x> <c0> <a0> <a1> [hmin]
axis y: horizontal cut at y=c0 along x in [a0,a1];  axis x: vertical cut at x=c0 along y in [a0,a1]."""
import os, sys, json, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
BR = os.path.abspath(os.path.join(HERE, '..', 'bus-ring'))
os.chdir(BR); sys.path.insert(0, BR)
from fd2d import STACKS, build, maxwell
from xsec import cut
os.chdir(HERE)
ax = sys.argv[1]; c0, a0, a1 = map(float, sys.argv[2:5]); hmin = float(sys.argv[5]) if len(sys.argv) > 5 else 0.005
ANA = ['/PHA_ISNS', '/PHB_ISNS', '/PHC_ISNS', '/PHA_VSNS', '/PHB_VSNS', '/PHC_VSNS', '+VREF', '+3V3A']
iv, vias = cut(ax, c0, a0, a1)
for L in ('In1.Cu', 'In2.Cu', 'In3.Cu', 'In4.Cu'):
    print(L, ' '.join(f"{n}[{','.join(f'{a:.2f}-{b:.2f}' for a, b in v)}]" for n, v in sorted(iv[L].items(), key=lambda kv: kv[1][0][0])))
blo, bhi = (a0, a1)
out = {'cut': [ax, c0, a0, a1]}
for sn in ('intended', 'asbuilt'):
    t = time.time()
    G = build(iv, STACKS[sn], a0, a1, blo, bhi, air=3, hmin_u=hmin, hmin_z=hmin)
    C, _, _ = maxwell(G)
    nets = G['nets']; ic = {n: i for i, n in enumerate(nets)}
    res = {}
    for n in ANA:
        if n not in ic: continue
        j = ic[n]
        row = {m: -C[j, ic[m]] * 1e12 for m in nets if m != n}   # fF/mm (C in F/m -> *1e12 fF/mm)
        res[n] = dict(Ctot=C[j, j] * 1e12, **{k: v for k, v in sorted(row.items(), key=lambda kv: -kv[1]) if v > 0.05})
    out[sn] = res
    print(sn, 'grid', G['eps'].shape, round(time.time() - t, 1), 's', file=sys.stderr)
json.dump(out, open(os.path.join(HERE, f'bundle2d_{ax}{c0:g}.json'), 'w'), indent=1)
for sn in ('intended', 'asbuilt'):
    print('==', sn, '(fF/mm)')
    for n, r in out[sn].items():
        print(f"  {n:10s} Ctot {r['Ctot']:6.1f} | " + ', '.join(f"{k} {v:.2f}" for k, v in r.items() if k != 'Ctot'))
