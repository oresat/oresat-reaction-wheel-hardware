"""Compact field products from the PyPEEC fields_all.npz of one stack (run on tinyhorse, in ~/rw8-fields).

usage: python post_fields.py <stack>      reads mp/<stack>/lane*/fields_all.npz + terminals.json, mp/<stack>/meta.json,
                                         state_<stack>.npz (from bus_state.py); writes products/<stack>/*.npz

1. Unit-port-current fields. Sweep j holds terminal voltages Vm[:, j] (driven terminal 1 mV, the rest 0 V). For a
   wanted terminal-voltage vector v the field is F @ inv(Vm) @ v. Port p = terminal p against its net's hub
   (devC_V / devC_G); unit current into port p gives v = [Zp[:, p] on the ports, 0 on the hubs], Zp = inv(Y_ports).
   Done at DC and at 10 MHz -> BJ0, BJ1 (current density) and BV0, BV1 (copper potential).
2. Loop scenarios: 1 A out of a bank's (or the feed's) VBUS terminal, through leg C's device, back into its PGND
   terminal: B_<x>_V - B_<x>_G, at DC and 10 MHz.
3. Frames: J(t) = Re BJ0 a(t) + Re BJ1 b(t) - Im BJ1 c(t) (weights from bus_state.py).
4. Per-layer reduction: sheet current K = sum_z J dz (A/m) per copper layer, layer-mean potential, via current
   Jz dx dy (A) at mid-gap.
5. B slices (exact cell-integrated 1/r kernel, FFT convolution, as power-stage-rev8/docs/stackup-sim/scripts/bfield.py)
   for the scenarios and a few frames: mid-gap x-y planes, y-z at x = 98 mm, x-z at y = 105 mm.
"""
import glob, json, os, sys, time
import numpy as np, scipy.sparse as sps, scipy.fft as sf

MU0 = 4e-7 * np.pi
stack = sys.argv[1]; root = os.path.join('mp', stack); out = os.path.join('products', stack)
os.makedirs(out, exist_ok=True); t0 = time.time()
log = lambda *a: print(f'[{time.time() - t0:7.1f} s]', *a, flush=True)
meta = json.load(open(os.path.join(root, 'meta.json')))
terms = list(meta['terminals']); nets = [meta['terminals'][t]['net'] for t in terms]; n = len(terms)
tix = {t: i for i, t in enumerate(terms)}
hubs = [tix['devC_V'], tix['devC_G']]; ports = [i for i in range(n) if i not in hubs]

# ---- load sweeps
F = {}; Vm = {}; Im = {}; idx = None
for lane in sorted(glob.glob(os.path.join(root, 'lane*'))):
    T = json.load(open(os.path.join(lane, 'terminals.json')))['sweeps']
    Z = np.load(os.path.join(lane, 'fields_all.npz'))
    if idx is None:
        idx = Z['idx_vc']; nn = [int(v) for v in Z['n']]; d = [float(v) for v in Z['d']]
    else:
        assert np.array_equal(idx, Z['idx_vc']), 'voxel sets differ between lanes'
    for tag, s in T.items():
        f = s['freq']; j = tix[tag.split('__t_')[1]]
        F.setdefault(f, {})[j] = (Z['J_' + tag].reshape(len(idx), -1)[:, :3].astype(np.complex64), Z['V_' + tag].reshape(-1).astype(np.complex64))
        Vm.setdefault(f, np.zeros((n, n), complex)); Im.setdefault(f, np.zeros((n, n), complex))
        for k, v in s['sources'].items():
            Vm[f][tix[k[2:]], j] = complex(*v['V']); Im[f][tix[k[2:]], j] = complex(*v['I'])
    log('loaded', lane)
