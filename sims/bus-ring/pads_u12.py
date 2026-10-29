"""Print LMG2100 (U12) pad geometry: number, net, kind, bounds, area."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build3d as b3
fp = b3.footprints()
for ref in sys.argv[1:] or ['U12']:
    u = fp[ref]; print(ref, u['layer'], u['x'], u['y'])
    for p in u['pads']:
        b = p['poly'].bounds
        print(f"  {p['num']:>3} {p['net']:14s} {p['kind']:4s} x {b[0]:.2f}-{b[2]:.2f} y {b[1]:.2f}-{b[3]:.2f}  {p['poly'].area:.3f} mm2")
