"""Two automatic, independent dating sources, used to audit the hand-made dates.

Wikipedia  For each theorem's English article (via Wikidata, or a search for Wiedijk-list titles),
           the earliest year that appears in a sentence saying something was proved, stated,
           discovered, conjectured, published or introduced. Lifespans in brackets are removed
           first. Centuries count as their midpoint ("3rd century BC" = 250 BC).
MacTutor   The St Andrews MacTutor chronology (39 pages, about 2,000 dated events). A theorem
           matches an event when the event contains the theorem's name, or names its namesake
           together with a word from the theorem's topic. The earliest matching year counts.

Neither source sees the hand dates. Writes data/derived/dates_independent.csv.
"""
import json
import re
import time
from html import unescape

import pandas as pd
import requests

from config import DERIVED, LABELS, RAW, USER_AGENT

MT = RAW / "mactutor"
WIKI_CACHE = RAW / "wikipedia_extracts.json"
TRIGGER = re.compile(r"\b(prov(ed|en|es|e|ing)|proofs?|stated?|statement|discover\w*|conjectur\w*|publish\w*|"
                     r"formulat\w*|introduc\w*|first|announc\w*|establish\w*|demonstrat\w*|obtained|gave)\b", re.I)
LIFESPAN = re.compile(r"\((?:[^()]*?\d{3,4}\s*(?:BC|BCE)?\s*[\u2013-]\s*(?:c\.\s*)?\d{2,4}[^()]*?|born[^()]*|died[^()]*|"
                      r"fl\.[^()]*|c\.\s*\d+\s*[\u2013-][^()]*)\)", re.I)
YEAR = re.compile(r"\b(\d{1,4})\s*(BC|BCE|AD|CE)\b|\b(1[0-9]{3}|20[0-2][0-9])\b(?!\s*[\u2013-]\s*\d)")
CENTURY = re.compile(r"\b(\d{1,2})(st|nd|rd|th)[\s-]+century\s*(BC|BCE)?", re.I)
STOP = {"theorem", "theorems", "the", "of", "a", "an", "on", "for", "in", "and", "to", "s", "lemma", "formula",
        "formulas", "law", "rule", "problem", "principle", "identity", "postulate", "inequality", "general",
        "solutions", "solution", "equation", "number", "numbers", "set", "sets", "series", "sum", "two"}


# ---------------- MacTutor ----------------

def mactutor_events():
    ev = []
    for i in range(1, 40):
        s = (MT / f"chron_{i}.html").read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"<h4>\s*(-?\d+)\s*</h4>\s*<ul>(.*?)</ul>", s, re.S):
            year = int(m.group(1))
            for li in re.findall(r"<li>(.*?)</li>", m.group(2), re.S):
                people = re.findall(r"Biographies/([A-Za-z_'-]+)/popup", li)
                text = unescape(re.sub(r"<[^>]+>", "", li))
                ev.append(dict(year=year, text=re.sub(r"\s+", " ", text).strip(), people=people))
    return pd.DataFrame(ev)


def norm(s):
    s = s.lower().replace("\u2019", "'").replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"[^a-z0-9' -]", " ", s)


def surnames(title, named_after):
    names = set()
    for full in named_after:
        if full and not full.startswith("Q"):
            names.add(full.split()[-1].lower())
    for m in re.finditer(r"([A-Z][a-zà-ÿ]+(?:[-\u2013][A-Z][a-zà-ÿ]+)*)(?:'s|\u2019s)?", title):
        for part in re.split(r"[-\u2013]", m.group(1)):
            if part.lower() not in STOP and part not in {"The", "Fundamental", "Solutions", "Lebesgue Measure"}:
                if re.search(r"'s|\u2019s|[-\u2013]", title) or part.lower() in {n.lower() for n in names}:
                    names.add(part.lower())
    return names


def match_mactutor(title, named_after, ev):
    t = norm(title)
    phrase = t.strip()
    names = surnames(title, named_after)
    topic = {w for w in re.findall(r"[a-z]+", t) if w not in STOP and w not in names and len(w) > 2}
    hits = []
    for r in ev.itertuples():
        txt = norm(r.text)
        if phrase and len(phrase) > 8 and phrase in txt:
            hits.append(r)
            continue
        if names:
            ppl = {p.split("_")[-1].lower() for p in r.people} | set(re.findall(r"[a-z]+", txt))
            if names & ppl and topic and topic & set(re.findall(r"[a-z]+", txt)):
                hits.append(r)
    if not hits:
        return None, None
    best = min(hits, key=lambda r: r.year)
    return best.year, best.text


# ---------------- Wikipedia ----------------

