"""Run the follow-up analyses in order, after run_all.py and the Lean steps in the README.

  variants    number systems taken as given; direct-use dependencies
  dating2     Wikipedia and MacTutor dates (network on first run, cached after)
  textbook    textbook restatements (needs data/derived/textbook_edges.tsv)
  metamath    Metamath set.mm (needs data/raw/metamath/set.mm)
  extensions  statistics, results/summary_extensions.json
  figures     figures/robustness.png, textbook.png, metamath.png and the hero again
Research projects are measured separately with `python research.py <name>`.
"""
import time

if __name__ == "__main__":
    import dating2
    import extensions
    import figures
    import figures_ext
    import metamath
    import textbook
    import variants
    from config import DERIVED

    def run_metamath():
        R = metamath.main()
        hundred, edges = metamath.hundred_table(R)
        hundred.to_csv(DERIVED / "metamath_hundred.csv", index=False)
        edges.to_csv(DERIVED / "metamath_famous_edges.csv", index=False)
        R["theorems"].to_csv(DERIVED / "metamath_theorems.csv", index=False)

    steps = [
        ("variants", variants.main),
        ("dating2", dating2.main),
        ("textbook", textbook.main),
        ("metamath", run_metamath),
        ("extensions", extensions.main),
        ("figures", lambda: (figures.hero(), figures_ext.robustness(), figures_ext.textbook(),
                             figures_ext.metamath())),
    ]
    for name, fn in steps:
        t = time.time()
        print(f"-- {name}")
        fn()
        print(f"   {time.time() - t:.0f} s")
