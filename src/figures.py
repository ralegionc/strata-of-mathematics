"""Figures.

figures/strata.png     hero: every famous theorem by discovery year and statement depth, with the
                       famous theorems its mathlib proof rests on drawn as threads
figures/cliff.png      statement depth of all named theorems in mathlib, split at the reals
figures/tangle.png     core concepts ordered by age (left) and by depth (right)
figures/arrow.png      how often a proof rests on a theorem discovered later, by era
figures/proofs.png     statement depth against proof size
"""
import json

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.path import Path

from config import DERIVED, FIGURES, RESULTS

BG, TEXT, SUBTLE, GRID = "#0a0d12", "#e8e4da", "#8a8f98", "#1c222b"
AMBER, BLUE, IVORY = "#f6b73c", "#4f86b8", "#e8e4da"
FWD, BACK = "#ffc56b", "#5b86b5"
FONT = "DejaVu Sans"
plt.rcParams["font.family"] = FONT
FIELDS = {
    "Number theory": "#f6b73c", "Algebra": "#7fb3ff", "Combinatorics": "#9be564",
    "Logic and foundations": "#d9d4c7", "Topology": "#b48cf2", "Analysis": "#ff7a59",
    "Measure and probability": "#e45f9a", "Geometry": "#5fd4b4",
}
HALO = [pe.withStroke(linewidth=2.6, foreground=BG)]
X0, XB, X1 = -650, 1500, 2008   # piecewise year axis: ancient part compressed
SPLIT = 0.22


def xmap(y):
    y = np.asarray(y, float)
    return np.where(y < XB, SPLIT * (y - X0) / (XB - X0), SPLIT + (1 - SPLIT) * (y - XB) / (X1 - XB))


def year_label(y):
    return f"{-y} BC" if y < 0 else str(y)


def year_axis(ax, ticks=(-600, 1, 500, 1000, 1500, 1600, 1700, 1800, 1900, 2000)):
    ax.set_xticks(xmap(list(ticks)))
    ax.set_xticklabels([year_label(t) if t != 1 else "AD 1" for t in ticks])
    ax.set_xlim(-0.01, 1.01)
    ax.axvline(SPLIT, color=GRID, lw=1.2, ls=(0, (2, 3)), zorder=0)


def base(ax):
    ax.set_facecolor(BG)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(colors=SUBTLE, labelsize=9, length=0)


def load():
    x = pd.read_csv(DERIVED / "theorems.csv")
    S = json.load(open(RESULTS / "summary.json"))
    return x, S


def spread(ys, gap, lo=-np.inf, hi=np.inf):
    """Push label positions apart so neighbours are at least `gap` apart (order kept)."""
    ys = np.asarray(ys, float)
    order = np.argsort(ys, kind="stable")
    v = ys[order].copy()
    for i in range(1, len(v)):
        v[i] = max(v[i], v[i - 1] + gap)
    if len(v) and v[-1] > hi:
        v[-1] = hi
        for i in range(len(v) - 2, -1, -1):
            v[i] = min(v[i], v[i + 1] - gap)
    v = np.maximum(v, lo)
    out = np.empty_like(v)
    out[order] = v
    return out


def glow_scatter(ax, xs, ys, sizes, colors, z=4):
    for k, a in ((5.0, 0.05), (2.6, 0.12)):
        ax.scatter(xs, ys, s=np.asarray(sizes) * k, c=colors, alpha=a, lw=0, zorder=z)
    ax.scatter(xs, ys, s=sizes, c=colors, alpha=0.95, lw=0, zorder=z + 0.2)


def thread(p0, p1, bend=0.18):
    (x0, y0), (x1, y1) = p0, p1
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = x1 - x0, y1 - y0
    c = (mx - dy * bend * 0.02, my + dx * bend * 40)
    return Path([p0, c, p1], [Path.MOVETO, Path.CURVE3, Path.CURVE3])


def bezier_points(path, n=24):
    (x0, y0), (cx, cy), (x1, y1) = path.vertices
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * np.array([x0, y0]) + 2 * (1 - t) * t * np.array([cx, cy]) + t ** 2 * np.array([x1, y1])