def wiki_extracts(titles):
    cache = json.load(open(WIKI_CACHE, encoding="utf-8")) if WIKI_CACHE.exists() else {}
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    for t in titles:
        if t in cache:
            continue
        for attempt in range(5):
            r = s.get("https://en.wikipedia.org/w/api.php", params=dict(
                action="query", prop="extracts", explaintext=1, redirects=1, titles=t, format="json"), timeout=60)
            if r.status_code == 200:
                break
            time.sleep(5 * (attempt + 1))
        pages = r.json().get("query", {}).get("pages", {})
        cache[t] = next(iter(pages.values())).get("extract", "") if pages else ""
        time.sleep(0.7)
    json.dump(cache, open(WIKI_CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    return cache


def wiki_search(q, s):
    r = s.get("https://en.wikipedia.org/w/api.php", params=dict(
        action="query", list="search", srsearch=q, srlimit=1, format="json"), timeout=60)
    hits = r.json().get("query", {}).get("search", [])
    time.sleep(0.7)
    return hits[0]["title"] if hits else None


def years_in(sentence):
    s = LIFESPAN.sub(" ", sentence)
    out = []
    for m in YEAR.finditer(s):
        if m.group(1):
            y = int(m.group(1))
            out.append(-y if m.group(2).upper().startswith("B") else y)
        else:
            out.append(int(m.group(3)))
    for m in CENTURY.finditer(s):
        c = int(m.group(1))
        out.append(-(c * 100 - 50) if m.group(3) else c * 100 - 50)
    return [y for y in out if -3000 <= y <= 2026]


MATHWORD = re.compile(r"\b(theorem|result|formula|identity|inequality|law|lemma|conjecture|proof|series|problem|"
                      r"rule|postulate|principle)\b", re.I)


def clean(text):
    """Drop rendered formulas: lines carrying LaTeX, and the runs of short lines around them."""
    keep = []
    for line in text.split("\n"):
        ls = line.strip()
        if "\\displaystyle" in ls or (ls and len(ls) < 30 and not ls.startswith("==") and not ls.endswith(".")):
            continue
        keep.append(line)
    return re.sub(r"\s+", " ", " ".join(keep))


def wiki_year(text, title, names):
    """(year, sentence, where): the first qualifying year in the lead section, else the earliest in the body."""
    text = re.split(r"\n==\s*(See also|References|Notes|Further reading|External links)\s*==", text)[0]
    parts = re.split(r"\n==[^=\n]+==\n", text, maxsplit=1)
    words = {w for w in re.findall(r"[a-z]+", norm(title)) if w not in STOP and len(w) > 3} | set(names)

    def ok(sent):
        low = sent.lower()
        return TRIGGER.search(sent) and (MATHWORD.search(sent) or any(w in low for w in words))

    def years(sent):
        return [y for y in years_in(sent) if y <= 2025]

    for sent in re.split(r"(?<=[.!?])\s+", clean(parts[0])):
        if ok(sent) and years(sent):
            return min(years(sent)), sent.strip()[:300], "lead"
    best = None
    body = clean(parts[1]) if len(parts) > 1 else ""
    for sent in re.split(r"(?<=[.!?])\s+", body):
        if ok(sent) and years(sent) and (best is None or min(years(sent)) < best[0]):
            best = (min(years(sent)), sent.strip()[:300], "body")
    return best or (None, None, None)


def main():
    t = pd.read_csv(DERIVED / "targets.csv")
    w = pd.read_csv(DERIVED / "wikidata_dates.csv").set_index("wikidata")
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    titles = {}
    search_cache = RAW / "wikipedia_search.json"
    found = json.load(open(search_cache, encoding="utf-8")) if search_cache.exists() else {}
    for r in t.itertuples():
        art = w.article.get(r.wikidata) if isinstance(r.wikidata, str) and r.wikidata in w.index else None
        if isinstance(art, str):
            titles[r.key] = (requests.utils.unquote(art.rsplit("/", 1)[1]).replace("_", " "), "wikidata")
        else:
            if r.title not in found:
                found[r.title] = wiki_search(r.title, s)
            if found[r.title]:
                titles[r.key] = (found[r.title], "search")
    json.dump(found, open(search_cache, "w", encoding="utf-8"), ensure_ascii=False)
    ext = wiki_extracts(sorted({v[0] for v in titles.values()}))
    ev = mactutor_events()
    rows = []
    for r in t.itertuples():
        named = []
        if isinstance(r.wikidata, str) and r.wikidata in w.index:
            named = list(json.loads(w.loc[r.wikidata, "named_after"])) + list(json.loads(w.loc[r.wikidata, "discoverers"]))
        art, how = titles.get(r.key, (None, None))
        wy, ws, wh = wiki_year(ext.get(art, ""), r.title, surnames(r.title, named)) if art else (None, None, None)
        my, mt = match_mactutor(r.title, named, ev)
        rows.append(dict(key=r.key, title=r.title, wiki_article=art, wiki_how=how, wiki_year=wy, wiki_where=wh,
                         wiki_sentence=ws, mactutor_year=my, mactutor_event=mt))
    out = pd.DataFrame(rows)
    out.to_csv(DERIVED / "dates_independent.csv", index=False)
    ev.to_csv(DERIVED / "mactutor_events.csv", index=False)
    return out


if __name__ == "__main__":
    out = main()
    hd = pd.read_csv(LABELS / "hand_dates.csv")
    x = out.merge(hd, on="key")
    print(out[["wiki_year", "mactutor_year"]].notna().sum().to_string())
    for col in ["wiki_year", "mactutor_year"]:
        y = x.dropna(subset=[col, "year_stated"])
        gap = pd.concat([(y[col] - y.year_stated).abs(), (y[col] - y.year_proved).abs()], axis=1).min(axis=1)
        print(col, len(y), "median gap", gap.median(), "within 10y", round((gap <= 10).mean(), 2),
              "within 50y", round((gap <= 50).mean(), 2))
