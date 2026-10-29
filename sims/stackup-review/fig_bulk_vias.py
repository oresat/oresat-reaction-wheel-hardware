"""Right-edge analog bundle (L3) vs the right bulk caps (C97/C98/C100/C107, B.Cu) and the VBUS/PGND vias that carry
their current. Writes fig_bulk_vias.png and prints the nearest via distance per analog net."""
import os, sys, math
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import Point
from shapely.ops import unary_union
HERE = os.path.dirname(os.path.abspath(__file__))
BR = os.path.join(HERE, '..', 'bus-ring'); sys.path.insert(0, BR)
import build3d as b3
g = b3.g; fps = b3.footprints()
ANA = ['/PHA_ISNS', '/PHB_ISNS', '/PHC_ISNS', '/PHA_VSNS', '/PHB_VSNS', '/PHC_VSNS', '+VREF', '+3V3A', 'AGND']
fig, ax = plt.subplots(figsize=(8, 11))
win = (108, 118, 88, 114)
for (L, n), geom in g['pours'].items():
    if L == 'In3.Cu' and n in ('VBUS', 'PGND', 'GND', 'AGND'):
        col = {'VBUS': '#f2b8b8', 'PGND': '#bcd0f0', 'GND': '#bfe5bf', 'AGND': '#f2e0b0'}[n]
        for pg in getattr(geom, 'geoms', [geom]):
            xs, ys = pg.exterior.xy; ax.fill(xs, ys, color=col, alpha=0.6, lw=0)
for t in g['tracks']:
    if t['layer'] == 'In2.Cu' and t['net'] in ANA:
        xs, ys = t['line'].xy; ax.plot(xs, ys, '-', color='k', lw=0.8)
for ref in ('C97', 'C98', 'C100', 'C107', 'C74', 'C75', 'C76', 'C77', 'C95', 'C127', 'C128', 'C131', 'C134', 'C137'):
    for pd in fps[ref]['pads']:
        xs, ys = pd['poly'].exterior.xy
        ax.fill(xs, ys, color='r' if pd['net'] == 'VBUS' else 'b', alpha=0.35)
    ax.annotate(ref, (fps[ref]['x'], fps[ref]['y']), fontsize=7)
vb = [v for v in g['vias'] if v['net'] in ('VBUS', 'PGND') and win[0] < v['x'] < win[1] and win[2] < v['y'] < win[3]]
for v in vb:
    ax.add_patch(plt.Circle((v['x'], v['y']), v['size'] / 2, color='r' if v['net'] == 'VBUS' else 'b'))
ax.set_xlim(win[0], win[1]); ax.set_ylim(win[3], win[2]); ax.set_aspect('equal'); ax.grid(alpha=0.3)
ax.set_title('L3 analog bundle (black) over L4 pours; red/blue = VBUS/PGND vias and bulk/local cap pads', fontsize=9)
plt.savefig(os.path.join(HERE, 'fig_bulk_vias.png'), dpi=110, bbox_inches='tight')
# nearest VBUS / PGND via to each analog trace, and how many vias lie within 1 mm
segs = {n: unary_union([t['line'] for t in g['tracks'] if t['layer'] == 'In2.Cu' and t['net'] == n]) for n in ANA if n != 'AGND'}
for n, ln in segs.items():
    dV = sorted(ln.distance(Point(v['x'], v['y'])) for v in g['vias'] if v['net'] == 'VBUS')
    dP = sorted(ln.distance(Point(v['x'], v['y'])) for v in g['vias'] if v['net'] == 'PGND')
    print(f'{n:10s} nearest VBUS via {dV[0]:.2f} mm ({sum(d < 1 for d in dV)} within 1 mm, {sum(d < 2 for d in dV)} within 2 mm); '
          f'nearest PGND via {dP[0]:.2f} mm ({sum(d < 1 for d in dP)} within 1 mm, {sum(d < 2 for d in dP)} within 2 mm)')
