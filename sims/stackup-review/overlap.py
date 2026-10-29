"""Cross-net plate overlaps between facing copper (nothing in between), both stackups.
Column model: at each pixel, consecutive copper layers (voids between are skipped) form a plate capacitor
C = eps0 * A / sum(t/eps). No fringing. Writes overlap_pairs.json and prints tables.
python overlap.py [min_pF=0.5]"""
import os, sys, json, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
R = np.load(os.path.join(HERE, 'raster.npz'))
ids = R['ids']; nets = ['<void>'] + list(R['nets']); p = float(R['pitch'])
A_px = p * p
CU_T = 0.035
# per gap: list of (t_mm, eps)
STACK = {
    'intended': [[(0.092, 4.1)], [(0.100, 4.6)], [(0.092, 4.1), (0.865, 4.6), (0.092, 4.1)], [(0.100, 4.6)], [(0.092, 4.1)]],
    'asbuilt': [[(0.100, 4.5)], [(0.535, 4.5)], [(0.100, 4.5)], [(0.535, 4.5)], [(0.100, 4.5)]],
}
EPS_FILL = {'intended': 4.3, 'asbuilt': 4.5}
def t_over_e(stack, i, j):
    s = sum(t / e for k in range(i, j) for (t, e) in STACK[stack][k])
    s += (j - i - 1) * CU_T / EPS_FILL[stack]
    return s
E0 = 8.854e-3  # pF/mm * mm2/mm -> eps0 in pF/mm
cu = ids > 0
area = collections.defaultdict(float)  # (i, j, na, nb) -> mm2 (unordered net pair, ordered layers)
loc = collections.defaultdict(lambda: [0.0, 0.0])
X0, Y0 = float(R['x0']), float(R['y0'])
nxp, nyp = ids.shape[1:]
xx = X0 + (np.arange(nxp) + 0.5) * p; yy = Y0 + (np.arange(nyp) + 0.5) * p
for i in range(6):
    for j in range(i + 1, 6):
        m = cu[i] & cu[j]
        for k in range(i + 1, j): m &= ~cu[k]
        if not m.any(): continue
        a = ids[i][m]; b = ids[j][m]
        diff = a != b
        a, b = a[diff], b[diff]
        ix, iy = np.nonzero(m); ix, iy = ix[diff], iy[diff]
        key = a.astype(np.int64) * 10000 + b
        uk, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
        sx = np.bincount(inv, weights=xx[ix]); sy = np.bincount(inv, weights=yy[iy])
        for kk, c, sxx, syy in zip(uk, cnt, sx, sy):
            na, nb = nets[kk // 10000], nets[kk % 10000]
            area[(i, j, na, nb)] += c * A_px
            loc[(i, j, na, nb)] = [sxx / c, syy / c]
rows = []
for (i, j, na, nb), A in area.items():
    ci = E0 * A / t_over_e('intended', i, j); cb = E0 * A / t_over_e('asbuilt', i, j)
    rows.append(dict(li=i + 1, lj=j + 1, na=na, nb=nb, area=A, c_int=ci, c_blt=cb, cx=loc[(i, j, na, nb)][0], cy=loc[(i, j, na, nb)][1]))
json.dump(rows, open(os.path.join(HERE, 'overlap_pairs.json'), 'w'), indent=0)
# aggregate by unordered net pair over all layer pairs
agg = collections.defaultdict(lambda: dict(ci=0, cb=0, A=0, where=[]))
for r in rows:
    k = tuple(sorted((r['na'], r['nb'])))
    agg[k]['ci'] += r['c_int']; agg[k]['cb'] += r['c_blt']; agg[k]['A'] += r['area']
    agg[k]['where'].append((r['li'], r['lj'], r['area'], r['c_int'], r['c_blt']))
minp = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
print(f"{'net A':22s} {'net B':22s} {'C int pF':>9s} {'C blt pF':>9s} {'ratio':>6s}  per layer pair (Li-Lj: mm2, int->blt pF)")
for k, v in sorted(agg.items(), key=lambda kv: -max(kv[1]['ci'], kv[1]['cb'])):
    if max(v['ci'], v['cb']) < minp: continue
    w = sorted(v['where'], key=lambda t: -max(t[3], t[4]))[:4]
    ws = '; '.join(f"L{a}-L{b}: {A:.1f} mm2 {ci:.1f}->{cb:.1f}" for a, b, A, ci, cb in w)
    print(f"{k[0][:22]:22s} {k[1][:22]:22s} {v['ci']:9.2f} {v['cb']:9.2f} {v['cb'] / max(v['ci'], 1e-9):6.2f}  {ws}")
