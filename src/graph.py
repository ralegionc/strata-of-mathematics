"""Load the mathlib dependency graph dumped by lean/Extract.lean and define node classes.

Node classes
  concept   a definition a mathematician would name: def, inductive type, structure, class,
            axiom or opaque constant that is not an instance, projection, auxiliary recursor,
            matcher, private or compiler-internal name, and lives in a mathematical module
  theorem   a `theorem`/`lemma` (kernel kind thm)
  glue      everything else (instances, projections, constructors, recursors, auxiliary
            definitions). Glue passes dependencies through but adds no depth.

Two graphs
  statement graph  edges out of non-theorems only, and never into a theorem: what you must
                   know to *read* a statement (definitions all the way down, no proofs)
  proof graph      every edge, type and value, for every constant
"""
import re

import numpy as np
import pandas as pd
import scipy.sparse as sp

from config import GRAPH

KINDS = ["axiom", "def", "thm", "opaque", "quot", "induct", "ctor", "rec"]
F_INTERNAL, F_INSTANCE, F_PROJ, F_AUXREC, F_MATCHER, F_CLASS, F_STRUCT, F_PRIVATE = (
    1, 2, 4, 8, 16, 32, 64, 128)

# auto-generated companions that are not flagged by the Lean predicates above
AUX_SUFFIX = re.compile(
    r"\.(?:noConfusionType|ctorIdx|toCtorIdx|ctorElim|ctorElimType|recAux|sizeOf_spec|"
    r"injEq|inj|ext_iff|ext|eq_\d+|eq_def|proof_\d+|match_\d+|congr_simp|_sunfold|"
    r"_unfold|elim|casesAuxOn|ibelow|binductionOn|below|brecOn|brecOn\.go|recOn|casesOn|"
    r"go|loop)$")

# modules whose definitions are not mathematics (tactics, elaborator, metaprogramming)
NON_MATH = re.compile(
    r"^(Lean|Lake|Aesop|Qq|ProofWidgets|LeanSearchClient|Plausible|ImportGraph|Cli|"
    r"Batteries\.(Tactic|Lean|CodeAction|Linter|Util)|Mathlib\.(Tactic|Util|Lean|Linter|"
    r"Testing|Deprecated)|Std\.(Tactic|Time|Internal|Sat|Do)|Init\.(Meta|Tactics|Grind|"
    r"Conv|Notation|Hints|Try|While|System|Data\.Format|Data\.Repr|Data\.ToString))")

# metaprogramming namespaces defined inside mathematical modules (Init.Prelude holds Lean.Syntax,
# which structures reach through `autoParam` tactic blocks in their field types)
META_NAME = re.compile(
    r"^(?:Lean|Lake|Aesop|Qq|ProofWidgets|LeanSearchClient|Plausible|ImportGraph|Cli|"
    r"Mathlib\.Tactic|Mathlib\.Meta|Mathlib\.Linter|Batteries\.Tactic|Std\.Tactic)\.")

# identity-function annotations: glue, not concepts
ANNOTATIONS = {"outParam", "semiOutParam", "optParam", "autoParam", "namedPattern",
               "inferInstance", "inferInstanceAs"}

_cache = {}


def set_graph(path):
    """Point every function here at another extracted graph (a research project's) and reset."""
    global GRAPH
    GRAPH = path
    _cache.clear()


def nodes():
    if "nodes" not in _cache:
        pq = GRAPH / "nodes.parquet"
        if not pq.exists():
            df = pd.read_csv(GRAPH / "nodes.tsv", sep="\t", quoting=3, keep_default_na=False,
                             dtype={"name": str, "kind": str, "module": str})
            df.to_parquet(pq)
        df = pd.read_parquet(pq)
        df["kind_code"] = df.kind.map({k: i for i, k in enumerate(KINDS)}).astype(np.int8)
        bad = F_INTERNAL | F_INSTANCE | F_PROJ | F_AUXREC | F_MATCHER | F_PRIVATE
        df["is_meta"] = df.module.str.match(NON_MATH) | df.name.str.match(META_NAME)
        math = ~df.is_meta
        aux = df.name.str.contains(AUX_SUFFIX)
        df["is_thm"] = df.kind == "thm"
        df["is_concept"] = (df.kind.isin(["def", "induct", "axiom", "opaque", "quot"])
                            & ((df["flags"] & bad) == 0) & ~aux & math
                            & ~df.name.isin(ANNOTATIONS))
        df["is_named_thm"] = df.is_thm & ((df["flags"] & (F_INTERNAL | F_PRIVATE)) == 0) & ~aux & math
        _cache["nodes"] = df
    return _cache["nodes"]


