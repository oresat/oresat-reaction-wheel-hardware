"""Rasterize every copper layer to a net-id grid (pours + tracks + pads + via rings).
Writes raster.npz: ids[6,nx,ny] (0 = no copper), nets[], x0, y0, pitch.
python raster.py [pitch_mm=0.025]"""
import os, sys, pickle, time
import numpy as np, shapely
from shapely.geometry import Point, box
from shapely.ops import unary_union
HERE = os.path.dirname(os.path.abspath(__file__))
BR = os.path.join(HERE, '..', 'bus-ring')
sys.path.insert(0, BR)
import build3d as b3
g = b3.g
CU = b3.CU
pitch = float(sys.argv[1]) if len(sys.argv) > 1 else 0.025
X0, Y0, X1, Y1 = 82.5, 75.0, 118.0, 125.5
nx = int(round((X1 - X0) / pitch)); ny = int(round((Y1 - Y0) / pitch))
xc = X0 + (np.arange(nx) + 0.5) * pitch; yc = Y0 + (np.arange(ny) + 0.5) * pitch
fps = b3.footprints()
parts = {}  # (layer, net) -> list of geoms
def add(L, net, geom):
    if not net or geom.is_empty: return
    parts.setdefault((L, net), []).append(geom)
for (L, net), geom in g['pours'].items(): add(L, net, geom)
for t in g['tracks']: add(t['layer'], t['net'], t['line'].buffer(t['w'] / 2, quad_segs=4))
for ref, f in fps.items():
    for pd in f['pads']:
        lays = pd['layers']
        if pd['kind'] in ('thru_hole', 'np_thru_hole') or '*.Cu' in lays:
            if pd['kind'] == 'np_thru_hole': continue
            for L in CU: add(L, pd['net'], pd['poly'])
        else:
            for L in lays:
                if L in CU: add(L, pd['net'], pd['poly'])
for v in g['vias']:
    for L in CU: add(L, v['net'], Point(v['x'], v['y']).buffer(v['size'] / 2, quad_segs=4))
nets = sorted({n for (_, n) in parts})
nid = {n: i + 1 for i, n in enumerate(nets)}
ids = np.zeros((6, nx, ny), np.int16)
t0 = time.time()
for (L, net), gl in parts.items():
    geom = unary_union(gl)
    shapely.prepare(geom)
    bx0, by0, bx1, by1 = geom.bounds
    i0 = max(0, int((bx0 - X0) / pitch) - 1); i1 = min(nx, int((bx1 - X0) / pitch) + 2)
    j0 = max(0, int((by0 - Y0) / pitch) - 1); j1 = min(ny, int((by1 - Y0) / pitch) + 2)
    XX, YY = np.meshgrid(xc[i0:i1], yc[j0:j1], indexing='ij')
    m = shapely.contains_xy(geom, XX, YY)
    sl = ids[CU.index(L), i0:i1, j0:j1]
    sl[m] = nid[net]
print(f'rasterized {len(parts)} layer/net groups in {time.time() - t0:.1f} s, grid {nx}x{ny} @ {pitch} mm')
np.savez_compressed(os.path.join(HERE, 'raster.npz'), ids=ids, nets=np.array(nets), x0=X0, y0=Y0, pitch=pitch)
for k, L in enumerate(CU):
    print(L, 'copper fraction', round(float((ids[k] > 0).mean()), 3))
