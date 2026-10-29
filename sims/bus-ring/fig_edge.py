"""Edge figure: VBUS at the feed probes (mean of P105/P110), feed current and sense-node pickup around the HS
turn-on command, for several cases. python fig_edge.py <out.png> <tag>[:label] [...]"""
import json, os, sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
out = sys.argv[1]; cases = [a.split(':', 1) + [None] for a in sys.argv[2:]]
fig, ax = plt.subplots(4, 2, figsize=(14, 13))
for k, (tag, lab, *_) in enumerate(cases):
    lab = lab or tag
    z = np.load(os.path.join(R, tag + '.npz')); pk = np.load(os.path.join(R, tag + '_pk.npz'))
    t = z['t']; te = float(z['t_on']); tc = (t - te) * 1e9
    v = 0.5 * (z['wav_P105'] + z['wav_P110']); v = v - v[(tc > -30) & (tc < 0)].mean()
    i = z['ifeed'] - z['ifeed'][(tc > -30) & (tc < 0)].mean()
    for col, (a, b) in enumerate(((-10, 120), (-100, 3000))):
        m = (tc > a) & (tc < b)
        ax[0, col].plot(tc[m], v[m] * 1e3, lw=.8, label=lab)
        ax[1, col].plot(tc[m], i[m], lw=.8, label=lab)
        ax[2, col].plot(tc[m], pk['vsns'][m] * 1e3, lw=.8, label=lab)
        ax[3, col].plot(tc[m], pk['emf_hi'][m] * 1e3, lw=.8, label=lab + ' (M high)')
for col in (0, 1):
    for r, yl in enumerate(('VBUS at feed, AC (mV)', 'feed current, AC (A)', 'VSNS node pickup (mV)', 'feed->trace EMF (mV)')):
        ax[r, col].set_ylabel(yl); ax[r, col].grid(alpha=.3); ax[r, col].legend(fontsize=7)
    ax[3, col].set_xlabel('t from HI rising (HS turn-on command), ns')
fig.tight_layout(); fig.savefig(out, dpi=100)