LABELS = {  # key: (label, dx, dy) offsets in points
    "wQ11518": ("Pythagorean theorem", -10, 16),
    "wQ1506253": ("Euclid: infinitely many primes", 8, -12),
    "f9": ("area of a circle (Archimedes)", 10, 12),
    "wQ285719": ("Thales", 2, -18),
    "wQ192760": ("fundamental theorem of algebra", 10, 10),
    "wQ132469": ("Fermat's Last Theorem\n(statement only)", -40, -26),
    "wQ810431": ("Basel problem", -50, 14),
    "wQ474881": ("Cantor's theorem", 8, -12),
    "wQ1032886": ("Hales–Jewett", 8, -10),
    "wQ2027347": ("optional stopping", -30, 14),
    "wQ190391": ("central limit theorem", -60, -18),
    "wQ472883": ("quadratic reciprocity", -64, -14),
    "wQ220680": ("Banach fixed point", 8, -12),
    "wQ420714": ("Akra–Bazzi", 8, 10),
    "wQ4695203": ("four functions theorem", -40, -16),
    "wQ1068976": ("Nullstellensatz", 8, -10),
    "wQ188295": ("Fermat's little theorem", -40, 14),
    "wQ1217677": ("fundamental theorem of calculus", -64, 16),
}


def hero():
    x, S = load()
    x = x.dropna(subset=["year_stated"]).copy()
    x["X"] = xmap(x.year_stated)
    real = S["real_depth"]
    fe = pd.read_csv(DERIVED / "famous_edges_reduced.csv")
    pos = x.set_index("key")[["X", "stmt_depth", "year_proved"]]
    fe = fe[fe.user.isin(pos.index) & fe.used.isin(pos.index)]

    fig = plt.figure(figsize=(17, 10.5), dpi=220, facecolor=BG)
    ax = fig.add_axes([0.05, 0.09, 0.70, 0.74])
    base(ax)
    ymax = 63
    # strata: two tinted zones split at the reals, faint bands every 5 levels
    ax.axhspan(-1, real - 0.5, color="#0c1119", zorder=0)
    ax.axhspan(real - 0.5, ymax, color="#120f0c", zorder=0)
    for d in range(0, ymax, 5):
        ax.axhline(d, color=GRID, lw=0.5, zorder=0.5)
    for lw, a in ((9, 0.05), (4, 0.12), (1.2, 0.9)):
        ax.axhline(real - 0.5, color=AMBER, lw=lw, alpha=a, zorder=1)

    # threads
    segs_f, segs_b = [], []
    for r in fe.itertuples():
        a, b = pos.loc[r.user], pos.loc[r.used]
        pts = bezier_points(thread((a.X, a.stmt_depth), (b.X, b.stmt_depth)))
        (segs_f if b.year_proved > a.year_proved else segs_b).append(pts)
    ax.add_collection(LineCollection(segs_b, colors=BACK, lw=0.45, alpha=0.13, zorder=2))
    ax.add_collection(LineCollection(segs_f, colors=FWD, lw=0.45, alpha=0.19, zorder=2.1))

    sizes = 8 + 70 * (np.log10(x.proof_size.fillna(0) + 1) / 4.6) ** 2
    cols = x.field.map(FIELDS).fillna(SUBTLE)
    so = x.statement_only.astype(bool)
    glow_scatter(ax, x.X[~so], x.stmt_depth[~so], sizes[~so], cols[~so])
    ax.scatter(x.X[so], x.stmt_depth[so], s=90, facecolors="none", edgecolors=AMBER, lw=1.4, zorder=5)

    rp = DERIVED / "research.csv"
    if rp.exists():
        rs = pd.read_csv(rp)
        rs["stmt_depth"] = rs.stmt_depth + (real - rs.ref_Real)  # calibrate to this mathlib version
        rx = xmap(rs.year_stated)
        for k, a in ((420, 0.08), (200, 0.2)):
            ax.scatter(rx, rs.stmt_depth, marker="*", s=k, color="#ffffff", alpha=a, lw=0, zorder=5)
        ax.scatter(rx, rs.stmt_depth, marker="*", s=120, color="#ffffff", lw=0, zorder=6)
        short = {"pfr": "PFR conjecture", "sphere-packing": "sphere packing in 8 dimensions",
                 "sphere-eversion": "sphere eversion", "carleson": "Carleson's theorem"}
        offsets = {"pfr": (-9, 6), "sphere-packing": (-9, -14), "sphere-eversion": (-10, 9), "carleson": (-9, 6)}
        for r, xv in zip(rs.itertuples(), rx):
            left = xv > 0.8
            dx, dy = offsets.get(r.name, (-9 if left else 9, 6))
            ax.annotate(f"{short.get(r.name, r.title)}, proved {r.year_proved}", (xv, r.stmt_depth),
                        xytext=(dx, dy), textcoords="offset points", ha="right" if dx < 0 else "left",
                        color="#ffffff", fontsize=7.6, path_effects=HALO, zorder=7)
        fig.text(0.785, 0.452, "★  research result formalized outside mathlib", color="#ffffff", fontsize=8.3)

    for k, (lab, dx, dy) in LABELS.items():
        if k not in pos.index:
            continue
        p = pos.loc[k]
        ax.annotate(lab, (p.X, p.stmt_depth), xytext=(dx, dy), textcoords="offset points",
                    color=TEXT, fontsize=7.6, path_effects=HALO, zorder=7,
                    arrowprops=dict(arrowstyle="-", color=SUBTLE, lw=0.5, alpha=0.8,
                                    shrinkA=0, shrinkB=3))

    ax.set_ylim(ymax, -1.5)
    year_axis(ax)
    ax.set_yticks(range(0, ymax, 10))
    ax.set_ylabel("statement depth: the longest chain of definitions under the statement",
                  color=SUBTLE, fontsize=10)
    ax.set_xlabel("year the result was first stated", color=SUBTLE, fontsize=10)
    ax.text(0.995, real - 1.0, f"ℝ   depth {real}", color=AMBER, fontsize=10, va="bottom", ha="right",
            transform=ax.get_yaxis_transform(), path_effects=HALO, fontweight="bold", zorder=8)
    ax.text(0.004, 1.2, "statements built from ℕ, sets, groups and graphs", color="#9fb7d4",
            fontsize=8.5, transform=ax.get_yaxis_transform(), va="center", style="italic")
    ax.text(0.004, real + 1.4, "statements that pass through the real numbers", color="#d9b27a",
            fontsize=8.5, transform=ax.get_yaxis_transform(), va="center", style="italic")

    # legend: fields, threads, sizes
    lx = 0.785
    fig.text(lx, 0.80, "Field", color=TEXT, fontsize=10, fontweight="bold")
    for i, (f, c) in enumerate(FIELDS.items()):
        fig.text(lx + 0.012, 0.775 - i * 0.022, f, color=c, fontsize=8.8, va="center")
        fig.patches.append(plt.Circle((lx + 0.004, 0.775 - i * 0.022), 0.0035, color=c,
                                      transform=fig.transFigure, figure=fig))
    y0 = 0.575
    fig.text(lx, y0, "Threads", color=TEXT, fontsize=10, fontweight="bold")
    fig.text(lx, y0 - 0.025, "a famous theorem the proof rests on", color=SUBTLE, fontsize=8)
    fig.lines.append(plt.Line2D([lx, lx + 0.025], [y0 - 0.052] * 2, color=FWD, lw=1.6,
                                transform=fig.transFigure))
    fig.text(lx + 0.032, y0 - 0.052, "found later than the result itself", color=FWD, fontsize=8.5,
             va="center")
    fig.lines.append(plt.Line2D([lx, lx + 0.025], [y0 - 0.074] * 2, color=BACK, lw=1.6,
                                transform=fig.transFigure))
    fig.text(lx + 0.032, y0 - 0.074, "found earlier", color=BACK, fontsize=8.5, va="center")
    fig.text(lx, y0 - 0.105, "Dot size: size of the proof in mathlib", color=SUBTLE, fontsize=8)

    # inset: what predicts depth
    ia = fig.add_axes([lx + 0.005, 0.12, 0.17, 0.25])
    base(ia)
    r2 = S["r2"]
    items = [("year found", r2["year"]), ("field", r2["field"]), ("passes through ℝ", r2["uses real numbers"]),
             ("ℝ, measures, inner products", r2["real, measure, inner product"])]
    ys = np.arange(len(items))[::-1]
    ia.barh(ys, [v for _, v in items], color=[SUBTLE, "#7fb3ff", AMBER, AMBER], height=0.55,
            alpha=0.9)
    for yv, (lab, v) in zip(ys, items):
        ia.text(v + 0.02, yv, f"{v:.0%}" if v >= 0.01 else f"{v:.1%}", color=TEXT, fontsize=8.5,
                va="center")
        ia.text(0, yv + 0.42, lab, color=SUBTLE, fontsize=8, va="bottom")
    ia.set_xlim(0, 1.15)
    ia.set_ylim(-0.5, len(items) - 0.1)
    ia.set_xticks([])
    ia.set_yticks([])
    ia.set_title("Share of the variation in depth\nexplained by", color=TEXT, fontsize=9.5, loc="left")

    fig.text(0.05, 0.925, "Strata of Mathematics", color=TEXT, fontsize=30, fontweight="bold")
    n = len(x)
    fig.text(0.05, 0.885,
             f"{n} famous theorems in Lean's mathlib, placed by when they were found and how much mathematics "
             f"their statements stand on. Old results are not shallow, and new ones are not deep:",
             color=SUBTLE, fontsize=11.5)
    fig.text(0.05, 0.862, "depth follows whether a statement needs the real numbers, not the calendar.",
             color=SUBTLE, fontsize=11.5)
    fig.text(0.05, 0.03,
             "Depth is counted in mathlib v4.35.0 (Lean 4): the longest chain of definitions below the constants in a "
             "theorem's statement, with instances, projections and auxiliary declarations passed through.",
             color=SUBTLE, fontsize=7.5)
    fig.text(0.05, 0.015,
             "Theorems from mathlib's lists of Wikipedia's 1000 theorems and Wiedijk's 100 theorems. Dates assigned by "
             "hand and audited against Wikidata. The year axis is compressed before 1500.",
             color=SUBTLE, fontsize=7.5)
    fig.savefig(FIGURES / "strata.png", facecolor=BG, pad_inches=0.2)
    plt.close(fig)


