"""Unit test: trapezoid harmonics -> irfft reproduces the trapezoid (minus its mean) when H = 1."""
import numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ac_bus as ab
nh = int(ab.F_MAX / ab.F_PWM); N = 2 * (nh + 1); T = 1 / ab.F_PWM
c = ab.trapezoid_harmonics(nh, 2.0, 0.3, 5e-9)
spec = c.copy(); spec[0] = 0
v = np.fft.irfft(spec * N, n=N); t = np.arange(N) * T / N
tt = np.where(t > T / 2, t - T, t)                      # centred time
ref = np.clip((0.3 * T / 2 + 2.5e-9 - np.abs(tt)) / 5e-9, 0, 1) * 2.0
ref = ref - ref.mean()
err = np.abs(v - ref).max()
print(f'max error {err:.4f} A on a 2 A trapezoid (Gibbs-limited near the 5 ns edges), mean {v.mean():.2e}')
print('PASS' if err < 0.05 else 'FAIL')
