"""Statement and proof measures for every target theorem.

statement depth  longest chain of concepts below the constants named in the statement
statement size   number of distinct concepts needed to read the statement
proof depth      longest chain of concepts and named theorems below the declaration
proof size       number of distinct concepts and named theorems the proof rests on

The representative declaration of a theorem is the first theorem listed in mathlib's docs.
Writes data/derived/measures.csv and data/derived/famous_edges.csv (which target theorems
each target's proof uses).
"""
import numpy as np
import pandas as pd

import graph as g
from config import DERIVED

FIELD_OF_TOP = {
    "Algebra": "Algebra", "GroupTheory": "Algebra", "RingTheory": "Algebra",
    "FieldTheory": "Algebra", "LinearAlgebra": "Algebra", "RepresentationTheory": "Algebra",
    "CategoryTheory": "Algebra", "AlgebraicGeometry": "Algebra",
    "NumberTheory": "Number theory",
    "Analysis": "Analysis", "Dynamics": "Analysis",
    "Topology": "Topology",
    "MeasureTheory": "Measure and probability", "Probability": "Measure and probability",
    "Combinatorics": "Combinatorics",
    "Geometry": "Geometry",
    "Logic": "Logic and foundations", "SetTheory": "Logic and foundations",
    "ModelTheory": "Logic and foundations", "Computability": "Logic and foundations",
    "Order": "Logic and foundations",
}
# Archive files and Mathlib.Data sub-areas need a hand assignment
FIELD_OF_MODULE = {
    "Archive.Wiedijk100Theorems.SumOfPrimeReciprocalsDiverges": "Number theory",
    "Archive.Wiedijk100Theorems.SolutionOfCubicQuartic": "Algebra",
    "Archive.Wiedijk100Theorems.Konigsberg": "Combinatorics",
    "Archive.Wiedijk100Theorems.PerfectNumbers": "Number theory",
    "Archive.Wiedijk100Theorems.InverseTriangleSum": "Analysis",
    "Archive.Wiedijk100Theorems.HeronsFormula": "Geometry",
    "Archive.Wiedijk100Theorems.FriendshipGraphs": "Combinatorics",
    "Archive.Wiedijk100Theorems.CubingACube": "Geometry",
    "Archive.Wiedijk100Theorems.BuffonsNeedle": "Measure and probability",
    "Archive.Wiedijk100Theorems.BirthdayProblem": "Combinatorics",
    "Archive.Wiedijk100Theorems.BallotProblem": "Measure and probability",
    "Archive.Wiedijk100Theorems.AscendingDescendingSequences": "Combinatorics",
    "Archive.Wiedijk100Theorems.AreaOfACircle": "Measure and probability",
    "Archive.Wiedijk100Theorems.AbelRuffini": "Algebra",
}
DATA_FIELD = [("Mathlib.Data.Nat", "Number theory"), ("Mathlib.Data.Int", "Number theory"),
              ("Mathlib.Data.ZMod", "Number theory"), ("Mathlib.Data.Real", "Analysis"),
              ("Mathlib.Data.Complex", "Analysis"), ("Mathlib.Data.Matrix", "Algebra"),
              ("Mathlib.Data.Polynomial", "Algebra"), ("Mathlib.Data.Fintype", "Combinatorics"),
              ("Mathlib.Data.Finset", "Combinatorics"), ("Mathlib.Data.Set", "Logic and foundations"),
              ("Mathlib.Data.Rat", "Number theory"), ("Mathlib.Data.Sym", "Combinatorics"),
              ("Mathlib.Data.Fin", "Combinatorics"), ("Mathlib.Data.Nat.Choose", "Combinatorics")]


def field_of(module):
    if module in FIELD_OF_MODULE:
        return FIELD_OF_MODULE[module]
    best = None
    for prefix, f in DATA_FIELD:
        if module.startswith(prefix) and (best is None or len(prefix) > len(best[0])):
            best = (prefix, f)
    if best:
        return best[1]
    parts = module.split(".")
    if len(parts) > 1 and parts[0] == "Mathlib":
        return FIELD_OF_TOP.get(parts[1], "Other")
    return "Other"


