"""Quick look at a Xyce transient csv: python peek_csv.py <x.csv> <out.png> [t0_ns t1_ns]"""
import sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

import xycsv; d = xycsv.load(sys.argv[1])
cols = list(d); t = d["TIME"] * 1e9
m = np.ones(len(t), bool)
if len(sys.argv) > 4: m = (t >= float(sys.argv[3])) & (t <= float(sys.argv[4]))
fig, ax = plt.subplots(len(cols) - 1, 1, figsize=(10, 2.0 * (len(cols) - 1)), sharex=True)
for a, c in zip(ax, cols[1:]):
    a.plot(t[m], d[c][m], lw=0.8); a.set_ylabel(c, fontsize=7); a.grid(alpha=.3)
    print(f'{c:22s} first {d[c][m][0]: .5g} last {d[c][m][-1]: .5g} min {d[c][m].min(): .5g} max {d[c][m].max(): .5g}')
ax[-1].set_xlabel('t (ns)'); fig.tight_layout(); fig.savefig(sys.argv[2], dpi=90)
print('steps', m.sum(), 'dt min', np.diff(d['TIME'][m]).min())
