"""Xyce leg-C transient -> device current over the last PWM period -> probe voltages and feed current by the full
frequency-domain bus model (R(f), Murata ladders), plus checks against Xyce's own device-port voltage and feed current.

usage: python post_tran.py <xyce csv> <stack_root> <stack> <vbias> <out prefix> [--duty 0.5]
writes <prefix>.npz and <prefix>.png; prints edge metrics.
"""
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ac_bus as ab, xycsv
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser(); ap.add_argument('csv'); ap.add_argument('stack_root'); ap.add_argument('stack')
ap.add_argument('vbias', type=float); ap.add_argument('out'); ap.add_argument('--duty', type=float, default=0.5)
ap.add_argument('--fr', type=float, default=1e7, help='R blend frequency of the Xyce board export (check only)')
a = ap.parse_args()
d = xycsv.load(a.csv); t = d['TIME']
T = 1 / ab.F_PWM; nper = int(round(t[-1] / T)); t0 = (nper - 1) * T          # last period
t_on = t0 + T / 2 - a.duty * T / 2; t_off = t0 + T / 2 + a.duty * T / 2      # HI command edges

# uniform resample of the last period; the window starts and ends in LS-on, where the device current is ~0
NF = 2 ** 20; tu = t0 + np.arange(NF) * T / NF
iu = np.interp(tu, t, d['I(VIVIN)'])
nh = int(ab.F_MAX / ab.F_PWM)
c = np.fft.rfft(iu)[:nh + 1] / NF                                            # two-sided Fourier coefficients
fh = ab.F_PWM * np.arange(1, nh + 1)
bus = ab.Bus(a.stack_root, a.stack, 'C', a.vbias, fr=None)
zdev, H, HI = bus.solve(fh)
bus10 = ab.Bus(a.stack_root, a.stack, 'C', a.vbias, fr=a.fr)
zdev10, _, HI10 = bus10.solve(fh)


