"""Interactive page: docs/index.html (self-contained, no external scripts).

Every theorem is a point (year, statement depth). Hover or tap shows its Lean name, the deepest chain of
definitions under its statement, and the famous theorems its proof rests on; younger ones are amber.
A switch shows the dated concepts instead.
"""
import json

import numpy as np
import pandas as pd

from config import DERIVED, DOCS, RESULTS
from figures import FIELDS


def payload():
    x = pd.read_csv(DERIVED / "theorems.csv")
    x = x.dropna(subset=["year_stated"])
    chains = json.load(open(DERIVED / "chains.json", encoding="utf-8"))
    fe = pd.read_csv(DERIVED / "famous_edges.csv")
    red = pd.read_csv(DERIVED / "famous_edges_reduced.csv")
    deps = fe.groupby("user").used.apply(list).to_dict()
    direct = red.groupby("user").used.apply(list).to_dict()
    th = []
    for r in x.itertuples():
        th.append(dict(
            k=r.key, t=r.title, ys=int(r.year_stated), yp=int(r.year_proved), f=r.field, d=r.decl,
            sd=int(r.stmt_depth), ss=int(r.stmt_size),
            pd=None if np.isnan(r.proof_depth) else int(r.proof_depth),
            ps=None if np.isnan(r.proof_size) else int(r.proof_size),
            so=bool(r.statement_only), re=bool(r.uses_real), c=r.confidence,
            ch=chains.get(r.key, []), dep=[k for k in deps.get(r.key, []) if k in set(x.key)],
            dir=[k for k in direct.get(r.key, []) if k in set(x.key)]))
    c = pd.read_csv(DERIVED / "concepts.csv")
    co = [dict(k="concept:" + r.decl, t=r.label, ys=int(r.year), f=r.field, d=r.decl, sd=int(r.depth),
               ss=int(r.size), re=bool(r.uses_real), c=r.confidence,
               ch=chains.get("concept:" + r.decl, [])) for r in c.itertuples()]
    S = json.load(open(RESULTS / "summary.json"))
    rs = []
    rp = DERIVED / "research.csv"
    if rp.exists():
        for r in pd.read_csv(rp).itertuples():
            rs.append(dict(k="r:" + r.name, t=r.title, ys=int(r.year_stated), yp=int(r.year_proved), f=r.field,
                           d=r.decl, sd=int(r.stmt_depth + S["real_depth"] - r.ref_Real), ss=int(r.stmt_size),
                           pd=int(r.proof_depth),
                           ps=int(r.proof_size), so=False, re=bool(r.uses_real), c="research", ch=json.loads(r.chain),
                           dep=[], dir=[], rs=True, sorry=bool(r.uses_sorry), note=r.note))
    return dict(theorems=th + rs, concepts=co, fields=FIELDS, real=S["real_depth"],
                r2=S["r2"], n=len(th), nres=len(rs))


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Strata of Mathematics</title>
<style>
:root{--bg:#0a0d12;--panel:#10151d;--text:#e8e4da;--subtle:#8a8f98;--grid:#1c222b;--amber:#f6b73c;--blue:#5b86b5;--fwd:#ffc56b}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 "DejaVu Sans",system-ui,-apple-system,"Segoe UI",sans-serif}
header{padding:24px 24px 6px;max-width:1400px;margin:0 auto}
h1{margin:0 0 6px;font-size:30px;letter-spacing:.2px}
header p{margin:0;color:var(--subtle);max-width:980px}
.bar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:12px 24px;max-width:1400px;margin:0 auto}
.bar button{background:var(--panel);color:var(--text);border:1px solid var(--grid);border-radius:6px;padding:6px 12px;cursor:pointer;font:inherit}
.bar button.on{border-color:var(--amber);color:var(--amber)}
.bar input{background:var(--panel);color:var(--text);border:1px solid var(--grid);border-radius:6px;padding:6px 10px;font:inherit;min-width:220px}
.wrap{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:16px;max-width:1400px;margin:0 auto;padding:0 24px 24px}
@media (max-width:900px){.wrap{grid-template-columns:1fr}}
#plot{width:100%;height:auto;display:block;background:var(--bg);touch-action:manipulation}
aside{background:var(--panel);border:1px solid var(--grid);border-radius:10px;padding:16px;min-height:300px;align-self:start;position:sticky;top:12px;max-height:calc(100vh - 24px);overflow:auto}
aside h2{margin:0 0 4px;font-size:18px}
aside .meta{color:var(--subtle);font-size:12.5px;margin-bottom:10px}
aside code{font-size:12px;color:#c9d4e3;word-break:break-all}
.nums{display:grid;grid-template-columns:repeat(2,1fr);gap:6px 12px;margin:10px 0}
.nums div{font-size:12.5px;color:var(--subtle)} .nums b{display:block;color:var(--text);font-size:16px}
.chain{list-style:none;margin:6px 0 0;padding:0;font-size:12px}
.chain li{display:flex;gap:8px;padding:1px 0} .chain li span:first-child{color:var(--subtle);min-width:22px;text-align:right}
.chain li.real span:last-child{color:var(--amber)}
.deps{font-size:12.5px;margin-top:6px} .deps .y{color:var(--fwd)} .deps .o{color:#9fb7d4}
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:12px;color:var(--subtle);padding:0 24px;max-width:1400px;margin:0 auto 6px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}
footer{color:var(--subtle);font-size:12px;max-width:1400px;margin:0 auto;padding:0 24px 30px}
a{color:#9fb7d4}
</style>
</head>
<body>
<header>
<h1>Strata of Mathematics</h1>
<p>__N__ famous theorems in Lean's mathlib by the year they were first stated and the depth of their statements:
the longest chain of definitions under them. Hover or tap a point. Depth follows the real numbers
(the glowing line), not the calendar.</p>
</header>
<div class="bar">
<button id="bt" class="on">Theorems</button><button id="bc">Concepts</button>
<input id="q" placeholder="Search, e.g. Pythagorean" aria-label="Search">
<span id="hint" style="color:var(--subtle);font-size:12.5px"></span>
</div>
<div class="legend" id="legend"></div>
<div class="wrap">
<svg id="plot" viewBox="0 0 1000 640" role="img" aria-label="Statement depth against year"></svg>
<aside id="info"><h2>Pick a point</h2><div class="meta">The panel shows what the statement stands on, and which famous theorems its mathlib proof uses.</div></aside>
</div>
<footer>Data: mathlib v4.35.0, docs/1000.yaml and docs/100.yaml. Dates assigned by hand and audited against Wikidata.
Year axis compressed before 1500. Source and method: README.</footer>
<script>
const D = __DATA__;
const svg = document.getElementById('plot'), info = document.getElementById('info');
const W = 1000, H = 640, M = {l: 58, r: 22, t: 14, b: 42};
const X0 = -650, XB = 1500, X1 = 2008, SPLIT = 0.22;
const xm = y => M.l + (W - M.l - M.r) * (y < XB ? SPLIT * (y - X0) / (XB - X0) : SPLIT + (1 - SPLIT) * (y - XB) / (X1 - XB));
const YMAX = 63, ym = d => M.t + (H - M.t - M.b) * (d + 1.5) / (YMAX + 1.5);
const NS = 'http://www.w3.org/2000/svg';
const el = (t, a, p) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); (p || svg).appendChild(e); return e; };
const yl = y => y < 0 ? (-y) + ' BC' : (y === 1 ? 'AD 1' : '' + y);
let mode = 'theorems', pinned = null;
const byKey = {}; D.theorems.forEach(t => byKey[t.k] = t);

