"""Print every number quoted in the README, from results/summary.json and the derived tables."""
import json

import pandas as pd

from config import DERIVED, RESULTS

S = json.load(open(RESULTS / "summary.json"))


def r(d):
    return f"{d['rho']:+.2f} [{d['lo']:+.2f}, {d['hi']:+.2f}], p = {d['p']:.3f}, n = {d['n']}"


def pct(v):
    return f"{v:.0%}"


def main():
    print("== Sample")
    print(f"theorems linked to Lean: {S['n_targets']} ({S['sources']}); dated: {S['n_dated']}")
    print(f"date confidence: {S['dating']['confidence']}")

    print("\n== H1: statement depth rises with the year a theorem was found")
    print("depth vs year:", r(S["h1_depth"]))
    print("size vs year: ", r(S["h1_size"]))
    s = S["h1_slope_per_century"]
    print(f"slope {s['slope']:+.2f} levels per century [{s['lo']:+.2f}, {s['hi']:+.2f}], R2 {s['r2']:.3f}")
    s = S["field_fe_slope_per_century"]
    print(f"within fields: {s['slope']:+.2f} per century [{s['lo']:+.2f}, {s['hi']:+.2f}]")
    for k, v in S["era_medians"].items():
        print(f"  {k:14s} n={v['n']:3d} median depth {v['depth']:.1f}, size {v['size']:.0f}")
    print("robustness:")
    for k, v in S["robustness"].items():
        print(f"  {k:58s} {r(v)}")

    print("\n== Fields")
    for k, v in S["fields"].items():
        print(f"  {k:25s} n={v['n']:3d} median {v['median_depth']:.0f}  rho {v['rho']:+.2f} p={v['p']:.3f}")

    print("\n== What explains depth (R2)")
    for k, v in S["r2"].items():
        print(f"  {k:40s} {v:.3f}")
    print(f"share of famous theorems whose statement passes through R: {pct(S['share_uses_real'])}")
    for k, v in S["strata"].items():
        print(f"  {k:8s} n={v['n']} depth {v['min']} to {v['max']}, median {v['median']:.0f}; "
              f"trend with year {r(v['trend'])}")
    print("does the year predict using R?", r(S["year_predicts_real"]))
    L = S["library"]
    print(f"R sits at depth {S['real_depth']}")
    print(f"library: {L['named_theorems']:,} named theorems; {pct(L['share_uses_real'])} pass through R; "
          f"{pct(L['share_nonreal_below_real'])} of the others are shallower than R; "
          f"{L['share_deeper_than_real_without_real']:.1%} of all are at least as deep as R without it; "
          f"median depth {L['median_depth_nonreal']:.0f} vs {L['median_depth_real']:.0f}")

    print("\n== Proofs")
    print("proof depth vs year proved:", r(S["proof_depth"]))
    print("proof size vs year proved: ", r(S["proof_size"]))
    print("statement depth vs proof depth:", r(S["proof_vs_statement"]))
    print("statement depth vs proof size: ", r(S["proof_size_vs_statement"]))
    print(f"median proof size {S['proof_size_median']:,.0f}")

    print("\n== Anachronism")
    A = S["anachronism"]
    print(f"{A['edges']} famous-on-famous dependencies; {pct(A['forward_share'])} point to a younger theorem, "
          f"{pct(A['backward_share'])} to an older one, {A['tie_share']:.1%} same year")
    print(f"history-blind null: {pct(A['null_forward_mean'])} [{pct(A['null_lo'])}, {pct(A['null_hi'])}], "
          f"share of shuffles at or below observed {A['p_less_than_null']:.3f}")
    print(f"{A['users']} theorems use another famous theorem; {pct(A['users_with_younger'])} use a younger one")
    for k, v in A["by_era"].items():
        print(f"  {k:14s} n={v['n']:3d} observed {pct(v['share'])}, blind {pct(v['null'])} "
              f"[{pct(v['null_lo'])}, {pct(v['null_hi'])}]")
    print(f"direct links after transitive reduction: {A['reduced_edges']}, {pct(A['reduced_forward_share'])} forward")

    print("\n== Concepts")
    C = S["concepts"]
    print(f"{C['n']} concepts; depth vs year {r(C['all'])}")
    for k, v in C["by_real"].items():
        print(f"  {k:8s} {r(v)}")
    for k, v in C["era_medians"].items():
        print(f"  {k:14s} n={v['n']:3d} median depth {v['depth']:.1f}")

    print("\n== Dating audit")
    d = S["dating"]
    print(f"Wikidata P575 overlap {d['p575_n']}: within 5 years {pct(d['p575_within5'])}, "
          f"median gap {d['p575_median_gap']:.0f}")
    print(f"lifetime check {d['lifetime_n']}: {pct(d['lifetime_pass'])} inside a credited person's adult life")

    print("\n== Examples")
    x = pd.read_csv(DERIVED / "theorems.csv").set_index("key")
    for k in ["wQ11518", "wQ1506253", "wQ132469", "wQ474881", "wQ2027347", "f9", "wQ1032886", "wQ632546"]:
        t = x.loc[k]
        print(f"  {t.title}: depth {t.stmt_depth}, statement concepts {t.stmt_size}, "
              f"proof size {t.proof_size if t.proof_size == t.proof_size else 'none'}")
    ch = json.load(open(DERIVED / "chains.json", encoding="utf-8"))
    for k in ["wQ11518", "wQ1506253"]:
        print("  chain", k, " > ".join(n for n, _ in ch[k]))
    c = pd.read_csv(DERIVED / "concepts.csv").set_index("label")
    for k in ["natural number", "integer", "rational number", "real number", "complex number", "group", "field",
              "topological space", "category", "metric space", "measure", "scheme", "martingale"]:
        print(f"  concept {k}: depth {c.loc[k, 'depth']}")