def cliff():
    x, S = load()
    lib = pd.read_parquet(DERIVED / "library_depths.parquet")
    real = S["real_depth"]
    fig, ax = plt.subplots(figsize=(12, 6.2), dpi=220, facecolor=BG)
    base(ax)
    bins = np.arange(-0.5, lib.depth.max() + 1.5)
    h0, _ = np.histogram(lib.depth[~lib.uses_real], bins)
    h1, _ = np.histogram(lib.depth[lib.uses_real], bins)
    mids = (bins[:-1] + bins[1:]) / 2
    ax.bar(mids, h0, width=0.86, color=BLUE, alpha=0.95, label="statement does not pass through ℝ")
    ax.bar(mids, h1, width=0.86, bottom=h0, color=AMBER, alpha=0.95, label="statement passes through ℝ")
    for lw, a in ((7, 0.06), (3, 0.15), (1, 0.9)):
        ax.axvline(real - 0.5, color=AMBER, lw=lw, alpha=a)
    ax.text(real - 0.1, ax.get_ylim()[1] * 0.95, f" ℝ sits at depth {real}", color=AMBER, fontsize=10,
            va="top")
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.set_xlabel("statement depth", color=SUBTLE, fontsize=10)
    ax.set_ylabel("named theorems", color=SUBTLE, fontsize=10)
    L = S["library"]
    ax.set_title(f"All {L['named_theorems']:,} named theorems in mathlib", color=TEXT, fontsize=15,
                 loc="left", pad=28, fontweight="bold")
    ax.text(0, 1.03, f"{L['share_uses_real']:.0%} pass through the real numbers; "
            f"{L['share_nonreal_below_real']:.0%} of the rest are shallower than ℝ itself. "
            f"Median depth {L['median_depth_nonreal']:.0f} without ℝ, {L['median_depth_real']:.0f} with.",
            color=SUBTLE, fontsize=10, transform=ax.transAxes)
    # famous theorems as a rug
    for r in x.itertuples():
        ax.plot([r.stmt_depth] * 2, [-0.035, -0.012], color=AMBER if r.uses_real else BLUE, lw=0.8,
                alpha=0.8, transform=ax.get_xaxis_transform(), clip_on=False)
    ax.text(-1.2, -0.024, "famous\ntheorems", color=SUBTLE, fontsize=7.5,
            transform=ax.get_xaxis_transform(), va="center", ha="right")
    leg = ax.legend(frameon=False, fontsize=9, loc="upper right")
    for t, c in zip(leg.get_texts(), [BLUE, AMBER]):
        t.set_color(c)
    ax.set_yticks(ax.get_yticks())
    ax.set_yticklabels([f"{int(v):,}" for v in ax.get_yticks()])
    ax.set_ylim(0, None)
    fig.savefig(FIGURES / "cliff.png", facecolor=BG, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)


