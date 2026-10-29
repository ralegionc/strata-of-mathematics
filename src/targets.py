"""Collect the famous theorems that mathlib links to Lean declarations.

Sources (both shipped in mathlib's docs/ folder at the pinned tag):
  1000.yaml  Wikipedia's list of theorems, keyed by Wikidata id
  100.yaml   Freek Wiedijk's "Formalizing 100 Theorems"
Extra links found by searching mathlib docstrings live in data/labels/extra_links.csv.

Writes data/derived/targets.csv with one row per theorem:
  key, source, wikidata, title, decls (space separated), statement_only
"""
import csv

import pandas as pd
import yaml

from config import DERIVED, LABELS, RAW

# entries that mathlib's lists link to the same Lean statement as another entry
DUPLICATES = {
    "f2": "wQ192760",          # Fundamental theorem of algebra, listed in both lists
    "wQ179467": "wQ3984053",   # "Fourier theorem" is linked to the Fourier inversion lemmas
    "wQ1187646": "wQ1065966",  # Fundamental theorem on homomorphisms = first isomorphism theorem
    "f74": "",                 # induction: linked to the type `Nat` itself, not to a statement
}


def _clean(name):
    """Lean prints names unescaped (`Theorems100.82.x`); the docs escape them (`«82»`)."""
    return name.replace("«", "").replace("»", "")


def _decls(entry):
    if "decl" in entry:
        return [_clean(entry["decl"])]
    if "decls" in entry:
        return [_clean(d) for d in entry["decls"]]
    return []


def load():
    rows = []
    d1000 = yaml.safe_load(open(RAW / "1000.yaml", encoding="utf-8"))
    for key, e in d1000.items():
        if not e:
            continue
        decls = _decls(e)
        stmt = e.get("statement")
        if not decls and not stmt:
            continue
        qid = str(key).rstrip("X")
        rows.append(dict(key=f"w{key}", source="1000", wikidata=qid, title=e["title"],
                         decls=" ".join(decls or [stmt]), statement_only=not decls))
    d100 = yaml.safe_load(open(RAW / "100.yaml", encoding="utf-8"))
    for key, e in d100.items():
        decls = _decls(e or {})
        if not decls:
            continue
        rows.append(dict(key=f"f{key}", source="100", wikidata="", title=e["title"],
                         decls=" ".join(decls), statement_only=False))
    extra = LABELS / "extra_links.csv"
    if extra.exists():
        for r in csv.DictReader(open(extra, encoding="utf-8")):
            if r.get("accept", "").strip().lower() != "yes":
                continue
            rows.append(dict(key=f"x{r['wikidata']}", source="docstring", wikidata=r["wikidata"],
                             title=r["title"], decls=r["decl"], statement_only=False))
    df = pd.DataFrame(rows)
    # Freek's list overlaps the 1000 list: drop a 100-list row when a 1000-list row
    # already uses one of its declarations.
    seen = set()
    for decls in df.loc[df.source != "100", "decls"]:
        seen.update(decls.split())
    dup = (df.source == "100") & df.decls.map(lambda s: bool(set(s.split()) & seen))
    df = df[~dup & ~df.key.isin(DUPLICATES)].reset_index(drop=True)
    return df


if __name__ == "__main__":
    df = load()
    df.to_csv(DERIVED / "targets.csv", index=False)
    print(df.source.value_counts().to_string())
    print(len(df), "targets")
