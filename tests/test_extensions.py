"""Tests for the follow-up analyses: each checks something that could come out wrong."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import dating2  # noqa: E402
import graph as g  # noqa: E402
from config import DERIVED, GRAPH, RAW  # noqa: E402

HAVE_GRAPH = (GRAPH / "nodes.parquet").exists() or (GRAPH / "nodes.tsv").exists()
need_graph = pytest.mark.skipif(not HAVE_GRAPH, reason="run lean/Extract first")
need_mm = pytest.mark.skipif(not (RAW / "metamath" / "set.mm").exists(), reason="download set.mm first")


# ---------- year parsing for the Wikipedia audit ----------

def test_years_in_handles_bc_centuries_and_lifespans():
    assert dating2.years_in("Euclid proved it around 300 BC.") == [-300]
    assert dating2.years_in("It goes back to the 3rd century BC.") == [-250]
    assert dating2.years_in("Gauss (1777–1855) proved it in 1799.") == [1799]
    assert dating2.years_in("The example 2^10 shows nothing.") == []


def test_lead_sentence_is_preferred_over_body():
    text = "Rolle's theorem was proved by Michel Rolle in 1691.\n== History ==\nBhaskara stated a form of it in 1150."
    y, _, where = dating2.wiki_year(text, "Rolle's theorem", {"rolle"})
    assert (y, where) == (1691, "lead")


# ---------- numbers taken as given ----------

@need_graph
def test_numbers_given_makes_each_number_system_a_leaf():
    h = np.load(DERIVED / "h_stmt_numbers.npy")
    idx = g.name_index()
    assert all(h[idx[n]] == 1 for n in ["Nat", "Int", "Rat", "Real", "Complex"])
    full = np.load(DERIVED / "h_stmt.npy")
    # structures built on the numbers keep their own layers, so they stay above 1 but drop
    for n in ["MetricSpace", "MeasureTheory.Measure"]:
        assert 1 < h[idx[n]] < full[idx[n]]
    # nothing touched by the cut can get deeper
    assert (h <= full).all()


# ---------- direct-use dependencies ----------

@need_graph
def test_direct_dependencies_are_a_subset_of_all_dependencies():
    allf = set(map(tuple, pd.read_csv(DERIVED / "famous_edges.csv")[["user", "used"]].to_numpy()))
    direct = set(map(tuple, pd.read_csv(DERIVED / "famous_edges_direct.csv")[["user", "used"]].to_numpy()))
    assert direct <= allf and len(direct) < len(allf)


# ---------- textbook restatements ----------

def test_integer_pythagoras_avoids_the_reals():
    t = pd.read_csv(DERIVED / "textbook.csv").set_index("name")
    assert not t.loc["pythagoras_int", "textbook_uses_real"]
    assert t.loc["pythagoras_int", "textbook_depth"] < t.loc["pythagoras", "textbook_depth"]
    # a restatement over the reals can never sit above the reals
    real = t[t.textbook_uses_real]
    assert (real.textbook_depth >= 22).all()


# ---------- Metamath ----------

@need_mm
def test_metamath_construction_chain_is_ordered():
    import metamath
    st, syntax, unique, synpos, defs, def_label, constructs = metamath.build()
    nodes = [s["label"] for s in syntax]
    h = metamath.heights(nodes, defs)
    chain = ["com", "cnpi", "cnq", "cnp", "cnr", "cr"]  # ordinals, N., Q., P., R., RR
    d = [h[c] for c in chain]
    assert d == sorted(d) and len(set(d)) == len(d), d
    # set.mm builds the naturals inside the complex numbers
    assert h["cn"] > h["cc"]


@need_mm
def test_metamath_parser_reads_compressed_proofs():
    import metamath
    labels = metamath.proof_labels(["(", "ax-mp", "syl", ")", "ABCD"])
    assert labels == ["ax-mp", "syl"]
    assert metamath.proof_labels(["wph", "wps", "ax-1"]) == ["wph", "wps", "ax-1"]


# ---------- research projects ----------

def test_research_versions_are_calibrated():
    r = pd.read_csv(DERIVED / "research.csv")
    assert set(r.name) == {"pfr", "sphere-packing", "sphere-eversion", "carleson"}
    # each project's mathlib must give the same number tower, up to the one-level shift in older Lean
    assert (r.ref_Nat == 1).all()
    assert ((r.ref_Real - r.ref_Rat) == 11).all() and ((r.ref_Complex - r.ref_Real) == 1).all()
    assert r.ref_Real.between(21, 22).all()
    # a statement through the reals can never be shallower than the reals
    assert (r.stmt_depth[r.uses_real] >= r.ref_Real[r.uses_real]).all()