function legend() {
  const L = document.getElementById('legend'); L.innerHTML = '';
  for (const [f, c] of Object.entries(D.fields)) L.insertAdjacentHTML('beforeend', `<span><i style="background:${c}"></i>${f}</span>`);
  L.insertAdjacentHTML('beforeend', '<span><i style="background:#ffc56b;border-radius:2px;height:3px;width:14px"></i>prerequisite found later</span>');
  L.insertAdjacentHTML('beforeend', '<span><i style="background:#5b86b5;border-radius:2px;height:3px;width:14px"></i>found earlier</span>');
  if (D.nres) L.insertAdjacentHTML('beforeend', '<span style="color:#fff">★ research result formalized outside mathlib</span>');
}

function axes() {
  el('rect', {x: M.l, y: M.t, width: W - M.l - M.r, height: ym(D.real - 0.5) - M.t, fill: '#0c1119'});
  el('rect', {x: M.l, y: ym(D.real - 0.5), width: W - M.l - M.r, height: H - M.b - ym(D.real - 0.5), fill: '#120f0c'});
  for (let d = 0; d < YMAX; d += 10) {
    el('line', {x1: M.l, x2: W - M.r, y1: ym(d), y2: ym(d), stroke: '#1c222b'});
    el('text', {x: M.l - 8, y: ym(d) + 4, fill: '#8a8f98', 'font-size': 11, 'text-anchor': 'end'}).textContent = d;
  }
  for (const y of [-600, 1, 500, 1000, 1500, 1600, 1700, 1800, 1900, 2000])
    el('text', {x: xm(y), y: H - M.b + 18, fill: '#8a8f98', 'font-size': 11, 'text-anchor': 'middle'}).textContent = yl(y);
  el('line', {x1: xm(XB), x2: xm(XB), y1: M.t, y2: H - M.b, stroke: '#1c222b', 'stroke-dasharray': '3 4'});
  for (const [w, o] of [[8, .06], [3.5, .14], [1.2, .9]])
    el('line', {x1: M.l, x2: W - M.r, y1: ym(D.real - 0.5), y2: ym(D.real - 0.5), stroke: '#f6b73c', 'stroke-width': w, opacity: o});
  el('text', {x: W - M.r - 4, y: ym(D.real - 0.5) - 6, fill: '#f6b73c', 'font-size': 12, 'text-anchor': 'end', 'font-weight': 'bold'}).textContent = `ℝ  depth ${D.real}`;
  el('text', {x: M.l + (W - M.l - M.r) / 2, y: H - 6, fill: '#8a8f98', 'font-size': 12, 'text-anchor': 'middle'}).textContent = 'year first stated';
  const t = el('text', {x: 14, y: (M.t + H - M.b) / 2, fill: '#8a8f98', 'font-size': 12, 'text-anchor': 'middle', transform: `rotate(-90 14 ${(M.t + H - M.b) / 2})`});
  t.textContent = 'statement depth';
}

