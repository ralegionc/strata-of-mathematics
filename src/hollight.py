"""Replication in a third library: HOL Light (prediction P5 in results/preregistration.md).

HOL Light is a set of OCaml scripts; definitions are made by calling functions on quoted terms. This
reads the scripts as text, with no OCaml, in HOL Light's own load order (hol_lib.ml, then
Multivariate/make.ml and make_complex.ml, then the remaining Library and 100 files), and rebuilds the
definitional graph:

  new_definition / new_basic_definition / define / new_recursive_definition   constant := term
  new_inductive_definition / new_inductive_set                               constants := rules
  new_(basic_)type_definition "ty" ("abs","rep") th   type and its two maps := the theorem's term
  define_quotient_type "ty" (..) `rel`                type := the relation
  lift_function ... "name" WELLDEF                    constant := the well-definedness theorem's term
  define_type "ty = C1 ... | C2 ..."                  type and constructors := the types named

Symbols are resolved the way HOL Light's parser would at that point in the load: replaying
make_overloadable, overload_interface, override_interface and prioritize_*() commands. So `+` inside
the construction of the positive reals means their addition, and `x / y` after prioritize_real() means
real division. A statement on Wiedijk's page is read with the real (or complex) interface when it
names real or complex material, and with the natural-number interface otherwise.

A constant's depth is one more than the deepest constant or type in its definition. Bound variables
(single letters with optional digits or primes) are never constants. Writes data/derived/hollight_*.
"""
import re
from html import unescape

import pandas as pd

from config import DERIVED, RAW, ROOT

HL = ROOT / "history" / "hol-light"
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")
SYMRUN = re.compile(r"[!#$%&*+\-./:<=>?@^|~\\]+")
VARIABLE = re.compile(r"^[a-z][0-9']*$")
KEYWORDS = {"if", "then", "else", "let", "in", "and", "or", "T", "F"}
LOGIC = {"=", "==>", "/\\", "\\/", "<=>", ",", "IN", "o", "!", "?", "\\", ".", ":", "~"}
DEFFUN = re.compile(r"(new_definition|new_basic_definition|define|new_recursive_definition\s+\w+|"
                    r"new_inductive_definition|new_inductive_set)\b")
TYDEF = re.compile(r'new_(?:basic_)?type_definition\s+"(\w+)"\s*\(\s*"(\w+)"\s*,\s*"(\w+)"\s*\)\s*\(?\s*([\w.]+)?')
PAIR = re.compile(r'"([^"]+)"\s*,\s*`\(?\s*([^`:)\s]+)\s*\)?\s*(?::([^`]*))?`')
REAL_MARKS = {"type:real", "real_of_num", "real_add", "real_mul", "real_le", "real_lt", "real_neg", "real_inv"}


def is_var(t):
    return bool(VARIABLE.match(t))


def strip_comments(t):
    while True:
        new = re.sub(r"\(\*[^()]*?\*\)", " ", t, flags=re.S)
        if new == t:
            return t
        t = new


def quoted_after(text, pos):
    a = text.find("`", pos)
    b = text.find("`", a + 1)
    return (text[a + 1:b], b) if a >= 0 and b > a else (None, pos)


def load_order():
    core = re.findall(r'loads\s+"([^"]+\.ml)"', (HL / "hol_lib.ml").read_text(encoding="latin-1"))
    files = [HL / f for f in core]
    for mk in ("Multivariate/make.ml", "Multivariate/make_complex.ml"):
        p = HL / mk
        if p.exists():
            files += [HL / f for f in re.findall(r'loadt\s+"([^"]+\.ml)"', p.read_text(encoding="latin-1"))]
    seen, out = set(), []
    for f in files + sorted(HL.glob("*.ml")) + sorted((HL / "Library").glob("*.ml")) + \
            sorted((HL / "Multivariate").glob("*.ml")) + sorted((HL / "100").glob("*.ml")):
        if f.exists() and f not in seen:
            seen.add(f)
            out.append(f)
    return out


