"""Render the PEEC field products (remote/post_fields.py) for the pages.

usage: python render_fields.py <stack> [--frames]
reads products/<stack>/{scen,frames,bslices}.npz and ../bus-ring/mp/<stack>/{labels.npz,meta.json}; writes fig/<stack>/

Plan views look down from the top (KiCad orientation, y down). Color: VBUS copper warm, PGND copper cool, brightness
= log10 |K| (sheet current, A/mm) on a fixed scale per figure set. Where outgoing (VBUS) and return (PGND) current
stack over each other in plan view the two colors add towards white.
"""
import argparse, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); BR = os.path.join(os.path.dirname(HERE), 'bus-ring')
sys.path.insert(0, BR)
from PIL import Image
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

BG = np.array([0.031, 0.035, 0.047])
WARM = np.array([1.00, 0.42, 0.16]); COOL = np.array([0.16, 0.58, 1.00])
LN = {'F.Cu': 'L1', 'In1.Cu': 'L2', 'In2.Cu': 'L3', 'In3.Cu': 'L4', 'In4.Cu': 'L5', 'B.Cu': 'L6'}
BMAP = LinearSegmentedColormap.from_list('b', ['#08090c', '#2a1458', '#6a1fa0', '#c2389a', '#f08a5d', '#fff2c8'])
VMAP = LinearSegmentedColormap.from_list('v', ['#4aa8ff', '#16324d', '#08090c', '#5a2410', '#ff7a3d'])

ap = argparse.ArgumentParser(); ap.add_argument('stack'); ap.add_argument('--frames', action='store_true'); a = ap.parse_args()
P = os.path.join(HERE, 'products', a.stack); OUT = os.path.join(HERE, 'fig', a.stack); os.makedirs(OUT, exist_ok=True)
meta = json.load(open(os.path.join(BR, 'mp', a.stack, 'meta.json')))
lab = np.load(os.path.join(BR, 'mp', a.stack, 'labels.npz'))['lab']
x0, y0, x1, y1 = meta['crop']; p = meta['pitch']; nx, ny = lab.shape[:2]
code_net = {1: 1, 3: 1, 2: 2, 4: 2}
for t, v in meta['terminals'].items(): code_net[v['code']] = 1 if v['net'] == 'VBUS' else 2
S = np.load(os.path.join(P, 'scen.npz'))
order = list(S['order']); nl = len(order)
netmap = np.zeros((nl, nx, ny), np.int8)
for k, L in enumerate(order):
    z0, z1 = meta['zlay'][L]; c = lab[:, :, z0:z1].max(2)
    for code, net in code_net.items(): netmap[k][c == code] = net

# ---- board context: footprints of the legs and banks
import build3d as b3
FP = b3.footprints()
from build_mp import LEGS, BANKS
CTX = [(ref, 'leg ' + leg) for leg, ref in LEGS.items()] + [(r, None) for refs in BANKS.values() for r in refs]
LABELS = {'leg A': None, 'leg B': None, 'leg C': None}


def context(ax, labels=True, color='#d9d4c7'):
    for ref, name in CTX:
        f = FP.get(ref)
        if f is None: continue
        polys = [pd['poly'] for pd in f['pads']]
        xs = [c for pg in polys for c in pg.exterior.xy[0]]; ys = [c for pg in polys for c in pg.exterior.xy[1]]
        bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
        ax.plot([bx0, bx1, bx1, bx0, bx0], [by0, by0, by1, by1, by0], color=color, lw=0.5, alpha=0.55)
        if labels and name: ax.text(bx0, by0 - 0.35, name, color=color, fontsize=7, alpha=0.85, fontfamily='monospace')
    if labels:
        for bank, txt in (('BULK_L', 'bulk L'), ('BULK_R', 'bulk R')):
            refs = BANKS[bank]; xs = [FP[r]['x'] for r in refs]; ys = [FP[r]['y'] for r in refs]
            ax.text(min(xs) - 0.5, max(ys) + 1.6, txt, color=color, fontsize=7, alpha=0.85, fontfamily='monospace')
        ax.text(116.6, 112.4, 'feed\n→ J1', color=color, fontsize=7, alpha=0.85, fontfamily='monospace', ha='right', va='bottom')


def bright(kmag, lo, hi):
    with np.errstate(divide='ignore'):
        return np.clip((np.log10(np.maximum(kmag, 1e-12)) - np.log10(lo)) / (np.log10(hi) - np.log10(lo)), 0, 1)