freqs = sorted(F); assert len(freqs) == 2 and all(len(F[f]) == n for f in freqs), {f: len(F[f]) for f in F}
nv = len(idx); nx, ny, nz = nn; dx, dy, dz = d
ix = idx % nx; iy = (idx // nx) % ny; iz = idx // (nx * ny)

# ---- unit-port-current bases
BJ, BV = {}, {}
for f in freqs:
    Y = Im[f] @ np.linalg.inv(Vm[f])
    Zp = np.linalg.inv(Y[np.ix_(ports, ports)])
    Vt = np.zeros((n, len(ports)), complex); Vt[ports, :] = Zp
    coef = np.linalg.solve(Vm[f], Vt)                                    # (n sweeps, n ports)
    resid = np.abs((Im[f] @ coef)[ports] - np.eye(len(ports))).max()    # unit current into each port, none elsewhere
    FJ = np.stack([F[f][j][0].reshape(-1) for j in range(n)], 1)         # (nv*3, n)
    FV = np.stack([F[f][j][1] for j in range(n)], 1)
    BJ[f] = (FJ @ coef.astype(np.complex64)); BV[f] = (FV @ coef.astype(np.complex64))
    del FJ, FV
    log(f'basis f={f:g}: port-current residual {resid:.2e}')
del F
f0, f1 = freqs
pname = [terms[i] for i in ports]; pix = {p: k for k, p in enumerate(pname)}

# ---- layer / gap reduction operators
zl = meta['zlay']; order = ['B.Cu', 'In4.Cu', 'In3.Cu', 'In2.Cu', 'In1.Cu', 'F.Cu']
lay = -np.ones(nv, int)
for k, L in enumerate(order):
    z0, z1 = zl[L]; lay[(iz >= z0) & (iz < z1)] = k
flat = ix + nx * iy; nl = len(order)
m = lay >= 0
S_K = sps.csr_matrix((np.full(m.sum(), dz), (lay[m] * nx * ny + flat[m], np.nonzero(m)[0])), shape=(nl * nx * ny, nv))
cnt = np.bincount(lay[m] * nx * ny + flat[m], minlength=nl * nx * ny).astype(float)
S_V = sps.csr_matrix((1.0 / cnt[lay[m] * nx * ny + flat[m]], (lay[m] * nx * ny + flat[m], np.nonzero(m)[0])), shape=(nl * nx * ny, nv))
gaps = [((zl[lo][1] + zl[hi][0]) // 2) for lo, hi in zip(order[:-1], order[1:])]
g = -np.ones(nv, int)
for k, zm in enumerate(gaps): g[iz == zm] = k
mg = g >= 0
S_G = sps.csr_matrix((np.full(mg.sum(), dx * dy), (g[mg] * nx * ny + flat[mg], np.nonzero(mg)[0])), shape=(len(gaps) * nx * ny, nv))
mask = (cnt > 0).reshape(nl, nx * ny)                                    # copper present, per layer


def reduce(J, V):
    """J (nv*3, k), V (nv, k) -> K (k, nl, 2, nx, ny) A/m, Vl (k, nl, nx, ny), Iz (k, ngap, nx, ny) A"""
    k = J.shape[1]; J3 = J.reshape(nv, 3, k)
    Kx = (S_K @ J3[:, 0, :]).reshape(nl, nx * ny, k)
    Ky = (S_K @ J3[:, 1, :]).reshape(nl, nx * ny, k)
    Vl = (S_V @ V).reshape(nl, nx * ny, k); Vl[~mask] = np.nan
    Iz = (S_G @ J3[:, 2, :]).reshape(len(gaps), nx * ny, k)
    to = lambda a, nlay: np.moveaxis(a, -1, 0).reshape(k, nlay, ny, nx).transpose(0, 1, 3, 2)   # flat = ix + nx*iy
    return np.stack([to(Kx, nl), to(Ky, nl)], 2), to(Vl, nl), to(Iz, len(gaps))


# ---- scenarios
loops = ['C_bot', 'C_top', 'B_bot', 'BULK_R', 'BULK_L', 'FEED']
sJ, sV, names = [], [], []
for f, tagf in ((f0, 'dc'), (f1, '10M')):
    for L in loops:
        a_, b_ = pix[L + '_V'], pix[L + '_G']
        sJ.append(BJ[f][:, a_] - BJ[f][:, b_]); sV.append(BV[f][:, a_] - BV[f][:, b_]); names.append(f'{L}_{tagf}')
SJ = np.stack(sJ, 1); SV = np.stack(sV, 1)
K, Vl, Iz = reduce(SJ, SV)
np.savez_compressed(os.path.join(out, 'scen.npz'), names=np.array(names), K=K.astype(np.complex64), V=Vl.astype(np.complex64),
                    Iz=Iz.astype(np.complex64), mask=mask.reshape(nl, ny, nx).transpose(0, 2, 1),
                    order=np.array(order), n=np.array(nn), d=np.array(d), crop=np.array(meta['crop']), pitch=meta['pitch'])
log('scenarios', names)

# ---- frames
st = np.load(f'state_{stack}.npz')
assert list(st['ports']) == pname, 'port order differs'
A = st['A'].astype(np.float32); Bw = st['B'].astype(np.float32); Cw = st['C'].astype(np.float32)
JT = np.real(BJ[f0]).astype(np.float32) @ A.T + np.real(BJ[f1]).astype(np.float32) @ Bw.T - np.imag(BJ[f1]).astype(np.float32) @ Cw.T
VT = np.real(BV[f0]).astype(np.float32) @ A.T + np.real(BV[f1]).astype(np.float32) @ Bw.T - np.imag(BV[f1]).astype(np.float32) @ Cw.T
K, Vl, Iz = reduce(JT, VT)
np.savez_compressed(os.path.join(out, 'frames.npz'), tf=st['tf'], t_on=st['t_on'], seg=st['seg'], K=K.astype(np.float16),
                    V=Vl.astype(np.float16), Iz=Iz.astype(np.float16), order=np.array(order))
log('frames', K.shape)


# ---- B slices
def F_(x, y, z):
    r = np.sqrt(x * x + y * y + z * z)
    with np.errstate(divide='ignore', invalid='ignore'):
        def at(num, den): return np.where(den != 0, np.arctan(num / np.where(den != 0, den, 1.0)), 0.0)
        t = (y * z * np.log(np.where(x + r > 0, x + r, 1.0)) + x * z * np.log(np.where(y + r > 0, y + r, 1.0)) + x * y * np.log(np.where(z + r > 0, z + r, 1.0))
             - 0.5 * x * x * at(y * z, x * r) - 0.5 * y * y * at(x * z, y * r) - 0.5 * z * z * at(x * y, z * r))
    return np.nan_to_num(t)


def kernel(near=(5, 5, 48)):
    kx = np.fft.fftfreq(2 * nx, 1 / (2 * nx)) * dx; ky = np.fft.fftfreq(2 * ny, 1 / (2 * ny)) * dy; kz = np.fft.fftfreq(2 * nz, 1 / (2 * nz)) * dz
    X, Y, Zg = np.meshgrid(kx, ky, kz, indexing='ij'); R = np.sqrt(X * X + Y * Y + Zg * Zg)
    with np.errstate(divide='ignore'): Kk = dx * dy * dz / (4 * np.pi * R)
    mm = (np.abs(X) <= near[0] * dx) & (np.abs(Y) <= near[1] * dy) & (np.abs(Zg) <= near[2] * dz)
    s = 0.0
    for sx, ax_ in ((1, dx / 2), (-1, -dx / 2)):
        for sy, ay_ in ((1, dy / 2), (-1, -dy / 2)):
            for sz, az_ in ((1, dz / 2), (-1, -dz / 2)):
                s = s + sx * sy * sz * F_(X[mm] + ax_, Y[mm] + ay_, Zg[mm] + az_)
    Kk[mm] = s / (4 * np.pi)
    return sf.fftn(Kk, workers=-1)


Kh = kernel(); log('kernel')
x0, y0 = meta['crop'][0], meta['crop'][1]; p = meta['pitch']
kxc = int((98.0 - x0) / p); kyc = int((105.0 - y0) / p)
gz = gaps


def bslices(J):
    """J (nv*3,) complex -> dict of B slices (T), vector components."""
    J3 = J.reshape(nv, 3); Acomp = []
    for c in range(3):
        Jd = np.zeros((2 * nx, 2 * ny, 2 * nz), np.complex128); Jd[ix, iy, iz] = J3[:, c]
        Acomp.append((sf.ifftn(sf.fftn(Jd, workers=-1) * Kh, workers=-1)[:nx, :ny, :nz] * MU0).astype(np.complex64)); del Jd
    Ax, Ay, Az = Acomp
    Bx = np.gradient(Az, dy, axis=1) - np.gradient(Ay, dz, axis=2)
    By = np.gradient(Ax, dz, axis=2) - np.gradient(Az, dx, axis=0)
    Bz = np.gradient(Ay, dx, axis=0) - np.gradient(Ax, dy, axis=1)
    B = np.stack([Bx, By, Bz], 0)
    return dict(gap=np.stack([B[:, :, :, zm] for zm in gz], 0), yz=B[:, kxc, :, :], xz=B[:, :, kyc, :])


bs = {}
pick = ['BULK_L_dc', 'BULK_L_10M', 'C_bot_10M', 'FEED_10M', 'C_bot_dc']
for nm in pick:
    bs[nm] = bslices(SJ[:, names.index(nm)]); log('B', nm)
tf = st['tf']; ton = float(st['t_on'])
fpick = {f'frame_{int(round((tf[i] - ton) * 1e9))}ns': i for i in
         [int(np.argmin(np.abs(tf - (ton + dt)))) for dt in (-100e-9, 39.5e-9, 41e-9, 100e-9, 500e-9, 2000e-9)]}
for nm, i in fpick.items():
    bs[nm] = bslices(JT[:, i].astype(np.complex64)); log('B', nm)
np.savez_compressed(os.path.join(out, 'bslices.npz'), names=np.array(list(bs)),
                    **{f'{k}__{s}': v[s].astype(np.complex64) for k, v in bs.items() for s in v},
                    zgap=np.array(gz), kx=kxc, ky=kyc, zlay=json.dumps(zl), d=np.array(d), crop=np.array(meta['crop']),
                    frame_idx=json.dumps(fpick))
log('done')
