"""Figures for the follow-up tests.

figures/robustness.png  every version of the main test on one forest plot
figures/textbook.png    mathlib's statements against textbook restatements
figures/metamath.png    the replication in Metamath's set.mm
"""
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import DERIVED, FIGURES, RESULTS
from figures import AMBER, BG, BLUE, FIELDS, GRID, HALO, SUBTLE, TEXT, base, glow_scatter, xmap, year_axis

S, E = {}, {}


def load():
    """Read the summaries when a figure is drawn, not at import, so reruns see fresh numbers."""
    S.clear()
    S.update(json.load(open(RESULTS / "summary.json")))
    E.clear()
    E.update(json.load(open(RESULTS / "summary_extensions.json")))


def forest_rows():
    load()
    rows = [("mathlib, all dated theorems", S["h1_depth"], "main"),
            ("statement size instead of depth", S["robustness"]["statement size"], "main"),
            ("high or medium confidence dates", S["robustness"]["high or medium confidence dates"], "main"),
            ("concrete statements only", S["robustness"]["concrete statements only (no type or instance arguments)"], "main"),
            ("number systems taken as given", E["numbers_given"]["depth"], "numbers"),
            ("textbook restatements swapped in", E["textbook"]["h1_substituted"], "textbook"),
            ("Wikipedia dates swapped in", E["dating"]["h1_swapped"], "dating"),
            ("Wikipedia dates only", E["dating"]["h1_wikipedia_only"], "dating"),
            ("MacTutor dates only", E["dating"]["h1_mactutor_only"], "dating"),
            ("Metamath set.mm", E["metamath"]["depth"], "metamath"),
            ("Metamath, numbers taken as given", E["metamath"]["depth_numbers"], "metamath"),
            ("concepts, mathlib", S["concepts"]["all"], "concepts"),
            ("concepts, numbers taken as given", E["numbers_given"]["concepts"], "concepts")]
    if E.get("research_h1"):
        rows.insert(6, ("with research projects added", E["research_h1"], "research"))
    r2 = RESULTS / "summary_round2.json"
    if r2.exists():
        R = json.load(open(r2))
        rows.insert(rows.index(next(r for r in rows if r[0] == "concepts, mathlib")),
                    ("HOL Light", R["p5"]["trend"], "hollight"))
        rows += [("SECTION", None, "Where depth does rise"),
                 ("library time: ported theorems, by month of entry", R["p4"]["ported"], "library"),
                 ("library time: all theorems, by month of entry", R["p4"]["all"], "library"),
                 ("concepts on the reals, first 60", S["concepts"]["by_real"]["real"], "realc"),
                 ("concepts on the reals, 59 fresh, hand dates", R["p3"]["hand"], "realc"),
                 ("same, Wikipedia dates", R["p3"]["wikipedia"], "realc")]
    return rows


def robustness():
    load()
    rows = forest_rows()
    cols = {"main": TEXT, "numbers": AMBER, "textbook": "#5fd4b4", "dating": "#b48cf2", "metamath": "#ff7a59",
            "concepts": "#7fb3ff", "research": "#e45f9a", "hollight": "#ffd27a", "library": "#9be564",
            "realc": AMBER}
    fig, ax = plt.subplots(figsize=(11, 0.46 * len(rows) + 2.2), dpi=220, facecolor=BG)
    base(ax)
    ys = np.arange(len(rows))[::-1]
    ax.axvline(0, color=SUBTLE, lw=1)
    ax.axvspan(-0.1, 0.1, color=GRID, alpha=0.6, lw=0)
    for y, (lab, d, kind) in zip(ys, rows):
        if lab == "SECTION":
            ax.axhline(y, color=GRID, lw=1)
            ax.text(-1.12, y - 0.05, kind, color=TEXT, fontsize=11, fontweight="bold", va="top")
            continue
        c = cols[kind]
        ax.plot([d["lo"], d["hi"]], [y, y], color=c, lw=2.2, alpha=0.8, solid_capstyle="round")
        ax.scatter([d["rho"]], [y], color=c, s=46, zorder=3)
        ax.text(-1.12, y, lab, color=c, fontsize=9.5, va="center", ha="left")
        ax.text(0.80, y, f"{d['rho']:+.2f}   n = {d['n']}", color=SUBTLE, fontsize=8.5, va="center")
    ax.set_xlim(-1.15, 1.02)
    ax.set_xticks([-0.4, -0.2, 0, 0.2, 0.4, 0.6])
    ax.set_yticks([])
    ax.set_xlabel("Spearman ρ between a date and depth (95% interval)", color=SUBTLE)
    ax.set_title("Flat against history, every way of measuring", color=TEXT, fontsize=16, loc="left", pad=30,
                 fontweight="bold")
    ax.text(0, 1.02, "Against the year of discovery, every version is flat. Depth rises only in the order the "
            "library was built, and among concepts on the reals.", color=SUBTLE, fontsize=10, transform=ax.transAxes)
    fig.savefig(FIGURES / "robustness.png", facecolor=BG, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)


