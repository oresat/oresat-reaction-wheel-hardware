"""Compare the Xyce AC run of the exported bus (mk_tb.py ac) with ac_bus.Bus at the same fixed R.
python cmp_ac.py <stack_root> <stack> <vbias> <xyce ac csv (.FD.csv)> [--fr 1e7]"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ac_bus as ab

ap = argparse.ArgumentParser(); ap.add_argument('stack_root'); ap.add_argument('stack'); ap.add_argument('vbias', type=float)
ap.add_argument('csv'); ap.add_argument('--fr', type=float, default=1e7)
a = ap.parse_args()
d = np.genfromtxt(a.csv, names=True, skip_footer=1)
cols = d.dtype.names
f = d[cols[0]] if 'FREQ' in cols[0].upper() else d['FREQ']
c = lambda pre: [n for n in cols if n.upper().startswith(pre)]
xs = {}
pairs = {'zdev': ('VRDEVC_V', 'VIDEVC_V'), 'P105': ('VRP105_VP105_G', 'VIP105_VP105_G'), 'P110': ('VRP110_VP110_G', 'VIP110_VP110_G'), 'HI': ('IRVFS', 'IIVFS')}
up = {n.upper(): n for n in cols}
for k, (r, i) in pairs.items():
    xs[k] = d[up[r]] + 1j * d[up[i]]
xs['zdev'] = -xs['zdev']
bus = ab.Bus(a.stack_root, a.stack, 'C', a.vbias, fr=a.fr)
zdev, H, HI = bus.solve(f)
py = {'zdev': zdev, 'P105': H['P105'], 'P110': H['P110'], 'HI': HI}
for k in pairs:
    err = np.abs(xs[k] - py[k]) / np.maximum(np.abs(py[k]), 1e-12)
    print(f'{k:5s}: max rel diff {err.max():.2e} (at {f[np.argmax(err)] / 1e6:.3g} MHz), median {np.median(err):.2e}')
bus_f = ab.Bus(a.stack_root, a.stack, 'C', a.vbias, fr=None)
z2, H2, _ = bus_f.solve(f)
for k, x, y in (('zdev', zdev, z2), ('P105', H['P105'], H2['P105'])):
    r = np.abs(x) / np.abs(y)
    print(f'fixed R at {a.fr / 1e6:g} MHz vs R(f): |{k}| ratio min {r.min():.3f} max {r.max():.3f}')
