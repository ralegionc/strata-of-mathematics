"""The deepest chain of definitions under each statement and concept, for labels and the web page.

Follows, from the statement's own constants, the dependency with the greatest height at every
step, and records each concept where the height drops. Writes data/derived/chains.json:
{key: [[name, depth], ...]} for theorems and {"concept:" + decl: [...]} for concepts.
"""
import json

import numpy as np
import pandas as pd

import graph as g
from config import DERIVED


def chain_from(sources, Gs, h, conc, names, limit=5000):
    if not len(sources):
        return []
    i = int(sources[np.argmax(h[sources])])
    out, seen, last = [], {i}, 10 ** 9
    for _ in range(limit):
        if conc[i] and h[i] < last:
            out.append([names[i], int(h[i])])
            last = h[i]
        ch = Gs.indices[Gs.indptr[i]:Gs.indptr[i + 1]]
        ch = ch[~np.isin(ch, list(seen))] if len(seen) < 2000 else ch
        if not len(ch):
            break
        c = int(ch[np.argmax(h[ch])])
        if h[c] == 0:
            break
        seen.add(c)
        i = c
    return out


def main():
    df = g.nodes()
    idx = g.name_index()
    names = df.name.to_numpy()
    conc = df.is_concept.to_numpy()
    is_thm, is_meta = df.is_thm.to_numpy(), df.is_meta.to_numpy()
    h = np.load(DERIVED / "h_stmt.npy")
    Gs = g.statement_graph()
    et, ev = g.edges_type(), g.edges_value()
    out = {}
    m = pd.read_csv(DERIVED / "measures.csv")
    for r in m.itertuples():
        i = int(idx[r.decl])
        src = g.out_neighbours(ev if r.statement_only else et, i)
        src = src[~is_thm[src] & ~is_meta[src]]
        out[r.key] = chain_from(src, Gs, h, conc, names)
    c = pd.read_csv(DERIVED / "concepts.csv")
    for r in c.itertuples():
        out["concept:" + r.decl] = chain_from(np.array([int(idx[r.decl])]), Gs, h, conc, names)
    json.dump(out, open(DERIVED / "chains.json", "w", encoding="utf-8"), ensure_ascii=False)
    return out


if __name__ == "__main__":
    out = main()
    for k in ["wQ11518", "wQ1506253", "wQ2027347", "wQ132469"]:
        print(k, " > ".join(f"{n}({d})" for n, d in out[k]))