class Interface:
    def __init__(self):
        self.overloadable, self.cands, self.override, self.priority = set(), {}, {}, None

    def resolve(self, t, context=None):
        """Constant a token stands for: override, then the defining constant's prefix, then the
        priority type, then the most recently declared overload (what type inference usually picks)."""
        if t in self.override:
            return self.override[t]
        if t in self.overloadable and self.cands.get(t):
            cands = self.cands[t]
            if context and "_" in context:
                prefix = context.split("_")[0] + "_"
                for c, ty in cands:
                    if c.startswith(prefix):
                        return c
            if self.priority:
                for c, ty in cands:
                    if ty and re.match(r"\(?\s*" + self.priority + r"", ty.strip()):
                        return c
            return cands[-1][0]
        return t

    def snapshot(self):
        s = Interface()
        s.overloadable, s.cands, s.override, s.priority = set(self.overloadable), dict(self.cands), dict(self.override), self.priority
        return s


class Parser:
    def __init__(self):
        self.infix = set()
        self.defs = {}      # constant -> set of resolved tokens
        self.where = {}
        self.theorems = {}
        self.I = Interface()

    def raw_tokens(self, term):
        toks = {t for t in IDENT.findall(term) if not is_var(t) and t not in KEYWORDS}
        toks |= {r for r in SYMRUN.findall(term) if r not in LOGIC}
        types = set(re.findall(r":\s*(\w+)", term)) | set(re.findall(r"(\w+)\^", term))
        return toks, {f"type:{t}" for t in types}

    def resolved(self, term, I=None, context=None):
        I = I or self.I
        toks, types = self.raw_tokens(term)
        return {I.resolve(t, context) for t in toks} | types

    def lhs_constant(self, term, binding):
        first = re.split(r"/\\", term)[0]
        lhs = re.split(r"<=>|(?<![=<>!])=(?![=>])", first, maxsplit=1)[0]
        while True:
            mb = re.match(r"\s*\(?\s*[!?][^.]{0,200}\.", lhs)
            if not mb:
                break
            lhs = lhs[mb.end():]
        runs = [r for r in SYMRUN.findall(lhs) if r not in LOGIC and r not in {"(", ")"}]
        for r in runs:
            if r in self.I.override or r in self.I.overloadable or r in self.infix:
                c = self.I.resolve(r)
                if c != r or r not in self.I.overloadable:
                    return c
                return binding if binding else r
        toks = [t for t in IDENT.findall(lhs) if not is_var(t) and t not in KEYWORDS]
        for t in toks:
            if t in self.I.override:
                return self.I.override[t]
            if t in self.I.overloadable:
                return binding or t
        if binding and binding.lower() in {t.lower() for t in toks}:
            return next(t for t in toks if t.lower() == binding.lower())
        return toks[0] if toks else None

    def add(self, name, term, src):
        if name and name not in self.defs and name not in LOGIC and not is_var(name):
            self.defs[name] = self.resolved(term or "", context=name) - {name}
            self.where[name] = src

    def interface_events(self, text):
        ev = []
        for m in re.finditer(r'make_overloadable\s+"([^"]+)"', text):
            ev.append((m.start(), "overloadable", m.group(1), None, None))
        for m in re.finditer(r'parse_as_infix\s*\(\s*"([^"]+)"', text):
            ev.append((m.start(), "infix", m.group(1), None, None))
        for m in re.finditer(r'(override|overload)_interface\s*\(\s*"([^"]+)"\s*,\s*`\(?\s*([^`:)\s]+)\s*\)?\s*(?::([^`]*))?`', text):
            ev.append((m.start(), m.group(1), m.group(2), m.group(3), m.group(4)))
        for m in re.finditer(r'do_list\s+(override|overload)_interface\s*\[(.*?)\]', text, re.S):
            for p in PAIR.finditer(m.group(2)):
                ev.append((m.start() + p.start(), m.group(1), p.group(1), p.group(2), p.group(3)))
        for m in re.finditer(r'^\s*prioritize_(\w+)\s*\(\s*\)\s*;;', text, re.M):
            ev.append((m.start(), "priority", m.group(1), None, None))
        return ev

    def apply(self, kind, sym, const, ty):
        I = self.I
        if kind == "overloadable":
            I.overloadable.add(sym)
        elif kind == "infix":
            self.infix.add(sym)
        elif kind == "override":
            I.override[sym] = const
        elif kind == "overload":
            I.override.pop(sym, None)
            I.cands.setdefault(sym, [])
            if (const, ty) not in I.cands[sym]:
                I.cands[sym] = I.cands[sym] + [(const, ty)]
        elif kind == "priority":
            I.priority = sym

    def run(self):
        files = load_order()
        texts = [(f, strip_comments(f.read_text(encoding="latin-1", errors="replace"))) for f in files]
        for _, text in texts:
            for m in re.finditer(r"let\s+(\w+)\s*=\s*prove\s*\(?\s*`", text):
                term, _ = quoted_after(text, m.end() - 1)
                if term:
                    self.theorems.setdefault(m.group(1), term)
        for f, text in texts:
            src = str(f.relative_to(HL))
            events = self.interface_events(text)
            for m in re.finditer(r"let\s+(\w+)(?:\s*,\s*\w+)*\s*=\s*", text):
                events.append((m.start(), "let", m, None, None))
            for m in re.finditer(r'define_quotient_type\s+"(\w+)"\s*\(\s*"(\w+)"\s*,\s*"(\w+)"\s*\)\s*`([^`]*)`', text):
                events.append((m.start(), "quotient", m, None, None))
            for m in re.finditer(r'lift_function\s+\([^)]*\)\s*\([^)]*\)\s*"(\w+)"\s*(\w+)', text):
                events.append((m.start(), "lift", m, None, None))
            for m in re.finditer(r'define_type\s+"(\w+)\s*=([^"]*)"', text):
                events.append((m.start(), "dtype", m, None, None))
            for pos, kind, a, b, c in sorted(events, key=lambda e: e[0]):
                if kind == "let":
                    self.let_binding(text, a, src)
                elif kind == "quotient":
                    ty, ab, rp, rel = a.groups()
                    for x in (f"type:{ty}", ab, rp):
                        self.add(x, rel, src)
                elif kind == "lift":
                    self.add(a.group(1), self.theorems.get(a.group(2), ""), src)
                elif kind == "dtype":
                    ty, body = a.groups()
                    self.add(f"type:{ty}", body, src)
                    for ctor in re.findall(r"(?:^|\|)\s*(\w+)", body):
                        self.add(ctor, f": {ty} " + body, src)
                else:
                    self.apply(kind, a, b, c)
        return self

    def let_binding(self, text, m, src):
        rest = text[m.end():m.end() + 200]
        dm = DEFFUN.match(rest)
        if dm:
            term, _ = quoted_after(text, m.end() + dm.end())
            if not term:
                return
            if dm.group(1).startswith("new_inductive"):
                for clause in re.split(r"/\\", term):
                    concl = re.split(r"==>", clause)[-1]
                    ids = [t for t in IDENT.findall(concl) if t not in KEYWORDS and not is_var(t)]
                    if ids:
                        self.add(self.I.resolve(ids[0]), term, src)
            else:
                self.add(self.lhs_constant(term, m.group(1)), term, src)
            return
        tm = TYDEF.match(rest)
        if tm:
            ty, a, r_, th = tm.groups()
            term = self.theorems.get(th.split(".")[-1]) if th else None
            if term is None:
                term, _ = quoted_after(text, m.end() + tm.end())
                if term and len(term) > 400:
                    term = None
            for c in (f"type:{ty}", a, r_):
                self.add(c, term, src)

    def graph(self):
        deps = {c: {t for t in toks if t in self.defs and t != c} for c, toks in self.defs.items()}
        memo, active = {}, set()

        def d(c):
            if c in memo:
                return memo[c]
            if c in active:
                return 0
            active.add(c)
            v = 1 + max((d(x) for x in sorted(deps[c])), default=0)
            active.discard(c)
            memo[c] = v
            return v

        for c in self.defs:
            d(c)

        def closure(cs):
            out, stack = set(cs), list(cs)
            while stack:
                for v in deps.get(stack.pop(), ()):
                    if v not in out:
                        out.add(v)
                        stack.append(v)
            return out

        return memo, deps, closure