# landmark concepts: does a statement's closure pass through them?
LANDMARKS = {"real": "Real", "complex": "Complex", "measure": "MeasureTheory.Measure",
             "topology": "TopologicalSpace", "inner": "InnerProductSpace", "rat": "Rat",
             "field": "Field", "set": "Set"}


def compute(targets):
    df = g.nodes()
    idx = g.name_index()
    is_thm = df.is_thm.to_numpy()
    is_meta = df.is_meta.to_numpy()
    conc = df.is_concept.to_numpy()
    named = df.is_named_thm.to_numpy()
    Gs, Gp = g.statement_graph(), g.proof_graph()
    print("heights (statement graph) ...")
    hs = g.heights(Gs, conc)
    print("heights (proof graph) ...")
    hp = g.heights(Gp, conc | named)
    et, ev = g.edges_type(), g.edges_value()

    def stmt_sources(i, statement_only):
        src = g.out_neighbours(ev if statement_only else et, i)
        return src[~is_thm[src] & ~is_meta[src]]

    lm = {k: int(idx[v]) for k, v in LANDMARKS.items()}
    rows, reach_p = [], {}
    for r in targets.itertuples():
        decls = [d for d in r.decls.split() if d in idx.index]
        if not decls:
            continue
        # representative: the first listed declaration that is a theorem (some lists name a
        # supporting definition first, e.g. `fourierCoeff` before the Fourier series theorem)
        thm_first = [d for d in decls if is_thm[int(idx[d])]]
        if thm_first and not r.statement_only:
            decls = thm_first + [d for d in decls if d not in thm_first]
        per = []
        for d in decls:
            i = int(idx[d])
            src = stmt_sources(i, r.statement_only)
            sd = int(hs[src].max()) if len(src) else 0
            rs = g.reach(Gs, src) if len(src) else np.zeros(len(df), bool)
            ss = int(conc[rs].sum())
            if r.statement_only:
                pd_, ps = np.nan, np.nan
            else:
                rp = g.reach(Gp, [i])
                rp[i] = False
                reach_p.setdefault(r.key, rp)
                pd_ = int(hp[i] - (1 if named[i] or conc[i] else 0))
                ps = int((conc | named)[rp].sum())
            per.append(dict(decl=d, stmt_depth=sd, stmt_size=ss, proof_depth=pd_, proof_size=ps,
                            **{f"uses_{k}": bool(rs[v]) for k, v in lm.items()}))
        first = per[0]
        i0 = int(idx[decls[0]])
        node = df.iloc[i0]
        rows.append(dict(
            key=r.key, title=r.title, source=r.source, wikidata=r.wikidata, decl=decls[0],
            n_decls=len(decls), kind=node.kind, module=node.module, field=field_of(node.module),
            statement_only=r.statement_only,
            nbinders=int(node.nbinders), ninst=int(node.ninst), nsort=int(node.nsort),
            stmt_depth=first["stmt_depth"], stmt_size=first["stmt_size"],
            proof_depth=first["proof_depth"], proof_size=first["proof_size"],
            **{k: v for k, v in first.items() if k.startswith("uses_")},
            stmt_depth_min=min(p["stmt_depth"] for p in per),
            stmt_size_min=min(p["stmt_size"] for p in per)))
    m = pd.DataFrame(rows)

    # which famous theorems does each famous proof use?
    key_of = {}
    for r in m.itertuples():
        for d in targets.set_index("key").loc[r.key, "decls"].split():
            if d in idx.index:
                key_of.setdefault(int(idx[d]), r.key)
    edges = []
    for a, rp in reach_p.items():
        for i, b in key_of.items():
            if b != a and rp[i]:
                edges.append((a, b))
    fe = pd.DataFrame(edges, columns=["user", "used"]).drop_duplicates()
    return m, fe, hs, hp


if __name__ == "__main__":
    t = pd.read_csv(DERIVED / "targets.csv")
    m, fe, hs, hp = compute(t)
    m.to_csv(DERIVED / "measures.csv", index=False)
    fe.to_csv(DERIVED / "famous_edges.csv", index=False)
    np.save(DERIVED / "h_stmt.npy", hs)
    np.save(DERIVED / "h_proof.npy", hp)
    print(m[["stmt_depth", "stmt_size", "proof_depth", "proof_size"]].describe().round(1).to_string())
    print(m.field.value_counts().to_string())
    print(len(fe), "famous-theorem dependencies")
