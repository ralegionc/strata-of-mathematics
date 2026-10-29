"""Does depth follow the syllabus? (prediction P2 in results/preregistration.md)

mathlib's docs/undergrad.yaml lists the undergraduate curriculum, docs/overview.yaml a wider survey that
adds graduate topics. Every entry names a Lean declaration. A theorem's depth is its statement depth;
a definition's depth is its own height. Writes data/derived/syllabus.csv.
"""
import numpy as np
import pandas as pd
import yaml

import graph as g
from config import DERIVED, RAW


def entries(fname):
    def walk(x, path=()):
        if isinstance(x, dict):
            for k, v in x.items():
                yield from walk(v, path + (k,))
        elif isinstance(x, str) and x.split():
            yield path, x.split()[0]
    return list(walk(yaml.safe_load(open(RAW / fname, encoding="utf-8"))))


def main():
    df = g.nodes()
    idx = g.name_index()
    hs = np.load(DERIVED / "h_stmt.npy")
    Gs = g.statement_graph()
    is_thm, is_meta = df.is_thm.to_numpy(), df.is_meta.to_numpy()
    et = g.edges_type()
    to_real = g.reach(Gs.T.tocsr(), [int(idx["Real"])])
    rows = []
    for fname, lst in (("undergrad.yaml", "undergraduate"), ("overview.yaml", "overview")):
        for path, decl in entries(fname):
            if decl not in idx.index:
                continue
            i = int(idx[decl])
            if is_thm[i]:
                src = g.out_neighbours(et, i)
                src = src[~is_thm[src] & ~is_meta[src]]
                depth = int(hs[src].max()) if len(src) else 0
                real = bool(to_real[src].any()) if len(src) else False
            else:
                depth, real = int(hs[i]), bool(to_real[i])
            rows.append(dict(list=lst, area=path[0], section=" / ".join(path[:-1]), label=path[-1], decl=decl,
                             kind="theorem" if is_thm[i] else "definition", depth=depth, uses_real=real))
    s = pd.DataFrame(rows)
    under = set(s[s.list == "undergraduate"].decl)
    s["overview_only"] = (s.list == "overview") & ~s.decl.isin(under)
    s.to_csv(DERIVED / "syllabus.csv", index=False)
    return s


if __name__ == "__main__":
    from scipy.stats import mannwhitneyu
    s = main()
    u = s[s.list == "undergraduate"].drop_duplicates("decl")
    o = s[s.overview_only].drop_duplicates("decl")
    print(len(u), "undergraduate,", len(o), "overview only")
    print("median depth", u.depth.median(), o.depth.median(),
          "one-sided p (undergrad shallower)", mannwhitneyu(u.depth, o.depth, alternative="less").pvalue)
    for k in (False, True):
        a, b = u[u.uses_real == k].depth, o[o.uses_real == k].depth
        print("real" if k else "no real", len(a), len(b), a.median(), b.median(),
              mannwhitneyu(a, b, alternative="less").pvalue)
    print(s.groupby(["list", "area"]).depth.median().to_string())