def statements():
    s = unescape((RAW / "hol-light" / "freek_hol.html").read_text(encoding="latin-1"))
    s = re.sub(r"<[^>]+>", "", s)
    pat = re.compile(r"\n\s*(\d+)\.\s+([^\n]+)\n\s*([A-Z0-9_']+)\s*\n(.*?)(?=\n\s*\d+\.\s+[^\n]+\n\s*[A-Z0-9_']+\s*\n|\Z)", re.S)
    return pd.DataFrame([dict(freek=int(m.group(1)), title=m.group(2).strip(), name=m.group(3),
                              statement=m.group(4).strip()) for m in pat.finditer(s)])


COMPLEX_HINT = re.compile(r"\bCx\b|complex|\bii\b|\bRe\b|\bIm\b|cexp|ccos|csin")
REAL_HINT = re.compile(r"&\s*\d|&\s*\(|:real|\breal\b|sqrt|\bpi\b|\bexp\b|\bln\b|\bsin\b|\bcos\b|integral|measure|"
                       r"\bvector|dist\b|\bnorm\b|rational|irrational|\bsum\b")


def main():
    P = Parser().run()
    d, deps, closure = P.graph()
    st = statements()
    rows = []
    for r in st.itertuples():
        I = P.I.snapshot()
        I.priority = "complex" if COMPLEX_HINT.search(r.statement) else (
            "real" if REAL_HINT.search(r.statement) else "num")
        used = {t for t in P.resolved(r.statement, I) if t in P.defs}
        rows.append(dict(freek=r.freek, title=r.title, name=r.name, read_as=I.priority, n_constants=len(used),
                         stmt_depth=max((d[u] for u in used), default=0), uses_real=bool(closure(used) & REAL_MARKS),
                         deepest=max(sorted(used), key=lambda u: d[u]) if used else None))
    t = pd.DataFrame(rows)
    t.to_csv(DERIVED / "hollight_hundred.csv", index=False)
    pd.DataFrame([dict(constant=k, depth=v, file=P.where.get(k)) for k, v in d.items()]).to_csv(
        DERIVED / "hollight_constants.csv", index=False)
    return t, d, deps, P


def chain(c, d, deps):
    """Deepest definitional chain below c, following strictly decreasing depth (so cycles end)."""
    out = [c]
    while True:
        nxt = [x for x in deps.get(c, ()) if d[x] < d[c]]
        if not nxt:
            return out
        c = max(sorted(nxt), key=lambda x: d[x])
        out.append(c)


if __name__ == "__main__":
    t, d, deps, P = main()
    print(len(d), "constants and types;", len(t), "statements")
    for c in ["type:num", "SUC", "type:nadd", "nadd_eq", "type:hreal", "type:real", "real_of_num", "integer",
              "type:int", "rational", "sqrt", "exp", "pi", "vsum", "integral", "measure", "prime", "Cx"]:
        print(f"  {c:14s} {d.get(c)}  {P.where.get(c)}")
    for c in ["type:real", "type:int", "rational"]:
        if c in d:
            print(f"chain {c}:", " > ".join(chain(c, d, deps)))
    print(t.stmt_depth.describe().round(1).to_dict(), "real share", round(t.uses_real.mean(), 2))
    print(t.read_as.value_counts().to_dict())
