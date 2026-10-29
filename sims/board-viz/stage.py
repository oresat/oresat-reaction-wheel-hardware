"""Stage the two sites for publishing: figures -> WebP under site_a/ and site_b/, chart data and frames copied.
python stage.py [a|b|both]"""
import glob, os, shutil, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); FIG = os.path.join(HERE, 'fig')
which = sys.argv[1] if len(sys.argv) > 1 else 'both'


def webp(src, dst, q=84, maxw=1400):
    im = Image.open(src).convert('RGB')
    if im.width > maxw: im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
    os.makedirs(os.path.dirname(dst), exist_ok=True); im.save(dst, quality=q, method=6)


def stage_a():
    S = os.path.join(HERE, 'site_a'); I = os.path.join(S, 'img')
    shutil.rmtree(I, ignore_errors=True); os.makedirs(I)
    fi = os.path.join(FIG, 'intended')
    want = ['flow_BULK_L_10M', 'flow_BULK_L_dc', 'byz_BULK_L_10M', 'byz_BULK_L_dc', 'pot_BULK_L_10M_L3_VBUS',
            ] + [f'layer_BULK_L_{f}_{l}' for f in ('dc', '10M') for l in ('L2', 'L3', 'L4', 'L5')]
    for w in want: webp(os.path.join(fi, w + '.png'), os.path.join(I, w + '.webp'))
    for w in ('e_band_x104_intended', 'e_bundle_y105_intended'): webp(os.path.join(FIG, w + '.png'), os.path.join(I, w + '.webp'))
    for l in ('L1', 'L6'):
        for f in ('dc', '10M'): webp(os.path.join(fi, f'layer_BULK_L_{f}_{l}.png'), os.path.join(I, f'layer_BULK_L_{f}_{l}.webp'))
    # leg C close-ups of the hot loop (plan images span x 85.5-117.5, y 89.5-113 mm)
    for src, dst in (('flow_C_bot_10M', 'hot_flow'), ('bgap0_C_bot_10M', 'hot_bgap')):
        im = Image.open(os.path.join(fi, src + '.png')).convert('RGB'); W, H = im.size
        px = lambda x: round((x - 85.5) / 32.0 * W); py = lambda y: round((y - 89.5) / 23.5 * H)
        im = im.crop((px(99.5), py(90.0), px(113.5), py(100.5))).resize((1200, round(1200 * (py(100.5) - py(90.0)) / (px(113.5) - px(99.5)))), Image.BICUBIC)
        im.save(os.path.join(I, dst + '.webp'), quality=86, method=6)
    shutil.copy(os.path.join(fi, 'info.json'), os.path.join(I, 'info.json'))
    os.makedirs(os.path.join(S, 'data'), exist_ok=True); shutil.copy(os.path.join(HERE, 'data', 'viz.json'), os.path.join(S, 'data', 'viz.json'))
    A = os.path.join(S, 'anim'); shutil.rmtree(A, ignore_errors=True); shutil.copytree(os.path.join(fi, 'anim'), A, ignore=shutil.ignore_patterns('overlay.png'))


def stage_b():
    S = os.path.join(HERE, 'site_b'); I = os.path.join(S, 'img')
    shutil.rmtree(I, ignore_errors=True); os.makedirs(I)
    for st in ('intended', 'asbuilt'):
        for w in ('byz_BULK_L_10M', 'flow_BULK_L_10M'):
            webp(os.path.join(FIG, st, w + '.png'), os.path.join(I, f'{w}_{st}.webp'))
        webp(os.path.join(FIG, f'e_bundle_y105_{st}.png'), os.path.join(I, f'e_bundle_y105_{st}.webp'))
    webp(os.path.join(os.path.dirname(HERE), 'stackup-review', 'fig_gnd_overlap.png'), os.path.join(I, 'fig_gnd_overlap.webp'), q=88, maxw=1000)
    # return-current shares and three moments of the edge (same frame times in both stacks)
    import json
    moments = [('t40', 39.75), ('t100', 100.0), ('t1000', 1000.0)]
    out = []
    for st in ('intended', 'asbuilt'):
        shutil.copy(os.path.join(FIG, st, 'info.json'), os.path.join(I, f'info_{st}.json'))
        F = json.load(open(os.path.join(FIG, st, 'anim', 'frames.json')))
        for key, tq in moments:
            i = min(range(len(F['t_ns'])), key=lambda k: abs(F['t_ns'][k] - tq))
            Image.open(os.path.join(FIG, st, 'anim', f'f{i:03d}.webp')).save(os.path.join(I, f'moment_{key}_{st}.webp'), quality=82, method=6)
            if st == 'intended':
                t = F['t_ns'][i]; out.append(dict(key=key, label=(f'{t:.2f} ns' if t < 100 else (f'{t:.0f} ns' if t < 1000 else f'{t / 1000:.2f} µs')) + ' from HI'))
    json.dump(out, open(os.path.join(I, 'moments.json'), 'w'))
    os.makedirs(os.path.join(S, 'data'), exist_ok=True); shutil.copy(os.path.join(HERE, 'data', 'viz.json'), os.path.join(S, 'data', 'viz.json'))


if which in ('a', 'both'): stage_a()
if which in ('b', 'both'): stage_b()
for s in ('site_a', 'site_b'):
    tot = sum(os.path.getsize(f) for f in glob.glob(os.path.join(HERE, s, '**', '*'), recursive=True) if os.path.isfile(f))
    print(s, round(tot / 1e6, 2), 'MB')
