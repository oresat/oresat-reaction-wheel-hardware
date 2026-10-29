"""Small checks: thermal vias under the LMG2100s, L4 stripline Z0, band stray field at the MA732, plane-cavity modes.
python misc.py"""
import os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
BR = os.path.abspath(os.path.join(HERE, '..', 'bus-ring'))
os.chdir(BR); sys.path.insert(0, BR)
import build3d as b3
from fd2d import STACKS, build, maxwell
os.chdir(HERE)
fps = b3.footprints(); g = b3.g
# ---------------- 1. thermal: vias under each LMG2100 ----------------
print('== 1. LMG2100 thermal path (per device) ==')
k_cu, k_fr4 = 390.0, 0.30
d, t_pl = 0.20, 0.020                       # drill, assumed plating (mm)
A_barrel = math.pi / 4 * (d ** 2 - (d - 2 * t_pl) ** 2)  # mm2 of copper per via
STK = {'intended': [0.092, 0.100, 1.049, 0.100, 0.092], 'asbuilt': [0.100, 0.535, 0.100, 0.535, 0.100]}
for ref in ('U8', 'U10', 'U12'):
    u = fps[ref]
    xs = [pd['x'] for pd in u['pads']]; ys = [pd['y'] for pd in u['pads']]
    x0, x1, y0, y1 = min(xs) - 1, max(xs) + 1, min(ys) - 1, max(ys) + 1
    vs = [v for v in g['vias'] if x0 <= v['x'] <= x1 and y0 <= v['y'] <= y1]
    A = (x1 - x0) * (y1 - y0)
    nets = {}
    for v in vs: nets[v['net']] = nets.get(v['net'], 0) + 1
    line = f'{ref}: area {A:.0f} mm2, vias {len(vs)} {nets}'
    for s, gaps in STK.items():
        # L6 -> L1 through the board: vias (whole length) in parallel with the dielectric column
        Lb = sum(gaps) + 4 * 0.035
        G_via = len(vs) * k_cu * A_barrel * 1e-6 / (Lb * 1e-3)
        R_diel = sum(t * 1e-3 / (k_fr4 * A * 1e-6) for t in gaps)
        # first gap only (L6 -> L5), the one that matters for spreading into the PGND plane
        R5 = gaps[4] * 1e-3 / (k_fr4 * A * 1e-6)
        line += f' | {s}: vias {1 / G_via:.1f} K/W, dielectric-only {R_diel:.0f} K/W, L6->L5 dielectric {R5:.1f} K/W'
    print(line)
print(f'   (via barrel copper {A_barrel:.4f} mm2 assumed; RthJB of the part is 6.2 K/W)')
# ---------------- 2. Z0 of a 0.102 mm L4 trace between L3 and L5 GND planes ----------------
print('\n== 2. L4 0.102 mm trace, GND on L3 and L5 (planes), Z0 ==')
for s in ('intended', 'asbuilt'):
    iv = {'In2.Cu': {'GND': [(-3.0, 3.0)]}, 'In3.Cu': {'SIG': [(-0.051, 0.051)]}, 'In4.Cu': {'GND': [(-3.0, 3.0)]},
          'In1.Cu': {'GND': [(-3.0, 3.0)]}, 'B.Cu': {}, 'F.Cu': {}}
    G = build(iv, STACKS[s], -3.0, 3.0, -3.0, 3.0, air=2, hmin_u=0.005, hmin_z=0.005)
    C, _, _ = maxwell(G)
    G0 = build(iv, STACKS[s], -3.0, 3.0, -3.0, 3.0, air=2, hmin_u=0.005, hmin_z=0.005, vacuum=True)
    C0, _, _ = maxwell(G0)
    i = G['nets'].index('SIG')
    c, c0 = C[i, i], C0[i, i]
    Z0 = 1 / (2.998e8 * math.sqrt(c * c0)); ee = c / c0
    print(f'   {s}: C {c * 1e12:.0f} fF/mm... (per m {c * 1e12:.1f} pF/m), eps_eff {ee:.2f}, Z0 {Z0:.1f} ohm, delay {math.sqrt(ee) / 0.2998:.2f} ps/mm')
# ---------------- 3. band stray field at the MA732 ----------------
print('\n== 3. Band current stray field at the MA732 (100.0, 102.19), die ~0.5 mm above F.Cu ==')
# 2D: band current along x, cross-section in (y,z). VBUS sheets on L3 and L4 (y 91.6..98.9), return PGND sheets
# directly over/under them on L2 and L5 (TEM, mirror width). Equal split between the two pairs.
def zlayers(gaps):
    z = [0.0]
    for t in gaps: z.append(z[-1] - t - 0.035)
    return z  # z of L1..L6 (F.Cu = 0, downward negative)
def Bfield(gaps, I=1.0, y0=91.6, y1=98.9, ys=102.19, zs=0.5, n=400):
    zl = zlayers(gaps)
    yy = np.linspace(y0, y1, n); dI = I / 2 / n
    sheets = [(zl[2], +1), (zl[3], +1), (zl[1], -1), (zl[4], -1)]   # L3, L4 VBUS ; L2, L5 PGND
    By = Bz = 0.0
    for z, sg in sheets:
        dy = (ys - yy) * 1e-3; dz = (zs - z) * 1e-3; r2 = dy ** 2 + dz ** 2
        # infinite line current along x: B = mu0 I/(2 pi r) * (x_hat cross r_hat)
        By += np.sum(sg * dI * 2e-7 * (-dz) / r2); Bz += np.sum(sg * dI * 2e-7 * dy / r2)
    return By, Bz
for s, gaps in STK.items():
    By, Bz = Bfield(gaps)
    print(f'   {s}: per amp of band current  |B_inplane(y)| {abs(By) * 1e6:.2f} uT/A, |Bz| {abs(Bz) * 1e6:.2f} uT/A')
Bi = Bfield(STK['intended']); Bb = Bfield(STK['asbuilt'])
print(f'   ratio as built / intended: in-plane {abs(Bb[0] / Bi[0]):.1f}x, normal {abs(Bb[1] / Bi[1]):.1f}x')
print('   at 5 A of band current: in-plane {:.3f} mT as built; a ~50 mT diametric magnet -> angle error {:.3f} deg'.format(
    abs(Bb[0]) * 5 * 1e3, math.degrees(abs(Bb[0]) * 5 / 0.05)))
# ---------------- 4. plane-cavity modes ----------------
print('\n== 4. Plane-pair cavity TM10 modes (thickness-independent) ==')
for name, Lx in (('VBUS band, 29 mm long', 29.0), ('board-size PGND/GND cavity, 49 mm', 49.0), ('board width 34 mm', 34.0)):
    for er in (4.3, 4.5):
        pass
    print(f'   {name}: {2.998e8 / (2 * Lx * 1e-3 * math.sqrt(4.4)) / 1e9:.2f} GHz')
# ---------------- 5. lost VBUS/PGND plate capacitance ----------------
print('\n== 5. VBUS/PGND plate C 221.6 -> 102.6 pF: |Z| at 330 MHz {:.2f} -> {:.2f} ohm'.format(
    1 / (2 * math.pi * 330e6 * 221.6e-12), 1 / (2 * math.pi * 330e6 * 102.6e-12)))
