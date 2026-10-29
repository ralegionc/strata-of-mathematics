"""Discovery years for every target, and an audit of the hand-made dates against Wikidata.

The dates in data/labels/hand_dates.csv were written by Claude from general knowledge *before*
Wikidata was queried, so Wikidata is an independent check:
  1. P575 "time of discovery or invention" (year precision), where Wikidata has one
  2. lifetimes: a credited discoverer (P61) or a namesake (P138) should have been alive
     (aged 15 or more) when the result was first stated or proved

Writes data/derived/dates.csv and results/dating_audit.csv.
"""
import json

import numpy as np
import pandas as pd

from config import DERIVED, LABELS, RESULTS


def load_dates():
    d = pd.read_csv(LABELS / "hand_dates.csv")
    t = pd.read_csv(DERIVED / "targets.csv")
    d = t[["key", "title", "wikidata"]].merge(d, on="key", how="left")
    return d


def audit(d):
    w = pd.read_csv(DERIVED / "wikidata_dates.csv").set_index("wikidata")
    rows = []
    for r in d.itertuples():
        if not isinstance(r.wikidata, str) or r.wikidata not in w.index or r.key.endswith("X"):
            continue
        wr = w.loc[r.wikidata]
        people = {**json.loads(wr.discoverers), **json.loads(wr.named_after)}
        alive = None
        if any(b is not None for b, _ in people.values()) and not np.isnan(r.year_stated):
            alive = False
            for b, dd in people.values():
                if b is None:
                    continue
                hi = dd if dd is not None else 2026
                if any(b + 15 <= y <= hi for y in (r.year_stated, r.year_proved)):
                    alive = True
        rows.append(dict(key=r.key, title=r.title, year_stated=r.year_stated,
                         year_proved=r.year_proved, confidence=r.confidence,
                         p575=wr.p575, people=json.dumps(people, ensure_ascii=False),
                         in_lifetime=alive))
    a = pd.DataFrame(rows)
    a["p575_gap"] = np.minimum((a.year_stated - a.p575).abs(), (a.year_proved - a.p575).abs())
    return a


if __name__ == "__main__":
    d = load_dates()
    d.to_csv(DERIVED / "dates.csv", index=False)
    a = audit(d)
    a.to_csv(RESULTS / "dating_audit.csv", index=False)
    p = a.dropna(subset=["p575", "year_stated"])
    print(f"P575 overlap: {len(p)}; median gap {p.p575_gap.median():.0f} y; "
          f"within 5 y {(p.p575_gap <= 5).mean():.0%}; within 25 y {(p.p575_gap <= 25).mean():.0%}")
    print(p.sort_values("p575_gap", ascending=False)[["title", "year_stated", "year_proved", "p575"]].head(10).to_string())
    l = a.dropna(subset=["in_lifetime"])
    print(f"lifetime check: {len(l)} theorems with a dated person; "
          f"{l.in_lifetime.astype(bool).mean():.0%} fall inside a lifetime")
    print(l[~l.in_lifetime.astype(bool)][["title", "year_stated", "year_proved", "people"]].to_string())