def resp(h, nout=2 ** 16):
    spec = np.zeros(nout // 2 + 1, complex); spec[1:nh + 1] = c[1:] * h
    return np.fft.irfft(spec * nout, n=nout)


NO = 2 ** 16; to = t0 + np.arange(NO) * T / NO
wav = {p: resp(h, NO) for p, h in H.items()}
ifeed = resp(HI, NO)
# checks against Xyce (board R fixed at --fr): device-port voltage and feed current above 1 MHz (Xyce's last period
# still carries the start-up transient of the source/bulk mode, ~40 kHz, which the periodic FD solution does not)
vdev_x = np.interp(to, t, d['V(DEVC_V)']); vdev_x -= vdev_x.mean()
vdev_f10 = -resp(zdev10, NO); vdev_f = -resp(zdev, NO)
ifeed_x = np.interp(to, t, d['I(VFS)']); ifeed_x -= ifeed_x.mean()
ifeed_f10 = resp(HI10, NO)
fo = np.fft.rfftfreq(NO, T / NO)
ramp = lambda x: x - x[0] - (x[-1] - x[0]) * np.arange(NO) / (NO - 1)        # no wrap step from the unsettled start-up
hp = lambda x: np.fft.irfft(np.fft.rfft(ramp(x)) * (fo > 1e6), n=NO)
rel = lambda x, y: float(np.sqrt(np.mean((hp(x) - hp(y)) ** 2) / np.mean(hp(y) ** 2)))
chk = {'vdev >1MHz rms err (FD R(fr) vs Xyce)': rel(vdev_f10, vdev_x), 'ifeed >1MHz rms err (FD R(fr) vs Xyce)': rel(ifeed_f10, ifeed_x)}
print(json.dumps(chk))

# edge metrics
sw = d['V(SW)']; met = {}
for name, te, sgn in (('on', t_on, +1), ('off', t_off, -1)):
    m = (t > te) & (t < te + 200e-9); tt, v = t[m], sw[m]
    lo, hi = 0.1 * a.vbias, 0.9 * a.vbias
    try:
        if sgn > 0: t1 = tt[np.argmax(v > lo)]; t2 = tt[np.argmax(v > hi)]
        else: t1 = tt[np.argmax(v < hi)]; t2 = tt[np.argmax(v < lo)]
        met[f'sw_{name}_10_90_ns'] = (t2 - t1) * 1e9; met[f'sw_{name}_delay_ns'] = ((t1 + t2) / 2 - te) * 1e9
    except Exception: pass
    met[f'sw_{name}_max_V'] = float(v.max()); met[f'sw_{name}_min_V'] = float(v.min())
    mi = (t > te) & (t < te + 200e-9); idv = d['I(VIVIN)'][mi]; ti = t[mi]
    didt = np.gradient(idv, ti); met[f'idev_{name}_didt_max_A_per_ns'] = float(np.abs(didt).max() * 1e-9)
    met[f'idev_{name}_peak_A'] = float(idv.max()); met[f'idev_{name}_min_A'] = float(idv.min())
    vd = d['V(DEVC_V)'][mi]; met[f'vdev_{name}_pk_pk_V'] = float(np.ptp(vd))
    tc = (to - te)
    for p in wav:
        w = wav[p]; win = (tc > -20e-9) & (tc < 0); base = w[win].mean()
        for lab, t_a, t_b in (('spike', 0, 20e-9), ('ring20_200', 20e-9, 200e-9), ('ring200_1000', 200e-9, 1000e-9)):
            mm = (tc >= t_a) & (tc < t_b)
            met[f'{p}_{name}_{lab}_pk_mV'] = float(np.abs(w[mm] - base).max() * 1e3)
    mm = (tc >= 0) & (tc < 200e-9); fb = (tc > -20e-9) & (tc < 0)
    met[f'ifeed_{name}_dIdt_max_A_per_ns'] = float(np.abs(np.gradient(ifeed[mm], to[mm])).max() * 1e-9)
for k, v in met.items(): print(f'{k:34s} {v: .4g}')

np.savez(a.out + '.npz', t=to - t0, idev=np.interp(to, t, d['I(VIVIN)']), sw=np.interp(to, t, sw), ifeed=ifeed,
         vdev_fd=vdev_f, vdev_x=vdev_x, ifeed_x=ifeed_x, t_on=t_on - t0, t_off=t_off - t0, c=c,
         **{f'wav_{p}': w for p, w in wav.items()}, met=json.dumps(met), chk=json.dumps(chk))

fig, ax = plt.subplots(4, 3, figsize=(15, 12))
for col, (name, te) in enumerate((('period', None), ('HS on', t_on), ('HS off', t_off))):
    if te is None: m = np.ones(NO, bool); x = (to - t0) * 1e6; xl = 't in period (us)'
    else: m = (to > te - 30e-9) & (to < te + 600e-9); x = (to - te) * 1e9; xl = f't from HI {name} (ns)'
    mx = (t > (te if te else t0) - 30e-9) & (t < (te if te else t0 + T) + 600e-9) if te else (t >= t0)
    xx = (t[mx] - te) * 1e9 if te else (t[mx] - t0) * 1e6
    ax[0, col].plot(xx, sw[mx], lw=.8, label='V(SW)'); ax[0, col].plot(xx, d['I(VIVIN)'][mx], lw=.8, label='I dev (A)')
    ax[1, col].plot(x[m], vdev_x[m] * 1e3, lw=.8, label='Xyce V dev (R@10MHz)'); ax[1, col].plot(x[m], vdev_f[m] * 1e3, lw=.8, label='FD V dev, R(f)')
    for p in wav: ax[2, col].plot(x[m], wav[p][m] * 1e3, lw=.8, label=f'{p} (FD)')
    ax[3, col].plot(x[m], ifeed_x[m], lw=.8, label='Xyce I feed'); ax[3, col].plot(x[m], ifeed[m], lw=.8, label='FD I feed')
    for r, yl in enumerate(('V, A', 'device port AC (mV)', 'probe AC (mV)', 'feed current AC (A)')):
        ax[r, col].set_ylabel(yl); ax[r, col].grid(alpha=.3); ax[r, col].legend(fontsize=7)
    ax[3, col].set_xlabel(xl)
fig.suptitle(f'{a.stack} {a.vbias} V, leg C, {os.path.basename(a.csv)}'); fig.tight_layout(); fig.savefig(a.out + '.png', dpi=90)