def extensions():
    p = RESULTS / "summary_extensions.json"
    if not p.exists():
        return
    E = json.load(open(p))
    print("\n== 1. Number systems taken as given")
    N = E["numbers_given"]
    print("depth vs year:", r(N["depth"]), "| size vs year:", r(N["size"]))
    print("R2:", {k: round(v, 3) for k, v in N["r2"].items()})
    print("era medians:", N["era_medians"])
    print("within strata:", {k: r(v) for k, v in N["within_real"].items()})
    print("depths:", N["depths"])
    print(f"median famous depth {N['median_depth_before']:.0f} -> {N['median_depth']:.0f}; library medians {N['library_median']}")
    print("concepts:", r(N["concepts"]), "| concepts on R:", r(N["concepts_real"]))

    print("\n== 2. Metamath set.mm")
    M = E["metamath"]
    print(f"{M['n_theorems']:,} theorems; {M['n_listed']} of Wiedijk's 100, {M['n_dated']} dated")
    print("depth vs year:", r(M["depth"]), "| numbers given:", r(M["depth_numbers"]))
    print("R2:", {k: round(v, 3) for k, v in M["r2"].items()})
    print(f"pass through CC {pct(M['share_complex'])}, RR {pct(M['share_real'])}; median depth "
          f"{M['median_depth']:.0f}, numbers given {M['median_depth_numbers']:.0f}")
    print(f"same theorems in both libraries ({M['n_shared']}): depth {r(M['cross_depth'])}; proof {r(M['cross_proof'])}")
    A = M["anachronism"]
    print(f"famous dependencies {A['edges']}, forward {pct(A['forward_share'])} (blind {pct(A['null_forward_mean'])} "
          f"[{pct(A['null_lo'])}, {pct(A['null_hi'])}]); {A['users']} users, {pct(A['users_with_younger'])} use a younger one")
    for k, v in A["by_era"].items():
        print(f"  {k:14s} n={v['n']:3d} observed {pct(v['share'])}, blind {pct(v['null'])}")

    print("\n== 3. Textbook restatements")
    T = E["textbook"]
    for row in T["rows"]:
        print(f"  {row['name']:20s} mathlib {row['mathlib_depth']:2d} -> textbook {row['textbook_depth']:2d} "
              f"(numbers given {row['mathlib_depth_numbers']} -> {row['textbook_depth_numbers']})")
    print(f"shallower {T['shallower']}, deeper {T['deeper']}, same {T['same']}; median change {T['median_change']:+.0f}")
    print("main test with restatements swapped in:", r(T["h1_substituted"]))

    print("\n== 4. Research projects")
    if E.get("research"):
        for row in E["research"]["rows"]:
            print(f"  {row['title']}: {row['decl']} depth {row['stmt_depth']} (calibrated {row['stmt_depth_adj']}), "
                  f"numbers given {row['depth_numbers']}, size {row['stmt_size']}, predicted {row['predicted']}, "
                  f"residual {row['residual']:+}, proof depth {row['proof_depth']}, proof size {row['proof_size']:,}, "
                  f"sorry {row['uses_sorry']}; refs Nat {row['ref_Nat']} Rat {row['ref_Rat']} Real {row['ref_Real']} "
                  f"Complex {row['ref_Complex']}")
        R = E["research"]
        print(f"sample misses: median {R['sample_abs_residual_median']:.1f}, 90th percentile {R['sample_abs_residual_p90']:.1f}")
        print(f"median depth of sample theorems from 1950 on: {E['research']['median_depth_sample_1950']:.1f}")
        if E.get("research_h1"):
            print("main test with research theorems added:", r(E["research_h1"]))

    print("\n== 5. Direct use in proofs only")
    D = E["direct"]
    print(f"{D['edges']} dependencies; forward {pct(D['forward_share'])} (blind {pct(D['null_forward_mean'])}, "
          f"p {D['p_less_than_null']:.3f}); {D['users']} users, {pct(D['users_with_younger'])} use a younger one")
    for k, v in D["by_era"].items():
        print(f"  {k:14s} n={v['n']:3d} observed {pct(v['share'])}, blind {pct(v['null'])}")

    print("\n== 6. Independent dates")
    W = E["dating"]
    for k in ["wikipedia lead, linked by Wikidata", "wikipedia lead, any", "wikipedia body", "mactutor"]:
        v = W[k]
        print(f"  {k:36s} n={v['n']:3d} median gap {v['median_gap']:.0f}, within 10y {pct(v['within10'])}, "
              f"within 50y {pct(v['within50'])}, rho with hand dates {v['rho_with_hand']['rho']:.2f}")
    print("large disagreements:", W["disagreements"])
    print("main test, Wikipedia dates swapped in:", r(W["h1_swapped"]))
    print("main test, Wikipedia dates only:", r(W["h1_wikipedia_only"]))
    print("main test, MacTutor dates only:", r(W["h1_mactutor_only"]))


