"""Plot ac_bus.py output: python plot_bus.py <bus_results.npz> <out.png> [--duty 0.5]
Panels: |Z| at the device and |H| to the probes vs f; probe voltage over a period; zoom on the rising edge."""
import sys, argparse
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

ap = argparse.ArgumentParser(); ap.add_argument('npz'); ap.add_argument('png'); ap.add_argument('--duty', type=float, default=0.5)
a = ap.parse_args()
z = np.load(a.npz)
stacks = [s for s in ('intended', 'asbuilt') if f'{s}_fz' in z]
fig, ax = plt.subplots(3, 1, figsize=(10, 12))
for s, ls in zip(stacks, ('-', '--')):
    fz = z[f'{s}_fz']; zd = np.abs(z[f'{s}_zdev'])
    ax[0].loglog(fz, zd * 1e3, 'k' + ls, label=f'{s} |Z| device port (mOhm)')
    pk, _ = find_peaks(np.log(zd)); print(s, 'Z_dev peaks:', ', '.join(f'{fz[i] / 1e6:.3g} MHz {zd[i] * 1e3:.2f} mOhm' for i in pk))
    for p, c in (('P105', 'C0'), ('P110', 'C1')):
        h = np.abs(z[f'{s}_H_{p}'])
        ax[0].loglog(fz, h * 1e3, c + ls, label=f'{s} |H| {p} (mV/A)')
        pk, _ = find_peaks(np.log(h)); print(s, p, 'H peaks:', ', '.join(f'{fz[i] / 1e6:.3g} MHz {h[i] * 1e3:.2f} mV/A' for i in pk))
    ax[0].loglog(fz, np.abs(z[f'{s}_HI']), 'C2' + ls, label=f'{s} |I_feed / I_dev|')
    t = z[f'{s}_t']; T = t[-1] + t[1]; tt = np.where(t > T / 2, t - T, t); o = np.argsort(tt)
    for p, c in (('P105', 'C0'), ('P110', 'C1')):
        v = z[f'{s}_wav_{p}']
        ax[1].plot(tt[o] * 1e6, v[o] * 1e3, c + ls, label=f'{s} {p}')
        te = -a.duty * T / 2; m = (tt > te - 100e-9) & (tt < te + 400e-9); oo = np.argsort(tt[m])
        ax[2].plot((tt[m][oo] - te) * 1e9, v[m][oo] * 1e3, c + ls, label=f'{s} {p}')
ax[0].set_xlabel('f (Hz)'); ax[0].legend(fontsize=7); ax[0].grid(True, which='both', alpha=.3)
ax[1].set_xlabel('t (us)'); ax[1].set_ylabel('mV'); ax[1].legend(fontsize=7); ax[1].grid(alpha=.3)
ax[2].set_xlabel('t from rising edge (ns)'); ax[2].set_ylabel('mV'); ax[2].legend(fontsize=7); ax[2].grid(alpha=.3)
fig.tight_layout(); fig.savefig(a.png, dpi=110)
