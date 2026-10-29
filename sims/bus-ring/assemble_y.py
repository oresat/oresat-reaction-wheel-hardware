"""Assemble the terminal admittance matrix Y(f) of the bus from the multi-terminal PEEC lanes.

usage: python assemble_y.py <stack_root>        (reads <stack_root>/lane*/terminals.json and meta.json)
writes <stack_root>/ymat.npz: freqs, terms, nets, Y[f] (n x n complex, I = Y V, I into the network)
checks: reciprocity (Y = Y^T), KCL per island (each net's columns sum to zero), and a cross-check against the earlier
single-port runs (loop from a cap bank to a shorted leg C device, other terminals open).
"""
import json, os, sys, glob
import numpy as np

root = sys.argv[1]
meta = json.load(open(os.path.join(root, 'meta.json')))
terms = list(meta['terminals']); nets = [meta['terminals'][t]['net'] for t in terms]; n = len(terms)
idx = {t: i for i, t in enumerate(terms)}
sweeps = {}
for f in sorted(glob.glob(os.path.join(root, 'lane*', 'terminals.json'))):
    for tag, s in json.load(open(f))['sweeps'].items():
        sweeps[tag] = s
freqs = sorted({s['freq'] for s in sweeps.values()})
Y = {}
for fr in freqs:
    Vm = np.zeros((n, n), complex); Im = np.zeros((n, n), complex); have = []
    for tag, s in sweeps.items():
        if s['freq'] != fr: continue
        j = idx[tag.split('__t_')[1]]; have.append(j)
        for k, v in s['sources'].items():
            i = idx[k[2:]]; Vm[i, j] = complex(*v['V']); Im[i, j] = complex(*v['I'])
    if len(have) != n:
        print(f'f={fr:g}: only {len(have)}/{n} excitations present'); continue
    Y[fr] = Im @ np.linalg.inv(Vm)          # Y V = I for every excitation column
for fr, y in Y.items():
    asym = np.abs(y - y.T).max() / np.abs(y).max()
    kcl = max(np.abs(y[[i for i in range(n) if nets[i] == nn]].sum(0)).max() for nn in ('VBUS', 'PGND')) / np.abs(y).max()
    print(f'f={fr / 1e6:g} MHz: max asymmetry {asym:.2e}, max KCL residual {kcl:.2e} (relative to max |Y|)')
np.savez(os.path.join(root, 'ymat.npz'), freqs=np.array(list(Y)), terms=np.array(terms), nets=np.array(nets),
         Y=np.array([Y[f] for f in Y]))


def loop_z(y, drive, short, ground='devC_G'):
    """impedance of the loop drive_V -> drive_G with device `short` shorted VIN-PGND, all other terminals open."""
    yt = y.copy(); a, b = idx[short + '_V'], idx[short + '_G']; gs = 1e9
    yt[a, a] += gs; yt[b, b] += gs; yt[a, b] -= gs; yt[b, a] -= gs
    g0 = idx[ground]; keep = [i for i in range(n) if i != g0]
    I = np.zeros(n, complex); I[idx[drive + '_V']] = 1; I[idx[drive + '_G']] = -1
    V = np.zeros(n, complex); V[keep] = np.linalg.solve(yt[np.ix_(keep, keep)], I[keep])
    return V[idx[drive + '_V']] - V[idx[drive + '_G']]


for fr, y in Y.items():
    if fr == 0: continue
    w = 2 * np.pi * fr
    for bank in ('C_bot', 'C_top', 'BULK_R', 'BULK_L', 'B_bot', 'B_top'):
        z = loop_z(y, bank, 'devC')
        print(f'  f={fr / 1e6:g} MHz  {bank:7s} -> leg C short: L = {z.imag / w * 1e12:7.1f} pH  R = {z.real * 1e3:6.3f} mOhm')