def round2():
    p = RESULTS / "summary_round2.json"
    if not p.exists():
        return
    Q = json.load(open(p, encoding="utf-8"))

    print("\n== Round 2, P1. Where research proofs get their depth")
    s = Q["p1"]["sample"]
    print(f"sample n={s['n']}: chain median {s['chain_median']:.0f}, max {s['chain_max']}; own folder median "
          f"{s['own_folder_median']:.0f}, folder above median {s['own_parent_median']:.0f}, max {s['own_parent_max']}; "
          f"library part max {s['library_max']}")
    for row in s["deepest"]:
        print(f"  {row['title']}: {row['chain_layers']} layers, own folder {row['own_folder']}, above {row['own_parent']}")
    for row in Q["p1"]["research"]:
        print(f"  {row['title']}: {row['chain_layers']:.0f} layers, own {row['own_layers']:.0f}, library {row['library_layers']:.0f}")
    print(f"research library parts above the sample's maximum: {Q['p1']['research_library_above_sample_max']}; "
          f"own parts above the sample's maximum: {Q['p1']['research_own_above_sample_own_max']}")

    print("\n== Round 2, P2. Syllabus")
    S2 = Q["p2"]
    print(f"undergraduate {S2['n_under']} median {S2['median_under']:.0f} vs overview only {S2['n_over']} median "
          f"{S2['median_over']:.0f}; p(shallower) {S2['p_less']:.3f}, p(deeper) {S2['p_greater']:.1e}; through R "
          f"{pct(S2['share_real_under'])} vs {pct(S2['share_real_over'])}")
    for k, v in S2["strata"].items():
        print(f"  {k}: n {v['n_under']} vs {v['n_over']}, median {v['median_under']} vs {v['median_over']}, "
              f"p(shallower) {v['p_less']:.3f}")
    print("  area medians:", S2["areas"])

    print("\n== Round 2, P3. Fresh concepts on R")
    C = Q["p3"]
    print(f"{C['n_fresh']} fresh concepts, {C['n_fresh_real']} through R; Wikipedia years for {C['n_wiki']} "
          f"({C['n_wiki_real']} through R)")
    for k in ["wikipedia", "hand", "hand_high_medium", "pooled"]:
        print(f"  {k}: {r(C[k])}")

    print("\n== Round 2, P4. Library time")
    L = Q["p4"]
    print("counts:", L["counts"], "| renames followed:", L["renames_followed"])
    print(f"R entered {L['real_entered']}; statements through R entered before it: {L['p4a_violations']}")
    for k in ["ported", "history_ported", "all", "history_same", "concepts_ported", "concepts"]:
        print(f"  {k}: {r(L[k])}")
    for k in ["diff_ported", "diff_all"]:
        v = L[k]
        print(f"  {k}: {v['diff']:+.2f} [{v['lo']:+.2f}, {v['hi']:+.2f}], n = {v['n']}")
    for k, v in L["within"].items():
        print(f"  within {k}: {r(v)}")
    print("  median depth by entry year:", {y: v["median"] for y, v in L["by_year"].items()})
    print("  share through R by entry year:", {y: round(v["share_real"], 2) for y, v in L["by_year"].items()})
    print("  first in:", [(f["title"], f["entered"][:7], f["stmt_depth"]) for f in L["first"]])
    if "audit" in L:
        print("  audit against git log -G:", L["audit"])

    print("\n== Round 2, P5. HOL Light")
    H = Q["p5"]
    print("tower:", H["tower"], "| as predicted:", H["p5a"])
    print(f"{H['n_statements']} statements, {H['n_dated']} dated; trend {r(H['trend'])}")
    print("R2:", {k: round(v, 3) for k, v in H["r2"].items()}, f"| through R {pct(H['share_real'])}, median depth {H['median_depth']:.0f}")
    print("vs mathlib:", r(H["vs_mathlib"]), "| vs Metamath:", r(H["vs_metamath"]))
    print("shallowest:", [(x["title"], x["stmt_depth"]) for x in H["shallowest"]])
    print("deepest:", [(x["title"], x["stmt_depth"]) for x in H["deepest"]])


if __name__ == "__main__":
    main()
    extensions()
    round2()
