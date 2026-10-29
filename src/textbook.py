"""Depth of the textbook restatements in lean/Textbook.lean, next to mathlib's own statements.

lean/ExtractNames.lean lists, by name, the constants each restatement uses; depths come from the
mathlib graph already extracted (the restatements add nothing that other declarations depend on).
Writes data/derived/textbook.csv.
"""
import numpy as np
import pandas as pd

import graph as g
from config import DERIVED

PAIRS = {  # Lean name -> key of mathlib's statement in the sample
    "pythagoras": "wQ11518", "pythagoras_int": "wQ11518", "thales": "wQ285719", "heron": "f57",
    "euclid_primes": "wQ1506253", "sqrt_two_irrational": "f1", "fermat_little": "wQ188295",
    "wilson": "wQ276082", "crt": "wQ193878", "bezout": "wQ513028", "two_squares": "wQ914517",
    "geometric_sum": "f66", "arithmetic_sum": "f68", "triangle": "f91", "am_gm": "f38",
    "binomial": "wQ26708", "ivt": "wQ245098", "fta": "wQ192760", "area_circle": "f9",
    "cauchy_schwarz": "f78",
}


def main():
    df = g.nodes()
    idx = g.name_index()
    conc, is_thm, is_meta = df.is_concept.to_numpy(), df.is_thm.to_numpy(), df.is_meta.to_numpy()
    hs = np.load(DERIVED / "h_stmt.npy")
    hn = np.load(DERIVED / "h_stmt_numbers.npy")
    Gs = g.statement_graph()
    real = int(idx["Real"])
    e = pd.read_csv(DERIVED / "textbook_edges.tsv", sep="\t", names=["name", "part", "used"], quoting=3)
    e = e[(e.part == "type") & e.used.isin(idx.index)]
    m = pd.read_csv(DERIVED / "theorems.csv").set_index("key")
    v = pd.read_csv(DERIVED / "variants_theorems.csv").set_index("key")
    rows = []
    for short, key in PAIRS.items():
        used = e[e.name == f"Textbook.{short}"].used.map(idx).to_numpy().astype(np.int64)
        src = used[~is_thm[used] & ~is_meta[used]]
        rs = g.reach(Gs, src)
        rows.append(dict(
            name=short, key=key, title=m.loc[key, "title"], year_stated=m.loc[key, "year_stated"],
            textbook_depth=int(hs[src].max()), textbook_size=int(conc[rs].sum()),
            textbook_depth_numbers=int(hn[src].max()), textbook_uses_real=bool(rs[real]),
            mathlib_decl=m.loc[key, "decl"], mathlib_depth=int(m.loc[key, "stmt_depth"]),
            mathlib_size=int(m.loc[key, "stmt_size"]), mathlib_depth_numbers=int(v.loc[key, "depth_numbers"]),
            mathlib_uses_real=bool(m.loc[key, "uses_real"])))
    t = pd.DataFrame(rows)
    t.to_csv(DERIVED / "textbook.csv", index=False)
    return t


if __name__ == "__main__":
    t = main()
    print(t[["name", "year_stated", "textbook_depth", "mathlib_depth", "textbook_uses_real", "mathlib_uses_real",
             "textbook_depth_numbers", "mathlib_depth_numbers"]].to_string())