TANGLE_LABELS = ["natural number", "rational number", "prime number", "real number", "complex number",
                 "logarithm", "derivative", "Gaussian law", "group", "field", "ideal", "set",
                 "topological space", "metric space", "Lebesgue measure", "Lp space", "category",
                 "Turing machine", "martingale", "distribution", "scheme", "regular expression",
                 "conditional expectation", "angle", "Lie group", "hyperreal number", "VC dimension",
                 "Riemannian manifold", "filter", "sine"]


def tangle():
    _, S = load()
    c = pd.read_csv(DERIVED / "concepts.csv")
    c = c.sort_values(["year", "label"]).reset_index(drop=True)
    n = len(c)
    c["ly"] = np.arange(n)
    c["ry"] = c.depth.rank(method="first").to_numpy() - 1
    fig, ax = plt.subplots(figsize=(11, 14), dpi=220, facecolor=BG)
    base(ax)
    xl, xr = 0.0, 1.0
    for r in c.itertuples():
        col = AMBER if r.uses_real else BLUE
        t = np.linspace(0, 1, 40)
        s = t * t * (3 - 2 * t)
        ys = r.ly + (r.ry - r.ly) * s
        lab = r.label in TANGLE_LABELS
        ax.plot(xl + (xr - xl) * t, ys, color=col, lw=1.1 if lab else 0.6, alpha=0.75 if lab else 0.28)
    ax.scatter([xl] * n, c.ly, s=6, color=[AMBER if u else BLUE for u in c.uses_real], zorder=3)
    ax.scatter([xr] * n, c.ry, s=6, color=[AMBER if u else BLUE for u in c.uses_real], zorder=3)
    lab = c[c.label.isin(TANGLE_LABELS)]
    gap = 2.6
    lys = spread(lab.ly.to_numpy(), gap, lo=0, hi=n - 1)
    rys = spread(lab.ry.to_numpy(), gap, lo=0, hi=n - 1)
    for r, ly, ry in zip(lab.itertuples(), lys, rys):
        col = AMBER if r.uses_real else "#9fb7d4"
        ax.plot([xl - 0.005, xl - 0.03, xl - 0.05], [r.ly, r.ly, ly], color=col, lw=0.5, alpha=0.6)
        ax.plot([xr + 0.005, xr + 0.03, xr + 0.05], [r.ry, r.ry, ry], color=col, lw=0.5, alpha=0.6)
        ax.text(xl - 0.06, ly, f"{r.label}  {year_label(int(r.year))}", color=col, fontsize=7.8,
                ha="right", va="center")
        ax.text(xr + 0.06, ry, f"{r.depth}  {r.label}", color=col, fontsize=7.8, ha="left", va="center")
    ax.set_ylim(n + 1, -6)
    ax.set_xlim(-0.55, 1.55)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.text(xl, -3.5, "oldest", color=TEXT, fontsize=10, ha="center")
    ax.text(xr, -3.5, "shallowest", color=TEXT, fontsize=10, ha="center")
    ax.text(xl, n + 0.5, "newest", color=TEXT, fontsize=10, ha="center", va="top")
    ax.text(xr, n + 0.5, "deepest", color=TEXT, fontsize=10, ha="center", va="top")
    ax.text(xl, -1.6, "ordered by the year the concept appeared", color=SUBTLE, fontsize=8.5, ha="center")
    ax.text(xr, -1.6, "ordered by depth in mathlib", color=SUBTLE, fontsize=8.5, ha="center")
    C = S["concepts"]
    fig.text(0.07, 0.955, "Age and depth disagree", color=TEXT, fontsize=22, fontweight="bold")
    fig.text(0.07, 0.938, f"{n} core definitions of mathlib. If older concepts sat higher, the lines would run "
             f"straight across. Spearman ρ between year and depth: {C['all']['rho']:+.2f}.",
             color=SUBTLE, fontsize=10)
    fig.text(0.07, 0.925, "Amber: the definition passes through the real numbers. Blue: it does not.",
             color=SUBTLE, fontsize=10)
    fig.savefig(FIGURES / "tangle.png", facecolor=BG, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)


