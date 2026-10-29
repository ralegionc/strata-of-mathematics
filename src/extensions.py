"""Statistics for the six follow-up tests. Writes results/summary_extensions.json.

Run after analysis.py, variants.py, dating2.py, textbook.py, metamath.py and research.py.
"""
import json

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

import graph as g
from analysis import ERA_LABELS, ERAS, anachronism, boot_rho
from config import DERIVED, LABELS, RESULTS


def r2(df, formula):
    return float(smf.ols(formula, df).fit().rsquared)


def numbers_given(x):
    v = pd.read_csv(DERIVED / "variants_theorems.csv")
    d = x.merge(v, on="key").dropna(subset=["year_stated"])
    d = d.assign(c=d.year_stated / 100)
    idx = g.name_index()
    hn = np.load(DERIVED / "h_stmt_numbers.npy")
    lib = pd.read_parquet(DERIVED / "library_depths_numbers.parquet")
    cc = pd.read_csv(DERIVED / "concepts.csv").merge(
        pd.read_csv(DERIVED / "variants_concepts.csv")[["decl", "depth_numbers"]], on="decl")
    return dict(
        depth=boot_rho(d.year_stated, d.depth_numbers), size=boot_rho(d.year_stated, d.size_numbers),
        r2={"year": r2(d, "depth_numbers ~ c"), "field": r2(d, "depth_numbers ~ C(field)"),
            "uses real numbers": r2(d, "depth_numbers ~ uses_real"),
            "real, measure, inner product": r2(d, "depth_numbers ~ uses_real + uses_measure + uses_inner")},
        era_medians={str(k): float(v.depth_numbers.median())
                     for k, v in d.groupby(pd.cut(d.year_stated, ERAS, labels=ERA_LABELS, right=False),
                                           observed=True)},
        within_real={("real" if k else "no real"): boot_rho(v.year_stated, v.depth_numbers)
                     for k, v in d.groupby("uses_real")},
        depths={n: int(hn[idx[n]]) for n in ["Nat", "Int", "Rat", "Real", "Complex", "Field", "Group",
                                             "TopologicalSpace", "MetricSpace", "MeasureTheory.Measure",
                                             "AlgebraicGeometry.Scheme", "MeasureTheory.Martingale"]},
        median_depth=float(d.depth_numbers.median()), median_depth_before=float(d.stmt_depth.median()),
        library_median=dict(real=float(lib.depth_numbers[lib.uses_real].median()),
                            nonreal=float(lib.depth_numbers[~lib.uses_real].median())),
        concepts=boot_rho(cc.year, cc.depth_numbers),
        concepts_real=boot_rho(cc[cc.uses_real].year, cc[cc.uses_real].depth_numbers))


def direct(x):
    fe = pd.read_csv(DERIVED / "famous_edges_direct.csv")
    A, _, _ = anachronism(x, fe)
    return A


def dating(x):
    ind = pd.read_csv(DERIVED / "dates_independent.csv")
    hd = pd.read_csv(LABELS / "hand_dates.csv")
    j = ind.merge(hd, on="key").merge(x[["key", "stmt_depth"]], on="key")

    def gap(df, col):
        return pd.concat([(df[col] - df.year_stated).abs(), (df[col] - df.year_proved).abs()], axis=1).min(axis=1)

    out = {}
    for name, sub, col in [("wikipedia lead, linked by Wikidata", j[(j.wiki_where == "lead") & (j.wiki_how == "wikidata")], "wiki_year"),
                           ("wikipedia lead, any", j[j.wiki_where == "lead"], "wiki_year"),
                           ("wikipedia body", j[j.wiki_where == "body"], "wiki_year"),
                           ("mactutor", j, "mactutor_year")]:
        s = sub.dropna(subset=[col, "year_stated"])
        gp = gap(s, col)
        out[name] = dict(n=len(s), median_gap=float(gp.median()), within10=float((gp <= 10).mean()),
                         within50=float((gp <= 50).mean()), rho_with_hand=boot_rho(s.year_stated, s[col]))
    dis = pd.read_csv(LABELS / "dating_disagreements.csv")
    out["disagreements"] = dis.category.value_counts().to_dict()
    # main test with independent dates swapped in where the clean source has one
    lead = j[(j.wiki_where == "lead") & (j.wiki_how == "wikidata")].set_index("key").wiki_year
    y = x.dropna(subset=["year_stated"]).copy()
    y["year_swap"] = y.key.map(lead).fillna(y.year_stated)
    out["h1_swapped"] = boot_rho(y.year_swap, y.stmt_depth)
    s = j[(j.wiki_where == "lead") & (j.wiki_how == "wikidata")].dropna(subset=["wiki_year"])
    out["h1_wikipedia_only"] = boot_rho(s.wiki_year, s.stmt_depth)
    s = j.dropna(subset=["mactutor_year"])
    out["h1_mactutor_only"] = boot_rho(s.mactutor_year, s.stmt_depth)
    return out