let threadLayer, dotLayer;
function draw() {
  svg.innerHTML = ''; axes();
  threadLayer = el('g', {}); dotLayer = el('g', {});
  const pts = mode === 'theorems' ? D.theorems : D.concepts;
  for (const p of pts) {
    const r = mode === 'theorems' ? 2.6 + 3.4 * Math.pow(Math.log10((p.ps || 0) + 1) / 4.6, 2) : 3.4;
    const col = D.fields[p.f] || '#8a8f98';
    const g = el('g', {class: 'pt', 'data-k': p.k, tabindex: 0, style: 'cursor:pointer'}, dotLayer);
    if (p.rs) {
      const cx = xm(p.ys), cy = ym(p.sd), pts = [];
      for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, rr = i % 2 ? 3.4 : 8; pts.push(`${cx + rr * Math.cos(a)},${cy + rr * Math.sin(a)}`); }
      el('circle', {cx, cy, r: 14, fill: '#ffffff', opacity: .10}, g);
      el('polygon', {points: pts.join(' '), fill: '#ffffff'}, g);
    } else {
    el('circle', {cx: xm(p.ys), cy: ym(p.sd), r: r * 2.4, fill: col, opacity: .10}, g);
    el('circle', {cx: xm(p.ys), cy: ym(p.sd), r: r, fill: p.so ? 'none' : col, stroke: p.so ? '#f6b73c' : 'none', 'stroke-width': 1.6}, g);
    }
    el('circle', {cx: xm(p.ys), cy: ym(p.sd), r: 9, fill: 'transparent'}, g);
    g.addEventListener('mouseenter', () => { if (!pinned) show(p); });
    g.addEventListener('click', e => { e.stopPropagation(); pinned = pinned === p.k ? null : p.k; show(p); });
    g.addEventListener('focus', () => show(p));
  }
}

function threads(p) {
  threadLayer.innerHTML = '';
  if (!p.dir) return;
  for (const k of p.dir) {
    const q = byKey[k]; if (!q) continue;
    const x0 = xm(p.ys), y0 = ym(p.sd), x1 = xm(q.ys), y1 = ym(q.sd);
    const fwd = q.yp > p.yp, mx = (x0 + x1) / 2, my = (y0 + y1) / 2 - Math.abs(x1 - x0) * .18;
    el('path', {d: `M${x0},${y0} Q${mx},${my} ${x1},${y1}`, fill: 'none', stroke: fwd ? '#ffc56b' : '#5b86b5', 'stroke-width': 1.4, opacity: .85}, threadLayer);
    el('circle', {cx: x1, cy: y1, r: 4.5, fill: 'none', stroke: fwd ? '#ffc56b' : '#5b86b5', 'stroke-width': 1.2}, threadLayer);
  }
}

