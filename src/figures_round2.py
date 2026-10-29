"""Figures for the second round.

figures/two_clocks.png   depth against the year of discovery and against the month of entry into mathlib
figures/libraries.png    how mathlib, Metamath and HOL Light build the number systems, and HOL Light against mathlib
"""
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import DERIVED, FIGURES, RESULTS
from figures import AMBER, BG, BLUE, FIELDS, GRID, HALO, SUBTLE, TEXT, base, glow_scatter, xmap, year_axis


def load():
    return json.load(open(RESULTS / "summary_round2.json"))


def two_clocks():
    R = load()["p4"]
    T = pd.read_csv(DERIVED / "library_time.csv", parse_dates=["entered"])
    x = pd.read_csv(DERIVED / "theorems.csv")
    t = T[(T.kind == "theorem") & (T.how == "mathlib3")].merge(
        x[["key", "title", "field", "stmt_depth", "year_stated"]], on="key").dropna(subset=["entered", "year_stated"])
    t["ly"] = t.entered.dt.year + (t.entered.dt.dayofyear - 1) / 366
    cols = t.field.map(FIELDS).fillna(SUBTLE)
    fig = plt.figure(figsize=(15, 7), dpi=220, facecolor=BG)
    a1 = fig.add_axes([0.05, 0.12, 0.42, 0.66])
    a2 = fig.add_axes([0.55, 0.12, 0.42, 0.66])
    for a in (a1, a2):
        base(a)
        a.set_ylim(t.stmt_depth.max() + 3, -1.5)
        a.axhline(21.5, color=AMBER, lw=1, alpha=0.6)
        a.grid(axis="y", color=GRID, lw=0.5)
        a.set_axisbelow(True)
    glow_scatter(a1, xmap(t.year_stated), t.stmt_depth, np.full(len(t), 20), cols)
    year_axis(a1, ticks=(-500, 1000, 1600, 1700, 1800, 1900, 2000))
    a1.set_xlabel("year the result was first stated", color=SUBTLE)
    a1.set_ylabel("statement depth", color=SUBTLE)
    h = R["history_ported"]
    a1.set_title(f"The calendar of mathematics: ρ {h['rho']:+.2f}", color=TEXT, fontsize=13, loc="left", pad=10)
    glow_scatter(a2, t.ly, t.stmt_depth, np.full(len(t), 20), cols)
    med = t.groupby(t.entered.dt.year).stmt_depth.median()
    a2.plot(med.index + 0.5, med.values, color=TEXT, lw=1.6, alpha=0.8, zorder=5)
    a2.set_xlim(2017.3, 2023.9)
    a2.set_xlabel("when it entered the library (mathlib3, 2017 to 2023)", color=SUBTLE)
    p = R["ported"]
    a2.set_title(f"The calendar of the library: ρ {p['rho']:+.2f} [{p['lo']:+.2f}, {p['hi']:+.2f}]", color=TEXT,
                 fontsize=13, loc="left", pad=10)
    a2.text(0.99, 0.02, "white line: median by year", color=SUBTLE, fontsize=8, ha="right", transform=a2.transAxes)
    for k, lab in {"wQ1506253": "Euclid's primes", "wQ474881": "Cantor", "wQ11518": "Pythagoras",
                   "wQ190391": "central limit theorem"}.items():
        q = t[t.key == k]
        if len(q):
            a2.annotate(lab, (q.ly.iat[0], q.stmt_depth.iat[0]), xytext=(6, 4), textcoords="offset points",
                        color=TEXT, fontsize=8, path_effects=HALO)
            a1.annotate(lab, (float(xmap(q.year_stated.iat[0])), q.stmt_depth.iat[0]), xytext=(6, 4),
                        textcoords="offset points", color=TEXT, fontsize=8, path_effects=HALO)
    fig.text(0.05, 0.93, "Two clocks", color=TEXT, fontsize=22, fontweight="bold")
    fig.text(0.05, 0.885, f"The same {p['n']} famous theorems, dated twice. Against history there are no strata; "
             f"in the order mathlib formalized them, the shallow ones came first.", color=SUBTLE, fontsize=11)
    fig.savefig(FIGURES / "two_clocks.png", facecolor=BG, pad_inches=0.2)
    plt.close(fig)


