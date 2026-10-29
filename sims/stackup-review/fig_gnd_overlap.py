"""Where PGND faces GND (and VBUS faces GND) across a dielectric with nothing between, coloured by plate C density
(pF/mm2) in each stackup. Writes fig_gnd_overlap.png and prints per-region totals by layer pair."""
import os, sys, collections
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
R = np.load(os.path.join(HERE, 'raster.npz'))
ids = R['ids']; nets = ['VOID'] + list(R['nets']); p = float(R['pitch']); X0 = float(R['x0']); Y0 = float(R['y0'])
STACK = {
    'intended': [[(0.092, 4.1)], [(0.100, 4.6)], [(0.092, 4.1), (0.865, 4.6), (0.092, 4.1)], [(0.100, 4.6)], [(0.092, 4.1)]],
    'asbuilt': [[(0.100, 4.5)], [(0.535, 4.5)], [(0.100, 4.5)], [(0.535, 4.5)], [(0.100, 4.5)]]}
EF = {'intended': 4.3, 'asbuilt': 4.5}
def toe(s, i, j): return sum(t / e for k in range(i, j) for (t, e) in STACK[s][k]) + (j - i - 1) * 0.035 / EF[s]
cu = ids > 0
def pair_maps(na, nb, s):
    a, b = nets.index(na), nets.index(nb)
    out = {}
    for i in range(6):
        for j in range(i + 1, 6):
            m = cu[i] & cu[j]
            for k in range(i + 1, j): m &= ~cu[k]
            m &= ((ids[i] == a) & (ids[j] == b)) | ((ids[i] == b) & (ids[j] == a))
            if m.any(): out[(i + 1, j + 1)] = m * (8.854e-3 / toe(s, i, j))
    return out
ext = [X0, X0 + ids.shape[1] * p, Y0, Y0 + ids.shape[2] * p]
fig, axs = plt.subplots(2, 2, figsize=(12, 15))
outline = (ids.max(axis=0) > 0)
for col, (na, nb) in enumerate([('PGND', 'GND'), ('VBUS', 'GND')]):
    for row, s in enumerate(('intended', 'asbuilt')):
        ax = axs[row, col]
        maps = pair_maps(na, nb, s)
        dens = sum(maps.values())
        ax.imshow(outline.T, origin='lower', extent=ext, cmap='Greys', alpha=0.12)
        im = ax.imshow(np.ma.masked_where(dens <= 0, dens).T, origin='lower', extent=ext, cmap='inferno_r', norm=LogNorm(0.005, 0.5))
        tot = dens.sum() * p * p
        lab, n = ndi.label(ndi.binary_dilation(dens > 0, iterations=8))
        regs = []
        for k in range(1, n + 1):
            m = lab == k
            parts = {lp: float((mp * m).sum() * p * p) for lp, mp in maps.items() if (mp * m).sum() > 0}
            A = {lp: float(((mp > 0) & m).sum() * p * p) for lp, mp in maps.items()}
            if sum(parts.values()) < 0.3: continue
            cx, cy = [c.mean() for c in np.nonzero(m & (dens > 0))]
            txt = '\n'.join(f'L{a}-L{b} {A[(a, b)]:.0f} mm2 {c:.1f} pF' for (a, b), c in sorted(parts.items(), key=lambda kv: -kv[1]) if c >= 0.1)
            ax.annotate(txt, (X0 + cx * p, Y0 + cy * p), fontsize=6.5, color='navy', xytext=(8, 0), textcoords='offset points')
            regs.append((X0 + cx * p, Y0 + cy * p, txt.replace('\n', '; ')))
        ax.set_title(f'{s.upper()}: {na} facing {nb}, total {tot:.1f} pF (plate)', fontsize=10)
        ax.set_xlim(83, 118); ax.set_ylim(126, 75); ax.set_aspect('equal'); ax.grid(alpha=0.2)
        print(f'{s} {na}/{nb}: {tot:.2f} pF')
        for x, y, t in regs: print(f'   region near ({x:.1f},{y:.1f}): {t}')
for ref, x, y in (('NT1', 109.56, 103.95), ('NT3', 99.96, 112.71), ('J1', 105.90, 121.46), ('U3 MCU', 99.33, 113.88), ('U4', 108.28, 106.95)):
    for ax in axs.ravel():
        ax.plot(x, y, 'b+', ms=8); ax.annotate(ref, (x, y), fontsize=7, color='b', xytext=(3, -8), textcoords='offset points')
fig.colorbar(im, ax=axs, shrink=0.5, label='plate C density, pF/mm2')
plt.savefig(os.path.join(HERE, 'fig_gnd_overlap.png'), dpi=100, bbox_inches='tight')
