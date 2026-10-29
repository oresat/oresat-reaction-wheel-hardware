"""Frequency-domain bus model from the PEEC terminal Y-matrix, and the VBUS waveform at the feed probes.

usage: python ac_bus.py <mp_root> [--leg C] [--i0 1.0] [--duty 0.5] [--tr 2e-9] [--vbias 8.4] [--fr none] [--out f.npz]

Board: Y(f) from assemble_y.py at DC and 10 MHz, reduced to hub-referenced ports, Z = R(f) + jwL with
L = L(10 MHz) and R(f) = R_dc + (R_10M - R_dc) sqrt(f / 10 MHz) (or R fixed at the blend for f = --fr, which is
what the SPICE export does).
External parts (two-terminal admittances between terminal pairs):
  cap banks: Murata SimSurfing ladders at the DC bias (murata.py), N parts in parallel
  FEED port: feed continuation to J1 (L_EXT) then C2/C27 (2 x 47 uF) in parallel with the source (R_SRC + jw L_SRC)
Excitation: the switching leg draws current between its VIN and PGND pads; the other legs are open. With a constant
phase current the device port current is the HS current, so I_dev(t) is the excitation for any edge shape.
Transfers per amp of device current: device port impedance zdev, probe voltages H[P], feed current HI (FEED port,
positive toward J1 on VBUS).
"""
import argparse, os
import numpy as np
import murata

BANK_PARTS = {'A_bot': {'2u2_0402': 5}, 'B_bot': {'2u2_0402': 5}, 'C_bot': {'2u2_0402': 5},
              'A_top': {'10u_0603': 5, '2u2_0402': 5}, 'B_top': {'10u_0603': 5, '2u2_0402': 5}, 'C_top': {'10u_0603': 5, '2u2_0402': 5},
              'BULK_L': {'47u_1210': 4}, 'BULK_R': {'47u_1210': 4}}
FEED_CAPS = {'47u_1210': 2}                                         # C2, C27 at J1
L_EXT = {'intended': 10 * 16.5e-12, 'asbuilt': 10 * 22.0e-12}     # ~10 mm of feed to J1, 2D per-mm loop L
R_EXT = 1.0e-3
L_SRC, R_SRC = 100e-9, 50e-3                                        # harness + pack (Solomon: good starting point)
F_PWM, F_MAX = 96e3, 1.0e9


def load(stack_root):
    z = np.load(os.path.join(stack_root, 'ymat.npz'), allow_pickle=True)
    terms = list(z['terms']); nets = list(z['nets']); freqs = list(z['freqs']); Y = {f: y for f, y in zip(freqs, z['Y'])}
    return terms, nets, Y


def port_model(terms, nets, Y, hubs=('devC_V', 'devC_G')):
    """hub-referenced port impedances: returns (A, Rdc, R10, L10, f10, ports) with port voltage = A @ terminal voltages."""
    n = len(terms); hub = {'VBUS': terms.index(hubs[0]), 'PGND': terms.index(hubs[1])}
    ports = [i for i in range(n) if i not in hub.values()]
    A = np.zeros((len(ports), n))
    for r, i in enumerate(ports): A[r, i] = 1; A[r, hub[nets[i]]] = -1
    f10 = max(Y); w10 = 2 * np.pi * f10
    Z0 = np.linalg.inv(Y[0.0][np.ix_(ports, ports)]).real
    Z10 = np.linalg.inv(Y[f10][np.ix_(ports, ports)])
    return A, Z0, Z10.real, Z10.imag / w10, f10, ports


def r_blend(Rdc, R10, f10, f):
    return Rdc + (R10 - Rdc) * np.sqrt(f / f10)


def y_board(f, A, Rdc, R10, L10, f10, fr=None):
    R = r_blend(Rdc, R10, f10, f if fr is None else fr)
    return A.T @ np.linalg.inv(R + 1j * 2 * np.pi * f * L10) @ A


def bank_y(f, parts, vbias):
    return sum(cnt / murata.z_part(k, vbias, f) for k, cnt in parts.items())


