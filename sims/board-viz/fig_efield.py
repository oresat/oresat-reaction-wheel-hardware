"""2D electrostatic E-field cross-sections (fd2d finite-volume Laplace, dielectrics included), both stackups.
VBUS at 1 V, every other net at 0 V; |E| in V/mm per volt of VBUS, log scale, with field lines.
python fig_efield.py <outdir>   (writes e_<cut>_<stack>.png and e_cuts.json)"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); BR = os.path.join(os.path.dirname(HERE), 'bus-ring')
OUT = os.path.abspath(sys.argv[1]); os.makedirs(OUT, exist_ok=True)
os.chdir(BR); sys.path.insert(0, BR)                   # xsec.py reads geom.pkl / pcb.pkl from the cwd
from fd2d import STACKS, build, maxwell
from xsec import cut
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import LogNorm, LinearSegmentedColormap
from scipy.interpolate import RegularGridInterpolator

BG = '#0b0d10'
NETC = {'VBUS': '#ff5d50', 'PGND': '#5b8fe0', 'GND': '#8c94a8', 'AGND': '#e2a93f'}
ANALOG = ('/PHA_ISNS', '/PHB_ISNS', '/PHC_ISNS', '/PHA_VSNS', '/PHB_VSNS', '/PHC_VSNS', '+VREF', '+3V3A')
cmap = LinearSegmentedColormap.from_list('e', ['#0b0d10', '#14324a', '#1f6f8b', '#3fb0a5', '#b8e986', '#fffbd5'])
CUTS = {'bundle_y105': dict(axis='y', c0=105.0, a0=108.0, a1=120.0, blo=108.0, bhi=117.497, view=(110.8, 117.8)),
        'band_x104': dict(axis='x', c0=104.08, a0=86.0, a1=103.0, blo=86.0, bhi=103.0, view=(88.0, 101.0))}


def netcolor(n):
    if n in NETC: return NETC[n]
    if n in ANALOG: return '#39ff6a'
    return '#6d727b'


def render(name, cfg, stack, zscale=2.0):
    iv, _ = cut(cfg['axis'], cfg['c0'], cfg['a0'], cfg['a1'])
    piv = {L: {f'{n}@{L}': v for n, v in d.items()} for L, d in iv.items()}
    G = build(piv, STACKS[stack], cfg['a0'], cfg['a1'], cfg['blo'], cfg['bhi'], air=3)
    C, V, (fidx, free) = maxwell(G)
    cols = [i for i, p in enumerate(G['nets']) if p.startswith('VBUS@')]
    phi = np.zeros(G['eps'].shape); phi[free] = V[:, cols].sum(1); phi[np.isin(G['cond'], cols)] = 1.0
    uc, zc = G['uc'], G['zc']
    u = np.linspace(cfg['view'][0], cfg['view'][1], 900); zt = G['ztot']; z = np.linspace(-0.12, zt + 0.12, 300)
    f = RegularGridInterpolator((uc, zc), phi, bounds_error=False, fill_value=0)
    U, Zg = np.meshgrid(u, z, indexing='ij'); P = f(np.stack([U, Zg], -1))
    Eu = -np.gradient(P, u, axis=0); Ez = -np.gradient(P, z, axis=1); Em = np.hypot(Eu, Ez)
    incu = np.zeros_like(P, bool)
    for Lname, z0, z1, kind, e in G['layers']:
        if kind != 'cu': continue
        for net, ivs in iv.get(Lname, {}).items():
            for a, b in ivs: incu |= (U >= a) & (U <= b) & (Zg >= z0) & (Zg <= z1)
    Em[incu] = np.nan
    w = (cfg['view'][1] - cfg['view'][0]); h = (zt + 0.24) * zscale
    fig = plt.figure(figsize=(10, max(2.2, 10 * h / w) + 0.2), dpi=170, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor(BG)
    ax.pcolormesh(u, z * zscale, Em.T, cmap=cmap, norm=LogNorm(1e-2, 30), shading='auto', rasterized=True)
    ax.streamplot(u, z * zscale, Eu.T, (Ez * zscale).T, color=(1, 1, 1, 0.33), density=2.2, linewidth=0.45, arrowsize=0.5)
    for Lname, z0, z1, kind, e in G['layers']:
        if kind != 'cu': continue
        for net, ivs in iv.get(Lname, {}).items():
            for a, b in ivs:
                ax.add_patch(Rectangle((a, z0 * zscale), b - a, (z1 - z0) * zscale, fc=netcolor(net), ec='none', alpha=0.95))
    LN = {'F.Cu': 'L1', 'In1.Cu': 'L2', 'In2.Cu': 'L3', 'In3.Cu': 'L4', 'In4.Cu': 'L5', 'B.Cu': 'L6'}
    for Lname, z0, z1, kind, e in G['layers']:
        if kind == 'cu':
            ax.text(cfg['view'][0] + 0.012 * w, (z0 + z1) / 2 * zscale, LN[Lname], color='#ebe9e3', fontsize=8, va='center', ha='left',
                    fontfamily='monospace', bbox=dict(fc=BG, ec='none', alpha=0.7, pad=1.2))
    ax.set_xlim(*cfg['view']); ax.set_ylim(-0.12 * zscale, (zt + 0.12) * zscale); ax.axis('off')
    fn = os.path.join(OUT, f'e_{name}_{stack}.png'); fig.savefig(fn, facecolor=BG); plt.close(fig)
    layz = {Ln: [round(z0, 4), round(z1, 4)] for Ln, z0, z1, k, e in G['layers'] if k == 'cu'}
    return dict(file=os.path.basename(fn), ztot=zt, zscale=zscale, view=cfg['view'], layers_z=layz,
                nets={Ln: sorted(d) for Ln, d in iv.items()})


meta = {}
for name, cfg in CUTS.items():
    for stack in ('intended', 'asbuilt'):
        meta[f'{name}_{stack}'] = render(name, cfg, stack); print(name, stack, 'ok', flush=True)
json.dump(meta, open(os.path.join(OUT, 'e_cuts.json'), 'w'), indent=1)
