"""Murata SimSurfing MLCC netlists (R/L/C ladders, one per DC bias) -> two-terminal impedance Z(f).

The .mod files live in murata_dl/ (downloaded with ~/.local/bin/download_murata_mlcc, 25 degC).
GRT155C81C225ME13 (the BOM's 2.2 uF 0402) has no SimSurfing model; GRT155C81C225KE13 (same size, dielectric,
rating and series; tolerance code K instead of M) is the proxy.
"""
import os, re
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DL = os.path.join(HERE, 'murata_dl')
PARTS = {'2u2_0402': 'GRT155C81C225KE13', '10u_0603': 'GRT188C81C106ME13', '47u_1210': 'GRT32EC81C476KE13'}


def mod_path(key, vbias):
    return os.path.join(DL, f'{PARTS[key]}_DC{vbias:g}V_25degC.mod')


def parse(path):
    """returns (subckt name, ports, [(kind, n1, n2, value)])"""
    elems, name, ports = [], None, None
    for ln in open(path):
        t = ln.split()
        if not t or t[0].startswith('*'): continue
        if t[0].upper() == '.SUBCKT': name, ports = t[1], t[2:4]; continue
        if t[0][0].upper() in 'RLC': elems.append((t[0][0].upper(), t[1], t[2], float(t[3])))
    return name, ports, elems


def z_of(path, f):
    """Z(f) between the two subckt ports, by nodal analysis (port2 = reference)."""
    _, (p1, p2), elems = parse(path)
    nodes = sorted({n for _, a, b, _ in elems for n in (a, b)} - {p2})
    ix = {n: i for i, n in enumerate(nodes)}
    f = np.atleast_1d(np.asarray(f, float)); out = np.zeros(len(f), complex)
    for k, fk in enumerate(f):
        s = 2j * np.pi * fk; Y = np.zeros((len(nodes), len(nodes)), complex)
        for kind, a, b, v in elems:
            y = 1 / v if kind == 'R' else (1 / (s * v) if kind == 'L' else s * v)
            for u, w in ((a, b), (b, a)):
                if u in ix:
                    Y[ix[u], ix[u]] += y
                    if w in ix: Y[ix[u], ix[w]] -= y
        I = np.zeros(len(nodes), complex); I[ix[p1]] = 1
        out[k] = np.linalg.solve(Y, I)[ix[p1]]
    return out


_cache = {}


def z_part(key, vbias, f):
    p = mod_path(key, vbias)
    if not os.path.exists(p): raise FileNotFoundError(p)
    return z_of(p, f)


def summary(key, vbias):
    """C at 10 kHz, series-resonance frequency, |Z| and ESR there, ESL from |Z| at 10x SRF."""
    f = np.logspace(3, 9.5, 2000); z = z_part(key, vbias, f)
    c = -1 / (2 * np.pi * 1e4 * np.interp(1e4, f, z.imag))
    i = np.argmin(np.abs(z)); srf = f[i]
    j = np.argmin(np.abs(f - 10 * srf)); esl = z[j].imag / (2 * np.pi * f[j])
    return dict(C=c, srf=srf, esr=z[i].real, esl=esl)


if __name__ == '__main__':
    for v in (7.6, 8.4):
        for k in PARTS:
            s = summary(k, v)
            print(f'{v:4.1f} V {k:9s} {PARTS[k]}: C {s["C"] * 1e6:6.2f} uF  SRF {s["srf"] / 1e6:6.2f} MHz  '
                  f'ESR {s["esr"] * 1e3:5.2f} mOhm  ESL(10xSRF) {s["esl"] * 1e12:5.0f} pH')
