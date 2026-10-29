"""Fetch dating evidence for each theorem from Wikidata.

For every Wikidata id in 1000.yaml (linked or not) we pull:
  P575  time of discovery or invention (with precision)
  P61   discoverer or inventor, with their birth (P569) and death (P570)
  P138  named after, kept only when the namesake is a human, with birth and death
  P577  publication date, P571 inception (rare for theorems, kept for completeness)
  enwiki sitelink title

Writes data/raw/wikidata.json (raw bindings) and data/derived/wikidata_dates.csv.
"""
import json
import time

import pandas as pd
import requests
import yaml

from config import DERIVED, RAW, USER_AGENT

ENDPOINT = "https://query.wikidata.org/sparql"

QUERY = """
SELECT ?item ?label ?p575 ?p575prec ?p577 ?p571 ?disc ?discLabel ?db ?dd ?named ?namedLabel ?nb ?nd ?article WHERE {
  VALUES ?item { %s }
  OPTIONAL { ?item rdfs:label ?label FILTER(lang(?label) = "en") }
  OPTIONAL { ?item p:P575/psv:P575 [ wikibase:timeValue ?p575 ; wikibase:timePrecision ?p575prec ] }
  OPTIONAL { ?item wdt:P577 ?p577 }
  OPTIONAL { ?item wdt:P571 ?p571 }
  OPTIONAL { ?item wdt:P61 ?disc . OPTIONAL { ?disc wdt:P569 ?db } OPTIONAL { ?disc wdt:P570 ?dd } }
  OPTIONAL { ?item wdt:P138 ?named . ?named wdt:P31 wd:Q5 .
             OPTIONAL { ?named wdt:P569 ?nb } OPTIONAL { ?named wdt:P570 ?nd } }
  OPTIONAL { ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""


def _year(v):
    """Wikidata xsd:dateTime -> integer year (handles BCE '-0300-01-01T...')."""
    if not v or not isinstance(v, str):
        return None
    neg = v.startswith("-")
    y = int(v.lstrip("-+").split("-")[0])
    return -y if neg else y


def fetch(qids, batch=150):
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"})
    out = []
    for i in range(0, len(qids), batch):
        values = " ".join(f"wd:{q}" for q in qids[i:i + batch])
        for attempt in range(5):
            r = s.post(ENDPOINT, data={"query": QUERY % values}, timeout=120)
            if r.status_code == 200:
                break
            time.sleep(10 * (attempt + 1))
        r.raise_for_status()
        out.extend(r.json()["results"]["bindings"])
        print(f"  {min(i + batch, len(qids))}/{len(qids)}")
        time.sleep(2)
    return out


def summarise(bindings):
    rows = {}
    for b in bindings:
        q = b["item"]["value"].rsplit("/", 1)[1]
        g = lambda k: b.get(k, {}).get("value")  # noqa: E731
        r = rows.setdefault(q, dict(wikidata=q, label=g("label"), p575=set(), p577=set(), p571=set(),
                                    disc={}, named={}, article=None))
        if g("p575"):
            r["p575"].add((_year(g("p575")), int(g("p575prec"))))
        for k in ("p577", "p571"):
            if g(k):
                r[k].add(_year(g(k)))
        if g("disc"):
            r["disc"][g("discLabel")] = (_year(g("db")), _year(g("dd")))
        if g("named"):
            r["named"][g("namedLabel")] = (_year(g("nb")), _year(g("nd")))
        if g("article"):
            r["article"] = g("article")
    recs = []
    for r in rows.values():
        # year-precision or better (precision >= 9) only; decade/century values kept separately
        fine = sorted(y for y, p in r["p575"] if p >= 9 and y is not None)
        coarse = sorted(y for y, p in r["p575"] if p < 9 and y is not None)
        recs.append(dict(
            wikidata=r["wikidata"], label=r["label"],
            p575=fine[0] if fine else None, p575_coarse=coarse[0] if coarse else None,
            p577=min(r["p577"]) if r["p577"] else None, p571=min(r["p571"]) if r["p571"] else None,
            discoverers=json.dumps(r["disc"], ensure_ascii=False),
            named_after=json.dumps(r["named"], ensure_ascii=False),
            article=r["article"]))
    return pd.DataFrame(recs)


if __name__ == "__main__":
    d1000 = yaml.safe_load(open(RAW / "1000.yaml", encoding="utf-8"))
    qids = sorted({str(k).rstrip("X") for k in d1000})
    print(len(qids), "wikidata ids")
    b = fetch(qids)
    json.dump(b, open(RAW / "wikidata.json", "w", encoding="utf-8"))
    df = summarise(b)
    df.to_csv(DERIVED / "wikidata_dates.csv", index=False)
    print(df[["p575", "p577", "p571"]].notna().sum().to_string())
