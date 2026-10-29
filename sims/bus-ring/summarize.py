"""Cross-case table from results/<tag>.npz (post_tran.py) and results/<tag>_pk.npz (pickup.py).
python summarize.py <tag> [...]  -> markdown on stdout"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(HERE, 'results')


def band(x, dt, lo, hi):
    f = np.fft.rfftfreq(len(x), dt); return np.fft.irfft(np.fft.rfft(x) * ((f > lo) & (f < hi)), n=len(x))


rows = []
for tag in sys.argv[1:]:
    z = np.load(os.path.join(R, tag + '.npz')); m = json.loads(str(z['met'])); t = z['t']; dt = t[1] - t[0]
    pk = np.load(os.path.join(R, tag + '_pk.npz')); pm = json.loads(str(pk['met']))
    v = 0.5 * (z['wav_P105'] + z['wav_P110'])
    r = dict(case=tag)
    r['SW 10-90 on/off ns'] = f"{m.get('sw_on_10_90_ns', np.nan):.2f} / {m.get('sw_off_10_90_ns', np.nan):.2f}"
    r['SW max V'] = f"{max(m['sw_on_max_V'], m['sw_off_max_V']):.1f}"
    r['I dev pk A'] = f"{m['idev_on_peak_A']:.1f}"
    r['VBUS LF p-p mV'] = f"{np.ptp(band(v, dt, 0, 1e6)) * 1e3:.0f}"
    for e in ('on', 'off'):
        te = float(z[f't_{e}']); tc = t - te
        hf = band(v, dt, 30e6, 2e9); bb = band(v, dt, 1e6, 30e6)
        r[f'{e}: VBUS >30MHz pk mV (0-300ns)'] = f"{np.abs(hf[(tc >= 0) & (tc < 300e-9)]).max() * 1e3:.1f}"
        r[f'{e}: VBUS 1-30MHz pk mV 0.1-0.3/0.6-1.2us'] = (f"{np.abs(bb[(tc >= 0.1e-6) & (tc < 0.3e-6)]).max() * 1e3:.1f} / "
                                                         f"{np.abs(bb[(tc >= 0.6e-6) & (tc < 1.2e-6)]).max() * 1e3:.1f}")
        r[f'{e}: VSNS pk mV raw/69ns 0-200ns'] = f"{pm[f'vsns_{e}_0_200ns_pk_mV']:.2f} / {pm[f'vsns_{e}_0_200ns_ap69_pk_mV']:.2f}"
        r[f'{e}: ISNS(20-100 ohm) 69ns pk mV 0-200ns'] = f"{pm[f'isns_z20_{e}_0_200ns_ap69_pk_mV']:.3f}-{pm[f'isns_z100_{e}_0_200ns_ap69_pk_mV']:.3f}"
        r[f'{e}: EMF 69ns pk mV 0-200ns'] = f"{pm[f'emf_lo_{e}_0_200ns_ap69_pk_mV']:.3f}-{pm[f'emf_hi_{e}_0_200ns_ap69_pk_mV']:.3f}"
        r[f'{e}: EMF raw pk mV'] = f"{pm[f'emf_lo_{e}_0_200ns_pk_mV']:.2f}-{pm[f'emf_hi_{e}_0_200ns_pk_mV']:.2f}"
    rows.append(r)
keys = list(rows[0])
print('| ' + ' | '.join(['quantity'] + [r['case'] for r in rows]) + ' |')
print('|' + '---|' * (len(rows) + 1))
for k in keys[1:]:
    print('| ' + ' | '.join([k] + [r[k] for r in rows]) + ' |')
