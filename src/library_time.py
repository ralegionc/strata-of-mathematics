"""When did each theorem and concept enter mathlib? (prediction P4 in results/preregistration.md)

Sources, both cloned under history/ (no checkout needed):
  mathlib3  leanprover-community/mathlib3, 2017-07 to 2023-10, Lean 3
  mathlib4  leanprover-community/mathlib4, 2021-05 to now, Lean 4

Method
  1. Port map. In September 2023 every ported mathlib4 declaration carried an `#align lean3 lean4` line.
     A recent rename is followed back through `@[deprecated] alias old := new` lines at v4.35.0.
  2. Monthly snapshots. At the last commit of each month, `git grep` for declarations of the target
     names (Lean 3 names in mathlib3, current names in mathlib4).
  3. Full names. Each match's full name is its declared name inside the `namespace` blocks open at that
     line, read from the file at that commit; matches inside comments are dropped. The entry date is the
     first month in which a declaration of exactly the target's full name exists. If the same file
     declared the same short name in the months before (a namespace change), the date moves back to the
     first of those months.
  4. A ported declaration takes its first mathlib3 month. One that is not in the port map takes the first
     month its current name appears in mathlib4: a "no later than" date, since it may have been renamed.
  5. Declarations of core Lean (Init, Std) never entered mathlib and are left out. Some, like groups and
     fields, came over from Lean 3's core library in 2020: their date is when mathlib took them over.

Writes data/derived/library_time.csv. The snapshot scans are cached in data/derived/library_scan_*.pkl.
"""
import pickle
import re
import subprocess
from collections import defaultdict
from datetime import date

import pandas as pd

import graph as g
from config import DERIVED, ROOT

H3, H4 = ROOT / "history" / "mathlib3", ROOT / "history" / "mathlib4"
P3 = [".", ":(exclude)test", ":(exclude)docs", ":(exclude)scripts", ":(exclude)counterexamples"]
P4 = ["Mathlib", "Archive"]
DECL3 = r"(?:theorem|lemma|irreducible_def|def|structure|class|inductive|abbreviation|instance)"
DECL4 = r"(?:theorem|lemma|irreducible_def|def|structure|class|inductive|abbrev|instance)"


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.stdout


def month_commits(repo, start, end):
    out = []
    y, m = start
    while (y, m) <= end:
        ny, nm = (y + (m == 12), m % 12 + 1)
        # a bare date means that day at the current time of day to git, so give midnight
        c = git(repo, "rev-list", "-1", f"--before={ny:04d}-{nm:02d}-01 00:00:00", "HEAD").strip()
        if c:
            out.append((date(y, m, 15), c))
        y, m = ny, nm
    return out


def align_map():
    c = git(H4, "rev-list", "-1", "--before=2023-09-01", "HEAD").strip()
    m = {}
    for line in git(H4, "grep", "-h", "^#align ", c, "--", "Mathlib").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2] not in m:
            m[parts[2]] = parts[1]
    aliases = defaultdict(list)
    c35 = git(H4, "rev-parse", "v4.35.0").strip()
    for line in git(H4, "grep", "-h", "-E", r"^@\[deprecated[^]]*\]\s*(protected )?alias ", c35, "--", "Mathlib").splitlines():
        mm = re.search(r"alias\s+(\S+)\s*:=\s*(\S+)", line)
        if mm:
            aliases[mm.group(2)].append(mm.group(1))
    return m, aliases


ALIAS3 = r"alias\s+\S+\s+(?:←|<-)\s+(?:\S+\s+)*?((?:[\w'.]*\.)?(?:{alt}))(?![\w'.])"
ALIAS4 = r"alias\s+((?:[\w'.]*\.)?(?:{alt}))\s*:="


