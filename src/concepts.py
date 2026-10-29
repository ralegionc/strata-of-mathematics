"""Depth of the concepts themselves: core definitions from mathlib's overview lists, dated by hand.

Reads data/labels/concept_dates.csv (dates written by Claude from general knowledge; see README)
and writes data/derived/concepts.csv with each concept's depth, closure size and whether its
definition passes through the real numbers.
"""
import numpy as np
import pandas as pd

import graph as g
from config import DERIVED, LABELS
from measures import field_of


def main():
    df = g.nodes()
    idx = g.name_index()
    hs = np.load(DERIVED / "h_stmt.npy")
    Gs = g.statement_graph()
    conc = df.is_concept.to_numpy()
    real = int(idx["Real"])
    c = pd.read_csv(LABELS / "concept_dates.csv")
    missing = c[~c.decl.isin(idx.index)]
    if len(missing):
        print("not in mathlib:", missing.decl.tolist())
    c = c[c.decl.isin(idx.index)].copy()
    rows = []
    for r in c.itertuples():
        i = int(idx[r.decl])
        rs = g.reach(Gs, [i])
        rows.append(dict(depth=int(hs[i]), size=int(conc[rs].sum()), uses_real=bool(rs[real]),
                         module=df.module.iat[i], field=field_of(df.module.iat[i])))
    c = pd.concat([c.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    c.to_csv(DERIVED / "concepts.csv", index=False)
    return c


if __name__ == "__main__":
    c = main()
    print(len(c), "concepts")
    print(c.groupby("uses_real").depth.describe().to_string())
