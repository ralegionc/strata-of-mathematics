"""Audit the library-time dates commit by commit, on a fixed random sample.

library_time.py looks at one snapshot a month. Here, for 30 theorems and 10 concepts dated from mathlib3,
git itself lists every commit whose diff adds or removes a declaration line of the short name
(`git log -G`), oldest first, and the first of them whose changed files declare exactly the full Lean 3
name gives the entry date to the day. The snapshot month should be that commit's month, or earlier when
library_time followed a namespace change inside the same file (months_back > 0): a change to a
`namespace` line alone does not touch the declaration line, so git's search cannot see it.
Writes results/library_audit.csv.
"""
import re
import sys
from datetime import datetime

import pandas as pd

from config import DERIVED, RESULTS
from library_time import DECL3, H3, P3, Files, git


def first_commit(files, full, short):
    pat = rf"^\s*(?:@\[[^\]]*\]\s*)*(?:(?:protected|private|noncomputable|@\[[^\]]*\])\s+)*{DECL3}\s+((?:[\w'.]*\.)?{re.escape(short)})(?![\w'.])"
    # `git log -G` takes POSIX extended regexes, without lookahead
    kw = DECL3[len("(?:"):-1]
    gpat = rf"({kw})\s+([A-Za-z0-9_'.]*\.)?{re.escape(short)}([^A-Za-z0-9_'.]|$)"
    # committer dates in local time, as `rev-list --before` reads them for the snapshots
    for line in git(H3, "log", "--reverse", "--format=%H %ct", "-G", gpat, "--", *P3).splitlines():
        c, when = line.split()
        changed = [p for p in git(H3, "show", "--format=", "--name-only", c).splitlines() if p.endswith(".lean")]
        if not changed:
            continue
        for hit in git(H3, "grep", "-n", "-P", "-o", pat, c, "--", *changed).splitlines():
            _, path, ln, text = hit.split(":", 3)
            tok = text.split()[-1]
            if files.full_name(c, path, int(ln), tok) == full:
                return pd.Timestamp(datetime.fromtimestamp(int(when)))
    return None


def main():
    T = pd.read_csv(DERIVED / "library_time.csv", parse_dates=["entered"])
    files = Files(H3)
    t = T[(T.how == "mathlib3") & (T.kind == "theorem")].sample(30, random_state=20261017)
    c = T[(T.how == "mathlib3") & (T.kind == "concept")].sample(10, random_state=20261017)
    rows = []
    for r in pd.concat([t, c]).itertuples():
        g = first_commit(files, r.lean3, r.short3)
        rows.append(dict(kind=r.kind, decl=r.decl, lean3=r.lean3, git_first=None if g is None else g.date()))
        print(rows[-1], flush=True)
    return compare(pd.DataFrame(rows))


def compare(a):
    """Set each audited name's snapshot month beside git's date (rerun with `compare` after library_time)."""
    T = pd.read_csv(DERIVED / "library_time.csv", parse_dates=["entered"])
    a = a[["kind", "decl", "lean3", "git_first"]].merge(T[["kind", "decl", "entered", "months_back"]],
                                                        on=["kind", "decl"])
    g = pd.to_datetime(a.git_first)
    a["snapshot_month"] = a.entered.dt.strftime("%Y-%m")
    a["months_late"] = (a.entered.dt.year - g.dt.year) * 12 + (a.entered.dt.month - g.dt.month)
    a = a.drop(columns="entered")
    a.to_csv(RESULTS / "library_audit.csv", index=False)
    return a


if __name__ == "__main__":
    a = compare(pd.read_csv(RESULTS / "library_audit.csv")) if "compare" in sys.argv else main()
    for k, v in a.groupby("kind"):
        g = v.months_late.dropna()
        print(k, len(v), "found by git", len(g), "same month", int((g == 0).sum()), "late", int((g > 0).sum()),
              "early", int((g < 0).sum()), "early through a namespace change", int(((g < 0) & (v.months_back > 0)).sum()))