def rgb_layers(K, layers, lo, hi, tint=0.10):
    """K (nl, 2, nx, ny) real or complex A/m -> RGB (ny, nx, 3) for the chosen layers, VBUS warm, PGND cool, added."""
    img = np.zeros((nx, ny, 3)); base = np.zeros((nx, ny, 3))
    for k in layers:
        kmag = np.sqrt(np.abs(K[k, 0]) ** 2 + np.abs(K[k, 1]) ** 2) * 1e-3     # A/mm
        b = bright(kmag, lo, hi)
        for net, col in ((1, WARM), (2, COOL)):
            m = netmap[k] == net
            img[m] += b[m][:, None] * col[None, :]; base[m] = np.maximum(base[m], tint * col)
    out = BG + base * 0.6 + img
    return np.clip(out, 0, 1).transpose(1, 0, 2)


def save_plan(rgb, fn, title=None, labels=True, scale_note=None, streams=None):
    w = x1 - x0; h = y1 - y0
    fig = plt.figure(figsize=(8.0, 8.0 * h / w), dpi=150, facecolor='#08090c')
    ax = fig.add_axes([0, 0, 1, 1]); ax.imshow(rgb, extent=[x0, x1, y1, y0], interpolation='bilinear')
    if streams is not None:
        X = x0 + (np.arange(nx) + 0.5) * p; Y = y0 + (np.arange(ny) + 0.5) * p
        for (U, V, col) in streams:
            mag = np.hypot(U, V); lw = 0.25 + 1.2 * bright(mag, mag.max() * 1e-2, mag.max())
            ax.streamplot(X, Y, U.T, V.T, color=col, density=1.6, linewidth=lw.T, arrowsize=0.45, broken_streamlines=True)
    context(ax, labels)
    ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.axis('off')
    fig.savefig(fn, facecolor='#08090c'); plt.close(fig)


def net_total(K, net):
    m = (netmap == net)[:, None]
    return (K * m).sum(0)                                   # (2, nx, ny)


# ---- scenarios
names = list(S['names']); K = S['K']; V = S['V']
info = {}
for nm in names:
    Ks = K[names.index(nm)]; lo, hi = 5e-3, 0.5                   # 1 A loop, all layers: 0.005-0.5 A/mm
    save_plan(rgb_layers(Ks, range(nl), lo, hi), os.path.join(OUT, f'plan_{nm}.png'))
    kv, kg = np.real(net_total(Ks, 1)), np.real(net_total(Ks, 2))
    save_plan(rgb_layers(Ks, range(nl), lo, hi), os.path.join(OUT, f'flow_{nm}.png'),
              streams=[(kv[0] * 1e-3, kv[1] * 1e-3, '#ffd2b8'), (kg[0] * 1e-3, kg[1] * 1e-3, '#bfe2ff')])
    for k, L in enumerate(order):
        save_plan(rgb_layers(Ks, [k], 0.01, 0.3), os.path.join(OUT, f'layer_{nm}_{LN[L]}.png'), labels=(LN[L] in ('L1', 'L6')))
    # share of the loop current per layer (VBUS side, PGND side) along a cut x = 98 mm (band) when it crosses
    kx = int((98.0 - x0) / p)
    share = {}
    for net, nn in ((1, 'VBUS'), (2, 'PGND')):
        tot = {LN[L]: float(np.abs(np.sum(np.real(Ks[k, 0, kx, :]) * (netmap[k, kx, :] == net))) * p * 1e-3) for k, L in enumerate(order)}
        share[nn] = tot
    info[nm] = dict(share_x98_A=share)
    print('scenario', nm, flush=True)

# potentials (10 MHz loops): volts per amp, VBUS island relative to the device VIN pad, PGND relative to its PGND pad
for nm in [n for n in names if n.endswith('10M')]:
    Vs = V[names.index(nm)]
    for k, L in enumerate(order):
        for net, tag in ((1, 'VBUS'), (2, 'PGND')):        # one net per image: via barrels of the other net would set the scale
            vv = np.where(netmap[k] == net, np.imag(Vs[k]) * 1e3, np.nan)    # mV per A, inductive part at 10 MHz
            if np.isfinite(vv).sum() < 200: continue
            vmax = float(np.nanpercentile(np.abs(vv), 99.5))
            info.setdefault(nm, {})[f'v_mV_{LN[L]}_{tag}'] = [float(np.nanmin(vv)), float(np.nanmax(vv))]
            fig = plt.figure(figsize=(8.0, 8.0 * (y1 - y0) / (x1 - x0)), dpi=150, facecolor='#08090c')
            ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor('#08090c')
            ax.imshow(vv.T, extent=[x0, x1, y1, y0], cmap=VMAP, vmin=-vmax, vmax=vmax, interpolation='bilinear')
            context(ax, True); ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.axis('off')
            fig.savefig(os.path.join(OUT, f'pot_{nm}_{LN[L]}_{tag}.png'), facecolor='#08090c'); plt.close(fig)

