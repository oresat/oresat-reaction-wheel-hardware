"""Export the PEEC bus (assemble_y.py ymat.npz) as a Xyce subcircuit.

usage: python mk_board_sub.py <stack_root> <out.sub> [--fr 1e7]

Hub-referenced star: each terminal k (not a hub) connects to its net's hub (devC_V for VBUS, devC_G for PGND) through
  L_k (L(10 MHz) diagonal) + R_k (diagonal of R at --fr) + B_k (sum_j R_kj I(L_j), the off-diagonal R),
with K couplings for every L pair. Exact at f = 10 MHz for --fr 1e7; R(f) blends between DC and 10 MHz as sqrt(f).
Subckt pins are the 28 terminals in meta order. Port current I_k = current into terminal k, out of the hub.
"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ac_bus as ab

ap = argparse.ArgumentParser(); ap.add_argument('stack_root'); ap.add_argument('out'); ap.add_argument('--fr', type=float, default=1e7)
ap.add_argument('--drop', default='devA_V,devA_G,devB_V,devB_G,P105_V,P105_G,P110_V,P110_G',
                help='open terminals left out (exact in Z form: zero current); open inductor-only nodes ring under trap')
a = ap.parse_args()
terms, nets, Y = ab.load(a.stack_root)
A, Rdc, R10, L10, f10, ports = ab.port_model(terms, nets, Y)
R = ab.r_blend(Rdc, R10, f10, a.fr)
L = 0.5 * (L10 + L10.T); R = 0.5 * (R + R.T)
drop = set(filter(None, a.drop.split(',')))
sel = [k for k, i in enumerate(ports) if terms[i] not in drop]
L, R = L[np.ix_(sel, sel)], R[np.ix_(sel, sel)]; ports = [ports[k] for k in sel]
terms_kept = [t for t in terms if t not in drop]
for nm, M in (('L', L), ('R', R)):
    ev = np.linalg.eigvalsh(M); print(f'{nm}: eig min {ev.min():.3e} max {ev.max():.3e}')
    if ev.min() <= 0: raise SystemExit(f'{nm} matrix not positive definite')
hub = {'VBUS': 'devC_V', 'PGND': 'devC_G'}
name = 'BOARD_' + os.path.basename(os.path.normpath(a.stack_root)).upper()
pn = [terms[i] for i in ports]
lines = [f'* PEEC bus {a.stack_root}: {len(terms_kept)} of {len(terms)} terminals, hub-referenced star, L at {f10 / 1e6:g} MHz, R at {a.fr / 1e6:g} MHz',
         f'.subckt {name} ' + ' '.join(terms_kept)]
for k, t in enumerate(pn):
    hb = hub[nets[ports[k]]]
    lines.append(f'VS{k} {t} s{k} 0')                      # current sense: Xyce cannot read I(L) of K-coupled inductors
    lines.append(f'L{k} s{k} a{k} {L[k, k]:.6e}')
    lines.append(f'R{k} a{k} b{k} {R[k, k]:.6e}')
    terms_r = ' + '.join(f'({R[k, j]:.6e})*I(VS{j})' for j in range(len(pn)) if j != k)
    lines.append(f'B{k} b{k} {hb} V={{{terms_r}}}')
kmax = 0
for i in range(len(pn)):
    for j in range(i + 1, len(pn)):
        kc = L[i, j] / np.sqrt(L[i, i] * L[j, j]); kmax = max(kmax, abs(kc))
        lines.append(f'K{i}_{j} L{i} L{j} {kc:.8f}')
lines.append(f'.ends {name}')
open(a.out, 'w').write('\n'.join(lines) + '\n')
print(f'wrote {a.out}: subckt {name}, {len(pn)} branches, max |k| {kmax:.5f}')
print('pins:', ' '.join(terms_kept))