def _edges(which):
    key = f"edges_{which}"
    if key not in _cache:
        npy = GRAPH / f"{key}.npy"
        if not npy.exists():
            e = pd.read_csv(GRAPH / f"{key}.tsv", sep="\t", dtype=np.int32).to_numpy()
            np.save(npy, e)
        _cache[key] = np.load(npy)
    return _cache[key]


def edges_type():
    return _edges("type")


def edges_value():
    return _edges("value")


def csr(src, dst, n):
    m = sp.csr_matrix((np.ones(len(src), dtype=np.int32), (src, dst)), shape=(n, n))
    m.sum_duplicates()
    m.data[:] = 1
    return m


def statement_graph():
    """Edges u -> v where neither end is a theorem and v is not metaprogramming."""
    if "G_s" not in _cache:
        df = nodes()
        thm = df.is_thm.to_numpy()
        meta = df.is_meta.to_numpy()
        e = np.concatenate([edges_type(), edges_value()])
        keep = ~thm[e[:, 0]] & ~thm[e[:, 1]] & ~meta[e[:, 1]]
        _cache["G_s"] = csr(e[keep, 0], e[keep, 1], len(df))
    return _cache["G_s"]


def proof_graph():
    if "G_p" not in _cache:
        df = nodes()
        meta = df.is_meta.to_numpy()
        e = np.concatenate([edges_type(), edges_value()])
        e = e[~meta[e[:, 1]]]
        _cache["G_p"] = csr(e[:, 0], e[:, 1], len(df))
    return _cache["G_p"]


def heights(G, weight):
    """Longest weighted path below every node (weight counted at each node, including itself).

    Strongly connected components (an inductive type and its constructors, mutual blocks)
    are condensed first; a component weighs 1 if any member has weight 1.
    Returns an int array indexed by node.
    """
    from scipy.sparse.csgraph import connected_components
    n = G.shape[0]
    ncomp, lab = connected_components(G, directed=True, connection="strong")
    w_c = np.zeros(ncomp, dtype=np.int32)
    np.maximum.at(w_c, lab, weight.astype(np.int32))
    coo = G.tocoo()
    cs, cd = lab[coo.row], lab[coo.col]
    m = cs != cd
    C = csr(cs[m], cd[m], ncomp)            # condensed DAG, parent -> child
    R = C.T.tocsr()                          # child -> parents
    outdeg = np.diff(C.indptr).astype(np.int64)
    best = np.zeros(ncomp, dtype=np.int32)
    h = np.full(ncomp, -1, dtype=np.int32)
    frontier = np.flatnonzero(outdeg == 0)
    h[frontier] = w_c[frontier]
    while len(frontier):
        starts, ends = R.indptr[frontier], R.indptr[frontier + 1]
        cnt = ends - starts
        if cnt.sum() == 0:
            break
        idx = np.repeat(starts - np.cumsum(np.r_[0, cnt[:-1]]), cnt) + np.arange(cnt.sum())
        parents = R.indices[idx]
        hv = np.repeat(h[frontier], cnt)
        np.maximum.at(best, parents, hv)
        np.subtract.at(outdeg, parents, 1)
        cand = np.unique(parents)
        frontier = cand[outdeg[cand] == 0]
        h[frontier] = w_c[frontier] + best[frontier]
    assert (h >= 0).all(), "cycle left after condensation"
    return h[lab]


def reach(G, sources):
    """Boolean mask of nodes reachable from `sources` (sources included)."""
    n = G.shape[0]
    seen = np.zeros(n, dtype=bool)
    frontier = np.unique(np.asarray(sources, dtype=np.int64))
    seen[frontier] = True
    indptr, indices = G.indptr, G.indices
    while len(frontier):
        starts, ends = indptr[frontier], indptr[frontier + 1]
        cnt = ends - starts
        tot = cnt.sum()
        if tot == 0:
            break
        idx = np.repeat(starts - np.cumsum(np.r_[0, cnt[:-1]]), cnt) + np.arange(tot)
        nb = np.unique(indices[idx])
        frontier = nb[~seen[nb]]
        seen[frontier] = True
    return seen


def name_index():
    if "name_index" not in _cache:
        df = nodes()
        _cache["name_index"] = pd.Series(df.id.to_numpy(), index=df.name.to_numpy())
    return _cache["name_index"]


def out_neighbours(edges, i):
    """Targets of edges leaving node i (edges sorted by src, as the extractor writes them)."""
    lo = np.searchsorted(edges[:, 0], i, side="left")
    hi = np.searchsorted(edges[:, 0], i, side="right")
    return edges[lo:hi, 1]
