"""Replication in a second library: Metamath's set.mm (ZFC set theory, ℝ built from Dedekind cuts).

Metamath has no type theory, so the measures are rebuilt from its own structure:

  construct   a syntax axiom (`cr $a class RR $.` introduces ℝ)
  definition  a `df-` axiom; the construct it defines is the newest construct appearing in it,
              because a definition may only use what came before plus the new symbol
  statement   the tokens of a theorem's assertion and its hypotheses; each constant token that
              belongs to exactly one syntax axiom names a construct (shared punctuation such as
              `(` or `{` is skipped)
  depth       longest chain of constructs, following definitions down to the primitive ones
  proof       labels cited in the proof (compressed or not); proof size is the number of
              distinct definitions and theorems reachable that way

Also computes the "numbers as given" variant: constructs in the section that builds the number
systems (from the first definition of positive integers, df-ni, up to the complex number axioms)
lose their definitions. Writes data/derived/metamath_*.
"""
import re
from collections import defaultdict

import numpy as np
import pandas as pd
import scipy.sparse as sp

import graph as g
from config import DERIVED, RAW

MM = RAW / "metamath" / "set.mm"
TYPECODES = {"|-", "wff", "class", "setvar", "set"}


def tokens(path=MM):
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\$\(.*?\$\)", " ", text, flags=re.S)  # comments
    return text.split()


def parse(toks):
    """Yield statements as dicts: label, kind ($a $p $e $f), typecode, math, proof, pos, hyps."""
    i, n = 0, len(toks)
    ehyps = [[]]  # stack of active essential hypotheses per scope
    pos = 0
    out = []
    consts, varsset = set(), set()
    while i < n:
        t = toks[i]
        if t == "${":
            ehyps.append([])
            i += 1
        elif t == "$}":
            ehyps.pop()
            i += 1
        elif t in ("$c", "$v", "$d"):
            j = toks.index("$.", i)
            if t == "$c":
                consts.update(toks[i + 1:j])
            elif t == "$v":
                varsset.update(toks[i + 1:j])
            i = j + 1
        elif i + 1 < n and toks[i + 1] in ("$a", "$p", "$e", "$f"):
            label, kind = t, toks[i + 1]
            if kind == "$p":
                j = toks.index("$=", i)
                k = toks.index("$.", j)
                math = toks[i + 2:j]
                proof = toks[j + 1:k]
            else:
                k = toks.index("$.", i)
                math = toks[i + 2:k]
                proof = []
            st = dict(label=label, kind=kind, typecode=math[0] if math else "", math=math[1:],
                      proof=proof, pos=pos, hyps=[h for scope in ehyps for h in scope])
            if kind == "$e":
                ehyps[-1].append(st)
            out.append(st)
            pos += 1
            i = k + 1
        else:
            i += 1
    return out, consts, varsset


def proof_labels(proof):
    if proof and proof[0] == "(":
        j = proof.index(")")
        return proof[1:j]
    return [p for p in proof if p != "?"]


def build():
    toks = tokens()
    st, consts, varsset = parse(toks)
    syntax = [s for s in st if s["kind"] == "$a" and s["typecode"] in ("wff", "class", "setvar")]
    # constant tokens of each syntax axiom
    tok2syn = defaultdict(set)
    for s in syntax:
        for t in s["math"]:
            if t in consts and t not in TYPECODES:
                tok2syn[t].add(s["label"])
    unique = {t: next(iter(v)) for t, v in tok2syn.items() if len(v) == 1}
    synpos = {s["label"]: s["pos"] for s in syntax}

    def constructs(math):
        return {unique[t] for t in math if t in unique}

    # definitions: construct -> constructs used in its df- axioms
    defs = defaultdict(set)
    def_label = {}
    for s in st:
        if s["kind"] == "$a" and s["label"].startswith("df-") and s["typecode"] == "|-":
            cs = constructs(s["math"])
            if not cs:
                continue
            new = max(cs, key=lambda c: synpos[c])
            defs[new] |= cs - {new}
            def_label.setdefault(new, s["label"])
    return st, syntax, unique, synpos, defs, def_label, constructs


def heights(nodes, edges):
    """Longest chain (weight 1 per construct) over a DAG given as dict node -> set(children)."""
    ids = {c: i for i, c in enumerate(nodes)}
    src, dst = [], []
    for u, vs in edges.items():
        for v in vs:
            if u in ids and v in ids:
                src.append(ids[u])
                dst.append(ids[v])
    G = g.csr(np.array(src, dtype=np.int64), np.array(dst, dtype=np.int64), len(nodes))
    h = g.heights(G, np.ones(len(nodes)))
    return {c: int(h[i]) for c, i in ids.items()}


NUMBER_START, NUMBER_END = "df-ni", "ax-cnex"


