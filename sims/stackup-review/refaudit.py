"""What faces each signal net 0.1 mm away, intended vs as built (raster version of under.py).
L3 nets: intended neighbour = L2 (0.1), as built = L4 (0.1).  L4 nets: intended = L5 (0.1), as built = L3 (0.1).
Prints mm2 of the net's copper over each facing net (or void) and the equivalent length at the net's main width.
python refaudit.py"""
import os, sys, collections, pickle
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
R = np.load(os.path.join(HERE, 'raster.npz'))
ids = R['ids']; nets = ['VOID'] + list(R['nets']); p = float(R['pitch'])
g = pickle.load(open(os.path.join(HERE, '..', 'bus-ring', 'geom.pkl'), 'rb'))
CU = ['F.Cu', 'In1.Cu', 'In2.Cu', 'In3.Cu', 'In4.Cu', 'B.Cu']
width = collections.defaultdict(collections.Counter)
for t in g['tracks']: width[(t['layer'], t['net'])][t['w']] += t['line'].length
def audit(L, nbr_int, nbr_blt, only=None):
    li = CU.index(L)
    tracked = sorted({t['net'] for t in g['tracks'] if t['layer'] == L})
    print(f"\n=== {L} (L{li+1}) signal nets: intended neighbour L{nbr_int+1}, as built L{nbr_blt+1}  [mm of trace length]")
    for n in tracked:
        if only and not only(n): continue
        k = nets.index(n)
        m = ids[li] == k
        w = width[(L, n)].most_common(1)[0][0]
        def summ(j):
            c = collections.Counter(ids[j][m].tolist())
            tot = sum(c.values())
            items = sorted(c.items(), key=lambda kv: -kv[1])
            return ', '.join(f"{nets[a]} {v * p * p / w:.1f}" for a, v in items if v * p * p / w >= 0.3)
        tl = m.sum() * p * p / w
        print(f"{n[:20]:20s} w{w:.3f} ~{tl:5.1f} mm | int: {summ(nbr_int)}\n{'':38s}| blt: {summ(nbr_blt)}")
PL = {'PGND', 'GND', 'AGND', 'VBUS'}
audit('In2.Cu', 1, 3, only=lambda n: n not in ('PGND',))
audit('In3.Cu', 4, 2, only=lambda n: True)
