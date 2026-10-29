"""Median / 90th percentile |K| (A/mm) per layer and net in a box, per scenario. python check_k.py <stack> <x0> <x1> <y0> <y1>"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); BR = os.path.join(os.path.dirname(HERE), 'bus-ring')
st = sys.argv[1]; bx0, bx1, by0, by1 = map(float, sys.argv[2:6])
S = np.load(os.path.join(HERE, 'products', st, 'scen.npz')); meta = json.load(open(os.path.join(BR, 'mp', st, 'meta.json')))
lab = np.load(os.path.join(BR, 'mp', st, 'labels.npz'))['lab']; x0, y0 = meta['crop'][:2]; p = meta['pitch']
order = list(S['order']); LN = {'F.Cu': 'L1', 'In1.Cu': 'L2', 'In2.Cu': 'L3', 'In3.Cu': 'L4', 'In4.Cu': 'L5', 'B.Cu': 'L6'}
i0, i1, j0, j1 = int((bx0 - x0) / p), int((bx1 - x0) / p), int((by0 - y0) / p), int((by1 - y0) / p)
for nm in ('BULK_L_dc', 'BULK_L_10M'):
    K = S['K'][list(S['names']).index(nm)]
    row = []
    for k, L in enumerate(order):
        z0, z1 = meta['zlay'][L]; c = lab[i0:i1, j0:j1, z0:z1].max(2)
        km = np.sqrt(np.abs(K[k, 0, i0:i1, j0:j1]) ** 2 + np.abs(K[k, 1, i0:i1, j0:j1]) ** 2) * 1e-3
        for net, codes in (('V', (1, 3)), ('G', (2, 4))):
            m = np.isin(c, codes)
            if m.sum() > 50: row.append(f'{LN[L]}{net} med {np.median(km[m]):.4f} p90 {np.percentile(km[m], 90):.4f}')
    print(nm, ' | '.join(row))