EXAMPLE_KEYS = ["f9", "wQ810431", "wQ11518", "wQ2027347"]


def examples(x, keys=EXAMPLE_KEYS):
    """(header, line) per example: how many famous theorems its proof rests on, how many are younger."""
    fe = pd.read_csv(DERIVED / "famous_edges.csv")
    t = x.set_index("key")
    out = []
    for key in keys:
        r = t.loc[key]
        used = t.loc[t.index.intersection(fe[fe.user == key].used)].dropna(subset=["year_proved"])
        young = used[used.year_proved > r.year_proved].sort_values("year_proved")
        head = f"{r.title}  ·  {year_label(int(r.year_proved))}"
        line = (f"rests on {len(used)} famous theorem{'s' if len(used) != 1 else ''} in the sample; "
                f"{len(young) if len(young) else 'none'} found later")
        if len(young) > 1:
            first, last = young.iloc[0], young.iloc[-1]
            line += (f", from {first.title} ({year_label(int(first.year_proved))}) "
                     f"to {last.title} ({int(last.year_proved)})")
        elif len(young) == 1:
            line += f": {young.iloc[0].title} ({int(young.iloc[0].year_proved)})"
        out.append((head, line))
    return out


def arrow():
    x, S = load()
    yr = x.set_index("key").year_proved
    re = pd.read_csv(DERIVED / "famous_edges_reduced.csv")
    re = re[re.user.isin(yr.dropna().index) & re.used.isin(yr.dropna().index)]
    fig = plt.figure(figsize=(14, 9), dpi=220, facecolor=BG)
    ax = fig.add_axes([0.06, 0.40, 0.90, 0.48])
    base(ax)
    for r in re.itertuples():
        a, b = float(xmap(yr[r.user])), float(xmap(yr[r.used]))
        fwd = yr[r.used] > yr[r.user]
        mid, rad = (a + b) / 2, abs(b - a) / 2
        th = np.linspace(0, np.pi, 50)
        ys = np.sin(th) * rad * (1 if fwd else -1)
        xs = mid - np.cos(th) * rad * np.sign(b - a if b != a else 1)
        ax.plot(xs, ys, color=FWD if fwd else BACK, lw=0.6, alpha=0.35 if fwd else 0.28)
    pts = x.dropna(subset=["year_proved"])
    ax.scatter(xmap(pts.year_proved), np.zeros(len(pts)), s=7, color=TEXT, zorder=3, lw=0)
    year_axis(ax)
    ax.set_yticks([])
    ax.set_ylim(-0.52, 0.52)
    ax.text(0.0, 0.47, "arcs above: the proof rests on a theorem found later", color=FWD, fontsize=9.5)
    ax.text(0.0, -0.49, "arcs below: on a theorem found earlier", color=BACK, fontsize=9.5)
    ax.set_xlabel("year first proved", color=SUBTLE, fontsize=9.5)
    A = S["anachronism"]
    fig.text(0.06, 0.95, "Time runs backwards in mathlib", color=TEXT, fontsize=22, fontweight="bold")
    fig.text(0.06, 0.92, f"Each arc joins a famous theorem to a famous theorem its mathlib proof rests on "
             f"({A['reduced_edges']} direct links after removing ones implied by others).", color=SUBTLE,
             fontsize=10.5)

    bx = fig.add_axes([0.06, 0.07, 0.42, 0.24])
    base(bx)
    eras = list(A["by_era"].keys())
    obs = [A["by_era"][e]["share"] for e in eras]
    nul = [A["by_era"][e]["null"] for e in eras]
    lo = [A["by_era"][e]["null_lo"] for e in eras]
    hi = [A["by_era"][e]["null_hi"] for e in eras]
    xs = np.arange(len(eras))
    bx.vlines(xs, lo, hi, color=SUBTLE, lw=6, alpha=0.35)
    bx.scatter(xs, nul, color=SUBTLE, s=18, zorder=3, label="if prerequisites were picked blind to history")
    bx.scatter(xs, obs, color=FWD, s=48, zorder=4, label="mathlib")
    bx.set_xticks(xs)
    bx.set_xticklabels([f"{e}\n(n={A['by_era'][e]['n']})" for e in eras], fontsize=8)
    bx.set_ylim(0, 1.05)
    bx.set_yticks([0, 0.5, 1])
    bx.set_yticklabels(["0", "50%", "100%"])
    bx.grid(axis="y", color=GRID, lw=0.6)
    bx.set_title("Share of theorems whose proof rests on a younger famous theorem", color=TEXT,
                 fontsize=10, loc="left")
    leg = bx.legend(frameon=False, fontsize=8, loc="lower left")
    for t, c in zip(leg.get_texts(), [SUBTLE, FWD]):
        t.set_color(c)

    tx = 0.54
    fig.text(tx, 0.29, "Examples", color=TEXT, fontsize=10.5,
             fontweight="bold")
    for i, (key, line) in enumerate(examples(x)):
        y = 0.255 - i * 0.055
        fig.text(tx, y, key, color=TEXT, fontsize=9)
        fig.text(tx, y - 0.022, line, color=SUBTLE, fontsize=8.3)
    fig.savefig(FIGURES / "arrow.png", facecolor=BG, pad_inches=0.2)
    plt.close(fig)