function esc(s) { return String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c])); }

function show(p) {
  threads(p);
  dotLayer.querySelectorAll('.pt').forEach(g => g.style.opacity = g.dataset.k === p.k ? 1 : (pinned ? .35 : .9));
  const isT = mode === 'theorems';
  let h = `<h2>${esc(p.t)}</h2><div class="meta">${esc(p.f)} · first stated ${yl(p.ys)}` +
    (isT && p.yp !== p.ys ? ` · first proved ${yl(p.yp)}` : '') + (p.rs ? '' : ` · date confidence ${esc(p.c)}`) + `</div>`;
  h += `<code>${esc(p.d)}</code>`;
  h += `<div class="nums"><div><b>${p.sd}</b>statement depth</div><div><b>${p.ss}</b>concepts in the statement</div>`;
  if (isT) h += `<div><b>${p.pd == null ? 'none' : p.pd}</b>proof depth</div><div><b>${p.ps == null ? 'no proof' : p.ps.toLocaleString()}</b>definitions and theorems under the proof</div>`;
  h += `</div>`;
  if (p.ch && p.ch.length) {
    h += `<div class="meta" style="margin:8px 0 0">Deepest chain of definitions below it</div><ul class="chain">`;
    for (const [n, d] of p.ch) h += `<li class="${d >= D.real ? 'real' : ''}"><span>${d}</span><span>${esc(n)}</span></li>`;
    h += `</ul>`;
  }
  if (p.rs) {
    h += `<div class="meta" style="margin:12px 0 0">Research result formalized outside mathlib: ${esc(p.note)}.` +
      (p.sorry ? ' Its proof in Lean is not finished yet (it still uses <code>sorry</code>); the statement is complete.' : '') + `</div>`;
  } else if (isT) {
    const dep = (p.dep || []).map(k => byKey[k]).filter(Boolean).sort((a, b) => a.yp - b.yp);
    const young = dep.filter(q => q.yp > p.yp);
    h += `<div class="meta" style="margin:12px 0 0">Its mathlib proof rests on ${dep.length} famous theorem${dep.length === 1 ? '' : 's'} from the sample, ${young.length} found later. Lines show the direct ones.</div><div class="deps">`;
    h += dep.map(q => `<span class="${q.yp > p.yp ? 'y' : 'o'}">${esc(q.t)} (${yl(q.yp)})</span>`).join(' · ');
    h += `</div>`;
  }
  info.innerHTML = h;
}

document.getElementById('bt').onclick = () => { mode = 'theorems'; pinned = null; setBtn(); draw(); };
document.getElementById('bc').onclick = () => { mode = 'concepts'; pinned = null; setBtn(); draw(); };
function setBtn() {
  document.getElementById('bt').classList.toggle('on', mode === 'theorems');
  document.getElementById('bc').classList.toggle('on', mode === 'concepts');
  document.getElementById('hint').textContent = mode === 'theorems' ? `${D.n} theorems` + (D.nres ? ` and ${D.nres} research results` : '') : `${D.concepts.length} concepts, by the year they appeared`;
}
document.getElementById('q').addEventListener('input', e => {
  const s = e.target.value.trim().toLowerCase(); if (!s) return;
  const pts = mode === 'theorems' ? D.theorems : D.concepts;
  const p = pts.find(p => p.t.toLowerCase().includes(s) || p.d.toLowerCase().includes(s));
  if (p) { pinned = p.k; show(p); }
});
svg.addEventListener('click', () => { pinned = null; });
legend(); setBtn(); draw();
const start = D.theorems.find(t => t.k === 'wQ11518'); if (start) show(start);
</script>
</body>
</html>
"""


def main():
    data = payload()
    html = PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("__N__", str(data["n"]))
    (DOCS / "index.html").write_text(html, encoding="utf-8")
    print(f"docs/index.html: {len(html) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
