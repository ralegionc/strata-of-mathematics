"""Where do deep proofs get their depth: from their own development, or from the library under it?

For a theorem, follow the longest chain of its proof (concepts and named theorems, as in proof depth)
and count how many layers of that chain sit inside the theorem's own development. For a research
project, the development is every file outside mathlib and its core dependencies. For a theorem in
mathlib, it is the folder its file sits in (and, more generously, the folder above that).

Writes data/derived/proofsplit.csv for the sample; research.py calls `split` for each project.
"""
import numpy as np
import pandas as pd

import graph as g
from config import DERIVED

LIBRARY_PREFIXES = ("Mathlib", "Batteries", "Init", "Std", "Lean", "Aesop", "Qq", "ProofWidgets",
                    "Plausible", "ImportGraph", "LeanSearchClient", "Archive")


def longest_chain(i, G, h, w):
    """Weighted nodes on one longest path below node i (greedy on heights, exact on a DAG)."""
    out, seen, cur = [], {i}, i
    while True:
        if w[cur]:
            out.append(cur)
        ch = G.indices[G.indptr[cur]:G.indptr[cur + 1]]
        ch = ch[h[ch] > 0]
        ch = [c for c in ch if c not in seen]
        if not ch:
            break
        nxt = max(ch, key=lambda c: h[c])
        seen.add(nxt)
        cur = nxt
    return out


def split(i, G, h, w, modules, own):
    """(total layers, own-development layers) on the longest proof chain of node i."""
    chain = longest_chain(i, G, h, w)
    mods = modules[np.array(chain, dtype=np.int64)] if chain else np.array([], dtype=object)
    n_own = int(sum(1 for m in mods if own(m)))
    return len(chain), n_own


def sample():
    df = g.nodes()
    idx = g.name_index()
    conc, named = df.is_concept.to_numpy(), df.is_named_thm.to_numpy()
    w = conc | named
    Gp = g.proof_graph()
    hp = np.load(DERIVED / "h_proof.npy")
    modules = df.module.to_numpy()
    m = pd.read_csv(DERIVED / "theorems.csv")
    rows = []
    for r in m.dropna(subset=["proof_depth"]).itertuples():
        i = int(idx[r.decl])
        mod = modules[i]
        folder = mod.rsplit(".", 1)[0]
        parent = folder.rsplit(".", 1)[0]
        total, own1 = split(i, Gp, hp, w, modules, lambda x, f=folder: x == f or x.startswith(f + "."))
        _, own2 = split(i, Gp, hp, w, modules, lambda x, f=parent: x == f or x.startswith(f + "."))
        rows.append(dict(key=r.key, title=r.title, year_proved=r.year_proved, proof_depth=r.proof_depth,
                         chain_layers=total, own_folder=own1, own_parent=own2, folder=folder, parent=parent))
    out = pd.DataFrame(rows)
    out.to_csv(DERIVED / "proofsplit.csv", index=False)
    return out


def is_own_research(module):
    return not module.startswith(LIBRARY_PREFIXES)


if __name__ == "__main__":
    s = sample()
    print(s[["chain_layers", "own_folder", "own_parent"]].describe().round(1).to_string())
    print(s.sort_values("proof_depth").tail(6)[["title", "proof_depth", "chain_layers", "own_folder",
                                                "own_parent", "parent"]].to_string())
