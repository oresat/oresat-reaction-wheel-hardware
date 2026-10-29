"""Chart data for the two pages (one JSON): device edges, VBUS at the feed, bus impedance, current hand-off between
the capacitor banks, coupling and pickup numbers. python export_viz.py <out.json>"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); BR = os.path.join(os.path.dirname(HERE), 'bus-ring')
R = os.path.join(BR, 'results')
out = {}
r3 = lambda a, n=4: [float(f'{v:.{n}g}') for v in np.asarray(a, float)]

for stack, tag in (('intended', 'in'), ('asbuilt', 'ab')):
    z = np.load(os.path.join(R, f'{tag}_8v4_10a_r300.npz')); t = z['t']
    met = json.loads(str(z['met']))
    d = {}
    for e in ('on', 'off'):
        te = float(z[f't_{e}']); tc = (t - te) * 1e9
        m = (tc > -5) & (tc < 90)
        g = np.arange(-5, 90, 0.1)
        d[f'edge_{e}'] = dict(t=r3(g), sw=r3(np.interp(g, tc[m], z['sw'][m])), idev=r3(np.interp(g, tc[m], z['idev'][m])))
    v = 0.5 * (z['wav_P105'] + z['wav_P110']); te = float(z['t_on']); tc = (t - te) * 1e9
    base = v[(tc > -30) & (tc < 0)].mean()
    g1 = np.arange(-10, 120, 0.2); g2 = np.arange(-100, 3000, 2.0)
    d['vbus_fast'] = dict(t=r3(g1), v=r3((np.interp(g1, tc, v) - base) * 1e3))
    d['vbus_slow'] = dict(t=r3(g2), v=r3((np.interp(g2, tc, v) - base) * 1e3))
    T = t[-1] + t[1] - t[0]; gp = np.arange(0, T, 20e-9)
    d['vbus_period'] = dict(t=r3(gp * 1e6), v=r3((np.interp(gp, t, v) - v.mean()) * 1e3), t_on=te * 1e6, t_off=float(z['t_off']) * 1e6)
    pk = np.load(os.path.join(R, f'{tag}_8v4_10a_r300_pk.npz'))
    d['pick_fast'] = {k: r3(np.interp(g1, tc, pk[k] * 1e3)) for k in ('vsns', 'isns_z100', 'emf_hi')}
    d['pick_slow'] = {k: r3(np.interp(g2, tc, pk[k] * 1e3)) for k in ('vsns', 'isns_z100', 'emf_hi')}
    d['metrics'] = met
    # current hand-off between banks after the HS-on switching instant
    st = np.load(os.path.join(HERE, 'data', f'state_{stack}.npz'))
    ports = list(st['ports']); tt = st['tt']; ip = st['i_ports']
    tsw = te + met['sw_on_delay_ns'] * 1e-9
    groups = {'leg C bottom 2.2 µF ×5': ['C_bot_V'], 'leg C top 10 µF + 2.2 µF': ['C_top_V'],
              'legs A and B banks': ['A_bot_V', 'A_top_V', 'B_bot_V', 'B_top_V'], 'bulk right 47 µF ×4': ['BULK_R_V'],
              'bulk left 47 µF ×4': ['BULK_L_V'], 'feed from J1': ['FEED_V']}
    lt = np.geomspace(0.1e-9, 5e-6, 400)
    cas = {}
    for k, ps in groups.items():
        s = sum(ip[:, ports.index(p)] for p in ps)
        pre = s[(tt > te - 30e-9) & (tt < te)].mean()
        cas[k] = r3(np.interp(tsw + lt, tt, s) - pre)
    d['cascade'] = dict(t_ns=r3(lt * 1e9), **{'groups': cas})
    out[stack] = d

bt = np.load(os.path.join(R, 'bus_trap_8v4.npz'))
out['zbus'] = dict(f=r3(bt['intended_fz']), intended=r3(np.abs(bt['intended_zdev']) * 1e3), asbuilt=r3(np.abs(bt['asbuilt_zdev']) * 1e3),
                   h_intended=r3(np.abs(0.5 * (bt['intended_H_P105'] + bt['intended_H_P110'])) * 1e3),
                   h_asbuilt=r3(np.abs(0.5 * (bt['asbuilt_H_P105'] + bt['asbuilt_H_P110'])) * 1e3),
                   ifeed_intended=r3(np.abs(bt['intended_HI'])), ifeed_asbuilt=r3(np.abs(bt['asbuilt_HI'])))
json.dump(out, open(sys.argv[1], 'w'), separators=(',', ':'))
print('wrote', sys.argv[1], os.path.getsize(sys.argv[1]) // 1024, 'kB')
for s in ('intended', 'asbuilt'):
    c = out[s]['cascade']['groups']; lt = np.array(out[s]['cascade']['t_ns'])
    for tq in (1, 10, 100, 1000, 4000):
        i = int(np.argmin(np.abs(lt - tq))); print(s, f't={tq} ns', {k[:14]: round(v[i], 2) for k, v in c.items()})
