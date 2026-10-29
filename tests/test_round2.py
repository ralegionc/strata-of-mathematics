"""Tests for the second round: each checks something that could come out wrong."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import DERIVED, ROOT  # noqa: E402

HAVE_HOL = (ROOT / "history" / "hol-light" / "realax.ml").exists()


def test_proof_chains_match_proof_depth():
    # the longest chain traced on the proof graph is the proof depth plus the statement itself, which
    # counts only when it is a named theorem (a few sample entries are instances or definitions)
    s = pd.read_csv(DERIVED / "proofsplit.csv")
    gap = s.chain_layers - s.proof_depth
    assert gap.isin([0, 1]).all() and (gap == 1).mean() > 0.95
    assert (s.own_folder <= s.own_parent).all() and (s.own_parent <= s.chain_layers).all()


def test_research_splits_are_consistent():
    r = pd.read_csv(DERIVED / "research.csv")
    done = r.dropna(subset=["own_layers"])
    assert (done.own_layers < done.chain_layers).all()
    assert (done.chain_layers == done.proof_depth + 1).all()


def test_syllabus_lists_are_disjoint_where_claimed():
    s = pd.read_csv(DERIVED / "syllabus.csv")
    under = set(s[s.list == "undergraduate"].decl)
    assert not (set(s[s.overview_only].decl) & under)


def test_library_time_respects_dependencies():
    t = pd.read_csv(DERIVED / "library_time.csv", parse_dates=["entered"])
    x = pd.read_csv(DERIVED / "theorems.csv")
    real = t[t.decl == "Real"].entered.iloc[0]
    j = t[t.kind == "theorem"].merge(x[["key", "uses_real"]], on="key").dropna(subset=["entered"])
    assert not (j.uses_real & (j.entered < real)).any()
    assert j.entered.min() >= pd.Timestamp("2017-07-01") and j.entered.max() <= pd.Timestamp("2026-10-31")


def test_namespace_reader():
    from library_time import scopes
    text = ("namespace a\n/- namespace b\n-/\nsection s\ndef x\nend s\nbegin\nend\n"
            "namespace c.d\ndef y\nend c.d\nend a\ndef z")
    in_comment, ns = scopes(text)
    assert ns == ["", "a", "a", "a", "a", "a", "a", "a", "a", "a.c.d", "a.c.d", "a", ""]
    assert list(in_comment) == [0, 0, 1] + [0] * 10


@pytest.mark.skipif(not HAVE_HOL, reason="clone HOL Light into history/ first")
def test_hol_light_construction_order():
    c = pd.read_csv(DERIVED / "hollight_constants.csv").set_index("constant").depth
    assert c["type:num"] < c["type:nadd"] < c["type:hreal"] < c["type:real"] < c["type:int"]
    assert "type:rat" not in c.index  # HOL Light has no type of rationals


def test_fresh_concepts_exclude_the_first_round():
    fresh = set(pd.read_csv(DERIVED / "concepts_fresh.csv").decl)
    first = set(pd.read_csv(DERIVED / "concepts.csv").decl)
    assert not (fresh & first)