# ---- B slices
B = np.load(os.path.join(P, 'bslices.npz'))
zl = json.loads(str(B['zlay'])); d = B['d']; dz = d[2] * 1e3
bnames = list(B['names'])
for nm in bnames:
    for s in ('yz', 'xz'):
        Bv = B[f'{nm}__{s}']; Bm = np.sqrt((np.abs(Bv) ** 2).sum(0)) * 1e6        # uT (per A for loops)
        if s == 'yz': ax_lo, ax_hi, ext0 = 90.0, 103.0, y0                       # band cut at x = 98 mm, y window
        else: ax_lo, ax_hi, ext0 = 95.0, 117.5, x0                                # bundle cut at y = 105 mm
        i0, i1 = int((ax_lo - ext0) / p), int((ax_hi - ext0) / p)
        img = Bm[i0:i1, :].T[::-1]                                                # z up
        zs = 4.0
        fig = plt.figure(figsize=(9, 9 * img.shape[0] * dz * zs / ((i1 - i0) * p)), dpi=150, facecolor='#08090c')
        axx = fig.add_axes([0, 0, 1, 1]); vmax = np.nanpercentile(img, 99.7)
        axx.imshow(img, aspect='auto', cmap=BMAP, vmin=0, vmax=vmax, interpolation='bilinear')
        axx.axis('off'); fig.savefig(os.path.join(OUT, f'b{s}_{nm}.png'), facecolor='#08090c'); plt.close(fig)
        info.setdefault('B', {})[f'{nm}_{s}_max_uT'] = float(np.nanmax(img))
    G = B[f'{nm}__gap']                                                           # (5 gaps, 3, nx, ny)
    for gi in range(G.shape[0]):
        Bm = np.sqrt((np.abs(G[gi]) ** 2).sum(0)) * 1e6
        vmax = np.nanpercentile(Bm, 99.7)
        fig = plt.figure(figsize=(8.0, 8.0 * (y1 - y0) / (x1 - x0)), dpi=150, facecolor='#08090c')
        axx = fig.add_axes([0, 0, 1, 1]); axx.imshow(Bm.T, extent=[x0, x1, y1, y0], cmap=BMAP, vmin=0, vmax=vmax, interpolation='bilinear')
        context(axx, True); axx.set_xlim(x0, x1); axx.set_ylim(y1, y0); axx.axis('off')
        fig.savefig(os.path.join(OUT, f'bgap{gi}_{nm}.png'), facecolor='#08090c'); plt.close(fig)
        info['B'][f'{nm}_gap{gi}_p99_uT'] = float(vmax)
    print('B', nm, flush=True)
json.dump(info, open(os.path.join(OUT, 'info.json'), 'w'), indent=1)

# ---- animation frames (WebP), plan view of all layers, fixed scale
if a.frames:
    Fz = np.load(os.path.join(P, 'frames.npz'))
    Kf = Fz['K']; tf = Fz['tf']; ton = float(Fz['t_on'])
    A = os.path.join(OUT, 'anim'); os.makedirs(A, exist_ok=True)
    # static context overlay (outlines + labels), transparent
    fig = plt.figure(figsize=(8.0, 8.0 * (y1 - y0) / (x1 - x0)), dpi=100)
    fig.patch.set_alpha(0); axx = fig.add_axes([0, 0, 1, 1]); axx.patch.set_alpha(0); context(axx, True)
    axx.set_xlim(x0, x1); axx.set_ylim(y1, y0); axx.axis('off'); ov = os.path.join(A, 'overlay.png'); fig.savefig(ov, transparent=True); plt.close(fig)
    overlay = Image.open(ov).convert('RGBA'); W, H = overlay.size
    times = []
    for i in range(Kf.shape[0]):
        rgb = rgb_layers(Kf[i].astype(np.float32) - Kf[0].astype(np.float32), range(nl), 0.03, 5.0)   # change since t_on - 100 ns
        im = Image.fromarray((rgb * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).convert('RGBA')
        Image.alpha_composite(im, overlay).convert('RGB').save(os.path.join(A, f'f{i:03d}.webp'), quality=78, method=5)
        times.append(round((tf[i] - ton) * 1e9, 3))
    rz = np.load(os.path.join(BR, 'results', ('in' if a.stack == 'intended' else 'ab') + '_8v4_10a_r300.npz'))
    tr = rz['t']; vb = 0.5 * (rz['wav_P105'] + rz['wav_P110']); tc = (tr - float(rz['t_on'])) * 1e9
    base = vb[(tc > -30) & (tc < 0)].mean()
    idev = np.interp(times, tc, rz['idev']); vbus = (np.interp(times, tc, vb) - base) * 1e3
    json.dump(dict(t_ns=times, seg=[int(v) for v in Fz['seg']], idev=[round(float(v), 3) for v in idev],
                   vbus=[round(float(v), 2) for v in vbus]), open(os.path.join(A, 'frames.json'), 'w'))
    print('frames', len(times))
