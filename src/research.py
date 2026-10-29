"""Research-level theorems formalized in Lean projects outside mathlib.

Each project is cloned under research/<name> with its own toolchain and mathlib on D: (see
tools/env.sh), built, and dumped with lean/Extract.lean importing the module that holds the main
theorem. The graph goes to data/derived/research/<name>/graph; this script measures the main
theorem with exactly the definitions used for the mathlib sample, records reference depths so the
versions can be compared, and appends a row to data/derived/research.csv.

Usage: python research.py <name>
"""
import json
import sys

import numpy as np
import pandas as pd

import graph as g
import variants
from chains import chain_from
from config import DERIVED, GRAPH

PROJECTS = {
    "pfr": dict(repo="teorth/pfr", module="PFR.Main", decl="PFR_conjecture",
                title="Polynomial Freiman–Ruzsa conjecture", year_stated=1999, year_proved=2023,
                field="Combinatorics",
                note="Marton's conjecture as stated by Ruzsa (1999); proved by Gowers, Green, Manners and Tao"),
    "sphere-packing": dict(repo="thefundamentaltheor3m/Sphere-Packing-Lean", module="SpherePacking.MainTheorem",
                           decl="SpherePacking.MainTheorem",
                           title="Sphere packing in dimension 8", year_stated=2003, year_proved=2016,
                           field="Geometry",
                           note="optimality of E8; Cohn and Elkies's bound (2003), proved by Viazovska"),
    "sphere-eversion": dict(repo="leanprover-community/sphere-eversion", module="SphereEversion.Main",
                            decl="Smale",
                            title="Smale's sphere eversion", year_stated=1957, year_proved=1957,
                            field="Topology", note="Smale 1957, published 1959"),
    "carleson": dict(repo="fpvandoorn/carleson", module="Carleson.Classical.ClassicalCarleson",
                     decl="classical_carleson", title="Carleson's theorem",
                     year_stated=1915, year_proved=1966, field="Analysis",
                     note="Lusin's conjecture (1915); proved by Carleson"),
}
REFERENCE = ["Nat", "Rat", "Real", "Complex", "Field", "MetricSpace", "MeasureTheory.Measure"]


def measure(name, decl=None):
    P = PROJECTS[name]
    decl = decl or P["decl"]
    g.set_graph(DERIVED / "research" / name / "graph")
    try:
        df = g.nodes()
        idx = g.name_index()
        conc, named = df.is_concept.to_numpy(), df.is_named_thm.to_numpy()
        is_thm, is_meta = df.is_thm.to_numpy(), df.is_meta.to_numpy()
        Gs, Gp = g.statement_graph(), g.proof_graph()
        hs = g.heights(Gs, conc)
        Gn, _ = variants.statement_graph_numbers()
        hn = g.heights(Gn, conc)
        hp = g.heights(Gp, conc | named)
        i = int(idx[decl])
        src = g.out_neighbours(g.edges_type(), i)
        src = src[~is_thm[src] & ~is_meta[src]]
        rs = g.reach(Gs, src)
        rp = g.reach(Gp, [i])
        rp[i] = False
        uses_sorry = bool(rp[int(idx["sorryAx"])]) if "sorryAx" in idx.index else False
        import proofsplit
        chain_layers, own_layers = proofsplit.split(i, Gp, hp, conc | named, df.module.to_numpy(),
                                                    proofsplit.is_own_research)
        row = dict(name=name, title=P["title"], decl=decl, module=df.module.iat[i], field=P["field"],
                   year_stated=P["year_stated"], year_proved=P["year_proved"], note=P["note"],
                   stmt_depth=int(hs[src].max()), stmt_size=int(conc[rs].sum()),
                   depth_numbers=int(hn[src].max()), uses_real=bool(rs[int(idx["Real"])]),
                   uses_measure=bool(rs[int(idx["MeasureTheory.Measure"])]) if "MeasureTheory.Measure" in idx.index else False,
                   uses_inner=bool(rs[int(idx["InnerProductSpace"])]) if "InnerProductSpace" in idx.index else False,
                   proof_depth=int(hp[i] - 1), proof_size=int((conc | named)[rp].sum()), uses_sorry=uses_sorry,
                   chain_layers=chain_layers, own_layers=own_layers,
                   nodes=len(df), chain=json.dumps(chain_from(src, Gs, hs, conc, df.name.to_numpy()), ensure_ascii=False),
                   **{f"ref_{n}": int(hs[idx[n]]) for n in REFERENCE if n in idx.index})
    finally:
        g.set_graph(GRAPH)
    out = DERIVED / "research.csv"
    old = pd.read_csv(out) if out.exists() else pd.DataFrame()
    if len(old):
        old = old[old.name != name]
    pd.concat([old, pd.DataFrame([row])], ignore_index=True).to_csv(out, index=False)
    return row


if __name__ == "__main__":
    r = measure(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    for k, v in r.items():
        print(f"{k:16s} {v}")
