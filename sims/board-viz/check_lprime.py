"""Field energy per unit length across the x = 98 mm cut, from the y-z B slice: L' = sum |B|^2 dy dz / mu0 per A^2.
Compare with the prior study (power-stage-rev8/docs/stackup-sim/HANDOFF.md): 15.4 intended, 59.0 as built (pH/mm)."""
import os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); MU0 = 4e-7 * np.pi
for st in ('intended', 'asbuilt'):
    B = np.load(os.path.join(HERE, 'products', st, 'bslices.npz'))
    d = B['d']
    for nm in ('BULK_L_10M', 'BULK_L_dc'):
        yz = B[f'{nm}__yz']                                   # (3, ny, nz), T per A
        Lp = float((np.abs(yz) ** 2).sum() * d[1] * d[2] / MU0)
        print(f'{st:8s} {nm:11s} L\' = {Lp * 1e9:6.1f} pH/mm')
