"""Print footprint ref, value, side, position for refs matching prefixes. python parts.py U J NT L FB"""
import os, sys
BR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bus-ring')
sys.path.insert(0, BR)
import build3d as b3
vals = {}
for f in b3.find(b3.T, 'footprint'):
    props = {p[1]: p[2] for p in b3.find(f, 'property')}
    vals[props.get('Reference')] = props.get('Value')
fp = b3.footprints()
pre = sys.argv[1:]
def key(r):
    import re
    m = re.match(r'([A-Z]+)(\d+)', r or '')
    return (m.group(1), int(m.group(2))) if m else (r, 0)
for r in sorted(fp, key=key):
    if any((r or '').startswith(p) and (r[len(p):len(p)+1].isdigit()) for p in pre):
        u = fp[r]
        nets = sorted({p['net'] for p in u['pads'] if p['net']})
        print(f"{r:6s} {str(vals.get(r)):22s} {u['layer']:5s} ({u['x']:7.2f},{u['y']:7.2f})  {', '.join(nets)[:160]}")