def libraries():
    R = load()["p5"]
    hol = R["tower"]
    S = json.load(open(RESULTS / "summary.json"))
    towers = {
        "mathlib (Lean)": {"ℕ": 1, "ℤ": 2, "ℚ": 11, "ℝ": S["real_depth"], "ℂ": S["real_depth"] + 1},
        "Metamath (set.mm)": {"ℕ": 23, "ℤ": 25, "ℚ": 26, "ℝ": 21, "ℂ": 21},
        "HOL Light": {"ℕ": hol["type:num"], "ℤ": hol["type:int"], "ℚ": hol["rational"], "ℝ": hol["type:real"]},
    }
    notes = {"mathlib (Lean)": "ℝ from Cauchy sequences of ℚ",
             "Metamath (set.mm)": "ℂ first, from signed reals; ℕ, ℤ, ℚ inside ℂ",
             "HOL Light": "ℝ straight from ℕ; ℤ and ℚ carved out of ℝ"}
    fig = plt.figure(figsize=(15, 7), dpi=220, facecolor=BG)
    a1 = fig.add_axes([0.05, 0.12, 0.50, 0.66])
    a2 = fig.add_axes([0.64, 0.12, 0.33, 0.66])
    base(a1)
    base(a2)
    nums = ["ℕ", "ℤ", "ℚ", "ℝ", "ℂ"]
    colors = {"ℕ": "#9be564", "ℤ": "#7fb3ff", "ℚ": "#b48cf2", "ℝ": AMBER, "ℂ": "#ff7a59"}
    for i, (lib, tw) in enumerate(towers.items()):
        y = len(towers) - 1 - i
        a1.plot([0, max(tw.values())], [y, y], color=GRID, lw=1.2, zorder=1)
        placed = []
        for n in sorted((n for n in nums if n in tw), key=lambda n: tw[n]):
            close = sum(1 for v in placed if abs(v - tw[n]) < 1.6)
            yy = y + (0.16 if close % 2 else 0) * (1 if close else 0) - (0.16 if close and close % 2 == 0 else 0)
            placed.append(tw[n])
            a1.scatter([tw[n]], [yy], s=260, color=colors[n], zorder=3 + len(placed) * 0.01, lw=1.5, edgecolors=BG)
            a1.text(tw[n], yy, n, color=BG, fontsize=10, ha="center", va="center", fontweight="bold",
                    zorder=4 + len(placed) * 0.01)
        a1.text(-1.0, y, lib, color=TEXT, fontsize=11, ha="right", va="center")
        a1.text(0, y - 0.32, notes[lib], color=SUBTLE, fontsize=8.5, va="center")
    a1.set_xlim(-14, 30)
    a1.set_ylim(-0.7, len(towers) - 0.4)
    a1.set_yticks([])
    a1.set_xticks([0, 5, 10, 15, 20, 25])
    a1.set_xlabel("depth of each number system's definition", color=SUBTLE)
    a1.set_title("Three libraries, three orders of construction", color=TEXT, fontsize=13, loc="left", pad=10)
    h = pd.read_csv(DERIVED / "hollight_hundred_dated.csv")
    m = pd.read_csv(DERIVED / "theorems.csv")[["key", "stmt_depth", "field"]]
    j = h.merge(m, on="key", suffixes=("_hol", "_lean"))
    glow_scatter(a2, j.stmt_depth_lean, j.stmt_depth_hol, np.full(len(j), 22), j.field.map(FIELDS).fillna(SUBTLE))
    a2.grid(color=GRID, lw=0.5)
    a2.set_axisbelow(True)
    a2.set_xlabel("depth in mathlib", color=SUBTLE)
    a2.set_ylabel("depth in HOL Light", color=SUBTLE)
    v = R["vs_mathlib"]
    a2.set_title(f"HOL Light against mathlib: ρ {v['rho']:+.2f}", color=TEXT, fontsize=13, loc="left", pad=10)
    tr = R["trend"]
    fig.text(0.05, 0.93, "The foundation sets the depth, in every library", color=TEXT, fontsize=20, fontweight="bold")
    fig.text(0.05, 0.885, f"In HOL Light, as in mathlib and Metamath, depth has no trend with the year of discovery "
             f"(ρ {tr['rho']:+.2f}, n = {tr['n']}); passing through ℝ explains {R['r2']['passes through the reals']:.0%} "
             f"of it, the year {R['r2']['year']:.0%}.", color=SUBTLE, fontsize=11)
    fig.savefig(FIGURES / "libraries.png", facecolor=BG, pad_inches=0.2)
    plt.close(fig)


if __name__ == "__main__":
    two_clocks()
    libraries()
    print("round-two figures written")
