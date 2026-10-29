"""Every statistic quoted in the README. Writes results/summary.json and data/derived/theorems.csv.

Run after targets.py, measures.py, dating.py and concepts.py.
"""
import json

import networkx as nx
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import spearmanr

import graph as g
from config import DERIVED, LABELS, RESULTS

RNG = np.random.default_rng(20261014)
B = 2000
ERAS = [-10000, 1500, 1800, 1900, 1950, 2100]
ERA_LABELS = ["before 1500", "1500 to 1799", "1800 to 1899", "1900 to 1949", "1950 on"]


def rho(x, y):
    return float(spearmanr(x, y).statistic)


def boot_rho(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    bs = [rho(x[i], y[i]) for i in (RNG.integers(0, n, n) for _ in range(B))]
    return dict(rho=rho(x, y), lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)),
                p=float(spearmanr(x, y).pvalue), n=n)


def boot_slope(df, formula, term):
    fit = smf.ols(formula, df).fit()
    n = len(df)
    bs = []
    for _ in range(B):
        s = df.iloc[RNG.integers(0, n, n)]
        try:
            bs.append(smf.ols(formula, s).fit().params[term])
        except Exception:  # a resample can lose a factor level
            continue
    return dict(slope=float(fit.params[term]), lo=float(np.percentile(bs, 2.5)),
                hi=float(np.percentile(bs, 97.5)), r2=float(fit.rsquared), n=n)


def theorems():
    m = pd.read_csv(DERIVED / "measures.csv")
    d = pd.read_csv(LABELS / "hand_dates.csv")
    x = m.merge(d, on="key", how="left")
    x["era"] = pd.cut(x.year_stated, ERAS, labels=ERA_LABELS, right=False)
    return x


def whole_library():
    """Statement depth of every named theorem in mathlib, and whether it passes through Real."""
    df = g.nodes()
    hs = np.load(DERIVED / "h_stmt.npy")
    Gs = g.statement_graph()
    real = int(g.name_index()["Real"])
    # nodes from which Real is reachable in the statement graph = reverse reach from Real
    to_real = g.reach(Gs.T.tocsr(), [real])
    is_thm, is_meta = df.is_thm.to_numpy(), df.is_meta.to_numpy()
    et = g.edges_type()
    keep = is_thm[et[:, 0]] & ~is_thm[et[:, 1]] & ~is_meta[et[:, 1]]
    e = et[keep]
    n = len(df)
    depth = np.zeros(n, dtype=np.int32)
    np.maximum.at(depth, e[:, 0], hs[e[:, 1]])
    uses_real = np.zeros(n, dtype=bool)
    np.logical_or.at(uses_real, e[:, 0], to_real[e[:, 1]])
    named = df.is_named_thm.to_numpy()
    out = pd.DataFrame(dict(depth=depth[named], uses_real=uses_real[named]))
    return out, int(hs[real])


