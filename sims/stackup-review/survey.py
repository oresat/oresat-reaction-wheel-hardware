"""Survey: pour area and track length per layer and net, board outline, net tie parts.
Reads the bus-ring pickles (read-only). python survey.py"""
import os, sys, pickle, collections, math
BR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bus-ring')
g = pickle.load(open(os.path.join(BR, 'geom.pkl'), 'rb'))
T = pickle.load(open(os.path.join(BR, 'pcb.pkl'), 'rb'))
CU = ['F.Cu', 'In1.Cu', 'In2.Cu', 'In3.Cu', 'In4.Cu', 'B.Cu']
LN = {L: f'L{i+1}' for i, L in enumerate(CU)}
print('== pour area per layer (mm2) ==')
for L in CU:
    items = sorted([(v.area, n) for (l, n), v in g['pours'].items() if l == L], reverse=True)
    print(LN[L], ', '.join(f'{n}:{a:.0f}' for a, n in items if a > 0.5))
print('\n== pour bounds per layer/net ==')
for (l, n), v in sorted(g['pours'].items()):
    if v.area > 0.5:
        b = v.bounds
        print(f'{LN[l]} {n:14s} area {v.area:7.1f}  bounds x {b[0]:.1f}-{b[2]:.1f} y {b[1]:.1f}-{b[3]:.1f}  parts {len(getattr(v, "geoms", [v]))}')
tl = collections.defaultdict(float)
for t in g['tracks']:
    tl[(t['layer'], t['net'])] += t['line'].length
print('\n== track length per layer (mm) ==')
for L in CU:
    items = sorted([(a, n) for (l, n), a in tl.items() if l == L], reverse=True)
    print(f'{LN[L]} total {sum(a for a, _ in items):.0f}:', ', '.join(f'{n}:{a:.1f}' for a, n in items))
# board outline
def find(node, key): return [c for c in node if isinstance(c, list) and c and c[0] == key]
def one(node, key):
    r = find(node, key); return r[0] if r else None
xs = []; ys = []
for kind in ('gr_line', 'gr_rect', 'gr_arc'):
    for e in find(T, kind):
        lay = one(e, 'layer')
        if lay and lay[1] == 'Edge.Cuts':
            for k in ('start', 'end', 'mid'):
                p = one(e, k)
                if p: xs.append(float(p[1])); ys.append(float(p[2]))
if xs: print('\nEdge.Cuts bounds x', min(xs), max(xs), 'y', min(ys), max(ys))
# stackup block in the file
st = None
for c in T:
    if isinstance(c, list) and c and c[0] == 'setup':
        st = one(c, 'stackup')
if st:
    print('\n== file stackup ==')
    for lay in find(st, 'layer'):
        print(lay[1], [(x[0], x[1]) for x in lay[2:] if isinstance(x, list) and len(x) > 1])
# net ties / footprints with multiple ground nets
print('\n== footprints touching >1 ground-ish net ==')
GN = {'PGND', 'GND', 'AGND', 'DGND'}
for f in find(T, 'footprint'):
    props = {p[1]: p[2] for p in find(f, 'property')}
    nets = set()
    for p in find(f, 'pad'):
        n = one(p, 'net')
        if n: nets.add(n[1] if len(n) > 1 else '')
    if len(nets & GN) > 1 or 'NetTie' in (one(f, 'footprint') or [''])[0] if False else len(nets & GN) > 1:
        at = one(f, 'at')
        print(props.get('Reference'), props.get('Value'), sorted(nets), 'at', at[1:3], f[1])