def textbook(x):
    t = pd.read_csv(DERIVED / "textbook.csv")
    main = t[t.name != "pythagoras_int"]
    y = x.dropna(subset=["year_stated"]).set_index("key")
    sub = main.drop_duplicates("key").set_index("key").textbook_depth
    d = y.stmt_depth.copy()
    d.loc[sub.index] = sub
    return dict(
        n=len(t), rows=t[["name", "title", "year_stated", "mathlib_depth", "textbook_depth",
                           "mathlib_depth_numbers", "textbook_depth_numbers", "textbook_uses_real"]].to_dict("records"),
        median_change=float((main.textbook_depth - main.mathlib_depth).median()),
        shallower=int((main.textbook_depth < main.mathlib_depth).sum()),
        deeper=int((main.textbook_depth > main.mathlib_depth).sum()),
        same=int((main.textbook_depth == main.mathlib_depth).sum()),
        h1_substituted=boot_rho(y.year_stated, d))


def metamath():
    from metamath import NUMBER_END, NUMBER_START  # noqa: F401  (documented constants)
    h = pd.read_csv(DERIVED / "metamath_hundred.csv")
    d = h.dropna(subset=["year_stated"]).copy()
    d = d.assign(c=d.year_stated / 100, ur=d.uses_real.astype(int), uc=d.uses_complex.astype(int))
    m = pd.read_csv(DERIVED / "theorems.csv")[["key", "stmt_depth", "proof_size"]].rename(
        columns={"stmt_depth": "lean_depth", "proof_size": "lean_proof"})
    j = d.merge(m, on="key").drop_duplicates("label")
    fe = pd.read_csv(DERIVED / "metamath_famous_edges.csv")
    xm = d.rename(columns={"label": "lbl"}).assign(key=d.label)
    xm["era"] = pd.cut(xm.year_stated, ERAS, labels=ERA_LABELS, right=False)
    A, _, _ = anachronism(xm, fe)
    th = pd.read_csv(DERIVED / "metamath_theorems.csv")
    return dict(
        n_listed=int(len(h)), n_dated=int(len(d)),
        depth=boot_rho(d.year_stated, d.stmt_depth), depth_numbers=boot_rho(d.year_stated, d.depth_numbers),
        r2={"year": r2(d, "stmt_depth ~ c"), "passes through RR": r2(d, "stmt_depth ~ ur"),
            "passes through CC": r2(d, "stmt_depth ~ uc")},
        share_complex=float(d.uses_complex.mean()), share_real=float(d.uses_real.mean()),
        cross_depth=boot_rho(j.lean_depth, j.stmt_depth), cross_proof=boot_rho(j.lean_proof, j.proof_size),
        n_shared=int(len(j)), anachronism=A, n_theorems=int(len(th)),
        median_depth=float(d.stmt_depth.median()), median_depth_numbers=float(d.depth_numbers.median()))


def research(x):
    p = DERIVED / "research.csv"
    if not p.exists():
        return None
    r = pd.read_csv(p)
    # calibrate each project's mathlib version to the main sample's: in v4.34 core Lean defines gcd
    # with one level less, so ℝ sits at 21 there instead of 22
    real = json.load(open(RESULTS / "summary.json"))["real_depth"]
    r["offset"] = real - r.ref_Real
    r["stmt_depth_adj"] = r.stmt_depth + r.offset
    d = x.dropna(subset=["year_stated"])
    fit = smf.ols("stmt_depth ~ uses_real + uses_measure + uses_inner", d).fit()
    pred = fit.predict(r[["uses_real", "uses_measure", "uses_inner"]])
    r = r.assign(predicted=pred.round(1), residual=(r.stmt_depth_adj - pred).round(1))
    resid_sample = (d.stmt_depth - fit.predict(d)).abs()
    return dict(rows=r.drop(columns=["chain"]).to_dict("records"),
                median_depth_sample_1950=float(x[x.year_stated >= 1950].stmt_depth.median()),
                sample_abs_residual_median=float(resid_sample.median()),
                sample_abs_residual_p90=float(resid_sample.quantile(0.9)))


def main():
    x = pd.read_csv(DERIVED / "theorems.csv")
    x["era"] = pd.cut(x.year_stated, ERAS, labels=ERA_LABELS, right=False)
    E = dict(numbers_given=numbers_given(x), direct=direct(x), dating=dating(x), textbook=textbook(x),
             metamath=metamath(), research=research(x))
    if E["research"]:
        rs = pd.DataFrame(E["research"]["rows"])
        d = x.dropna(subset=["year_stated"])
        E["research_h1"] = boot_rho(pd.concat([d.year_stated, rs.year_stated]),
                                    pd.concat([d.stmt_depth, rs.stmt_depth_adj]))
        E["research_h1_proved"] = boot_rho(pd.concat([d.year_proved, rs.year_proved]),
                                           pd.concat([d.stmt_depth, rs.stmt_depth_adj]))
    json.dump(E, open(RESULTS / "summary_extensions.json", "w"), indent=1, default=str)
    return E


if __name__ == "__main__":
    E = main()
    print(json.dumps({k: (v if k != "textbook" else {kk: vv for kk, vv in v.items() if kk != "rows"})
                      for k, v in E.items()}, indent=1, default=str)[:7000])
