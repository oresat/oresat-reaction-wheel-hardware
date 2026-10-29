"""Xyce decks for the rev8 bus: PEEC board subckt + Murata cap banks + feed/source, driven at leg C.

usage:
  python mk_tb.py ac   <stack> <vbias> <out.cir>                      AC: 1 A drawn VIN -> PGND at leg C's pads
  python mk_tb.py tran <stack> <vbias> <i0> <out.cir> [--duty 0.5] [--lpad 0] [--periods 2]

tran: LMG2100R044 (models/lmg2100r044.lib) on leg C's pads, the leg's real gate-drive parts (R36 2.7 ohm VCC,
C73 100 nF + R37 2.7 ohm bootstrap, R34/R35 22 ohm + C72/C70 47 pF input filters), HRTIM dead time 10.4 ns,
96 kHz centre-aligned PWM. Load: 100 uH phase inductance from SW (through the 2 mOhm R39 shunt) to a duty*Vbus
source; i0 > 0 means current out of SW (HS turn-on is the hard edge). The load current is pre-charged through
IPRE and handed to the bridge at 3 ns (models/README.md). Node 0 = leg C PGND pad. The other legs are open.
Board subckt from mk_board_sub.py (xyce/board_<stack>.sub).
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ac_bus as ab, murata

HERE = os.path.dirname(os.path.abspath(__file__))
T_DEAD = 10.4e-9                       # HRTIM dead time (firmware config.h: 10.4 ns)
L_LOAD = 100e-6


def node(t):
    return '0' if t == 'devC_G' else t


def sub_pins(sub):
    for ln in open(sub):
        if ln.lower().startswith('.subckt'): return ln.split()[2:]


def network(stack, vbias, sub=None):
    sub = sub or os.path.join(HERE, 'xyce', f'board_{stack}.sub')
    out = [f'.include {sub}']
    names = {}
    for k in murata.PARTS:
        p = murata.mod_path(k, vbias); out.append(f'.include {p}'); names[k] = murata.parse(p)[0]
    out.append(f'XBRD ' + ' '.join(node(t) for t in sub_pins(sub)) + f' BOARD_{stack.upper()}')
    for bank, parts in ab.BANK_PARTS.items():
        for k, cnt in parts.items():
            for i in range(cnt):
                out.append(f'XC_{bank}_{k}_{i} {node(bank + "_V")} {node(bank + "_G")} {names[k]}')
    out += ['VFS FEED_V fe0 0', f'RFEXT fe0 fe1 {ab.R_EXT:g}', f'LFEXT fe1 fe2 {ab.L_EXT[stack]:.4e}']
    for i in range(ab.FEED_CAPS['47u_1210']):
        out.append(f'XC_J1_{i} fe2 FEED_G {names["47u_1210"]}')
    out += [f'RSRC fe2 fs1 {ab.R_SRC:g}', f'LSRC fs1 fs2 {ab.L_SRC:g}']
    return out, names


def ac_deck(stack, vbias):
    net, _ = network(stack, vbias)
    return '\n'.join([f'* rev8 bus AC, {stack}, caps at {vbias} V: 1 A drawn from leg C VIN, returned to PGND'] + net + [
        'VBAT fs2 FEED_G 0',
        'IDEV devC_V 0 AC 1',
        '.ac dec 40 1e4 1e9',
        '.print ac format=csv vr(devC_V) vi(devC_V) ir(VFS) ii(VFS)',
        '.end'])


def tran_deck(stack, vbias, i0, duty, lpad, periods, sub=None):
    net, _ = network(stack, vbias, sub)
    T = 1 / ab.F_PWM; W = duty * T
    # centre-aligned: HS on for W centred at T/2 of each period; LS on outside, dead time at both ends of HS on
    t_on = T / 2 - W / 2; t_off = T / 2 + W / 2; tr = 1e-9
    hi, li = ['0 0'], ['0 0', '5e-9 0', '6e-9 3.3']        # both off at the OP (Xyce cannot start with LS on + load)
    for p in range(periods):
        o = p * T
        li += [f'{o + t_on - T_DEAD:.6e} 3.3', f'{o + t_on - T_DEAD + tr:.6e} 0', f'{o + t_off + T_DEAD:.6e} 0', f'{o + t_off + T_DEAD + tr:.6e} 3.3']
        hi += [f'{o + t_on:.6e} 0', f'{o + t_on + tr:.6e} 3.3', f'{o + t_off:.6e} 3.3', f'{o + t_off + tr:.6e} 0']
    t_end = periods * T
    vin_pin = 'vinp'
    lib = os.path.join(HERE, 'models', 'lmg2100r044.lib')
    lines = [f'* rev8 bus transient, {stack}, Vbus {vbias} V, phase current {i0} A, duty {duty}, leg C switching'] + net + [
        f'VBAT fs2 FEED_G {vbias}',
        f'.include {lib}',
        '* device port: current sense into the VIN pin, optional pad-gap L',
        f'VIVIN devC_V vs1 0',
        (f'LPAD vs1 {vin_pin} {lpad:g}' if lpad > 0 else f'RPAD vs1 {vin_pin} 1u'),
        'XU12 vinp sw 0 hb hs hi li vcc agnd LMG2100R044 PARAMS: TJ=25',
        '* driver ground: GND pin 15 to PGND through the board GND return (estimate)',
        'LAGND agnd 0 2n',
        '* VCC: +5V -> R36 2.7 ohm -> VCC pin; bootstrap C73 100 nF + R37 2.7 ohm to HS',
        'V5 v5 0 5', 'CV5 v5 0 1u', 'R36 v5 vcc 2.7',
        'C73 hb bst 100n', 'R37 bst hs 2.7',
        '* MCU inputs through 22 ohm + 47 pF (R34/C72, R35/C70)',
        'VHIS his 0 PWL(' + ' '.join(hi) + ')', 'R34 his hi 22', 'C72 hi 0 47p',
        'VLIS lis 0 PWL(' + ' '.join(li) + ')', 'R35 lis li 22', 'C70 li 0 47p',
        '* phase: R39 2 mOhm shunt, 100 uH, back-EMF source at duty*Vbus; IPRE hands i0 to the bridge at 100-110 ns, LS already on',
        'R39 sw swl 2m', f'LLOAD swl vmid {L_LOAD:g}', f'VMID vmid 0 {duty * vbias:.6g}',
        f'IPRE vmid swl PWL(0 {i0:g} 100n {i0:g} 110n 0)',
        '* BDF2: trap rings and diverges on the stiff Murata ladders; Gear above order 2 is not A-stable and stalls',
        '.options timeint method=gear maxord=2',
        '.options nonlin-tran maxstep=100',
        f'.tran 0.02n {t_end:.6e} 0 0.1n',
        '.print tran format=csv v(sw) i(VIVIN) v(devC_V) i(VFS) i(LLOAD) {v(hb)-v(hs)} v(hi) v(li)',
        '.end']
    return '\n'.join(lines)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('kind'); ap.add_argument('stack'); ap.add_argument('vbias', type=float)
    ap.add_argument('rest', nargs='+'); ap.add_argument('--duty', type=float, default=0.5)
    ap.add_argument('--lpad', type=float, default=0.0); ap.add_argument('--periods', type=int, default=2); ap.add_argument('--sub', default=None)
    a = ap.parse_args()
    if a.kind == 'ac':
        open(a.rest[0], 'w').write(ac_deck(a.stack, a.vbias))
    else:
        open(a.rest[1], 'w').write(tran_deck(a.stack, a.vbias, float(a.rest[0]), a.duty, a.lpad, a.periods, a.sub))
