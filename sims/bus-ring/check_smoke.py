"""Sanity-check a multi-terminal sweep: KCL per island and the driven terminal's self-admittance. python check_smoke.py <case_dir> <meta.json>"""
import json, sys
t = json.load(open(sys.argv[1] + '/terminals.json')); meta = json.load(open(sys.argv[2]))
net = {'t_' + k: v['net'] for k, v in meta['terminals'].items()}
for tag, s in t['sweeps'].items():
    I = {k: complex(*v['I']) for k, v in s['sources'].items()}
    V = {k: complex(*v['V']) for k, v in s['sources'].items()}
    drv = tag.split('__')[1]
    sv = sum(I[k] for k in I if net[k] == 'VBUS'); sg = sum(I[k] for k in I if net[k] == 'PGND')
    print(tag, 'f', s['freq'], 'iters', s['n_iter'], 'ok', s['solver_ok'])
    print(f'  driven {drv}: V={V[drv]:.3e} I={I[drv]:.4e} -> R_in={abs(V[drv] / I[drv]) * 1e3:.3f} mOhm')
    print(f'  KCL VBUS sum {abs(sv):.2e}  PGND sum {abs(sg):.2e}  (|I_drv| {abs(I[drv]):.2e})')
    big = sorted(I.items(), key=lambda kv: -abs(kv[1]))[:6]
    print('  largest:', ', '.join(f'{k[2:]} {abs(v):.3e}' for k, v in big))
