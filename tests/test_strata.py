"""Tests that could fail: toy graphs with known answers, then known facts about mathlib."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import graph as g  # noqa: E402
from config import DERIVED, GRAPH, LABELS  # noqa: E402

HAVE_GRAPH = (GRAPH / "nodes.parquet").exists() or (GRAPH / "nodes.tsv").exists()
need_graph = pytest.mark.skipif(not HAVE_GRAPH, reason="run lean/Extract first")


# ---------- toy graphs ----------

def toy(edges, n):
    e = np.array(edges, dtype=np.int64)
    return g.csr(e[:, 0], e[:, 1], n)


def test_heights_chain_counts_only_weighted_nodes():
    # 0 -> 1 -> 2 -> 3, node 1 is glue (weight 0)
    G = toy([(0, 1), (1, 2), (2, 3)], 4)
    h = g.heights(G, np.array([1, 0, 1, 1]))
    assert h.tolist() == [3, 2, 2, 1]


def test_heights_take_the_longest_branch():
    # 0 -> 1 -> 2 and 0 -> 3 ; all weight 1
    G = toy([(0, 1), (1, 2), (0, 3)], 4)
    assert g.heights(G, np.ones(4)).tolist() == [3, 2, 1, 1]


def test_heights_condense_cycles():
    # inductive type 1 and its constructor 2 point at each other; 0 uses 1; 2 uses 3
    G = toy([(0, 1), (1, 2), (2, 1), (2, 3)], 4)
    h = g.heights(G, np.array([1, 1, 0, 1]))
    assert h[1] == h[2] == 2 and h[0] == 3 and h[3] == 1


def test_reach():
    G = toy([(0, 1), (1, 2), (3, 2)], 4)
    assert g.reach(G, [0]).tolist() == [True, True, True, False]
    assert g.reach(G, [3]).tolist() == [False, False, True, True]


# ---------- the real graph ----------

@pytest.fixture(scope="module")
def real():
    df = g.nodes()
    h = np.load(DERIVED / "h_stmt.npy")
    return df, h, g.name_index(), g.statement_graph()


@need_graph
def test_number_tower_is_ordered(real):
    _, h, idx, _ = real
    d = [h[idx[n]] for n in ["Nat", "Int", "Rat", "Real", "Complex"]]
    assert d == sorted(d) and len(set(d)) == 5, d


@need_graph
def test_category_sits_on_quiver(real):
    _, h, idx, _ = real
    assert h[idx["Quiver"]] < h[idx["CategoryTheory.CategoryStruct"]] < h[idx["CategoryTheory.Category"]]
    assert h[idx["CategoryTheory.Category"]] <= 4


@need_graph
def test_autoparam_tactics_are_not_dependencies(real):
    # structures with `:= by tactic` fields used to reach Lean.Syntax and Array through autoParam
    df, h, idx, Gs = real
    reached = g.reach(Gs, [idx["Monoid"]])
    assert not reached[idx["Lean.Syntax"]]
    assert not reached[idx["Array"]]
    assert h[idx["Monoid"]] <= 5


@need_graph
def test_statement_graph_never_enters_theorems(real):
    df, _, _, Gs = real
    thm = df.is_thm.to_numpy()
    assert not thm[Gs.indices].any()


@need_graph
def test_heights_never_increase_along_edges(real):
    _, h, _, Gs = real
    coo = Gs.tocoo()
    rng = np.random.default_rng(0)
    pick = rng.choice(len(coo.row), size=min(200000, len(coo.row)), replace=False)
    assert (h[coo.row[pick]] >= h[coo.col[pick]]).all()


@need_graph
def test_known_famous_dependencies():
    fe = pd.read_csv(DERIVED / "famous_edges.csv")
    E = set(map(tuple, fe[["user", "used"]].to_numpy()))
    assert ("wQ192760", "wQ576478") in E      # algebra: proved through Liouville's theorem
    assert ("wQ1057919", "wQ1139041") in E    # Sylow uses Cauchy's theorem
    assert ("wQ193286", "wQ752375") in E      # Rolle uses the extreme value theorem
    assert ("wQ1506253", "wQ3984053") not in E  # Euclid's primes do not need Fourier inversion


@need_graph
def test_every_target_is_measured():
    m = pd.read_csv(DERIVED / "measures.csv")
    t = pd.read_csv(DERIVED / "targets.csv")
    assert set(t.key) == set(m.key)


# ---------- labels ----------

def test_dates_are_complete_and_ordered():
    d = pd.read_csv(LABELS / "hand_dates.csv")
    t = pd.read_csv(DERIVED / "targets.csv")
    assert set(t.key) <= set(d.key)
    known = d.dropna(subset=["year_stated"])
    assert (known.year_proved >= known.year_stated).all()
    assert set(d.confidence) <= {"high", "medium", "low", "unknown"}
    assert d[d.year_stated.isna()].confidence.eq("unknown").all()


@need_graph
def test_concept_dates_name_real_declarations(real):
    _, _, idx, _ = real
    c = pd.read_csv(LABELS / "concept_dates.csv")
    assert c.decl.isin(idx.index).all()
    assert c.decl.is_unique