def scan(repo, commits, shorts, decl_kw, pathspec, alias_pat=None):
    """For each snapshot, {short name: [(path, declared token, keyword, line)]} for the given names."""
    shorts = sorted(shorts)
    found = []
    for d, c in commits:
        hits = defaultdict(list)
        for i in range(0, len(shorts), 150):
            alt = "|".join(re.escape(s) for s in shorts[i:i + 150])
            # the name must end the token (`def topological_space.positive_compacts...` does not declare
            # `topological_space`), though Lean 4 may follow it with universes (`def PMF.{u}`)
            pat = rf"^\s*(?:@\[[^\]]*\]\s*)*(?:(?:protected|private|noncomputable|nonrec|irreducible|partial|unsafe|@\[[^\]]*\])\s+)*{decl_kw}\s+((?:[\w'.]*\.)?(?:{alt}))(?![\w']|\.(?!\{{))"
            out = git(repo, "grep", "--threads=4", "-n", "-P", "-o", pat, c, "--", *pathspec)
            if alias_pat:
                apat = alias_pat.replace("{alt}", alt)
                for line in git(repo, "grep", "--threads=4", "-n", "-P", "-o", apat, c, "--", *pathspec).splitlines():
                    _, path, ln, text = line.split(":", 3)
                    m = re.search(apat, text)
                    if m:
                        hits[m.group(1).rsplit(".", 1)[-1]].append((path, m.group(1), "alias", int(ln)))
            for line in out.splitlines():
                _, path, ln, text = line.split(":", 3)
                tok = re.search(rf"({decl_kw})\s+(\S+)", text)
                if tok:
                    full = tok.group(2)
                    hits[full.rsplit(".", 1)[-1]].append((path, full, tok.group(1), int(ln)))
        found.append((d, c, dict(hits)))
        print(f"  {repo.name} {d} {sum(len(v) for v in hits.values())} hits", flush=True)
    return found


def cached_scan(tag, repo, commits, shorts, *args):
    p = DERIVED / f"library_scan_{tag}.pkl"
    key = (tuple(c for _, c in commits), tuple(sorted(shorts)), args)
    if p.exists():
        k, found = pickle.load(open(p, "rb"))
        if k == key:
            return found
    found = scan(repo, commits, shorts, *args)
    pickle.dump((key, found), open(p, "wb"))
    return found


SCOPE = re.compile(r"^\s*(?:noncomputable\s+)?(namespace|section)\s+([^\s-]+)")
END = re.compile(r"^\s*end\s+([^\s-]+)")


def scopes(text):
    """Per line: whether it starts inside a block comment, and the namespace open at it.

    Only named scopes matter: anonymous sections add no namespace, and a bare `end` may close a
    tactic block, so both are ignored. Lean block comments nest."""
    in_comment, ns_at, stack, depth = bytearray(), [], [], 0
    for line in text.split("\n"):
        in_comment.append(depth > 0)
        ns_at.append(".".join(n for k, n in stack if k == "namespace"))
        code, i = [], 0
        while i < len(line):
            if depth == 0 and line.startswith("--", i):
                break
            if line.startswith("/-", i):
                depth, i = depth + 1, i + 2
            elif depth and line.startswith("-/", i):
                depth, i = depth - 1, i + 2
            else:
                if depth == 0:
                    code.append(line[i])
                i += 1
        code = "".join(code)
        m = SCOPE.match(code)
        if m:
            stack.append((m.group(1), m.group(2)))
            continue
        m = END.match(code)
        if m:
            for j in range(len(stack) - 1, -1, -1):
                if stack[j][1] == m.group(1):
                    del stack[j:]
                    break
    return in_comment, ns_at


class Files:
    """Files at a commit, read through one `git cat-file --batch` process, parsed by `scopes`."""

    def __init__(self, repo):
        self.p = subprocess.Popen(["git", "-C", str(repo), "cat-file", "--batch"], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE)
        self.parsed = {}

    def scopes(self, c, path):
        self.p.stdin.write(f"{c}:{path}\n".encode())
        self.p.stdin.flush()
        head = self.p.stdout.readline().split()
        if len(head) < 3 or head[1] != b"blob":
            return None
        data = self.p.stdout.read(int(head[2]))
        self.p.stdout.read(1)
        if head[0] not in self.parsed:
            if len(self.parsed) > 4000:
                self.parsed.clear()
            self.parsed[head[0]] = scopes(data.decode("utf-8", "replace"))
        return self.parsed[head[0]]

    def full_name(self, c, path, ln, tok):
        s = self.scopes(c, path)
        if s is None or ln > len(s[1]) or s[0][ln - 1]:
            return None
        if tok.startswith("_root_."):
            return tok[len("_root_."):]
        return f"{s[1][ln - 1]}.{tok}" if s[1][ln - 1] else tok