def main():
    st, syntax, unique, synpos, defs, def_label, constructs = build()
    nodes = [s["label"] for s in syntax]
    h = heights(nodes, defs)

    # numbers as given: drop definitions of constructs introduced in the construction section
    label_pos = {s["label"]: s["pos"] for s in st}
    lo, hi = label_pos[NUMBER_START], label_pos[NUMBER_END]
    in_numbers = {c for c in nodes if lo - 200 <= synpos[c] <= hi}
    defs_n = {c: (set() if c in in_numbers else vs) for c, vs in defs.items()}
    hn = heights(nodes, defs_n)

    # theorems
    th = [s for s in st if s["kind"] == "$p" and s["typecode"] == "|-"]
    by_label = {s["label"]: s for s in st}
    rows = []
    for s in th:
        math = list(s["math"]) + [t for hyp in s["hyps"] for t in hyp["math"]]
        cs = constructs(math)
        rows.append(dict(label=s["label"], pos=s["pos"], stmt_depth=max((h[c] for c in cs), default=0),
                         depth_numbers=max((hn[c] for c in cs), default=0), n_constructs=len(cs),
                         uses_real="cr" in cs or any("cr" in closure_of(c, defs) for c in cs)))
    t = pd.DataFrame(rows)

    # proof graph over $a/$p labels: proof size = distinct theorems and definitions reachable
    assert_labels = [s["label"] for s in st if s["kind"] in ("$a", "$p") and s["typecode"] == "|-"]
    aid = {l: i for i, l in enumerate(assert_labels)}
    src, dst = [], []
    for s in th:
        for l in proof_labels(s["proof"]):
            if l in aid and l != s["label"]:
                src.append(aid[s["label"]])
                dst.append(aid[l])
    P = g.csr(np.array(src, dtype=np.int64), np.array(dst, dtype=np.int64), len(assert_labels))
    return dict(st=st, h=h, hn=hn, defs=defs, def_label=def_label, unique=unique, theorems=t,
                P=P, aid=aid, assert_labels=assert_labels, by_label=by_label, constructs=constructs)


_closure_cache = {}


def closure_of(c, defs):
    if c in _closure_cache:
        return _closure_cache[c]
    seen, stack = set(), [c]
    while stack:
        u = stack.pop()
        for v in defs.get(u, ()):
            if v not in seen:
                seen.add(v)
                stack.append(v)
    _closure_cache[c] = seen
    return seen


def hundred():
    """Metamath's list of Wiedijk's 100 theorems: number, title, label."""
    s = (RAW / "metamath" / "mm_100.html").read_text(encoding="utf-8", errors="replace")
    rows = []
    for m in re.finditer(r'<li><a name="(\d+)">\d+</a>\.\s*(.*?)\(<a\s+href="mpeuni/([^".]+)\.html"', s, re.S):
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(2))).strip()
        rows.append(dict(freek=int(m.group(1)), title=title, label=m.group(3)))
    return pd.DataFrame(rows).drop_duplicates("freek")


def freek_keys():
    """Wiedijk number -> key of the dated theorem in the mathlib sample (or f<number>)."""
    import yaml

    from targets import DUPLICATES, _decls
    d1 = yaml.safe_load(open(RAW / "1000.yaml", encoding="utf-8"))
    d2 = yaml.safe_load(open(RAW / "100.yaml", encoding="utf-8"))
    dec2key = {}
    for k, e in d1.items():
        for d in _decls(e or {}):
            dec2key.setdefault(d, f"w{k}")
    out = {}
    for num, e in d2.items():
        key = None
        for d in _decls(e or {}):
            if d in dec2key:
                key = dec2key[d]
                break
        if key is None and DUPLICATES.get(f"f{num}"):
            key = DUPLICATES[f"f{num}"]
        out[int(num)] = key or f"f{num}"
    return out


def hundred_table(R):
    from config import LABELS
    hd = pd.concat([pd.read_csv(LABELS / "hand_dates.csv"), pd.read_csv(LABELS / "hand_dates_extra.csv")])
    hd = hd.drop_duplicates("key").set_index("key")
    H = hundred()
    fk = freek_keys()
    t = R["theorems"].set_index("label")
    defs = R["defs"]
    P, aid = R["P"], R["aid"]
    rows, reach = [], {}
    for r in H.itertuples():
        if r.label not in t.index:
            continue
        key = fk.get(r.freek, f"f{r.freek}")
        y = hd.loc[key] if key in hd.index else None
        cs = R["constructs"](list(R["by_label"][r.label]["math"]) +
                             [tok for hyp in R["by_label"][r.label]["hyps"] for tok in hyp["math"]])
        clos = set(cs).union(*[closure_of(c, defs) for c in cs]) if cs else set()
        rp = g.reach(P, [aid[r.label]])
        rp[aid[r.label]] = False
        reach[r.label] = rp
        rows.append(dict(freek=r.freek, title=r.title, label=r.label, key=key,
                         year_stated=None if y is None else y.year_stated,
                         year_proved=None if y is None else y.year_proved,
                         stmt_depth=int(t.loc[r.label, "stmt_depth"]),
                         depth_numbers=int(t.loc[r.label, "depth_numbers"]),
                         uses_real="cr" in clos, uses_complex="cc" in clos, proof_size=int(rp.sum())))
    df = pd.DataFrame(rows)
    edges = [(a, b) for a in df.label for b in df.label if a != b and reach[a][aid[b]]]
    fe = pd.DataFrame(edges, columns=["user", "used"])
    return df, fe


if __name__ == "__main__":
    R = main()
    df, fe = hundred_table(R)
    df.to_csv(DERIVED / "metamath_hundred.csv", index=False)
    fe.to_csv(DERIVED / "metamath_famous_edges.csv", index=False)
    R["theorems"].to_csv(DERIVED / "metamath_theorems.csv", index=False)
    print(df.drop(columns=["title"]).head(12).to_string())
    h, hn, defs, dl = R["h"], R["hn"], R["defs"], R["def_label"]
    syn_of = {v: k for k, v in R["unique"].items()}
    for c in ["cn", "cz", "cq", "cr", "cc", "cnr", "cnp", "cnq", "cnpi", "com", "cgrp", "ctop"]:
        print(c, syn_of.get(c), dl.get(c), "depth", h.get(c), "numbers given", hn.get(c))
    t = R["theorems"]
    print(len(t), "theorems; depth", t.stmt_depth.describe().round(1).to_dict())
    hd = hundred()
    print(len(hd), "of Wiedijk's 100 in set.mm;", hd.label.isin(t.label).sum(), "found")