def proofs():
    x, S = load()
    x = x.dropna(subset=["proof_size"])
    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=220, facecolor=BG)
    base(ax)
    cols = x.field.map(FIELDS).fillna(SUBTLE)
    glow_scatter(ax, x.stmt_depth, x.proof_size, np.full(len(x), 16), cols)
    ax.set_yscale("log")
    ax.grid(color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    real = S["real_depth"]
    ax.axvline(real - 0.5, color=AMBER, lw=1, alpha=0.7)
    ax.set_xlabel("statement depth", color=SUBTLE)
    ax.set_ylabel("size of the proof: definitions and named theorems it rests on", color=SUBTLE)
    r = S["proof_size_vs_statement"]
    ax.set_title("Deep statements need big proofs", color=TEXT, fontsize=15, loc="left", pad=24,
                 fontweight="bold")
    ax.text(0, 1.025, f"Spearman ρ between statement depth and proof size {r['rho']:.2f}. "
            f"Number theory (amber, left) is the exception: shallow statements, proofs built on analysis.",
            color=SUBTLE, fontsize=9.5, transform=ax.transAxes)
    ax.text(real - 0.2, 1.0, "ℝ ", color=AMBER, fontsize=10, ha="right", va="top",
            transform=ax.get_xaxis_transform())
    for i, (f, c) in enumerate(FIELDS.items()):
        ax.text(1.01, 0.98 - i * 0.045, f, color=c, fontsize=8.5, transform=ax.transAxes, va="top")
    for k, (lab, dx, dy) in {"wQ474881": ("Cantor's theorem", 6, 4), "wQ1506253": ("Euclid's primes", 6, -10),
                             "wQ632546": ("Bertrand's postulate", 6, 6),
                             "wQ2027347": ("optional stopping", -60, 8),
                             "wQ11518": ("Pythagorean theorem", 6, -10)}.items():
        p = x[x.key == k]
        if len(p):
            ax.annotate(lab, (p.stmt_depth.iat[0], p.proof_size.iat[0]), xytext=(dx, dy),
                        textcoords="offset points", color=TEXT, fontsize=8, path_effects=HALO)
    fig.savefig(FIGURES / "proofs.png", facecolor=BG, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)


if __name__ == "__main__":
    hero()
    cliff()
    tangle()
    arrow()
    proofs()
    print("figures written")
