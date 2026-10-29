"""Statistics for the second round of follow-ups, scored against results/preregistration.md.

Run after proofsplit.py, research.py (all projects), syllabus.py, concepts2.py, library_time.py and
hollight.py. Writes results/summary_round2.json.
"""
import json

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import mannwhitneyu

import metamath
from analysis import RNG, boot_rho
from config import DERIVED, LABELS, RESULTS

B = 2000


def p1():
    s = pd.read_csv(DERIVED / "proofsplit.csv")
    r = pd.read_csv(DERIVED / "research.csv")
    done = r[~r.uses_sorry & r.own_layers.notna()]
    s["library_layers"] = s.chain_layers - s.own_parent
    out = dict(
        sample=dict(n=len(s), chain_max=int(s.chain_layers.max()), chain_median=float(s.chain_layers.median()),
                    own_folder_median=float(s.own_folder.median()), own_parent_median=float(s.own_parent.median()),
                    own_parent_max=int(s.own_parent.max()), library_max=int(s.library_layers.max()),
                    deepest=s.sort_values("chain_layers").tail(3)[["title", "chain_layers", "own_folder",
                                                                    "own_parent"]].to_dict("records")),
        research=done[["name", "title", "chain_layers", "own_layers"]].assign(
            library_layers=lambda d: d.chain_layers - d.own_layers).to_dict("records"))
    lib = [x["library_layers"] for x in out["research"]]
    out["research_library_above_sample_max"] = int(sum(v > out["sample"]["library_max"] for v in lib))
    out["research_own_above_sample_own_max"] = int(sum(x["own_layers"] > out["sample"]["own_parent_max"]
                                                       for x in out["research"]))
    return out


def p2():
    s = pd.read_csv(DERIVED / "syllabus.csv")
    u = s[s.list == "undergraduate"].drop_duplicates("decl")
    o = s[s.overview_only].drop_duplicates("decl")
    res = dict(n_under=len(u), n_over=len(o), median_under=float(u.depth.median()), median_over=float(o.depth.median()),
               p_less=float(mannwhitneyu(u.depth, o.depth, alternative="less").pvalue),
               p_greater=float(mannwhitneyu(u.depth, o.depth, alternative="greater").pvalue),
               share_real_under=float(u.uses_real.mean()), share_real_over=float(o.uses_real.mean()))
    res["strata"] = {}
    for k in (False, True):
        a, b = u[u.uses_real == k].depth, o[o.uses_real == k].depth
        res["strata"]["real" if k else "no real"] = dict(n_under=len(a), n_over=len(b), median_under=float(a.median()),
                                                        median_over=float(b.median()),
                                                        p_less=float(mannwhitneyu(a, b, alternative="less").pvalue))
    res["areas"] = {f"{l}: {a}": float(v) for (l, a), v in s.groupby(["list", "area"]).depth.median().items()}
    return res


def p3():
    c = pd.read_csv(DERIVED / "concepts_fresh.csv")
    h = pd.read_csv(LABELS / "concept_dates_fresh.csv")
    r = c[c.uses_real].merge(h, on="label", how="left")
    w = r.dropna(subset=["wiki_year"])
    old = pd.read_csv(DERIVED / "concepts.csv")
    o = old[old.uses_real]
    hm = r[r.confidence.isin(["high", "medium"])]
    return dict(n_fresh=len(c), n_fresh_real=len(r), n_wiki=int(c.wiki_year.notna().sum()), n_wiki_real=len(w),
                hand=boot_rho(r.year, r.depth), hand_high_medium=boot_rho(hm.year, hm.depth),
                wikipedia=boot_rho(w.wiki_year, w.depth),
                pooled=boot_rho(pd.concat([o.year, r.year]), pd.concat([o.depth, r.depth])))


