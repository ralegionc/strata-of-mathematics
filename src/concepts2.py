"""Fresh concepts for prediction P3 (results/preregistration.md).

Every definition named in mathlib's undergrad.yaml and overview.yaml that is a concept and was not among
the first 183, minus a fixed rule set out before dating: no data structures (the overview's "Data
structures" area) and no theorem-like entries (labels naming a theorem, an isomorphism, an existence
result, an equivalence, a correspondence or a formula).

Dates come from Wikipedia, as in test 6: search for the label, read the article's opening section, take
the earliest year in a sentence saying the concept was introduced, defined, first used or named.
Writes data/derived/concepts_fresh.csv.
"""
import json
import re

import numpy as np
import pandas as pd
import requests

import dating2
import graph as g
from config import DERIVED, RAW, USER_AGENT
from syllabus import entries

EXCLUDE_LABEL = re.compile(r"theorem|isomorphism|existence|equivalence|correspondence|formula", re.I)
SEARCH_CACHE = RAW / "wikipedia_search_concepts.json"


def fresh():
    df = g.nodes()
    idx = g.name_index()
    old = set(pd.read_csv(DERIVED / "concepts.csv").decl)
    rows, seen = [], set()
    for fname in ("overview.yaml", "undergrad.yaml"):
        for path, decl in entries(fname):
            if decl in seen or decl in old or decl not in idx.index:
                continue
            i = int(idx[decl])
            if not df.is_concept.iat[i]:
                continue
            if path[0] == "Data structures" or EXCLUDE_LABEL.search(path[-1]):
                continue
            seen.add(decl)
            rows.append(dict(label=path[-1], decl=decl, area=path[0], list=fname.split(".")[0]))
    return pd.DataFrame(rows)


def main():
    c = fresh()
    df = g.nodes()
    idx = g.name_index()
    hs = np.load(DERIVED / "h_stmt.npy")
    Gs = g.statement_graph()
    real = int(idx["Real"])
    c["depth"] = [int(hs[idx[d]]) for d in c.decl]
    c["uses_real"] = [bool(g.reach(Gs, [int(idx[d])])[real]) for d in c.decl]
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    found = json.load(open(SEARCH_CACHE, encoding="utf-8")) if SEARCH_CACHE.exists() else {}
    for lab in c.label:
        if lab not in found:
            found[lab] = dating2.wiki_search(f"{lab} mathematics", s)
    json.dump(found, open(SEARCH_CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    ext = dating2.wiki_extracts(sorted({v for v in found.values() if v}))
    out = []
    for r in c.itertuples():
        art = found.get(r.label)
        y, sent, where = dating2.wiki_year(ext.get(art, ""), r.label, set()) if art else (None, None, None)
        out.append(dict(wiki_article=art, wiki_year=y, wiki_where=where, wiki_sentence=sent))
    c = pd.concat([c.reset_index(drop=True), pd.DataFrame(out)], axis=1)
    c.to_csv(DERIVED / "concepts_fresh.csv", index=False)
    return c


if __name__ == "__main__":
    c = main()
    print(len(c), "fresh concepts;", c.uses_real.sum(), "through the reals")
    print(c.wiki_year.notna().sum(), "dated by Wikipedia;", c[c.uses_real].wiki_year.notna().sum(), "of the real ones")
    print(c.wiki_where.value_counts().to_string())
