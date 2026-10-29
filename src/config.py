"""Paths and constants shared by every script."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DERIVED = ROOT / "data" / "derived"
LABELS = ROOT / "data" / "labels"
FIGURES = ROOT / "figures"
DOCS = ROOT / "docs"
RESULTS = ROOT / "results"
LEAN = ROOT / "lean"
GRAPH = DERIVED / "graph"          # output of the Lean extractor
MATHLIB_SRC = LEAN / ".lake" / "packages" / "mathlib"

MATHLIB_TAG = "v4.35.0"
USER_AGENT = "strata-of-mathematics/0.1 (research project; https://github.com/ralegionc)"

for p in (RAW, DERIVED, LABELS, FIGURES, DOCS, RESULTS):
    p.mkdir(parents=True, exist_ok=True)