KIND = {"theorem": "theorem", "lemma": "theorem", "alias": "theorem", "instance": "instance", "def": "def",
        "abbrev": "def", "abbreviation": "def", "irreducible_def": "def", "structure": "type", "class": "type",
        "inductive": "type"}


def first_month(found, files, target, short):
    """(first snapshot declaring exactly `target`, months moved back through a namespace change).

    A namespace change is a declaration of the same short name and kind, in the same file, that disappears
    in the month `target` appears: `zmod.quadratic_reciprocity` became `legendre_sym.quadratic_reciprocity`.
    The date then follows the old name back. One that stays is a different declaration: the general
    `finite_field.pow_card_sub_one_eq_one` sits beside Fermat's `zmod.pow_card_sub_one_eq_one`."""
    for k, (d, c, hits) in enumerate(found):
        for path, tok, kw, ln in hits.get(short, []):
            if files.full_name(c, path, ln, tok) != target:
                continue
            if k == 0:
                return d, 0

            def names(j):
                cj = found[j][1]
                return {files.full_name(cj, p, l, t) for p, t, kw2, l in found[j][2].get(short, [])
                        if p == path and KIND[kw2] == KIND[kw]} - {None}
            gone = sorted(names(k - 1) - names(k))
            if len(gone) != 1:
                return d, 0
            j = k
            while j > 0 and gone[0] in names(j - 1):
                j -= 1
            return found[j][0], k - j
    return None, 0


def renamed_from(full, month, files):
    """Old full name, if the commit that introduced `full` in this month added a deprecated alias to it.

    Both names in `alias old := new` are read inside the namespace open at that line of the file at that
    commit. An alias whose `new` is `full` wins, since one commit may rename the same short name in several
    namespaces; failing that, one whose `new` is the bare short name (it may resolve through `open`)."""
    short = full.rsplit(".", 1)[-1]
    loose = None
    y, m = month.year, month.month
    since = f"{y - (m == 1):04d}-{(m - 2) % 12 + 1:02d}-01"
    until = f"{y + (m == 12):04d}-{m % 12 + 1:02d}-01"
    for c in git(H4, "log", "--reverse", "--format=%H", f"-S{short}", f"--since={since}", f"--until={until}",
                 "--", *P4).split()[:3]:
        path, ln = None, 0
        for line in git(H4, "show", "--format=", "-U0", c).splitlines():
            if line.startswith("+++ "):
                path = line[len("+++ b/"):] if line.startswith("+++ b/") else None
            elif line.startswith("@@"):
                ln = int(re.search(r"\+(\d+)", line).group(1))
            elif line.startswith("+"):
                mm = re.search(r"alias\s+(\S+)\s*:=\s*(\S+)", line)
                if (path and mm and mm.group(2).rsplit(".", 1)[-1] == short
                        and mm.group(1).rsplit(".", 1)[-1] != short):
                    new = files.full_name(c, path, ln, mm.group(2))
                    old = files.full_name(c, path, ln, mm.group(1))
                    if old and full in (new, mm.group(2)):
                        return old
                    if old and mm.group(2) == short and loose is None:
                        loose = old
                ln += 1
    return loose


def date_rows(T, f3, f4, files):
    d3, d4, back = [], [], []
    for r in T.itertuples():
        a, b3 = first_month(f3, files[3], r.lean3, r.short3) if isinstance(r.lean3, str) else (None, 0)
        b, b4 = first_month(f4, files[4], r.full4, r.short4)
        d3.append(a)
        d4.append(b)
        back.append(b3 if a is not None else b4)
    return d3, d4, back


