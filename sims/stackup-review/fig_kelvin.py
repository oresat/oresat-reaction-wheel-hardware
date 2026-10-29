"""Kelvin SNS+/- pairs (L3) over the L4/L5 keep-outs and the L6 SW pours. Writes fig_kelvin.png"""
import os, sys, pickle
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import box
HERE = os.path.dirname(os.path.abspath(__file__))
g = pickle.load(open(os.path.join(HERE, '..', 'bus-ring', 'geom.pkl'), 'rb'))
R = np.load(os.path.join(HERE, 'raster.npz'))
ids = R['ids']; nets = ['VOID'] + list(R['nets']); p = float(R['pitch']); X0 = float(R['x0']); Y0 = float(R['y0'])
win = (88, 118, 74, 100)
fig, axs = plt.subplots(1, 2, figsize=(16, 7.5))
def rgb_layer(k):
    img = np.ones(ids.shape[1:] + (3,))
    def put(name, col):
        if name in nets: img[ids[k] == nets.index(name)] = col
    put('PGND', (0.75, 0.82, 0.95)); put('AGND', (0.96, 0.88, 0.70)); put('VBUS', (0.95, 0.75, 0.75)); put('GND', (0.75, 0.9, 0.75))
    for n in nets:
        if 'SW' in n and 'SWFILT' not in n and 'SWD' not in n and 'SWO' not in n and 'SWC' not in n:
            img[ids[k] == nets.index(n)] = (0.55, 0.2, 0.55)
    return img
ext = [X0, X0 + ids.shape[1] * p, Y0, Y0 + ids.shape[2] * p]
for ax, (k, title) in zip(axs, [(3, 'L4 (In3) copper: white = keep-out; Kelvin pairs (L3) on top'), (5, 'L6 (B.Cu): SW pours (purple); Kelvin pairs (L3) on top')]):
    img = rgb_layer(k)
    if k == 3:
        # mark L5 voids too (hatched grey where both L4 and L5 are void)
        both = (ids[3] == 0) & (ids[4] == 0)
        img[both] = (0.85, 0.85, 0.85)
    ax.imshow(np.transpose(img, (1, 0, 2)), origin='lower', extent=ext)
    for t in g['tracks']:
        if t['layer'] == 'In2.Cu' and 'Phase' in t['net'] and 'SNS' in t['net']:
            xs, ys = t['line'].xy
            col = {'A': 'm', 'B': 'c', 'C': 'orange'}[t['net'].split('/')[1][-1]]
            ax.plot(xs, ys, '-', color=col, lw=1.4)
        if t['layer'] == 'In2.Cu' and t['net'] in ('/PHA_ISNS', '/PHA_VSNS', '+VREF', '+3V3A'):
            xs, ys = t['line'].xy; ax.plot(xs, ys, '-', color='k', lw=0.4)
    ax.set_xlim(win[0], win[1]); ax.set_ylim(win[3], win[2]); ax.set_aspect('equal'); ax.set_title(title, fontsize=10)
    ax.grid(alpha=0.3)
axs[0].text(89, 99, 'grey = L4 and L5 both void (pair sees L6 through the hole)', fontsize=8)
plt.tight_layout(); plt.savefig(os.path.join(HERE, 'fig_kelvin.png'), dpi=110)
print('ok')
