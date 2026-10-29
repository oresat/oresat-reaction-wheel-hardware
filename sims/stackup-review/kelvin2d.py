"""2D quasi-static cut across the Kelvin pairs where they run parallel to the SW pours (current along y).
DM mutual from each SW pour into each Kelvin pair: M_dm = L[SW,SNS+] - L[SW,SNS-] (PGND = return, TEM limit).
Also CM C from each SW pour to each trace, both stackups.
python kelvin2d.py <y_cut> [x0 x1] [hmin]"""
import os, sys, json, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
BR = os.path.abspath(os.path.join(HERE, '..', 'bus-ring'))
os.chdir(BR); sys.path.insert(0, BR)
from fd2d import STACKS, build, maxwell, reduce_ref, MU0, EPS0
from xsec import cut
os.chdir(HERE)
y = float(sys.argv[1]); x0 = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0; x1 = float(sys.argv[3]) if len(sys.argv) > 3 else 112.0
hmin = float(sys.argv[4]) if len(sys.argv) > 4 else 0.01
iv, vias = cut('y', y, x0, x1)
# drop tiny slivers of signal copper we do not care about; keep everything (all nets become conductors)
out = {'y': y, 'x0': x0, 'x1': x1, 'hmin': hmin}
for L in iv:
    for n, ivs in iv[L].items():
        if 'SNS' in n or 'SW' in n: print(L, n, [(round(a, 3), round(b, 3)) for a, b in ivs])
for sn in ('intended', 'asbuilt'):
    t = time.time()
    G = build(iv, STACKS[sn], x0, x1, x0, x1, air=3, hmin_u=hmin, hmin_z=min(hmin, 0.005), hmax_u=0.05)
    C, _, _ = maxwell(G)
    G0 = build(iv, STACKS[sn], x0, x1, x0, x1, air=3, hmin_u=hmin, hmin_z=min(hmin, 0.005), hmax_u=0.05, vacuum=True)
    C0, _, _ = maxwell(G0)
    nets = G['nets']
    C0r, nr = reduce_ref(C0, nets, 'PGND')
    Lm = MU0 * EPS0 * np.linalg.inv(C0r)  # H/m
    il = {n: i for i, n in enumerate(nr)}; ic = {n: i for i, n in enumerate(nets)}
    sw = [n for n in nr if n.endswith('_SW') or n.endswith('/SW')]
    res = {}
    for ph in 'ABC':
        p, m = f'/Phase {ph}/SNS+', f'/Phase {ph}/SNS-'
        if p not in il or m not in il: continue
        Ldm = Lm[il[p], il[p]] + Lm[il[m], il[m]] - 2 * Lm[il[p], il[m]]
        r = {'Ldm_pH_mm': Ldm * 1e9}
        for s in sw:
            r[f'Mdm_{s}_pH_mm'] = (Lm[il[s], il[p]] - Lm[il[s], il[m]]) * 1e9
            r[f'Mcm_{s}_pH_mm'] = 0.5 * (Lm[il[s], il[p]] + Lm[il[s], il[m]]) * 1e9
            r[f'C_{s}_to+_fF_mm'] = -C[ic[s], ic[p]] * 1e12
            r[f'C_{s}_to-_fF_mm'] = -C[ic[s], ic[m]] * 1e12
        r['Cself+_fF_mm'] = C[ic[p], ic[p]] * 1e12
        res[ph] = r
    out[sn] = res
    print(sn, 'grid', G['eps'].shape, round(time.time() - t, 1), 's', file=sys.stderr)
json.dump(out, open(os.path.join(HERE, f'kelvin2d_y{y:g}.json'), 'w'), indent=1)
for sn in ('intended', 'asbuilt'):
    print('==', sn)
    for ph, r in out[sn].items():
        print(' ', ph, ', '.join(f'{k} {v:.3g}' for k, v in r.items()))