class Bus:
    """board + externals at one stack / bias; solve(f) gives the transfers per amp of device current."""

    def __init__(self, stack_root, stack, leg='C', vbias=8.4, fr=None):
        self.terms, self.nets, Y = load(stack_root); self.n = len(self.terms)
        self.ix = {t: i for i, t in enumerate(self.terms)}
        self.A, self.Rdc, self.R10, self.L10, self.f10, _ = port_model(self.terms, self.nets, Y)
        self.stack, self.leg, self.vbias, self.fr = stack, leg, vbias, fr
        self.probes = sorted({t[:-2] for t in self.terms if t.startswith('P') and t[-2:] in ('_V', '_G')})

    def y_feed(self, f):
        w = 2 * np.pi * f
        z_c2 = 1 / bank_y(f, FEED_CAPS, self.vbias); z_src = R_SRC + 1j * w * L_SRC
        return 1 / (R_EXT + 1j * w * L_EXT[self.stack] + z_c2 * z_src / (z_c2 + z_src))

    def solve(self, fgrid):
        ix, n, leg = self.ix, self.n, self.leg
        g0 = ix[f'dev{leg}_G']; keep = [i for i in range(n) if i != g0]
        fgrid = np.atleast_1d(fgrid)
        bank = {b: bank_y(fgrid, p, self.vbias) for b, p in BANK_PARTS.items()}
        yfeed = self.y_feed(fgrid)
        zdev = np.zeros(len(fgrid), complex); HI = np.zeros(len(fgrid), complex)
        H = {p: np.zeros(len(fgrid), complex) for p in self.probes}
        for k, f in enumerate(fgrid):
            yt = y_board(max(f, 1.0), self.A, self.Rdc, self.R10, self.L10, self.f10, self.fr).astype(complex)

            def add(a, b, y):
                i, j = ix[a], ix[b]; yt[i, i] += y; yt[j, j] += y; yt[i, j] -= y; yt[j, i] -= y
            for b in BANK_PARTS: add(b + '_V', b + '_G', bank[b][k])
            add('FEED_V', 'FEED_G', yfeed[k])
            I = np.zeros(n, complex); I[ix[f'dev{leg}_V']] = -1; I[ix[f'dev{leg}_G']] = +1   # device draws 1 A from VIN, returns it to PGND
            V = np.zeros(n, complex); V[keep] = np.linalg.solve(yt[np.ix_(keep, keep)], I[keep])
            zdev[k] = -(V[ix[f'dev{leg}_V']] - V[ix[f'dev{leg}_G']])
            HI[k] = yfeed[k] * (V[ix['FEED_V']] - V[ix['FEED_G']])
            for p in self.probes: H[p][k] = V[ix[p + '_V']] - V[ix[p + '_G']]
        return zdev, H, HI


def trapezoid_harmonics(nh, i0, duty, tr):
    """Fourier coefficients c_k (k = 0..nh, x(t) = sum_k c_k e^{jwkt} over all k) of a periodic trapezoid centred at
    t = 0: full width at half height duty*T, rise and fall tr. Trapezoid = box(duty*T) convolved with a unit-area box(tr)."""
    T = 1 / F_PWM; W = duty * T; w = 2 * np.pi * np.arange(nh + 1) / T
    sinc = lambda x: np.sinc(x / np.pi)                      # sin(x)/x
    return i0 * W / T * sinc(w * W / 2) * sinc(w * tr / 2)


def periodic_response(c, h):
    """time samples over one period of sum_k c_k h_k e^{jwkt} (DC term omitted: static IR drop)."""
    nh = len(c) - 1; N = 2 * (nh + 1)
    spec = np.zeros(nh + 1, complex); spec[1:] = c[1:] * h
    return np.fft.irfft(spec * N, n=N)                       # x[m] = sum_k c_k e^{...}: irfft needs X_k = N c_k


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('mp_root'); ap.add_argument('--leg', default='C')
    ap.add_argument('--i0', type=float, default=1.0); ap.add_argument('--duty', type=float, default=0.5)
    ap.add_argument('--tr', type=float, default=2e-9); ap.add_argument('--vbias', type=float, default=8.4)
    ap.add_argument('--fr', type=float, default=None); ap.add_argument('--out', default=None)
    a = ap.parse_args()
    nh = int(F_MAX / F_PWM)
    fh = F_PWM * np.arange(1, nh + 1)
    fz = np.logspace(4, 9, 400)
    out = {}
    for stack in ('intended', 'asbuilt'):
        sr = os.path.join(a.mp_root, stack)
        if not os.path.exists(os.path.join(sr, 'ymat.npz')): print('missing', stack); continue
        bus = Bus(sr, stack, a.leg, a.vbias, a.fr)
        zdev, Hz, HIz = bus.solve(fz)
        _, Hh, HIh = bus.solve(fh)
        c = trapezoid_harmonics(nh, a.i0, a.duty, a.tr)
        T = 1 / F_PWM; N = 2 * (nh + 1); t = np.arange(N) * T / N
        wav = {p: periodic_response(c, h) for p, h in Hh.items()}
        out[stack] = dict(fz=fz, zdev=zdev, H=Hz, HI=HIz, t=t, wav=wav, ifeed=periodic_response(c, HIh))
        for p in Hz:
            v = wav[p]
            print(f'{stack:8s} {p}: |H| @1MHz {np.interp(1e6, fz, np.abs(Hz[p])) * 1e3:.3f} mV/A, @100MHz {np.interp(1e8, fz, np.abs(Hz[p])) * 1e3:.3f} mV/A;'
                  f' waveform p-p {(v.max() - v.min()) * 1e3:.2f} mV for {a.i0:g} A, duty {a.duty}, tr {a.tr * 1e9:g} ns')
        sel = fz < 3e7; pk = fz[sel][np.argmax(np.abs(zdev[sel]))]
        print(f'{stack:8s} |Z| at leg {a.leg}: peak {np.abs(zdev[sel]).max() * 1e3:.2f} mOhm at {pk / 1e6:.2f} MHz;'
              f' feed current p-p {np.ptp(out[stack]["ifeed"]):.3f} A per {a.i0:g} A')
    if a.out:
        np.savez(a.out, **{f'{s}_{k}': v for s, d in out.items() for k, v in d.items() if k in ('fz', 'zdev', 't', 'HI', 'ifeed')},
                 **{f'{s}_H_{p}': h for s, d in out.items() for p, h in d['H'].items()},
                 **{f'{s}_wav_{p}': w for s, d in out.items() for p, w in d['wav'].items()})


if __name__ == '__main__':
    main()
