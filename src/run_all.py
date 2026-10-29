"""Run the Python pipeline in order (after the Lean extraction, see README).

  targets   which declarations stand for which famous theorems
  wikidata  dating evidence from Wikidata (network)
  measures  statement and proof depth, famous-theorem dependencies
  dating    dates and their audit
  concepts  depth of the dated core concepts
  chains    deepest definition chains for labels and the web page
  analysis  every statistic, results/summary.json
  figures   figures/*.png
  webpage   docs/index.html
"""
import importlib
import sys
import time

STEPS = ["targets", "wikidata", "measures", "dating", "concepts", "chains", "analysis", "figures", "webpage"]

if __name__ == "__main__":
    skip = set(sys.argv[1:])  # e.g. `python run_all.py wikidata` to reuse the cached Wikidata pull
    for s in STEPS:
        if s in skip:
            print(f"-- {s}: skipped")
            continue
        t = time.time()
        print(f"-- {s}")
        mod = importlib.import_module(s)
        if s == "targets":
            mod.load().to_csv(mod.DERIVED / "targets.csv", index=False)
        elif s == "wikidata":
            import json

            import yaml
            qids = sorted({str(k).rstrip("X") for k in yaml.safe_load(open(mod.RAW / "1000.yaml", encoding="utf-8"))})
            b = mod.fetch(qids)
            json.dump(b, open(mod.RAW / "wikidata.json", "w", encoding="utf-8"))
            mod.summarise(b).to_csv(mod.DERIVED / "wikidata_dates.csv", index=False)
        elif s == "measures":
            import numpy as np
            import pandas as pd
            m, fe, hs, hp = mod.compute(pd.read_csv(mod.DERIVED / "targets.csv"))
            m.to_csv(mod.DERIVED / "measures.csv", index=False)
            fe.to_csv(mod.DERIVED / "famous_edges.csv", index=False)
            np.save(mod.DERIVED / "h_stmt.npy", hs)
            np.save(mod.DERIVED / "h_proof.npy", hp)
        elif s == "dating":
            d = mod.load_dates()
            d.to_csv(mod.DERIVED / "dates.csv", index=False)
            mod.audit(d).to_csv(mod.RESULTS / "dating_audit.csv", index=False)
        elif s == "figures":
            for f in (mod.hero, mod.cliff, mod.tangle, mod.arrow, mod.proofs):
                f()
        else:
            mod.main()
        print(f"   {time.time() - t:.0f} s")