def p4():
    T = pd.read_csv(DERIVED / "library_time.csv", parse_dates=["entered"])
    x = pd.read_csv(DERIVED / "theorems.csv")
    t = T[T.kind == "theorem"].merge(x[["key", "title", "uses_real", "stmt_depth", "year_stated"]], on="key")
    t = t.dropna(subset=["entered", "year_stated"]).copy()
    t["ly"] = t.entered.dt.year + (t.entered.dt.dayofyear - 1) / 366
    real = T[T.decl == "Real"].entered.iloc[0]
    viol = t[t.uses_real & (t.entered < real)]

    def diff(sub):
        n = len(sub)
        ys, ls, ds = sub.year_stated.to_numpy(), sub.ly.to_numpy(), sub.stmt_depth.to_numpy()
        from scipy.stats import spearmanr
        obs = spearmanr(ls, ds).statistic - spearmanr(ys, ds).statistic
        bs = []
        for _ in range(B):
            i = RNG.integers(0, n, n)
            bs.append(spearmanr(ls[i], ds[i]).statistic - spearmanr(ys[i], ds[i]).statistic)
        return dict(diff=float(obs), lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)), n=n)

    ported = t[t.how == "mathlib3"]
    cc = T[T.kind == "concept"].merge(pd.read_csv(DERIVED / "concepts.csv")[["decl", "depth", "year"]], on="decl")
    cc = cc.dropna(subset=["entered"])
    cc["ly"] = cc.entered.dt.year + (cc.entered.dt.dayofyear - 1) / 366
    audit = {}
    if (RESULTS / "library_audit.csv").exists():   # written by library_audit.py
        for k, v in pd.read_csv(RESULTS / "library_audit.csv").groupby("kind"):
            gap = v.months_late.dropna()
            audit[k] = dict(n=len(v), found_by_git=len(gap), same_month=int((gap == 0).sum()),
                            late=int((gap > 0).sum()), late_max=int(gap.max()) if len(gap) else 0,
                            early=int((gap < 0).sum()),
                            early_via_namespace_change=int(((gap < 0) & (v.months_back > 0)).sum()))
    return dict(
        audit=audit,
        counts=T.groupby("kind").how.value_counts().unstack(fill_value=0).to_dict("index"),
        renames_followed=int(T.renamed_from.notna().sum()),
        real_entered=str(real.date()), p4a_violations=len(viol),
        all=boot_rho(t.ly, t.stmt_depth), ported=boot_rho(ported.ly, ported.stmt_depth),
        history_same=boot_rho(t.year_stated, t.stmt_depth),
        history_ported=boot_rho(ported.year_stated, ported.stmt_depth),
        diff_all=diff(t), diff_ported=diff(ported),
        concepts=boot_rho(cc.ly, cc.depth), concepts_ported=boot_rho(cc[cc.how == "mathlib3"].ly,
                                                                     cc[cc.how == "mathlib3"].depth),
        by_year={int(k): dict(median=float(v.median()), n=int(v.size), share_real=float(u.mean()))
                 for (k, v), (_, u) in zip(t.groupby(t.entered.dt.year).stmt_depth,
                                           t.groupby(t.entered.dt.year).uses_real)},
        within={f"{name}, {'real' if ur else 'no real'}": boot_rho(sub[sub.uses_real == ur].ly,
                                                                     sub[sub.uses_real == ur].stmt_depth)
                for name, sub in [("all", t), ("ported", ported)] for ur in (False, True)},
        first=t.sort_values("entered").head(6)[["title", "entered", "stmt_depth"]].astype(str).to_dict("records"))


def p5():
    hd = pd.concat([pd.read_csv(LABELS / "hand_dates.csv"), pd.read_csv(LABELS / "hand_dates_extra.csv")])
    hd = hd.drop_duplicates("key").set_index("key")
    fk = metamath.freek_keys()
    h = pd.read_csv(DERIVED / "hollight_hundred.csv")
    h["key"] = h.freek.map(lambda n: fk.get(n, f"f{n}"))
    h["year"] = h.key.map(lambda k: hd.year_stated.get(k))
    h.to_csv(DERIVED / "hollight_hundred_dated.csv", index=False)
    d = h.dropna(subset=["year"]).assign(c=lambda z: z.year / 100, ur=lambda z: z.uses_real.astype(int))
    c = pd.read_csv(DERIVED / "hollight_constants.csv").set_index("constant").depth
    m = pd.read_csv(DERIVED / "theorems.csv")[["key", "stmt_depth"]].rename(columns={"stmt_depth": "lean"})
    j = d.merge(m, on="key")
    mm = pd.read_csv(DERIVED / "metamath_hundred.csv")[["freek", "stmt_depth"]].rename(columns={"stmt_depth": "mm"})
    k = d.merge(mm, on="freek")
    tower = {n: int(c[n]) for n in ["type:num", "type:nadd", "type:hreal", "type:real", "type:int", "rational",
                                    "type:complex"] if n in c.index}
    return dict(n_statements=len(h), n_dated=len(d), tower=tower,
                p5a=bool(tower["type:real"] > tower["type:hreal"] > tower["type:nadd"] > tower["type:num"]
                         and tower["type:int"] > tower["type:real"]),
                trend=boot_rho(d.year, d.stmt_depth),
                r2={"year": float(smf.ols("stmt_depth ~ c", d).fit().rsquared),
                    "passes through the reals": float(smf.ols("stmt_depth ~ ur", d).fit().rsquared)},
                share_real=float(d.uses_real.mean()), median_depth=float(d.stmt_depth.median()),
                vs_mathlib=boot_rho(j.lean, j.stmt_depth), vs_metamath=boot_rho(k.mm, k.stmt_depth),
                shallowest=h.sort_values("stmt_depth").head(4)[["title", "stmt_depth"]].to_dict("records"),
                deepest=h.sort_values("stmt_depth").tail(4)[["title", "stmt_depth"]].to_dict("records"))


def main():
    R = dict(p1=p1(), p2=p2(), p3=p3(), p4=p4(), p5=p5())
    json.dump(R, open(RESULTS / "summary_round2.json", "w"), indent=1, default=str)
    return R


if __name__ == "__main__":
    R = main()
    print(json.dumps(R, indent=1, default=str)[:9000])
