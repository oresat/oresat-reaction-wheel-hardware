"""Ring frequencies and decay after each edge, from post_tran.py output.
python ring_fit.py <results.npz> [...]
Per edge (times from the HI command edge):
  device current, band > 30 MHz, 0-300 ns: dominant f (Hann FFT peak), peak, 1/e envelope time
  probe high band (> 30 MHz), 0-300 ns: same
  probe bus band (1-30 MHz), 0.1-4 us: dominant f; peak |v| in delay windows (the modes beat, so no single tau)"""
import sys
import numpy as np
from scipy.signal import hilbert


def band(x, dt, lo, hi):
    f = np.fft.rfftfreq(len(x), dt); return np.fft.irfft(np.fft.rfft(x) * ((f > lo) & (f < hi)), n=len(x))


def ring(t, x, t0, t1, pad=8):
    m = (t >= t0) & (t < t1); y = x[m]; tt = t[m]; dt = tt[1] - tt[0]
    n = len(y) * pad; F = np.abs(np.fft.rfft(y * np.hanning(len(y)), n=n)); f = np.fft.rfftfreq(n, dt)
    fpk = f[1:][np.argmax(F[1:])]
    env = np.abs(hilbert(y)); i0 = np.argmax(env); a0 = env[i0]
    after = np.nonzero(env[i0:] < a0 / np.e)[0]
    return fpk, a0, (after[0] * dt) if len(after) else np.nan


WIN = ((0.1e-6, 0.3e-6), (0.3e-6, 0.6e-6), (0.6e-6, 1.2e-6), (1.2e-6, 2.5e-6))
for fn in sys.argv[1:]:
    z = np.load(fn); t = z['t']; dt = t[1] - t[0]
    print('==', fn)
    for edge in ('on', 'off'):
        te = float(z[f't_{edge}'])
        f, a, tau = ring(t, band(z['idev'], dt, 30e6, 2e9), te, te + 300e-9)
        print(f'  {edge:3s} device current >30 MHz  {f / 1e6:6.1f} MHz  pk {a:6.2f} A    1/e {tau * 1e9:5.1f} ns')
        for p in ('P105', 'P110'):
            f, a, tau = ring(t, band(z[f'wav_{p}'], dt, 30e6, 2e9), te, te + 300e-9)
            print(f'  {edge:3s} {p} >30 MHz          {f / 1e6:6.1f} MHz  pk {a * 1e3:6.2f} mV   1/e {tau * 1e9:5.1f} ns')
            bb = band(z[f'wav_{p}'], dt, 1e6, 30e6)
            f, a, _ = ring(t, bb, te + 0.1e-6, te + 4e-6)
            tc = t - te
            pk = [np.abs(bb[(tc >= a_) & (tc < b_)]).max() * 1e3 for a_, b_ in WIN]
            print(f'  {edge:3s} {p} 1-30 MHz         {f / 1e6:6.2f} MHz  |v| mV at 0.1-0.3/0.3-0.6/0.6-1.2/1.2-2.5 us: '
                  + ' / '.join(f'{v:.2f}' for v in pk))