def textbook():
    load()
    t = pd.read_csv(DERIVED / "textbook.csv")
    t = t.sort_values(["mathlib_depth", "textbook_depth"]).reset_index(drop=True)
    real = S["real_depth"]
    fig, ax = plt.subplots(figsize=(11, 8), dpi=220, facecolor=BG)
    base(ax)
    for lw, a in ((7, 0.06), (3, 0.15), (1, 0.9)):
        ax.axvline(real - 0.5, color=AMBER, lw=lw, alpha=a)
    for i, r in t.iterrows():
        c = AMBER if r.textbook_uses_real else BLUE
        ax.annotate("", xy=(r.textbook_depth, i), xytext=(r.mathlib_depth, i),
                    arrowprops=dict(arrowstyle="-|>", color=c, lw=1.6, alpha=0.9, shrinkA=4, shrinkB=2))
        ax.scatter([r.mathlib_depth], [i], s=40, facecolors="none", edgecolors=SUBTLE, lw=1.2, zorder=3)
        ax.scatter([r.textbook_depth], [i], s=40, color=c, zorder=4)
        lab = r["name"].replace("_", " ")
        ax.text(-1.5, i, f"{lab}", color=TEXT, fontsize=9, va="center", ha="right")
    ax.set_yticks([])
    ax.set_xlim(-0.5, 58)
    ax.set_ylim(-1, len(t))
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.set_xlabel("statement depth", color=SUBTLE)
    ax.text(real - 0.1, len(t) - 0.3, " ℝ", color=AMBER, fontsize=11)
    ax.set_title("Restated the textbook way", color=TEXT, fontsize=16, loc="left", pad=30, fontweight="bold")
    T = E["textbook"]
    ax.text(0, 1.02, f"Hollow: mathlib's statement. Filled: a plain restatement proved from it. "
            f"{T['shallower']} of the {T['shallower'] + T['deeper'] + T['same']} (integer Pythagoras aside) get shallower "
            f"(median {T['median_change']:+.0f}), but nothing that needs ℝ gets above it.",
            color=SUBTLE, fontsize=9.5, transform=ax.transAxes)
    fig.subplots_adjust(left=0.2)
    fig.savefig(FIGURES / "textbook.png", facecolor=BG, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)


def metamath():
    load()
    h = pd.read_csv(DERIVED / "metamath_hundred.csv").dropna(subset=["year_stated"])
    m = pd.read_csv(DERIVED / "theorems.csv")[["key", "stmt_depth", "field", "title"]].rename(
        columns={"stmt_depth": "lean_depth", "title": "lean_title"})
    j = h.merge(m, on="key").drop_duplicates("label")
    M = E["metamath"]
    fig = plt.figure(figsize=(15, 6.8), dpi=220, facecolor=BG)
    a1 = fig.add_axes([0.05, 0.12, 0.52, 0.66])
    a2 = fig.add_axes([0.64, 0.12, 0.33, 0.66])
    for ax in (a1, a2):
        base(ax)
    cdepth = 21
    for lw, a in ((7, 0.06), (3, 0.15), (1, 0.9)):
        a1.axhline(cdepth - 0.5, color=AMBER, lw=lw, alpha=a)
    a1.text(1.0, cdepth - 1.2, "ℂ and ℝ  depth 21 ", color=AMBER, fontsize=9, ha="right",
            transform=a1.get_yaxis_transform())
    col = h.key.map(pd.read_csv(DERIVED / "theorems.csv").set_index("key").field).map(FIELDS).fillna(SUBTLE)
    glow_scatter(a1, xmap(h.year_stated), h.stmt_depth, np.full(len(h), 22), col)
    a1.set_ylim(h.stmt_depth.max() + 3, -1.5)
    year_axis(a1)
    a1.set_ylabel("statement depth in set.mm", color=SUBTLE)
    a1.set_xlabel("year first stated", color=SUBTLE)
    a1.set_title(f"Metamath: {M['n_dated']} of Wiedijk's 100 theorems", color=TEXT, fontsize=12, loc="left", pad=24)
    a1.text(0, 1.02, f"ρ with year {M['depth']['rho']:+.2f}. Set theory first: ℕ, ℤ and ℚ are built inside ℂ, "
            f"so {M['share_complex']:.0%} of statements pass through it.", color=SUBTLE, fontsize=9,
            transform=a1.transAxes, va="bottom")
    glow_scatter(a2, j.lean_depth, j.stmt_depth, np.full(len(j), 22), j.field.map(FIELDS).fillna(SUBTLE))
    for k, lab in {"wQ11518": "Pythagoras", "wQ1506253": "Euclid's primes", "f9": "area of a circle",
                   "wQ474881": "Cantor"}.items():
        p = j[j.key == k]
        if len(p):
            a2.annotate(lab, (p.lean_depth.iat[0], p.stmt_depth.iat[0]), xytext=(5, 4), textcoords="offset points",
                        color=TEXT, fontsize=8, path_effects=HALO)
    a2.grid(color=GRID, lw=0.6)
    a2.set_axisbelow(True)
    a2.set_xlabel("depth in mathlib", color=SUBTLE)
    a2.set_ylabel("depth in Metamath", color=SUBTLE)
    a2.set_title(f"The same {M['n_shared']} theorems in both", color=TEXT, fontsize=12, loc="left", pad=24)
    a2.text(0, 1.02, f"Spearman ρ {M['cross_depth']['rho']:+.2f} [{M['cross_depth']['lo']:+.2f}, "
            f"{M['cross_depth']['hi']:+.2f}]", color=SUBTLE, fontsize=9, transform=a2.transAxes, va="bottom")
    fig.text(0.05, 0.94, "A second library, a second foundation, the same flat line", color=TEXT, fontsize=17,
             fontweight="bold")
    fig.savefig(FIGURES / "metamath.png", facecolor=BG, pad_inches=0.2)
    plt.close(fig)


if __name__ == "__main__":
    robustness()
    textbook()
    metamath()
    print("extension figures written")
