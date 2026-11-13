"""Extract the chart runtime from design/index.html for the Power BI HTML Content visual.

The prototype is the source of truth for every page body. This script slices its CSS and JS (formatting, date
helpers, daily engine, shared chart pieces, page1..page6, rolling table) into semantic/pbi_runtime.css and
semantic/pbi_runtime.js. semantic/ga4_measures.py embeds them in the "0N · 002 Body HTML" measures, which feed the
runtime a DATA object built in DAX from the model (so the date slicer drives it).

    python3 scripts/build_pbi_runtime.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "design" / "index.html").read_text(encoding="utf-8")


def between(start: str, end: str) -> str:
    i = SRC.index(start)
    j = SRC.index(end, i)
    return SRC[i:j]


css = between("<style>", "/* cover (00 Welcome)")[len("<style>"):]
css += """
html,body{background:transparent!important;height:100vh;overflow:hidden}
#pages{position:absolute;inset:0}
#tip{position:fixed}
"""

prelude = r"""
const DATA = window.__D;
const D = {day: DATA.days || [], ch_day: [], dev_day: [], daily: DATA.daily || [], ti_daily: DATA.ti_daily || [],
           all: {kpi: DATA.allkpi || {}, weekly: []}, jan: {kpi: DATA.jankpi || {}}};
const DAY0 = '2020-11-01', DAYN = '2021-01-31', CART0 = '2020-11-25';
const S = {page: DATA.page, key: 'pbi', range: DATA.range, p1metric: 'r', p4dim: 'all', p3type: 'all', p6metric: 'r', sort: {}};
const C = getComputedStyle(document.documentElement);
const T = k => C.getPropertyValue('--'+k).trim();
"""
engine = between("/* ---------------- formatting ---------------- */", "/* ---------------- tooltip ---------------- */")
tooltip = r"""
VIEW = DATA.view;
if (VIEW.pareto_rv) { const r = VIEW.pareto_rv, t = r.reduce((a,b) => a + b, 0) || 1; let c = 0;
  const cv = r.map(v => +((c += v) / t).toFixed(4)); VIEW.pareto = {n: r.length, curve: cv.filter((_, i) => i % 3 === 0).slice(0, 100).concat([1])}; }
/* ---------------- tooltip (visual-relative) ---------------- */
const tip = document.getElementById('tip');
function showTip(e, html){
  tip.innerHTML = html; tip.style.opacity = 1;
  let x = e.clientX + 14, y = e.clientY + 14;
  if (x > innerWidth - 280) x -= 290; if (y > innerHeight - 110) y -= 100;
  tip.style.left = Math.max(4, x) + 'px'; tip.style.top = Math.max(4, y) + 'px';
}
const hideTip = () => tip.style.opacity = 0;
function bindTips(root){
  root.querySelectorAll('[data-tip]').forEach(el => {
    el.addEventListener('mousemove', e => showTip(e, el.getAttribute('data-tip')));
    el.addEventListener('mouseleave', hideTip);
  });
}
"""
rolling = between("/* ---------------- rolling-window table ---------------- */", "/* ---------------- shared chart pieces ---------------- */")
pages = between("/* ---------------- shared chart pieces ---------------- */", "/* ================= PAGE 0 · WELCOME (cover) ================= */")
page6 = between("/* ================= PAGE 6 · TIME INTELLIGENCE ================= */", "/* ---------------- render ---------------- */")
render = r"""
/* ---------------- render (one page body per visual) ---------------- */
const RENDER = {1: page1, 2: page2, 3: page3, 4: page4, 5: page5, 6: page6};
function render(){
  const pages = document.getElementById('pages');
  pages.innerHTML = RENDER[S.page]();
  fillSlots(pages); bindTips(pages); bindSort(pages);
  pages.querySelectorAll('[data-tog]').forEach(g => g.querySelectorAll('button').forEach(b => b.onclick = () => { S[g.dataset.tog] = b.dataset.v; render(); }));
  pages.querySelectorAll('[data-chip]').forEach(g => g.querySelectorAll('button').forEach(b => b.onclick = () => { S[g.dataset.chip] = b.dataset.v; render(); }));
}
render();
addEventListener('resize', () => { clearTimeout(window.__rt); window.__rt = setTimeout(render, 120); });
"""
js = prelude + engine + tooltip + rolling + pages + page6 + render
(ROOT / "semantic" / "pbi_runtime.css").write_text(css, encoding="utf-8")
(ROOT / "semantic" / "pbi_runtime.js").write_text(js, encoding="utf-8")
print(f"pbi_runtime.css {len(css):,} chars · pbi_runtime.js {len(js):,} chars")