def anachronism(x, fe):
    yr = x.set_index("key").year_proved.dropna()
    e = fe[fe.user.isin(yr.index) & fe.used.isin(yr.index)].copy()
    e["y_user"], e["y_used"] = e.user.map(yr), e.used.map(yr)

    def stats(yu, yb):
        fwd, back = (yb > yu).mean(), (yb < yu).mean()
        return fwd, back

    fwd, back = stats(e.y_user.to_numpy(), e.y_used.to_numpy())
    keys = yr.index.to_numpy()
    vals = yr.to_numpy()
    null = []
    for _ in range(B):
        perm = pd.Series(RNG.permutation(vals), index=keys)
        f, _b = stats(e.user.map(perm).to_numpy(), e.used.map(perm).to_numpy())
        null.append(f)
    null = np.array(null)
    per_user = e.groupby("user").apply(lambda s: bool((s.y_used > s.y_user).any()), include_groups=False)
    era = x.set_index("key").era
    by_era = (per_user.groupby(era.reindex(per_user.index).astype(str)).agg(["mean", "size"])
              .reindex(ERA_LABELS))
    # history-blind null by era: each user keeps its number of famous prerequisites, but they
    # are drawn at random from the other dated theorems
    k = e.groupby("user").size()
    pool = yr
    null_era = {lab: [] for lab in ERA_LABELS}
    users_era = era.reindex(k.index).astype(str)
    for _ in range(500):
        hit = {}
        for u, ku in k.items():
            others = pool.drop(u).to_numpy()
            draw = RNG.choice(others, size=ku, replace=False)
            hit[u] = bool((draw > yr[u]).any())
        hit = pd.Series(hit)
        for lab, v in hit.groupby(users_era):
            if lab in null_era:
                null_era[lab].append(v.mean())
    # transitive reduction: the "direct" famous prerequisites
    G = nx.DiGraph()
    G.add_edges_from(map(tuple, fe[["user", "used"]].to_numpy()))
    red = nx.transitive_reduction(G) if nx.is_directed_acyclic_graph(G) else G
    re = pd.DataFrame(list(red.edges()), columns=["user", "used"])
    re = re[re.user.isin(yr.index) & re.used.isin(yr.index)]
    rf = float((re.used.map(yr) > re.user.map(yr)).mean())
    return dict(
        edges=len(e), forward_share=float(fwd), backward_share=float(back),
        tie_share=float(1 - fwd - back),
        null_forward_mean=float(null.mean()), null_lo=float(np.percentile(null, 2.5)),
        null_hi=float(np.percentile(null, 97.5)), p_less_than_null=float((null <= fwd).mean()),
        users=int(len(per_user)), users_with_younger=float(per_user.mean()),
        by_era={k: dict(share=None if pd.isna(r["mean"]) else float(r["mean"]),
                        n=0 if pd.isna(r["size"]) else int(r["size"]),
                        null=float(np.mean(null_era[k])) if null_era[k] else None,
                        null_lo=float(np.percentile(null_era[k], 2.5)) if null_era[k] else None,
                        null_hi=float(np.percentile(null_era[k], 97.5)) if null_era[k] else None)
                for k, r in by_era.iterrows()},
        reduced_edges=len(re), reduced_forward_share=rf,
        dag=bool(nx.is_directed_acyclic_graph(G))), e, re


