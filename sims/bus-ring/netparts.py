"""List footprints (ref, value) with a pad on each named net. python netparts.py <net> [<net> ...]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build3d as b3
vals = {}
for f in b3.find(b3.T, 'footprint'):
    props = {p[1]: p[2] for p in b3.find(f, 'property')}
    vals[props.get('Reference')] = props.get('Value')
fp = b3.footprints()
for net in sys.argv[1:]:
    hits = sorted({(r, p['num']) for r, u in fp.items() for p in u['pads'] if p['net'] == net})
    print(net, ':', ', '.join(f"{r}.{n}({vals.get(r)})" for r, n in hits))
