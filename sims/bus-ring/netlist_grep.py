"""List board nets matching a substring, with the parts on each: python netlist_grep.py <substr> [...]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build3d as b3
vals = {}
for f in b3.find(b3.T, 'footprint'):
    props = {p[1]: p[2] for p in b3.find(f, 'property')}
    vals[props.get('Reference')] = props.get('Value')
fp = b3.footprints()
nets = {}
for r, u in fp.items():
    for p in u['pads']:
        nets.setdefault(p['net'], set()).add((r, p['num']))
for s in sys.argv[1:]:
    for n in sorted(k for k in nets if s.lower() in k.lower()):
        print(n, ':', ', '.join(f"{r}.{q}({vals.get(r)})" for r, q in sorted(nets[n])))
