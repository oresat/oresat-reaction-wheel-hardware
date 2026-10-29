"""Multi-terminal PyPEEC case of the rev8 VBUS/PGND bus for a full Y-matrix extraction.

usage: python build_mp.py <intended|asbuilt> <out_root> [--pitch 0.1] [--dz 0.0115] [--freqs 0,1e7] [--lanes 3]

Terminals (every one a stiff lumped voltage source; one sweep per driven terminal at 1 mV, all others at 0 V):
  leg A/B/C device: LMG2100 VIN pad (V) and PGND pads (G)
  each leg's bottom 2.2 uF bank and top bank (10 uF + 2.2 uF): VBUS pads (V), PGND pads (G)
  left and right 47 uF bulk banks
  two probes on the L4 VBUS feed under the analog sense bundle (V on L4, G on L5 directly below)
  the feed cut at the crop edge toward J1 (V: VBUS voxels in the last row, G: PGND voxels in the last row)
Y[:, k] = I / 1 mV for the sweep that drives terminal k. VBUS and PGND are separate islands here: the only
connections between them are the external parts placed across terminal pairs afterwards (caps, device, source).
Writes <out_root>/<stack>_lane<i>/ case folders that share one geometry.
"""
import os, sys, json, argparse
import numpy as np, shapely, yaml
from shapely.geometry import box, Point
from shapely.ops import unary_union
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build3d as b3          # reuses the stackup table, the footprint/pad parser and the board geometry

