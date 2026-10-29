"""Bus waveforms (post_tran.py npz) -> pickup on the analog sense nodes, with the 2D coupling numbers of the
stackup study (power-stage-rev8/docs/stackup-sim/HANDOFF.md, 2D table and VSNS table).

usage: python pickup.py <results.npz> <stack> <out prefix>

Capacitive (VBUS feed voltage -> trace; the probe voltage is VBUS on L4 vs PGND on L5 under the bundle, mean of
P105 and P110):
  VSNS: 2.03 kOhm source, C_tot 13.4 pF (C52 10 pF + trace), C_c 1.88 pF as built / 0.188 pF intended
        (fits the HANDOFF fractions 0.23 % at 96 kHz and 14 % HF limit).  H = jw R C_c / (1 + jw R C_tot)
  ISNS: INA296A3 output straight to the ADC pin (no RC). Output impedance above the amplifier's loop bandwidth is
        bracketed 20 / 100 Ohm (assumption), node C 10 pF + C_c.  H = jw Z C_c / (1 + jw Z C_tot)
Inductive (feed current -> trace/AGND loop): EMF = M dI_feed/dt, M = 2.5-6.9 pH/mm as built, 0.2-0.9 pH/mm intended,
  over 23-27 mm of trace on the feed: band low = 2.5 x 23, high = 6.9 x 27 (as built). Full EMF is a bound; how much
  reaches the ADC depends on where the trace loop closes.
ADC: 69 ns aperture (sample-and-hold window), modelled as a 69 ns moving average.
"""
import argparse, json
import numpy as np

CPL = {'asbuilt': dict(Cc=1.88e-12, M=(2.5e-12 * 23, 6.9e-12 * 27)),
       'intended': dict(Cc=0.188e-12, M=(0.2e-12 * 23, 0.9e-12 * 27))}
R_VSNS, C_VSNS = 2.03e3, 13.4e-12
Z_INA, C_ISNS = (20.0, 100.0), 10e-12
T_AP = 69e-9

ap = argparse.ArgumentParser(); ap.add_argument('npz'); ap.add_argument('stack'); ap.add_argument('out')
a = ap.parse_args()
z = np.load(a.npz); t = z['t']; N = len(t); dt = t[1] - t[0]
f = np.fft.rfftfreq(N, dt); w = 2 * np.pi * f
vbus = 0.5 * (z['wav_P105'] + z['wav_P110']); V = np.fft.rfft(vbus)
c = CPL[a.stack]


def filt(H):
    return np.fft.irfft(V * H, n=N)


out = {}
out['vsns'] = filt(1j * w * R_VSNS * c['Cc'] / (1 + 1j * w * R_VSNS * C_VSNS))
for zo in Z_INA:
    out[f'isns_z{zo:g}'] = filt(1j * w * zo * c['Cc'] / (1 + 1j * w * zo * (C_ISNS + c['Cc'])))
didt = np.fft.irfft(np.fft.rfft(z['ifeed']) * 1j * w, n=N)
for k, m in zip(('lo', 'hi'), c['M']):
    out[f'emf_{k}'] = m * didt
nap = max(1, int(round(T_AP / dt)))
kern = np.ones(nap) / nap


def boxavg(x):   # circular moving average, value at the end of the aperture
    return np.real(np.fft.ifft(np.fft.fft(x) * np.fft.fft(kern, N)))


met = {}
for edge in ('on', 'off'):
    te = float(z[f't_{edge}'])
    tc = (t - te + t[-1] / 2) % (t[-1] + dt) - t[-1] / 2          # time from the HI command edge, wrapped
    for k, x in out.items():
        xa = boxavg(x)
        for lab, ta, tb in (('0_200ns', 0, 200e-9), ('200_500ns', 200e-9, 500e-9), ('500_2000ns', 500e-9, 2000e-9)):
            m = (tc >= ta) & (tc < tb)
            met[f'{k}_{edge}_{lab}_pk_mV'] = float(np.abs(x[m]).max() * 1e3)
            met[f'{k}_{edge}_{lab}_ap69_pk_mV'] = float(np.abs(xa[m]).max() * 1e3)
for k, v in met.items(): print(f'{k:36s} {v:8.3f}')
np.savez(a.out + '.npz', t=t, **out, met=json.dumps(met))