def main():
    x = theorems()
    x.to_csv(DERIVED / "theorems.csv", index=False)
    dated = x.dropna(subset=["year_stated"])
    S = {"n_targets": len(x), "n_dated": len(dated)}
    S["sources"] = x.source.value_counts().to_dict()

    # H1: statement depth rises with discovery year
    S["h1_depth"] = boot_rho(dated.year_stated, dated.stmt_depth)
    S["h1_size"] = boot_rho(dated.year_stated, dated.stmt_size)
    S["h1_slope_per_century"] = boot_slope(dated.assign(c=dated.year_stated / 100),
                                           "stmt_depth ~ c", "c")
    S["era_medians"] = {str(k): dict(depth=float(v.stmt_depth.median()), size=float(v.stmt_size.median()),
                                     n=len(v))
                        for k, v in dated.groupby("era", observed=True)}
    rob = {}
    rob["statement size"] = S["h1_size"]
    rob["smallest of the listed declarations"] = boot_rho(dated.year_stated, dated.stmt_depth_min)
    rob["year first proved"] = boot_rho(dated.year_proved, dated.stmt_depth)
    c = dated[(dated.ninst == 0) & (dated.nsort == 0)]
    rob["concrete statements only (no type or instance arguments)"] = boot_rho(c.year_stated, c.stmt_depth)
    ng = dated[dated.field != "Geometry"]
    rob["without geometry"] = boot_rho(ng.year_stated, ng.stmt_depth)
    hc = dated[dated.confidence.isin(["high", "medium"])]
    rob["high or medium confidence dates"] = boot_rho(hc.year_stated, hc.stmt_depth)
    l1 = dated[dated.source.astype(str) == "1000"]
    rob["Wikipedia list only"] = boot_rho(l1.year_stated, l1.stmt_depth)
    modern = dated[dated.year_stated >= 1800]
    rob["since 1800 only"] = boot_rho(modern.year_stated, modern.stmt_depth)
    S["robustness"] = rob

    # fields
    S["fields"] = {f: dict(n=len(v), median_depth=float(v.stmt_depth.median()),
                           rho=rho(v.year_stated, v.stmt_depth) if len(v) > 4 else None,
                           p=float(spearmanr(v.year_stated, v.stmt_depth).pvalue) if len(v) > 4 else None)
                   for f, v in dated.groupby("field")}
    S["field_fe_slope_per_century"] = boot_slope(dated.assign(c=dated.year_stated / 100),
                                                 "stmt_depth ~ c + C(field)", "c")

    # what explains depth
    fits = {}
    dd = dated.assign(c=dated.year_stated / 100)
    for name, f in [("year", "stmt_depth ~ c"), ("field", "stmt_depth ~ C(field)"),
                    ("uses real numbers", "stmt_depth ~ uses_real"),
                    ("real, measure, inner product", "stmt_depth ~ uses_real + uses_measure + uses_inner"),
                    ("real, measure, inner product + year",
                     "stmt_depth ~ uses_real + uses_measure + uses_inner + c")]:
        fits[name] = float(smf.ols(f, dd).fit().rsquared)
    S["r2"] = fits
    S["share_uses_real"] = float(dated.uses_real.mean())
    S["strata"] = {}
    for k, v in dated.groupby("uses_real"):
        S["strata"]["real" if k else "no real"] = dict(
            n=len(v), min=int(v.stmt_depth.min()), median=float(v.stmt_depth.median()),
            max=int(v.stmt_depth.max()), trend=boot_rho(v.year_stated, v.stmt_depth))
    S["year_predicts_real"] = boot_rho(dated.year_stated, dated.uses_real.astype(int))

    # whole library
    lib, real_depth = whole_library()
    S["real_depth"] = real_depth
    S["library"] = dict(
        named_theorems=len(lib), share_uses_real=float(lib.uses_real.mean()),
        share_deeper_than_real_without_real=float(((lib.depth >= real_depth) & ~lib.uses_real).mean()),
        share_nonreal_below_real=float((lib.depth[~lib.uses_real] < real_depth).mean()),
        median_depth_real=float(lib.depth[lib.uses_real].median()),
        median_depth_nonreal=float(lib.depth[~lib.uses_real].median()))
    lib.to_parquet(DERIVED / "library_depths.parquet")

    # proofs
    pr = dated.dropna(subset=["year_proved", "proof_depth"])
    S["proof_depth"] = boot_rho(pr.year_proved, pr.proof_depth)
    S["proof_size"] = boot_rho(pr.year_proved, pr.proof_size)
    S["proof_vs_statement"] = boot_rho(pr.stmt_depth, pr.proof_depth)
    S["proof_size_vs_statement"] = boot_rho(pr.stmt_depth, pr.proof_size)
    S["proof_size_median"] = float(pr.proof_size.median())

    # anachronism
    fe = pd.read_csv(DERIVED / "famous_edges.csv")
    S["anachronism"], e, re = anachronism(x, fe)
    re.to_csv(DERIVED / "famous_edges_reduced.csv", index=False)

    # concepts
    cc = pd.read_csv(DERIVED / "concepts.csv")
    S["concepts"] = dict(all=boot_rho(cc.year, cc.depth),
                         n=len(cc),
                         by_real={("real" if k else "no real"): boot_rho(v.year, v.depth)
                                  for k, v in cc.groupby("uses_real")},
                         era_medians={str(k): dict(depth=float(v.depth.median()), n=len(v))
                                      for k, v in cc.groupby(pd.cut(cc.year, ERAS, labels=ERA_LABELS,
                                                                    right=False), observed=True)})

    # dating audit
    a = pd.read_csv(RESULTS / "dating_audit.csv")
    p = a.dropna(subset=["p575", "year_stated"])
    lt = a.dropna(subset=["in_lifetime"])
    S["dating"] = dict(p575_n=len(p), p575_within5=float((p.p575_gap <= 5).mean()),
                       p575_median_gap=float(p.p575_gap.median()),
                       lifetime_n=len(lt), lifetime_pass=float(lt.in_lifetime.astype(bool).mean()),
                       confidence=dated.confidence.value_counts().to_dict())

    json.dump(S, open(RESULTS / "summary.json", "w"), indent=1, default=str)
    return S


if __name__ == "__main__":
    S = main()
    print(json.dumps({k: S[k] for k in ["h1_depth", "r2", "strata", "library", "anachronism", "concepts"]},
                     indent=1, default=str)[:6000])