LEGS = {'A': 'U8', 'B': 'U10', 'C': 'U12'}
BANKS = {
    'A_bot': ['C42', 'C43', 'C44', 'C45', 'C93'],
    'A_top': ['C109', 'C110', 'C46', 'C48', 'C90', 'C117', 'C118', 'C129', 'C132', 'C135'],
    'B_bot': ['C58', 'C59', 'C60', 'C61', 'C94'],
    'B_top': ['C112', 'C113', 'C62', 'C64', 'C91', 'C122', 'C123', 'C130', 'C133', 'C136'],
    'C_bot': ['C74', 'C75', 'C76', 'C77', 'C95'],
    'C_top': ['C115', 'C116', 'C78', 'C80', 'C92', 'C127', 'C128', 'C131', 'C134', 'C137'],
    'BULK_L': ['C96', 'C99', 'C101', 'C106'],
    'BULK_R': ['C97', 'C98', 'C100', 'C107'],
}
PROBES = {'P105': (115.5, 105.0), 'P110': (115.5, 110.0)}   # under the analog bundle, on the L4 feed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stack'); ap.add_argument('out')
    ap.add_argument('--pitch', type=float, default=0.1); ap.add_argument('--dz', type=float, default=0.0115)
    ap.add_argument('--freqs', default='0,1e7'); ap.add_argument('--lanes', type=int, default=3)
    ap.add_argument('--crop', default='85.5,89.5,117.5,113.0')
    a = ap.parse_args()
    x0, y0, x1, y1 = map(float, a.crop.split(',')); p = a.pitch; dz = a.dz
    nx = int(round((x1 - x0) / p)); ny = int(round((y1 - y0) / p))
    xc = x0 + (np.arange(nx) + 0.5) * p; yc = y0 + (np.arange(ny) + 0.5) * p
    XX, YY = np.meshgrid(xc, yc, indexing='ij')
    ncu = max(1, int(round(0.035 / dz))); gaps = [max(1, int(round(t / dz))) for t in b3.STACK[a.stack]]
    zlay = {}; iz = 1
    for k, L in enumerate(reversed(b3.CU)):
        zlay[L] = (iz, iz + ncu); iz += ncu
        if k < 5: iz += gaps[::-1][k]
    nz = iz + 1
    fps = b3.footprints(); g = b3.g

    def raster(geom):
        if geom.is_empty: return np.zeros((nx, ny), bool)
        return shapely.contains_xy(geom, XX, YY)

    # ---- copper: 1 VBUS, 2 PGND, 3 VBUS via, 4 PGND via
    lab = np.zeros((nx, ny, nz), np.int16)
    crop = box(x0, y0, x1, y1)
    for L in b3.CU:
        for ni, net in enumerate(b3.NETS):
            parts = []
            if (L, net) in g['pours']: parts.append(g['pours'][(L, net)])
            parts += [t['line'].buffer(t['w'] / 2) for t in g['tracks'] if t['layer'] == L and t['net'] == net]
            for f in fps.values():
                for pd in f['pads']:
                    if pd['net'] == net and (L in pd['layers'] or '*.Cu' in pd['layers']):
                        parts.append(pd['poly'] if pd['kind'] == 'smd' else Point(pd['x'], pd['y']).buffer(0.2))
            m = raster(unary_union(parts).intersection(crop)); z0, z1 = zlay[L]
            sl = lab[:, :, z0:z1]; sl[m] = ni + 1
    vlist = [(v['x'], v['y'], v['drill'], v['net']) for v in g['vias'] if v['net'] in b3.NETS]
    for f in fps.values():
        for pd in f['pads']:
            if pd['kind'] == 'thru_hole' and pd['net'] in b3.NETS: vlist.append((pd['x'], pd['y'], pd['drill'] or 0.2, pd['net']))
    zt, zb = zlay['F.Cu'][1], zlay['B.Cu'][0]
    for vx, vy, dr, net in vlist:
        if not (x0 < vx < x1 and y0 < vy < y1): continue
        i = int((vx - x0) / p); j = int((vy - y0) / p); r = max(dr / 2, p * 0.75)
        cells = [(u, w) for u in range(max(0, i - 2), min(nx, i + 3)) for w in range(max(0, j - 2), min(ny, j + 3))
                 if (xc[u] - vx) ** 2 + (yc[w] - vy) ** 2 <= r * r] or [(i, j)]
        for u, w in cells:
            col = lab[u, w, zb:zt]; col[col == 0] = 3 if net == 'VBUS' else 4

    # ---- terminals (codes from 10 up); name -> (code, net)
    term = {}; code = 10

    def add_term(name, mask3d, net):
        nonlocal code
        base = (1, 3) if net == 'VBUS' else (2, 4)
        sel = mask3d & np.isin(lab, base)
        if not sel.any(): raise SystemExit(f'terminal {name} is empty')
        lab[sel] = code; term[name] = (code, net); code += 1

    def pad_mask(refs, net, pad_filter=None):
        m3 = np.zeros(lab.shape, bool)
        for ref in refs:
            f = fps[ref]; z0, z1 = zlay[f['layer']]
            for pd in f['pads']:
                if pd['net'] == net and pd['kind'] == 'smd' and (pad_filter is None or pd['num'] in pad_filter):
                    m3[:, :, z0:z1] |= raster(pd['poly'])[:, :, None]
        return m3
    for leg, ref in LEGS.items():
        add_term(f'dev{leg}_V', pad_mask([ref], 'VBUS', {'7'}), 'VBUS')
        add_term(f'dev{leg}_G', pad_mask([ref], 'PGND', {'6', '17'}), 'PGND')
    for bk, refs in BANKS.items():
        add_term(f'{bk}_V', pad_mask(refs, 'VBUS'), 'VBUS')
        add_term(f'{bk}_G', pad_mask(refs, 'PGND'), 'PGND')
    for pr, (px, py) in PROBES.items():
        sq = raster(box(px - 0.16, py - 0.16, px + 0.16, py + 0.16))
        for L, net, nm in (('In3.Cu', 'VBUS', 'V'), ('In4.Cu', 'PGND', 'G')):
            m3 = np.zeros(lab.shape, bool); z0, z1 = zlay[L]; m3[:, :, z0:z1] = sq[:, :, None]
            add_term(f'{pr}_{nm}', m3, net)
    edge = np.zeros(lab.shape, bool); edge[(xc > 108.0), ny - 1, :] = True
    add_term('FEED_V', edge, 'VBUS'); add_term('FEED_G', edge, 'PGND')

    # ---- keep only copper connected to a terminal; then each net must be exactly one island
    grp = np.zeros(lab.shape, np.int8)
    vcodes = [1, 3] + [c for c, n in term.values() if n == 'VBUS']; gcodes = [2, 4] + [c for c, n in term.values() if n == 'PGND']
    grp[np.isin(lab, vcodes)] = 1; grp[np.isin(lab, gcodes)] = 2
    nshort = 0
    for axn in range(3):
        q = np.moveaxis(grp, axn, 0); nshort += int((((q[:-1] == 1) & (q[1:] == 2)) | ((q[:-1] == 2) & (q[1:] == 1))).sum())
    if nshort: raise SystemExit(f'{nshort} VBUS/PGND faces touch: clearances unresolved at pitch {p}')
    removed = 0; islands = {}
    for gid, nm in ((1, 'VBUS'), (2, 'PGND')):
        cl, n = ndi.label(grp == gid)
        tcodes = [c for c, nn in term.values() if nn == nm]
        keep = np.unique(cl[np.isin(lab, tcodes)]); keep = keep[keep > 0]
        drop = (grp == gid) & ~np.isin(cl, keep); removed += int(drop.sum()); lab[drop] = 0
        islands[nm] = int(len(keep))
    if islands['VBUS'] != 1 or islands['PGND'] != 1:
        raise SystemExit(f'expected one island per net, got {islands}')
    for t, (c, n) in term.items():
        if not (lab == c).any(): raise SystemExit(f'terminal {t} lost')

    # ---- write one shared geometry and one problem per lane
    names = {1: 'cu_VBUS', 2: 'cu_PGND', 3: 'via_VBUS', 4: 'via_PGND'}; names.update({c: f't_{t}' for t, (c, n) in term.items()})
    flat = lab.ravel(order='F')
    dom = {nm: np.flatnonzero(flat == c).tolist() for c, nm in names.items()}
    geo = {'mesh_type': 'voxel',
           'data_voxelize': {'param': {'n': [nx, ny, nz], 'd': [p * 1e-3, p * 1e-3, dz * 1e-3],
                                       'c': [(x0 + x1) / 2 * 1e-3, (y0 + y1) / 2 * 1e-3, nz * dz / 2 * 1e-3]}, 'domain_index': dom},
           'data_point': {'check_cloud': False, 'filter_cloud': False, 'pts_cloud': []},
           'data_resampling': {'use_reduce': False, 'use_resample': False, 'resampling_factor': [1, 1, 1]},
           'data_conflict': {'resolve_rules': False, 'resolve_random': False, 'conflict_rules': []},
           'data_integrity': {'check_integrity': False, 'domain_connected': {}, 'domain_adjacent': {}}}
    rho = 1.72e-8; rho_via = rho * (0.1 ** 2 / (0.1 ** 2 - 0.075 ** 2))
    tnames = [f't_{t}' for t in term]
    freqs = [float(f) for f in a.freqs.split(',')]
    lanes = [tnames[i::a.lanes] for i in range(a.lanes)]
    root = os.path.join(a.out, a.stack); os.makedirs(root, exist_ok=True)
    with open(os.path.join(root, 'geometry.yaml'), 'w') as fh:
        yaml.safe_dump(geo, fh, default_flow_style=None, width=10 ** 9)
    for li, drive in enumerate(lanes):
        prob = {'material_def': {
                    'copper': {'domain_list': ['cu_VBUS', 'cu_PGND'] + tnames, 'material_type': 'electric', 'orientation_type': 'isotropic', 'var_type': 'lumped'},
                    'via': {'domain_list': ['via_VBUS', 'via_PGND'], 'material_type': 'electric', 'orientation_type': 'isotropic', 'var_type': 'lumped'}},
                'source_def': {t: {'domain_list': [t], 'source_type': 'voltage', 'var_type': 'lumped'} for t in tnames},
                'sweep_solver': {}}
        mv = {'copper': {'rho_re': rho, 'rho_im': 0.0}, 'via': {'rho_re': rho_via, 'rho_im': 0.0}}
        for t in drive:
            for f in freqs:
                sv = {u: {'V_re': 1e-3 if u == t else 0.0, 'V_im': 0.0, 'Z_re': 1e-9, 'Z_im': 0.0} for u in tnames}
                prob['sweep_solver'][f'f{f / 1e6:g}M__{t}'] = {'init': None, 'param': {'freq': f, 'material_val': mv, 'source_val': sv}}
        d = os.path.join(root, f'lane{li}'); os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, 'problem.yaml'), 'w') as fh:
            yaml.safe_dump(prob, fh, default_flow_style=None, width=10 ** 9, sort_keys=False)
        if not os.path.exists(os.path.join(d, 'geometry.yaml')):
            os.symlink('../geometry.yaml', os.path.join(d, 'geometry.yaml'))
    meta = dict(stack=a.stack, pitch=p, dz=dz, crop=[x0, y0, x1, y1], n=[nx, ny, nz], n_grid=nx * ny * nz, n_active=int((lab > 0).sum()),
                zlay=zlay, gaps_mm=[gv * dz for gv in gaps], terminals={t: dict(code=c, net=n, voxels=int((lab == c).sum())) for t, (c, n) in term.items()},
                banks=BANKS, legs=LEGS, probes=PROBES, freqs=freqs, lanes=lanes, removed_island_vox=removed)
    json.dump(meta, open(os.path.join(root, 'meta.json'), 'w'), indent=1)
    np.savez_compressed(os.path.join(root, 'labels.npz'), lab=lab)
    print(json.dumps({k: meta[k] for k in ('n', 'n_grid', 'n_active', 'gaps_mm', 'removed_island_vox')}),
          len(term), 'terminals,', sum(len(l) for l in lanes) * len(freqs), 'sweeps')


if __name__ == '__main__':
    main()
