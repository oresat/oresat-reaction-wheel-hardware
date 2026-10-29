"""Full bus state per harmonic for a switching period, and the frame weights for the field animation.

usage: python bus_state.py <stack> <vbias> <results.npz from post_tran.py> <out.npz>

For the leg-C device-current spectrum c_k (two-sided, k = 0..nh) of one PWM period, solves the bus circuit of
sims/bus-ring/ac_bus.py at every harmonic and keeps all 28 terminal voltages and the current each external part
injects into the board at each terminal. The port current of terminal p (non-hub) is that injection: it enters at p
and leaves at the net's hub (devC_V for VBUS, devC_G for PGND).

Field weights (see post_fields.py). With unit-port-current fields B_p at DC and at 10 MHz,
  J(r,t) = sum_p a_p(t) B_p^DC(r) + b_p(t) Re B_p^10M(r) - c_p(t) Im B_p^10M(r)
  a_p(t) = I_p,0 + 2 Re sum_k (1 - w_k) I_p,k e^{j w_k t}
  b_p(t) = 2 Re sum_k w_k I_p,k e^{j w_k t},  c_p(t) = 2 Im sum_k w_k I_p,k e^{j w_k t}
with w_k = f^2 / (f^2 + FC^2), FC = 1 MHz (where wL ~ R for the bank and bulk loops: 0.5-1.3 MHz).
"""
import argparse, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
BR = os.path.join(os.path.dirname(HERE), 'bus-ring')
sys.path.insert(0, BR)
import ac_bus as ab

FC = 1e6


def frame_times(t_on):
    """times in the period (s): baseline, the HS-on burst at 0.25 ns, then log-spaced to just before HS off."""
    pre = [t_on - 100e-9]
    burst = t_on + np.arange(32e-9, 64e-9 + 1e-12, 0.25e-9)
    slow = t_on + np.geomspace(66e-9, 5000e-9, 40)
    return np.concatenate([pre, burst, slow]), dict(pre=1, burst=len(burst), slow=len(slow))


def state(bus, fgrid):
    """terminal voltages V (nf x 28) and board injections I (nf x 28) per amp of device current."""
    ix, n = bus.ix, bus.n
    g0 = ix['devC_G']; keep = [i for i in range(n) if i != g0]
    bank = {b: ab.bank_y(fgrid, p, bus.vbias) for b, p in ab.BANK_PARTS.items()}
    yfeed = bus.y_feed(fgrid)
    Vs = np.zeros((len(fgrid), n), complex); Is = np.zeros((len(fgrid), n), complex)
    for k, f in enumerate(fgrid):
        yb = ab.y_board(max(f, 1.0), bus.A, bus.Rdc, bus.R10, bus.L10, bus.f10).astype(complex)
        yt = yb.copy()

        def add(a, b, y):
            i, j = ix[a], ix[b]; yt[i, i] += y; yt[j, j] += y; yt[i, j] -= y; yt[j, i] -= y
        for b in ab.BANK_PARTS: add(b + '_V', b + '_G', bank[b][k])
        add('FEED_V', 'FEED_G', yfeed[k])
        I = np.zeros(n, complex); I[ix['devC_V']] = -1; I[ix['devC_G']] = +1
        V = np.zeros(n, complex); V[keep] = np.linalg.solve(yt[np.ix_(keep, keep)], I[keep])
        Vs[k] = V; Is[k] = yb @ V                                   # current into the board copper at each terminal
    return Vs, Is


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('stack'); ap.add_argument('vbias', type=float)
    ap.add_argument('res'); ap.add_argument('out'); a = ap.parse_args()
    z = np.load(a.res); c = z['c']; nh = len(c) - 1
    T = 1 / ab.F_PWM; f = ab.F_PWM * np.arange(nh + 1); f[0] = 1.0                 # DC solved at 1 Hz (caps open)
    bus = ab.Bus(os.path.join(BR, 'mp', a.stack), a.stack, 'C', a.vbias)
    Vs, Is = state(bus, f)
    terms = bus.terms; hubs = {'devC_V', 'devC_G'}
    ports = [i for i, t in enumerate(terms) if t not in hubs]
    Ip = Is[:, ports] * c[:, None]                                               # two-sided port-current coefficients
    t_on = float(z['t_on']); tf, seg = frame_times(t_on)
    w = f ** 2 / (f ** 2 + FC ** 2); w[0] = 0.0
    E = np.exp(2j * np.pi * np.outer(tf, ab.F_PWM * np.arange(nh + 1)))            # e^{j w_k t}
    lf = (1 - w)[:, None] * Ip; hf = w[:, None] * Ip
    A = np.real(Ip[0])[None, :] + 2 * np.real(E[:, 1:] @ lf[1:])
    S = 2 * (E[:, 1:] @ hf[1:])
    Bw, Cw = np.real(S), np.imag(S)
    # port currents vs time (all bands) on a fine grid for plots
    N = 2 ** 16; tt = np.arange(N) * T / N
    spec = np.zeros((N // 2 + 1, len(ports)), complex); spec[:nh + 1] = Ip
    it = np.fft.irfft(spec * N, n=N, axis=0)
    np.savez(a.out, terms=np.array(terms), ports=np.array([terms[i] for i in ports]), tf=tf, t_on=t_on,
             seg=np.array([seg['pre'], seg['burst'], seg['slow']]), A=A, B=Bw, C=Cw, FC=FC, tt=tt, i_ports=it.astype(np.float32),
             idev=z['idev'], t_dev=z['t'])
    k = int(np.argmin(np.abs(tf - (t_on + 39e-9))))
    print(a.stack, 'frames', len(tf), 'max |a|', np.abs(A).max().round(2), 'max |b|', np.abs(Bw).max().round(2),
          'sum of port currents at the edge (VBUS)', round(sum(A[k, j] + Bw[k, j] for j, p in enumerate(ports) if terms[p].endswith('_V')), 2))


if __name__ == '__main__':
    main()
