"""Analog bundle (L3) near the MCU and the regulator corner, over L4 (as built, 0.1 mm) and L2 (intended, 0.1 mm).
Marks regulator parts, net ties, the U4 input caps. Writes fig_bundle_mcu.png"""
import os, sys, pickle
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
BR = os.path.join(HERE, '..', 'bus-ring'); sys.path.insert(0, BR)
import build3d as b3
g = b3.g
R = np.load(os.path.join(HERE, 'raster.npz'))
ids = R['ids']; nets = ['VOID'] + list(R['nets']); p = float(R['pitch']); X0 = float(R['x0']); Y0 = float(R['y0'])
fps = b3.footprints()
ANA = {'/PHA_ISNS', '/PHB_ISNS', '/PHC_ISNS', '/PHA_VSNS', '/PHB_VSNS', '/PHC_VSNS', '+VREF', '+3V3A'}
COL = {'PGND': (0.75, 0.82, 0.95), 'AGND': (0.96, 0.88, 0.70), 'VBUS': (0.95, 0.72, 0.72), 'GND': (0.72, 0.9, 0.72)}
def img_for(k):
    img = np.ones(ids.shape[1:] + (3,))
    for n, c in COL.items():
        if n in nets: img[ids[k] == nets.index(n)] = c
    other = (ids[k] > 0)
    for n in COL:
        if n in nets: other &= ids[k] != nets.index(n)
    img[other] = (0.55, 0.55, 0.55)
    return img
ext = [X0, X0 + ids.shape[1] * p, Y0, Y0 + ids.shape[2] * p]
win = (94, 118, 100, 118)
fig, axs = plt.subplots(1, 2, figsize=(17, 7))
for ax, (k, title) in zip(axs, [(1, 'INTENDED: L3 analog bundle over L2 (0.1 mm)'), (3, 'AS BUILT: L3 analog bundle over L4 (0.1 mm)')]):
    ax.imshow(np.transpose(img_for(k), (1, 0, 2)), origin='lower', extent=ext)
    for t in g['tracks']:
        if t['layer'] == 'In2.Cu' and t['net'] in ANA:
            xs, ys = t['line'].xy; ax.plot(xs, ys, '-', color='k', lw=1.0)
        if t['layer'] == 'In2.Cu' and t['net'] == 'VBUS' and t['w'] < 0.4:
            xs, ys = t['line'].xy; ax.plot(xs, ys, '-', color='r', lw=1.2)
    for ref in ('U4', 'U14', 'L1', 'L2', 'NT1', 'NT2', 'NT3', 'NT4', 'C4', 'C5', 'C86', 'U3', 'U5', 'U7', 'C88', 'C12', 'C87', 'C15', 'C21'):
        f = fps[ref]; ax.plot(f['x'], f['y'], 'x' if f['layer'] == 'F.Cu' else '+', color='purple', ms=7)
        ax.annotate(ref, (f['x'], f['y']), fontsize=7, color='purple', xytext=(2, 2), textcoords='offset points')
    ax.set_xlim(win[0], win[1]); ax.set_ylim(win[3], win[2]); ax.set_aspect('equal'); ax.set_title(title, fontsize=10); ax.grid(alpha=0.3)
axs[1].text(94.3, 117.6, 'green GND, tan AGND, pink VBUS, blue PGND, grey other nets; black = L3 analog traces; red = thin L3 VBUS trace; x = top part, + = bottom part', fontsize=7)
plt.tight_layout(); plt.savefig(os.path.join(HERE, 'fig_bundle_mcu.png'), dpi=110)
print('ok')
