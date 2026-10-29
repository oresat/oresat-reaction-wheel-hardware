"""Waveform export for the explorer page: one PWM period per case, on a non-uniform time grid
(0.25 ns within 300 ns of each edge, 5 ns elsewhere), times in ns from the period start (LS on, then HS on
centred in the period).
python export_wave.py <out.json> <tag>:<label> [...]
Per case: edges (HI command times), VBUS AC at the feed (mean P105/P110, mV), feed current AC (A), device current (A),
SW (V), VSNS pickup (mV), ISNS pickup at 20 / 100 ohm INA output impedance (mV), feed->trace EMF low/high M (mV)."""
import json, os, sys
import numpy as np

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
doc = {'units': {'t': 'ns', 'vbus': 'mV', 'ifeed': 'A', 'idev': 'A', 'sw': 'V', 'vsns': 'mV', 'isns_z20': 'mV',
                 'isns_z100': 'mV', 'emf_lo': 'mV', 'emf_hi': 'mV'}, 'cases': {}}
for arg in sys.argv[2:]:
    tag, lab = arg.split(':', 1)
    z = np.load(os.path.join(R, tag + '.npz')); pk = np.load(os.path.join(R, tag + '_pk.npz'))
    t = z['t']; dt = t[1] - t[0]; T = t[-1] + dt
    edges = [float(z['t_on']), float(z['t_off'])]
    near = np.zeros(len(t), bool)
    for te in edges: near |= (t > te - 20e-9) & (t < te + 300e-9)
    keep = np.zeros(len(t), bool); step_far = int(round(5e-9 / dt)); step_near = max(1, int(round(0.25e-9 / dt)))
    keep[::step_far] = True; idx = np.nonzero(near)[0]; keep[idx[::step_near]] = True
    v = 0.5 * (z['wav_P105'] + z['wav_P110'])
    ser = dict(vbus=v * 1e3, ifeed=z['ifeed'], idev=z['idev'], sw=z['sw'], vsns=pk['vsns'] * 1e3,
               isns_z20=pk['isns_z20'] * 1e3, isns_z100=pk['isns_z100'] * 1e3, emf_lo=pk['emf_lo'] * 1e3, emf_hi=pk['emf_hi'] * 1e3)
    doc['cases'][lab] = dict(tag=tag, period_ns=T * 1e9, edges_ns=[e * 1e9 for e in edges], t=np.round(t[keep] * 1e9, 3).tolist(),
                             **{k: np.round(s[keep], 4).tolist() for k, s in ser.items()},
                             metrics=json.loads(str(z['met'])), pickup=json.loads(str(pk['met'])))
json.dump(doc, open(sys.argv[1], 'w'))
print('wrote', sys.argv[1], {k: len(c['t']) for k, c in doc['cases'].items()})
