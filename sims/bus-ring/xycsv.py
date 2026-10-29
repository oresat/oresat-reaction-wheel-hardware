"""Read a Xyce format=csv file whose header has commas inside V(a,b) and {expr}: load(path) -> {NAME: array}."""
import numpy as np


def split_header(h):
    out, cur, depth = [], '', 0
    for ch in h.strip():
        if ch in '({': depth += 1
        if ch in ')}': depth -= 1
        if ch == ',' and depth == 0: out.append(cur); cur = ''
        else: cur += ch
    return out + [cur]


def load(path):
    with open(path) as fh:
        names = split_header(fh.readline())
    rows = []
    for ln in open(path).readlines()[1:]:
        t = ln.strip().split(',')
        if len(t) == len(names):
            try: rows.append([float(x) for x in t])
            except ValueError: pass
    a = np.array(rows)
    return {n.upper(): a[:, i] for i, n in enumerate(names)}
