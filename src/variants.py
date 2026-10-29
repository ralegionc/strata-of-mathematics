"""Two re-measurements that test the main results against their most obvious objections.

1. Number systems as given. Textbooks take ℕ, ℤ, ℚ, ℝ and ℂ as known. Here every declaration in
   the files that construct them (and ℚ≥0, ℝ≥0, [0, ∞], the extended reals) loses its outgoing
   edges, so each number system becomes a single leaf. Statement depth is then the number of
   layers built *on top of* the numbers. Definitions elsewhere that use Cauchy sequences (the
   exponential, for one) keep them: that is analysis, not the construction of ℝ.

2. Direct use in proofs. The famous-theorem dependencies in measures.py follow every edge, so a
   proof "rests on" whatever the library used to build its objects (area on the plane is a Haar
   measure, and Haar's construction uses Tychonoff's theorem). Here a dependency only counts if
   it is reached through proof terms alone: theorem to theorem, never through a definition.
   Prop-valued instances are theorems in Lean, so instance arguments still count.

Writes data/derived/variants_theorems.csv, variants_concepts.csv, famous_edges_direct.csv,
library_depths_numbers.parquet and h_stmt_numbers.npy.
"""
import re

import numpy as np
import pandas as pd

import graph as g
from config import DERIVED

NUMBER_MODULES = re.compile(
    r"^(Init\.Data\.(Nat|Int|Rat)(\.|$)|Batteries\.Data\.(Nat|Int|Rat)(\.|$)|"
    r"Mathlib\.(Basic|Data)\.(Real|NNReal|ENNReal|EReal|Complex|Rat|NNRat)\.(Basic|Defs|Init)$)")
NUMBER_NAMES = re.compile(r"^(Nat|Int|Rat|NNRat|Real|NNReal|ENNReal|EReal|Complex)(\.|$)")


def number_mask(df):
    """Declarations that belong to the construction of the number systems."""
    mod = df.module.str.match(NUMBER_MODULES)
    prelude_nat = (df.module == "Init.Prelude") & df.name.str.match(r"^Nat(\.|$)")
    named = df.name.isin(["Nat", "Int", "Rat", "NNRat", "Real", "NNReal", "ENNReal", "EReal", "Complex"])
    return (mod | prelude_nat | named).to_numpy()


def statement_graph_numbers():
    df = g.nodes()
    thm, meta = df.is_thm.to_numpy(), df.is_meta.to_numpy()
    cut = number_mask(df)
    e = np.concatenate([g.edges_type(), g.edges_value()])
    keep = ~thm[e[:, 0]] & ~thm[e[:, 1]] & ~meta[e[:, 1]] & ~cut[e[:, 0]]
    return g.csr(e[keep, 0], e[keep, 1], len(df)), cut


def proof_graph_direct():
    """Value edges between theorems only (Prop-valued instances are theorems)."""
    df = g.nodes()
    thm, meta = df.is_thm.to_numpy(), df.is_meta.to_numpy()
    e = g.edges_value()
    keep = thm[e[:, 0]] & thm[e[:, 1]] & ~meta[e[:, 1]]
    return g.csr(e[keep, 0], e[keep, 1], len(df))


def main():
    df = g.nodes()
    idx = g.name_index()
    conc = df.is_concept.to_numpy()
    is_thm, is_meta = df.is_thm.to_numpy(), df.is_meta.to_numpy()
    et, ev = g.edges_type(), g.edges_value()

    # 1. numbers as given
    Gn, cut = statement_graph_numbers()
    hn = g.heights(Gn, conc)
    np.save(DERIVED / "h_stmt_numbers.npy", hn)
    m = pd.read_csv(DERIVED / "measures.csv")
    rows = []
    for r in m.itertuples():
        i = int(idx[r.decl])
        src = g.out_neighbours(ev if r.statement_only else et, i)
        src = src[~is_thm[src] & ~is_meta[src]]
        d = int(hn[src].max()) if len(src) else 0
        s = int(conc[g.reach(Gn, src)].sum()) if len(src) else 0
        rows.append(dict(key=r.key, depth_numbers=d, size_numbers=s))
    vt = pd.DataFrame(rows)

    c = pd.read_csv(DERIVED / "concepts.csv")
    c["depth_numbers"] = [int(hn[idx[d]]) for d in c.decl]
    c[["label", "decl", "depth_numbers"]].to_csv(DERIVED / "variants_concepts.csv", index=False)

    keep = is_thm[et[:, 0]] & ~is_thm[et[:, 1]] & ~is_meta[et[:, 1]]
    e = et[keep]
    depth = np.zeros(len(df), dtype=np.int32)
    np.maximum.at(depth, e[:, 0], hn[e[:, 1]])
    lib = pd.read_parquet(DERIVED / "library_depths.parquet")
    lib["depth_numbers"] = depth[df.is_named_thm.to_numpy()]
    lib.to_parquet(DERIVED / "library_depths_numbers.parquet")

    # 2. direct use in proofs
    Gd = proof_graph_direct()
    t = pd.read_csv(DERIVED / "targets.csv")
    key_of = {}
    for r in m.itertuples():
        for dname in t.set_index("key").loc[r.key, "decls"].split():
            if dname in idx.index:
                key_of.setdefault(int(idx[dname]), r.key)
    ids = np.array(list(key_of))
    edges = []
    for r in m.itertuples():
        if r.statement_only:
            continue
        i = int(idx[r.decl])
        rp = g.reach(Gd, [i])
        rp[i] = False
        for j in ids[rp[ids]]:
            if key_of[int(j)] != r.key:
                edges.append((r.key, key_of[int(j)]))
    fd = pd.DataFrame(edges, columns=["user", "used"]).drop_duplicates()
    fd.to_csv(DERIVED / "famous_edges_direct.csv", index=False)
    vt.to_csv(DERIVED / "variants_theorems.csv", index=False)
    return vt, c, fd, hn


if __name__ == "__main__":
    vt, c, fd, hn = main()
    idx = g.name_index()
    print("depth with numbers given:", {n: int(hn[idx[n]]) for n in
                                         ["Nat", "Int", "Rat", "Real", "Complex", "Field", "Group",
                                          "MetricSpace", "MeasureTheory.Measure", "AlgebraicGeometry.Scheme"]})
    print(vt.describe().round(1).to_string())
    print(len(fd), "direct famous dependencies")