def main():
    df = g.nodes()
    idx = g.name_index()
    th = pd.read_csv(DERIVED / "theorems.csv")
    cc = pd.read_csv(DERIVED / "concepts.csv")
    targets = [dict(kind="theorem", key=r.key, decl=r.decl) for r in th.itertuples()]
    targets += [dict(kind="concept", key="concept:" + r.decl, decl=r.decl) for r in cc.itertuples()]
    amap, aliases = align_map()
    rows = []
    for t in targets:
        mod = df.module.iat[int(idx[t["decl"]])]
        core = mod.startswith(("Init", "Std", "Lean"))
        names = [t["decl"]] + aliases.get(t["decl"], [])
        l3 = next((amap[n] for n in names if n in amap), None)
        rows.append(dict(**t, module=mod, core=core, lean3=l3))
    T = pd.DataFrame(rows)
    T["short3"] = T.lean3.map(lambda s: s.rsplit(".", 1)[-1] if isinstance(s, str) else None)
    T["ns3"] = T.lean3.map(lambda s: s.rsplit(".", 1)[0] if isinstance(s, str) and "." in s else "")
    T["short4"] = T.decl.map(lambda s: s.rsplit(".", 1)[-1])
    T["ns4"] = T.decl.map(lambda s: s.rsplit(".", 1)[0] if "." in s else "")
    T["full4"] = T.decl
    c3 = month_commits(H3, (2017, 7), (2023, 9))
    c4 = month_commits(H4, (2021, 5), (2026, 9))
    files = {3: Files(H3), 4: Files(H4)}
    f3 = cached_scan("mathlib3", H3, c3, set(T.short3.dropna()), DECL3, P3, ALIAS3)
    f4 = cached_scan("mathlib4", H4, c4, set(T.short4), DECL4, P4, ALIAS4)
    d3, d4, back = date_rows(T, f3, f4, files)
    T["renamed_from"] = None
    # follow renames made after the port, up to three hops
    for hop in range(3):
        todo = [i for i, (a, b4) in enumerate(zip(d3, d4))
                if a is None and b4 is not None and b4 >= date(2023, 8, 1) and not T.core.iat[i]]
        changed = []
        for i in todo:
            old = renamed_from(T.full4.iat[i], d4[i], files[4])
            if old:
                T.at[T.index[i], "renamed_from"] = old if T.renamed_from.iat[i] is None else T.renamed_from.iat[i] + " <- " + old
                l3 = amap.get(old) or next((amap[n] for n in aliases.get(old, []) if n in amap), None)
                if l3:
                    T.at[T.index[i], "lean3"] = l3
                    T.at[T.index[i], "short3"] = l3.rsplit(".", 1)[-1]
                    T.at[T.index[i], "ns3"] = l3.rsplit(".", 1)[0] if "." in l3 else ""
                T.at[T.index[i], "full4"] = old
                T.at[T.index[i], "short4"] = old.rsplit(".", 1)[-1]
                T.at[T.index[i], "ns4"] = old.rsplit(".", 1)[0] if "." in old else ""
                changed.append(i)
        print(f"rename hop {hop + 1}: {len(changed)} followed", flush=True)
        if not changed:
            break
        sub = T.iloc[changed]
        f3n = cached_scan(f"mathlib3_hop{hop + 1}", H3, c3, set(sub.short3.dropna()), DECL3, P3, ALIAS3)
        f4n = cached_scan(f"mathlib4_hop{hop + 1}", H4, c4, set(sub.short4), DECL4, P4, ALIAS4)
        n3, n4, _ = date_rows(sub, f3n, f4n, files)
        for j, i in enumerate(changed):
            if n3[j] is not None:
                d3[i] = n3[j] if d3[i] is None else min(d3[i], n3[j])
            if n4[j] is not None and (d4[i] is None or n4[j] < d4[i]):
                d4[i] = n4[j]
    T["first_mathlib3"], T["first_mathlib4"], T["months_back"] = d3, d4, back
    T["entered"] = [a if a is not None else b for a, b in zip(d3, d4)]
    T["how"] = ["core" if r.core else ("mathlib3" if a is not None else ("mathlib4" if b is not None else "not found"))
                for r, a, b in zip(T.itertuples(), d3, d4)]
    T.loc[T.core, "entered"] = None
    T.to_csv(DERIVED / "library_time.csv", index=False)
    return T


if __name__ == "__main__":
    T = main()
    print(T.how.value_counts().to_string())
    print(T.groupby("kind").how.value_counts().to_string())
