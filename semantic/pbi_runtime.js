
const DATA = window.__D;
const D = {day: DATA.days || [], ch_day: [], dev_day: [], daily: DATA.daily || [], ti_daily: DATA.ti_daily || [],
           all: {kpi: DATA.allkpi || {}, weekly: []}, jan: {kpi: DATA.jankpi || {}}};
const DAY0 = '2020-11-01', DAYN = '2021-01-31', CART0 = '2020-11-25';
const S = {page: DATA.page, key: 'pbi', range: DATA.range, p1metric: 'r', p4dim: 'all', p3type: 'all', p6metric: 'r', sort: {}};
const C = getComputedStyle(document.documentElement);
const T = k => C.getPropertyValue('--'+k).trim();
/* ---------------- formatting ---------------- */
const nz = v => v === null || v === undefined || Number.isNaN(v);
const fInt = v => nz(v) ? '—' : v >= 1e6 ? (v/1e6).toFixed(2)+'M' : v >= 1e4 ? (v/1e3).toFixed(1)+'K' : Math.round(v).toLocaleString('en-US');
const fUsd = v => nz(v) ? '—' : '$' + fInt(v);
const fUsd2 = v => nz(v) ? '—' : '$' + v.toFixed(2);
const fPct = (v, d=2) => nz(v) ? '—' : (v*100).toFixed(d) + '%';
const fSec = v => nz(v) ? '—' : Math.floor(v/60) + 'm ' + String(Math.floor(v%60)).padStart(2,'0') + 's';
const fNum = (v, d=2) => nz(v) ? '—' : v.toFixed(d);
const FMT = {int: fInt, usd: fUsd, usd2: fUsd2, pct: fPct, sec: fSec, num2: fNum};
const esc = s => String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
const dv = (a, b) => b ? a / b : null;

/* ---------------- dates ---------------- */
const U = s => new Date(s + 'T00:00:00Z');
const dstr = d => d.toISOString().slice(0,10);
const addD = (s, n) => { const d = U(s); d.setUTCDate(d.getUTCDate() + n); return dstr(d); };
const nDays = (s, e) => Math.round((U(e) - U(s)) / 864e5) + 1;
const mEnd = s => dstr(new Date(Date.UTC(+s.slice(0,4), +s.slice(5,7), 0)));
const mStart = s => s.slice(0,8) + '01';
const addM = (s, n) => { const y = +s.slice(0,4), m = +s.slice(5,7) - 1 + n, d = +s.slice(8,10); const last = new Date(Date.UTC(y, m + 1, 0)).getUTCDate(); return dstr(new Date(Date.UTC(y, m, Math.min(d, last)))); };
const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], MONL = ['January','February','March','April','May','June','July','August','September','October','November','December'];
const sd = s => MON[+s.slice(5,7)-1] + ' ' + (+s.slice(8,10));
const isFullMonth = (s, e) => s === mStart(s) && e === mEnd(s);
function rangeLabel(s, e){
  if (isFullMonth(s, e)) return MONL[+s.slice(5,7)-1] + ' ' + s.slice(0,4);
  if (s === e) return sd(s) + ', ' + s.slice(0,4);
  return s.slice(0,4) === e.slice(0,4) ? `${sd(s)} – ${sd(e)}, ${e.slice(0,4)}` : `${sd(s)}, ${s.slice(0,4)} – ${sd(e)}, ${e.slice(0,4)}`;
}
function ppRange(s, e){
  const r = isFullMonth(s, e) ? {s: addM(s, -1), e: mEnd(addM(s, -1))} : {s: addD(s, -nDays(s, e)), e: addD(s, -1)};
  return r.s >= DAY0 ? r : null;
}
const ppLabel = (s, e, p) => !p ? 'no earlier period in data' : isFullMonth(s, e) ? 'vs ' + MON[+p.s.slice(5,7)-1] + ' ' + p.s.slice(0,4) : `vs prior ${nDays(s, e)} days`;

/* ---------------- daily engine (custom ranges + rolling windows) ---------------- */
const tag0 = r => ({...r, d: r.date.slice(0,10)});
const DAYS = D.day.filter(r => r.date).map(tag0), CHD = D.ch_day.filter(r => r.date).map(tag0), DVD = D.dev_day.filter(r => r.date).map(tag0);
const DAYMAP = Object.fromEntries(DAYS.map(r => [r.d, r]));
const F = ['s','r','tx','cs','pv','es','nu','et','vi','atc','bc','api','ps','ir','u'];
function agg(s, e, rows = DAYS){
  const o = {n: 0, cvi: 0, catc: 0, cbc: 0, capi: 0, cps: 0}; F.forEach(f => o[f] = 0);
  for (const x of rows){ if (x.d < s || x.d > e) continue; o.n++; for (const f of F) o[f] += x[f] || 0;
    if (x.d >= CART0){ o.cvi += x.vi||0; o.catc += x.atc||0; o.cbc += x.bc||0; o.capi += x.api||0; o.cps += x.ps||0; } }
  o.cr = dv(o.cs, o.s); o.aov = dv(o.r, o.tx); o.rps = dv(o.r, o.s); return o;
}
const dow = s => (U(s).getUTCDay() + 6) % 7;
const DOWN = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
function weekdayRows(s, e){
  const g = DOWN.map((n,i) => ({day_of_week_num: i+1, day_name: n, day_short: n.slice(0,3), is_weekend: i >= 5, days: 0, r: 0, s: 0, cs: 0}));
  let tr = 0, tn = 0;
  for (const x of DAYS){ if (x.d < s || x.d > e) continue; const w = g[dow(x.d)]; w.days++; w.r += x.r||0; w.s += x.s||0; w.cs += x.cs||0; tr += x.r||0; tn++; }
  const avg = dv(tr, tn);
  return g.filter(w => w.days).map(w => ({...w, adr: w.r / w.days, ads: w.s / w.days, ix: dv(w.r / w.days, avg), cr: dv(w.cs, w.s)}));
}
function weeklyRows(s, e){
  const g = {};
  for (const x of DAYS){ if (x.d < s || x.d > e) continue; const ws = addD(x.d, -dow(x.d)); (g[ws] ||= []).push(x); }
  return Object.entries(g).sort().map(([ws, rows]) => { const a = rows[0].d, b = rows[rows.length-1].d, o = agg(a, b);
    const p = addD(a, -7) >= DAY0 ? agg(addD(a, -7), addD(b, -7)) : null;
    return {week_start: ws + 'T00:00:00', days: rows.length, r: o.r, s: o.s, cr: o.cr, tx: o.tx, wr: p && p.r ? (o.r - p.r) / p.r : null, ws: p && p.s ? (o.s - p.s) / p.s : null}; });
}
function groupRows(rows, key, s, e){
  const g = {}; for (const x of rows) if (x.d >= s && x.d <= e && x[key]) (g[x[key]] ||= []).push(x);
  const tot = agg(s, e);
  return Object.entries(g).map(([k, rs]) => { const o = agg(s, e, rs), ss = dv(o.s, tot.s), rsh = dv(o.r, tot.r);
    return {[key]: k, s: o.s, r: o.r, tx: o.tx, cr: o.cr, aov: o.aov, rps: o.rps, ss, rs: rsh, ri: dv(rsh, ss), cvs: o.cr !== null && tot.cr !== null ? (o.cr - tot.cr) * 100 : null,
      vi: o.cvi, atc: o.catc, bc: o.cbc, api: o.capi, ps: o.cps}; });
}
function tiCalc(s, e){
  const ms = mStart(e), pms = addM(ms, -1), pme = addM(e, -1);
  const mtd = agg(ms, e), pm = pms >= DAY0 ? agg(pms, pme) : null;
  const l7 = agg(addD(e, -6), e), p7 = addD(e, -13) >= DAY0 ? agg(addD(e, -13), addD(e, -7)) : null;
  const a7 = addD(e, -6) >= DAY0 ? l7.r / 7 : null, a28 = addD(e, -27) >= DAY0 ? agg(addD(e, -27), e).r / 28 : null;
  const wd = weekdayRows(s, e), best = wd.slice().sort((a,b) => b.adr - a.adr)[0], worst = wd.slice().sort((a,b) => a.adr - b.adr)[0];
  const tot = agg(s, e); let we = {r: 0, n: 0, s: 0, cs: 0}, wk = {s: 0, cs: 0};
  for (const x of DAYS){ if (x.d < s || x.d > e) continue; if (dow(x.d) >= 5){ we.r += x.r||0; we.n++; we.s += x.s||0; we.cs += x.cs||0; } else { wk.s += x.s||0; wk.cs += x.cs||0; } }
  const pc = (a, b) => b ? (a - b) / b : null;
  return {'Revenue MTD': mtd.r, 'Revenue PMTD': pm ? pm.r : null, 'Revenue MTD vs PMTD %': pm ? pc(mtd.r, pm.r) : null,
    'Sessions MTD': mtd.s, 'Sessions PMTD': pm ? pm.s : null, 'Sessions MTD vs PMTD %': pm ? pc(mtd.s, pm.s) : null,
    'Conversion Rate MTD': mtd.cr, 'Conversion Rate PMTD': pm ? pm.cr : null, 'Conversion Rate MTD vs PMTD pts': pm ? (mtd.cr - pm.cr) * 100 : null,
    'MTD Label': pm ? `vs ${MON[+pms.slice(5,7)-1]} 1–${+pme.slice(8,10)}` : 'no prior month in data',
    'Revenue L7D': l7.r, 'Revenue P7D': p7 ? p7.r : null, 'Revenue WoW %': p7 ? pc(l7.r, p7.r) : null,
    'Revenue 7D Avg': a7, 'Revenue 28D Avg': a28, 'Revenue Momentum %': a28 ? pc(a7, a28) : null,
    'Best Weekday': best ? best.day_name : '—', 'Worst Weekday': worst ? worst.day_name : '—', 'Best Weekday Index': best ? best.ix : null,
    'Weekend Revenue Share': dv(we.r, tot.r), 'Weekend Day Share': dv(we.n, tot.n), 'Weekend Conversion Rate': dv(we.cs, we.s), 'Weekday Conversion Rate': dv(wk.cs, wk.s)};
}
const PTS = ['Conversion Rate','Engagement Rate','Cart Abandonment Rate','View Item to Purchase Rate'];
function kpiVals(o){
  return o && {'Sessions': o.s, 'Revenue': o.r, 'Transactions': o.tx, 'Conversion Rate': o.cr, 'AOV': o.aov, 'Revenue per Session': o.rps,
    'Pageviews': o.pv, 'Pages per Session': dv(o.pv, o.s), 'Engagement Rate': dv(o.es, o.s), 'New Users': o.nu, 'Avg Engagement Time (sec)': dv(o.et, o.s),
    'View Item Sessions': o.vi, 'Begin Checkout Sessions': o.bc, 'Purchase Sessions': o.ps, 'Cart Abandonment Rate': o.catc ? 1 - o.cps / o.catc : null,
    'Item Revenue': o.ir, 'Units Purchased': o.u, 'Avg Item Price': dv(o.ir, o.u), 'View Item to Purchase Rate': dv(o.cps, o.cvi)};
}
/* week over week: last 7 days ending on the period end vs the 7 days before (every KPI, every window) */
function wowKpi(e){
  const o = {}, names = Object.keys(kpiVals(agg(e, e)));
  const c = addD(e, -6) >= DAY0 ? kpiVals(agg(addD(e, -6), e)) : null;
  const p = c && addD(e, -13) >= DAY0 ? kpiVals(agg(addD(e, -13), addD(e, -7))) : null;
  for (const n of names){ const a = c ? c[n] : null, b = p ? p[n] : null, ok = !nz(a) && !nz(b);
    o[n + ' L7D'] = a ?? null;
    if (PTS.includes(n)) o[n + ' L7D Δ pts'] = ok ? (a - b) * 100 : null; else o[n + ' L7D Δ%'] = ok && b ? (a - b) / b : null; }
  return o;
}
function buildView(){
  const {s, e} = S.range;
  if (S.key !== 'custom') return {...D[S.key], kpi: {...D[S.key].kpi, ...wowKpi(e)}, custom: false, base: S.key};
  const base = s.slice(0,7) === e.slice(0,7) ? {'2020-11':'nov','2020-12':'dec','2021-01':'jan'}[s.slice(0,7)] : 'all';
  const B = D[base], c = agg(s, e), pr = ppRange(s, e), p = pr ? agg(pr.s, pr.e) : null, cv = kpiVals(c), pv = kpiVals(p);
  const K = {...B.kpi, ...cv, 'Users': null, 'Items Sold': null};
  for (const n in cv){ const a = cv[n], b = pv ? pv[n] : null, ok = !nz(a) && !nz(b);
    K[n + ' PP'] = b; if (PTS.includes(n)) K[n + ' Δ pts'] = ok ? (a - b) * 100 : null; else K[n + ' Δ%'] = ok && b ? (a - b) / b : null; }
  K['Period Label'] = rangeLabel(s, e); K['PP Label'] = ppLabel(s, e, pr);
  K['Session to View Item Rate'] = dv(c.vi, c.s); K['View Item to Cart Rate'] = dv(c.catc, c.cvi);
  let best = null; for (const x of DAYS) if (x.d >= s && x.d <= e && (!best || x.r > best.r)) best = x;
  K['Best Revenue Day'] = best ? `${sd(best.d)} · ${fUsd(best.r)}` : '—';
  Object.assign(K, tiCalc(s, e), wowKpi(e));
  const channel = groupRows(CHD, 'channel_group', s, e), device = groupRows(DVD, 'device_category', s, e);
  const top = channel.slice().sort((a,b) => b.r - a.r)[0];
  K['Top Channel'] = top ? top.channel_group : '—'; K['Revenue Share of Top Channel'] = top ? top.rs : null;
  const V = {...B, kpi: K, channel, device, funnel_ch: channel, funnel: {vi: c.cvi, atc: c.catc, bc: c.cbc, api: c.capi, ps: c.cps},
    weekly: weeklyRows(s, e), weekday: weekdayRows(s, e), custom: true, base};
  K['01 Headline'] = K['Revenue Δ%'] !== null && K['Revenue Δ%'] !== undefined
    ? `Revenue ${K['Revenue Δ%'] >= 0 ? 'grew' : 'fell'} ${fPct(Math.abs(K['Revenue Δ%']),0)} ${K['PP Label']}, and ${K['Top Channel']} carried ${fPct(K['Revenue Share of Top Channel'],0)} of it.`
    : `${fUsd(c.r)} in revenue from ${fInt(c.s)} sessions; ${K['Top Channel']} carried ${fPct(K['Revenue Share of Top Channel'],0)} of it.`;
  const big = channel.filter(x => x.ss >= .02), bySes = big.slice().sort((a,b) => b.s - a.s)[0], byIx = big.slice().sort((a,b) => (b.ri||0) - (a.ri||0))[0];
  if (bySes && byIx) K['02 Headline'] = `${bySes.channel_group} brings ${fPct(bySes.ss,0)} of sessions and ${fPct(bySes.rs,0)} of revenue; ${byIx.channel_group} earns ${(byIx.ri||0).toFixed(1)}× its share of traffic.`;
  const f = V.funnel, steps = [['view → cart', f.atc/f.vi], ['cart → checkout', f.bc/f.atc], ['checkout → payment', f.api/f.bc], ['payment → purchase', f.ps/f.api]].filter(x => isFinite(x[1]));
  const leak = steps.sort((a,b) => a[1] - b[1])[0];
  if (leak) K['04 Headline'] = `${fPct(K['Session to View Item Rate'],0)} of sessions open a product page, and ${leak[0]} loses the most shoppers (${fPct(1 - leak[1],0)} drop out).`;
  const mt = K['Revenue MTD vs PMTD %'], mo = K['Revenue Momentum %'];
  K['06 Headline'] = !nz(mt) ? `${MONL[+e.slice(5,7)-1]} revenue is pacing ${fPct(Math.abs(mt),0)} ${mt >= 0 ? 'ahead of' : 'behind'} the same days of ${MONL[+addM(e,-1).slice(5,7)-1]}${nz(mo) ? '.' : `, and the 7-day trend is ${fPct(Math.abs(mo),0)} ${mo >= 0 ? 'above' : 'below'} the 28-day average.`}`
    : !nz(mo) ? `The 7-day revenue trend ends ${fPct(Math.abs(mo),0)} ${mo >= 0 ? 'above' : 'below'} the 28-day average.` : `${K['Best Weekday']}s earn ${(K['Best Weekday Index']||0).toFixed(1)}× a typical day's revenue.`;
  return V;
}
let VIEW = null;
const P = () => VIEW;
const K = n => VIEW.kpi[n];


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
/* ---------------- rolling-window table ---------------- */
function rollTable(){
  const e = S.range.e, M = [['Sessions','s','int'],['Pageviews','pv','int'],['Transactions','tx','int'],['Revenue','r','usd'],['Conversion rate','cr','pct',1],['Average order value','aov','usd2']];
  const W = [7, 14, 28].map(n => ({n, c: agg(addD(e, -(n-1)), e), p: addD(e, -(2*n-1)) >= DAY0 ? agg(addD(e, -(2*n-1)), addD(e, -n)) : null}));
  const chg = (a, b, pts) => { if (nz(a) || nz(b) || (!pts && !b)) return '<span style="color:var(--muted)">—</span>';
    const d = pts ? (a - b) * 100 : (a - b) / b, g = d >= 0;
    return `<span class="pill ${g?'good':'bad'}">${g?'▲ +':'▼ −'}${pts ? Math.abs(d).toFixed(2)+' pts' : (Math.abs(d)*100).toFixed(1)+'%'}</span>`; };
  return `<table class="rt"><thead><tr><th></th>${W.map(w => `<th colspan="3" class="sep">LAST ${w.n} DAYS</th>`).join('')}</tr>
    <tr><th style="text-align:left">METRIC</th>${W.map(() => '<th class="sep">VALUE</th><th>PRIOR</th><th>CHANGE</th>').join('')}</tr></thead>
    <tbody>${M.map(([l,f,k,pts]) => `<tr><th>${l}</th>${W.map(w => `<td class="sep"><b>${FMT[k](w.c[f])}</b></td><td class="p">${w.p ? FMT[k](w.p[f]) : '—'}</td><td>${chg(w.c[f], w.p && w.p[f], pts)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}

/* ---------------- shared chart pieces ---------------- */
function hbars(rows, {label, value, fmt, color, max, sub, tipf, hi}){
  const mx = max ?? (Math.max(...rows.map(r => value(r) || 0)) || 1);
  return rows.map(r => {
    const v = value(r) || 0, w = Math.max(v/mx*100, .8);
    const c = typeof color === 'function' ? color(r) : (color || T('acc'));
    return `<div class="hb" data-tip="${tipf?esc(tipf(r)):''}" style="display:grid;grid-template-columns:150px 1fr 60px;gap:8px;align-items:center;padding:3px 0;${hi&&hi(r)?'font-weight:700':''}">
      <div style="font-size:10.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(label(r))}${sub?`<div style="font-size:9px;color:${T('muted')};font-weight:500">${sub(r)}</div>`:''}</div>
      <div style="height:12px;background:${T('soft')};border-radius:6px;overflow:hidden"><div style="height:100%;width:${w}%;background:${c};border-radius:6px;transition:width .4s"></div></div>
      <div style="font-size:10.5px;font-weight:700;text-align:right">${fmt(v)}</div></div>`;
  }).join('');
}
function sortTable(id, rows, cols, defKey){
  const st = S.sort[id] || {k: defKey, d: -1};
  const sorted = rows.slice().sort((a,b) => ((a[st.k] ?? -1e18) > (b[st.k] ?? -1e18) ? 1 : -1) * st.d);
  return `<table data-id="${id}"><thead><tr>${cols.map(c => `<th data-k="${c.k}" class="${st.k===c.k?'sorted':''}">${c.h}${st.k===c.k?(st.d<0?' ↓':' ↑'):''}</th>`).join('')}</tr></thead>
    <tbody>${sorted.map(r => `<tr ${r._tip?`data-tip="${esc(r._tip)}"`:''}>${cols.map(c => `<td>${c.f(r)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}
function bindSort(root){
  root.querySelectorAll('table[data-id] th').forEach(th => th.addEventListener('click', () => {
    const id = th.closest('table').dataset.id, k = th.dataset.k, cur = S.sort[id];
    S.sort[id] = {k, d: cur && cur.k === k ? -cur.d : -1}; render();
  }));
}
const tag = t => `<div class="tag">${t}</div>`;
const SLOTS = {};
const slot = (id, fn) => { SLOTS[id] = fn; return `<div class="slot" data-slot="${id}" style="position:absolute;inset:0"></div>`; };
function fillSlots(root){ root.querySelectorAll('[data-slot]').forEach(el => { const fn = SLOTS[el.dataset.slot]; if (fn) el.innerHTML = fn(el.clientWidth, el.clientHeight); }); }

/* ================= PAGE 1 · OVERVIEW ================= */
function page1(){
  const daily = D.daily.filter(d => d.date), m = S.p1metric;
  const sel = !(S.range.s === DAY0 && S.range.e === DAYN);
  const trendSvg = (W, H) => { const pl = 38, pr = 10, pt = 26, pb = 22;
  const vals = daily.map(d => d[m] ?? 0), mx = Math.max(...vals) * 1.08;
  const x = i => pl + i * (W - pl - pr) / (daily.length - 1), y = v => pt + (1 - v / mx) * (H - pt - pb);
  const inSel = d => d.date.slice(0,10) >= S.range.s && d.date.slice(0,10) <= S.range.e;
  let band = '', peakStart = daily.findIndex(d => d.is_peak_season), peakEnd = daily.length - 1 - [...daily].reverse().findIndex(d => d.is_peak_season);
  band = `<rect x="${x(peakStart)}" y="${pt}" width="${x(peakEnd)-x(peakStart)}" height="${H-pt-pb}" fill="${T('soft')}"/>
          <text x="${x(peakStart)+6}" y="${H-pb-7}" font-size="9" font-weight="700" fill="${T('acc')}" letter-spacing="1">PEAK SEASON · ${fPct(D.all.kpi['Peak Season Day Share'],0)} OF DAYS</text>`;
  if (sel) { const a = daily.findIndex(inSel), b = daily.length-1-[...daily].reverse().findIndex(inSel);
    band += `<rect x="${x(0)}" y="${pt}" width="${x(a)-x(0)}" height="${H-pt-pb}" fill="#fff" fill-opacity=".72"/><rect x="${x(b)}" y="${pt}" width="${x(daily.length-1)-x(b)}" height="${H-pt-pb}" fill="#fff" fill-opacity=".72"/>`; }
  const path = vals.map((v,i) => (i?'L':'M') + x(i).toFixed(1) + ',' + y(v).toFixed(1)).join('');
  const area = path + `L${x(daily.length-1)},${H-pb}L${x(0)},${H-pb}Z`;
  const imax = vals.indexOf(Math.max(...vals));
  const fm = m === 'r' ? fUsd : m === 's' ? fInt : v => fPct(v);
  let grid = ''; for (let g = 0; g <= 3; g++) { const gv = mx * g / 3; grid += `<line x1="${pl}" x2="${W-pr}" y1="${y(gv)}" y2="${y(gv)}" stroke="${T('line')}"/><text x="${pl-6}" y="${y(gv)+3}" font-size="9" fill="${T('muted')}" text-anchor="end">${m==='cr'?(gv*100).toFixed(1)+'%':fInt(gv)}</text>`; }
  const months = [['Nov',0],['Dec',30],['Jan',61]].map(([t,i]) => `<text x="${x(i)}" y="${H-6}" font-size="9.5" fill="${T('sub')}" font-weight="600">${t}</text>`).join('');
  const hol = daily.map((d,i) => d.holiday_name ? `<g data-tip="<b>${d.holiday_name}</b> · ${d.date.slice(0,10)}<br>Revenue ${fUsd(d.r)} · ${fInt(d.s)} sessions · CR ${fPct(d.cr)}"><line x1="${x(i)}" x2="${x(i)}" y1="${y(vals[i])}" y2="${H-pb}" stroke="${T('acc')}" stroke-dasharray="2 3"/><circle cx="${x(i)}" cy="${y(vals[i])}" r="4" fill="#fff" stroke="${T('acc')}" stroke-width="2"/><text x="${x(i)}" y="${y(vals[i])-8}" font-size="8.5" font-weight="700" text-anchor="middle" fill="${T('ink')}">${d.holiday_name.replace('Cyber Monday','Cyber Mon').replace('Black Friday','Black Fri')}</text></g>` : '').join('');
  const hits = daily.map((d,i) => `<rect x="${x(i)-3.5}" y="${pt}" width="7" height="${H-pt-pb}" fill="transparent" data-tip="<b>${new Date(d.date).toDateString().slice(0,10)}</b><br>Revenue ${fUsd(d.r)}<br>Sessions ${fInt(d.s)}<br>Conversion ${fPct(d.cr)}"/>`).join('');
  return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">${band}${grid}
    <defs><linearGradient id="ga" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${T('acc')}" stop-opacity=".35"/><stop offset="1" stop-color="${T('acc')}" stop-opacity="0"/></linearGradient></defs>
    <path d="${area}" fill="url(#ga)"/><path d="${path}" fill="none" stroke="${T('acc')}" stroke-width="2"/>
    <g><rect x="${x(imax)-26}" y="${y(vals[imax])-24}" width="52" height="15" rx="7.5" fill="${T('ink')}"/><text x="${x(imax)}" y="${y(vals[imax])-13.5}" font-size="8.5" font-weight="800" fill="#fff" text-anchor="middle">PEAK</text></g>
    ${months}${hol}${hits}</svg>`; };

  const ch = P().channel.filter(c => c.channel_group).sort((a,b) => (b.r||0)-(a.r||0)).slice(0, 6);
  const top = ch[0];
  const k = P().kpi;
  return `<div class="body" style="grid-template-columns:1.62fr 1fr;grid-template-rows:1fr 168px">
    <div class="card" style="grid-row:span 2">
      <div class="ct"><div><h3>Daily ${m==='r'?'revenue':m==='s'?'sessions':'conversion rate'}, Nov 1 – Jan 31</h3><p>Shaded band = peak season (Black Friday week to Christmas) · hover a day or a holiday marker</p></div>
      <div class="tog" data-tog="p1metric">${[['r','Revenue'],['s','Sessions'],['cr','Conv. rate']].map(([v,t]) => `<button data-v="${v}" class="${m===v?'on':''}">${t}</button>`).join('')}</div></div>
      <div class="fill">${slot('trend', trendSvg)}</div>
      <div class="foot">Holiday window: the series is not a normal trend. ${sel?'Days outside the selected range are dimmed.':''} Best day: <b>${esc(k['Best Revenue Day'])}</b></div>
      ${tag('Native line chart · Date[date] × [Revenue] / [Sessions] / [Conversion Rate] via field parameter · error band = Date[is_peak_season] · holiday markers = Date[holiday_name]')}
    </div>
    <div class="card">
      <div class="ct"><div><h3>Revenue by channel</h3><p>${esc(top.channel_group)} carries ${fPct(k['Revenue Share of Top Channel'],0)} of revenue — a concentration risk</p></div><span class="pill acc">TOP ${fPct(k['Revenue Share of Top Channel'],0)}</span></div>
      <div class="fill" style="display:flex;flex-direction:column;justify-content:space-around">${hbars(ch, {label:r=>r.channel_group, value:r=>r.r, fmt:fUsd, color:r=>r===top?T('acc'):T('acc3'),
        sub:r=>`${fPct(r.rs,0)} of revenue · ${fPct(r.ss,0)} of sessions`, tipf:r=>`<b>${r.channel_group}</b><br>Revenue ${fUsd(r.r)} (${fPct(r.rs,1)})<br>Sessions ${fInt(r.s)} (${fPct(r.ss,1)})<br>Conversion ${fPct(r.cr)} · AOV ${fUsd2(r.aov)}`})}</div>
      ${tag('Native bar chart · Channel[channel_group] × [Revenue] · conditional colour = [Channel Revenue Rank]=1 · subtitle = [Top Channel], [Revenue Share of Top Channel]')}
    </div>
    <div class="card insight">
      <div class="lbl2">KEY INSIGHT · PEAK SEASON</div>
      <div style="display:flex;gap:18px;align-items:flex-end;margin-top:8px">
        <div><div class="big">${fPct(D.all.kpi['Peak Season Revenue Share'],0)}</div><div style="font-size:10.5px;color:#C9CAF5">of revenue in ${fPct(D.all.kpi['Peak Season Day Share'],0)} of the days</div></div>
        <div><div class="big" style="color:${T('acc3')}">+${fPct(D.all.kpi['Peak Conversion Lift'],0)}</div><div style="font-size:10.5px;color:#C9CAF5">conversion lift vs off-peak days</div></div>
      </div>
      <div style="font-size:10.5px;line-height:1.5;color:#E3E4FF;margin-top:10px">In January revenue falls ${fPct(-D.jan.kpi['Revenue Δ%'],0)} but sessions only ${fPct(-D.jan.kpi['Sessions Δ%'],0)}: the visitors stay, the buyers leave.</div>
      ${tag('HTML Content · [01 · 002 Key Insight HTML] from [Peak Season Revenue Share], [Peak Season Day Share], [Peak Conversion Lift] (full-window, REMOVEFILTERS on Date)')}
    </div></div>`;
}

/* ================= PAGE 2 · ACQUISITION ================= */
function page2(){
  const k = P().kpi;
  const ch = P().channel.filter(c => c.channel_group && c.s > 0).sort((a,b) => b.s - a.s);
  const mxs = Math.max(...ch.map(c => Math.max(c.ss, c.rs)));
  const rows = ch.map(c => {
    const ix = c.ri || 0, good = ix >= 1;
    return `<div data-tip="<b>${c.channel_group}</b><br>${fPct(c.ss,1)} of sessions → ${fPct(c.rs,1)} of revenue<br>Revenue index ${ix.toFixed(2)}× · Conversion ${fPct(c.cr)} (${(c.cvs>=0?'+':'')+(c.cvs||0).toFixed(2)} pts vs site)" style="display:grid;grid-template-columns:96px 1fr 1fr 56px;gap:8px;align-items:center;flex:1;border-bottom:1px solid #F2F3FA">
      <div style="font-size:11px;font-weight:600">${c.channel_group}</div>
      <div style="display:flex;justify-content:flex-end"><div style="height:12px;width:${c.ss/mxs*100}%;background:${T('acc3')};border-radius:6px 0 0 6px"></div></div>
      <div><div style="height:12px;width:${c.rs/mxs*100}%;background:${T('acc')};border-radius:0 6px 6px 0"></div></div>
      <div style="text-align:right"><span class="pill ${good?'good':'bad'}">${ix.toFixed(2)}×</span></div></div>`; }).join('');
  const sm = P().srcmed.map(r => ({...r, src: r.session_source + ' / ' + r.session_medium,
    _tip: `<b>${esc(r.session_source)} / ${esc(r.session_medium)}</b><br>${r.channel_group}<br>${fInt(r.s)} sessions · ${fUsd(r.r)}<br>Conversion ${fPct(r.cr)} · ${fUsd2(r.rps)} per session`}));
  const mxr = Math.max(...sm.map(r => r.rps || 0));
  const dev = P().device.slice().sort((a,b) => b.s - a.s);
  return `<div class="body" style="grid-template-columns:1fr 1.25fr;grid-template-rows:1fr 150px">
    <div class="card">
      <div class="ct"><div><h3>Traffic share vs revenue share</h3><p>Left = share of sessions · right = share of revenue · chip = revenue index</p></div></div>
      <div style="display:grid;grid-template-columns:96px 1fr 1fr 56px;gap:8px;font-size:9.5px;font-weight:700;color:${T('sub')};letter-spacing:.8px;margin-top:10px"><div>CHANNEL</div><div style="text-align:right">SESSIONS ◂</div><div>▸ REVENUE</div><div style="text-align:right">INDEX</div></div>
      <div class="fill" style="margin-top:2px;display:flex;flex-direction:column">${rows}</div>
      <div class="foot">Index above 1× = the channel earns more than the traffic it brings. Email is tiny (${fInt(ch.find(c=>c.channel_group==='Email')?.s)} sessions) but converts at ${fPct(ch.find(c=>c.channel_group==='Email')?.cr,1)}.</div>
      ${tag('Native clustered bar (mirrored) or Deneb · Channel × [Session Share] / [Revenue Share] · chip = [Revenue Index] with conditional colour')}
    </div>
    <div class="card">
      <div class="ct"><div><h3>Top sources by sessions</h3><p>Click a header to sort · the store's own domain shows up as a "referrer"</p></div></div>
      <div class="fill" style="overflow:auto">${sortTable('src', sm, [
        {k:'src',h:'SOURCE / MEDIUM',f:r=>`<span class="trunc" style="max-width:150px">${esc(r.src)}</span>${r.session_source==='shop.googlemerchandisestore.com'?' <span class="pill warn">SELF-REF</span>':''}`},
        {k:'s',h:'SESSIONS',f:r=>fInt(r.s)},{k:'r',h:'REVENUE',f:r=>fUsd(r.r)},
        {k:'rps',h:'REV / SESSION',f:r=>`${fUsd2(r.rps)}<span class="bar" style="width:${(r.rps||0)/mxr*30}px"></span>`}], 's')}</div>
      ${tag('Native table · Sessions[session_source], [session_medium] · [Sessions] [Conversion Rate] [Revenue] [Revenue per Session] (data bars) [Revenue Index] · icon rule for self-referral')}
    </div>
    <div class="card">
      <div class="ct"><div><h3>Device split</h3><p>Share of sessions and conversion by device</p></div></div>
      <div class="fill" style="display:flex;gap:10px;align-items:stretch">${dev.map(d => `<div data-tip="<b>${d.device_category}</b><br>${fInt(d.s)} sessions · ${fUsd(d.r)}<br>Conversion ${fPct(d.cr)} · ${fUsd2(d.rps)} / session" style="flex:${Math.max(d.ss,.12)};background:${T('soft')};border-radius:10px;padding:10px;display:flex;flex-direction:column;justify-content:space-between">
        <div style="font-size:10px;font-weight:700;letter-spacing:1px;color:${T('sub')};text-transform:uppercase">${d.device_category}</div>
        <div style="font-size:20px;font-weight:800;color:${T('acc')}">${fPct(d.ss,0)}</div><div style="font-size:10px;color:${T('sub')}">CR ${fPct(d.cr)}</div></div>`).join('')}</div>
      ${tag('Native 100% bar or HTML · Device × [Session Share], [Conversion Rate]')}
    </div>
    <div class="card insight">
      <div class="lbl2">ATTRIBUTION CHECK</div>
      <div style="display:flex;gap:16px;align-items:flex-end;margin-top:6px"><div class="big">${fPct(k['Self-Referral Revenue Share'],0)}</div>
      <div style="font-size:11px;line-height:1.55;color:#E3E4FF">of revenue (${fUsd(k['Self-Referral Revenue'])}) is credited to the store’s own domain, a checkout redirect rather than a partner. Read Referral’s lead with caution.</div></div>
      ${tag('HTML Content · [02 · 002 Attribution Check HTML] · [Self-Referral Revenue Share] [Self-Referral Revenue] [Event Param Attribution Share]')}
    </div></div>`;
}

/* ================= PAGE 3 · CONTENT ================= */
function page3(){
  const k = P().kpi;
  let lp = P().landing.filter(l => l.page_path && l.s > 0);
  const types = ['all', ...new Set(lp.map(l => l.page_type))];
  if (S.p3type !== 'all') lp = lp.filter(l => l.page_type === S.p3type);
  const quadSvg = (W, H) => { const pl = 40, pr = 12, pt = 14, pb = 28;
  const xs = lp.map(l => Math.log10(l.s)), xmin = Math.min(2.5, ...xs), xmax = Math.max(...xs) + .1;
  const ymax = Math.max(2.2, ...lp.map(l => l.ix || 0)) * 1.05;
  const X = v => pl + (Math.log10(v) - xmin) / (xmax - xmin) * (W - pl - pr), Y = v => pt + (1 - v / ymax) * (H - pt - pb);
  const share2 = lp.length ? null : null;
  const sThresh = (P().pagetype.reduce((a,b)=>a+(b.s||0),0)) * 0.02;
  const ROLE = {'Earner':T('acc'),'Attractor':T('bad'),'Hidden gem':T('good'),'Long tail':T('muted')};
  const mr = Math.max(...lp.map(l => l.r || 0)) || 1;
  const dots = lp.map(l => `<circle cx="${X(l.s)}" cy="${Y(l.ix||0)}" r="${4 + Math.sqrt((l.r||0)/mr)*14}" fill="${ROLE[l.role]||T('muted')}" fill-opacity=".55" stroke="${ROLE[l.role]||T('muted')}" data-tip="<b>${esc(l.page_path)}</b><br>${l.role} · ${l.page_type}<br>${fInt(l.s)} sessions (${fPct(l.ss,1)}) · ${fUsd(l.r)}<br>${fUsd2(l.rps)} / session · index ${(l.ix||0).toFixed(2)}× · CR ${fPct(l.cr)}"/>`).join('');
  const qx = X(sThresh), qy = Y(1);
  return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">
    <rect x="${qx}" y="${pt}" width="${W-pr-qx}" height="${qy-pt}" fill="${T('soft')}"/><rect x="${qx}" y="${qy}" width="${W-pr-qx}" height="${H-pb-qy}" fill="#FDF0F0"/>
    <line x1="${pl}" x2="${W-pr}" y1="${qy}" y2="${qy}" stroke="${T('acc3')}" stroke-dasharray="3 3"/><line x1="${qx}" x2="${qx}" y1="${pt}" y2="${H-pb}" stroke="${T('acc3')}" stroke-dasharray="3 3"/>
    <text x="${W-pr-6}" y="${pt+12}" text-anchor="end" font-size="9.5" font-weight="800" fill="${T('acc')}">EARNERS</text>
    <text x="${W-pr-6}" y="${H-pb-6}" text-anchor="end" font-size="9.5" font-weight="800" fill="${T('bad')}">ATTRACTORS</text>
    <text x="${pl+6}" y="${pt+12}" font-size="9.5" font-weight="800" fill="${T('good')}">HIDDEN GEMS</text>
    <text x="${pl+6}" y="${H-pb-6}" font-size="9.5" font-weight="800" fill="${T('muted')}">LONG TAIL</text>
    <text x="${pl-6}" y="${qy+3}" font-size="9" text-anchor="end" fill="${T('sub')}">1.0×</text>
    <text x="${(pl+W)/2}" y="${H-6}" font-size="9.5" text-anchor="middle" fill="${T('sub')}">Landing sessions (log scale) · line = 2% of sessions</text>
    <text x="10" y="${(pt+H)/2}" font-size="9.5" fill="${T('sub')}" transform="rotate(-90 10 ${(pt+H)/2})" text-anchor="middle">Revenue / session index</text>${dots}</svg>`; };
  const pt3 = P().pagetype.filter(p => p.page_type).sort((a,b) => b.s - a.s);
  const mxsh = Math.max(...pt3.map(p => Math.max(p.ss||0, p.rs||0)));
  const tbl = lp.map(l => ({...l, _tip:`<b>${esc(l.page_path)}</b><br>${l.role}: ${fPct(l.ss,1)} of landing sessions at ${(l.ix||0).toFixed(2)}× the average yield`}));
  return `<div class="body" style="grid-template-columns:1fr 1.1fr;grid-template-rows:1fr 150px">
    <div class="card">
      <div class="ct"><div><h3>Landing pages: traffic vs yield</h3><p>Bubble = revenue · above the line earns more per session than average</p></div></div>
      <div class="chips" style="margin-top:8px" data-chip="p3type">${types.map(t => `<button data-v="${t}" class="${S.p3type===t?'on':''}">${t}</button>`).join('')}</div>
      <div class="fill">${slot('quad', quadSvg)}</div>
      ${tag('Native scatter · Page Type[page_path] · X [Sessions] (log) · Y [Landing RPS Index] · size [Revenue] · legend [Landing Page Role] · chips = Page Type[page_type] slicer')}
    </div>
    <div class="card">
      <div class="ct"><div><h3>Top landing pages</h3><p>Role: traffic ≥ 2% of landing sessions, yield vs the selection average</p></div></div>
      <div class="fill" style="overflow:auto">${sortTable('lp', tbl, [
        {k:'page_path',h:'LANDING PAGE',f:r=>`<span class="trunc" style="max-width:190px">${esc(r.page_path)}</span>`},
        {k:'role',h:'ROLE',f:r=>`<span class="pill ${{'Earner':'acc','Attractor':'bad','Hidden gem':'good'}[r.role]||'mute'}">${r.role}</span>`},
        {k:'s',h:'SESSIONS',f:r=>fInt(r.s)},{k:'rps',h:'REV / SES.',f:r=>fUsd2(r.rps)},
        {k:'ix',h:'INDEX',f:r=>`${(r.ix||0).toFixed(2)}×<span class="bar" style="width:${Math.min((r.ix||0)/3,1)*40}px;background:${(r.ix||0)>=1?T('acc'):T('bad')}"></span>`}], 's')}</div>
      ${tag('Native table · [Landing Page Role] as icon/background rule · [Landing RPS Index] data bar')}
    </div>
    <div class="card" style="grid-column:span 2">
      <div class="ct"><div><h3>By page type</h3><p>Share of landing sessions (light) vs share of revenue (dark)</p></div><div class="legend"><span><i style="background:${T('acc3')}"></i>Sessions</span><span><i style="background:${T('acc')}"></i>Revenue</span></div></div>
      <div class="fill" style="display:flex;gap:10px;align-items:flex-end">${pt3.map(p => `<div data-tip="<b>${p.page_type}</b><br>${fPct(p.ss,1)} of sessions · ${fPct(p.rs,1)} of revenue<br>${fUsd2(p.rps)} / session · CR ${fPct(p.cr)}" style="flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;height:100%">
        <div style="flex:1;width:100%;display:flex;gap:3px;align-items:flex-end;justify-content:center"><div style="width:16px;height:${(p.ss||0)/mxsh*100}%;background:${T('acc3')};border-radius:4px 4px 0 0"></div><div style="width:16px;height:${(p.rs||0)/mxsh*100}%;background:${T('acc')};border-radius:4px 4px 0 0"></div></div>
        <div style="font-size:9.5px;font-weight:700;color:${T('sub')};text-transform:capitalize">${p.page_type}</div></div>`).join('')}</div>
      ${tag('Native clustered column · Page Type[page_type] × [Landing Session Share], [Landing Revenue Share]')}
    </div></div>`;
}

/* ================= PAGE 4 · FUNNEL ================= */
function page4(){
  const k = P().kpi;
  const src = S.p4dim === 'all' ? P().funnel : P().device.find(d => d.device_category === S.p4dim);
  const steps = [['Viewed a product','vi'],['Added to cart','atc'],['Began checkout','bc'],['Added payment','api'],['Purchased','ps']];
  const top = src.vi || 1;
  const rates = steps.map(([,s],i) => i ? (src[s] / src[steps[i-1][1]]) : 1);
  const minR = Math.min(...rates.slice(1)), leak = rates.indexOf(minR);
  const funnel = steps.map(([lab,s],i) => `<div data-tip="<b>${lab}</b><br>${fInt(src[s])} sessions${i?`<br>${fPct(rates[i],1)} of the previous step<br>${fInt(src[steps[i-1][1]]-src[s])} sessions lost here`:''}" style="display:grid;grid-template-columns:112px 1fr 62px 52px;gap:10px;align-items:center;flex:1">
      <div style="font-size:11.5px;font-weight:600">${lab}</div>
      <div style="height:100%;max-height:34px;background:${T('soft')};border-radius:9px;overflow:hidden;display:flex;justify-content:center"><div style="height:100%;width:${Math.max(src[s]/top*100,1.5)}%;background:${i===leak?T('bad'):T('acc')};border-radius:9px;transition:width .4s"></div></div>
      <div style="font-size:12px;font-weight:800;text-align:right">${src[s].toLocaleString('en-US')}</div>
      <div style="font-size:11px;font-weight:700;text-align:right;color:${i===leak?T('bad'):T('sub')}">${i?fPct(rates[i],1):'100%'}</div></div>`).join('');
  const ch = P().funnel_ch.filter(c => c.channel_group && c.vi > 50).sort((a,b) => b.vi - a.vi);
  const stepR = [['View→Cart','vi','atc'],['Cart→Chk','atc','bc'],['Chk→Pay','bc','api'],['Pay→Buy','api','ps']];
  const heat = (v, base) => { const r = Math.max(0, Math.min(1, v)); return `rgba(91,91,214,${(.08 + r*.85).toFixed(2)})`; };
  const hm = `<table style="font-size:10px"><thead><tr><th>CHANNEL</th>${stepR.map(s => `<th>${s[0].toUpperCase()}</th>`).join('')}</tr></thead><tbody>${ch.map(c => `<tr><td style="font-weight:600">${c.channel_group}</td>${stepR.map(([n,a,b],j) => { const v = c[b]/c[a]; const norm = j===4 ? v/0.15 : v; return `<td data-tip="<b>${c.channel_group}</b> · ${n}<br>${fInt(c[b])} of ${fInt(c[a])} sessions = ${fPct(v,1)}" style="text-align:center;padding:3px 2px"><span style="display:block;padding:4px 0;border-radius:6px;background:${heat(norm)};color:${norm>.55?'#fff':T('ink')};font-weight:700">${fPct(v,1)}</span></td>`; }).join('')}</tr>`).join('')}</tbody></table>`;
  const lost = [['View → Cart', src.vi-src.atc],['Cart → Checkout', src.atc-src.bc],['Checkout → Payment', src.bc-src.api],['Payment → Purchase', src.api-src.ps]];
  return `<div class="body" style="grid-template-columns:1.1fr 1fr;grid-template-rows:1fr 150px">
    <div class="card" style="grid-row:span 2">
      <div class="ct"><div><h3>Purchase funnel</h3><p>Sessions reaching each step · % = step-to-step rate · red = biggest leak</p></div>
      <div class="tog" data-tog="p4dim">${['all','desktop','mobile','tablet'].map(v => `<button data-v="${v}" class="${S.p4dim===v?'on':''}">${v==='all'?'All':v[0].toUpperCase()+v.slice(1)}</button>`).join('')}</div></div>
      <div class="fill" style="display:flex;flex-direction:column;gap:8px;padding:6px 0">${funnel}</div>
      <div style="display:flex;gap:10px;margin-top:8px">${lost.map(([n,v],i) => `<div style="flex:1;background:${i+1===leak?'#FDE8E8':T('soft')};border-radius:10px;padding:8px 10px"><div style="font-size:9px;font-weight:700;letter-spacing:.8px;color:${i+1===leak?T('bad'):T('sub')}">LOST · ${n.toUpperCase()}</div><div style="font-size:16px;font-weight:800;color:${i+1===leak?T('bad'):T('ink')}">${fInt(v)}</div></div>`).join('')}</div>
      <div class="foot">${esc(k['Cart Window Note'] || 'All steps counted from Nov 25, when add_to_cart tracking starts in the GA4 sample.')}</div>
      ${tag('HTML Content · [04 · 002 Funnel HTML] (cart-tracked window) · device buttons = native Device slicer (tiles) · lost cards = [Lost at …] measures')}
    </div>
    <div class="card">
      <div class="ct"><div><h3>Step rates by channel</h3><p>Darker = higher pass-through · View→Buy scaled to 15%</p></div></div>
      <div class="fill" style="overflow:auto">${hm}</div>
      ${tag('Native matrix · Channel × step-rate measures · background colour scale (soft → accent)')}
    </div>
    <div class="card insight">
      <div class="lbl2">WHERE TO ACT</div>
      <div style="display:flex;gap:16px;align-items:flex-end;margin-top:6px"><div class="big">${fPct(k['Session to View Item Rate'],0)}</div>
      <div style="font-size:10.5px;line-height:1.5;color:#E3E4FF">of sessions ever open a product page. Fixing view → cart helps the ${fPct(k['Session to View Item Rate'],0)}; getting more visitors to a product page widens the whole funnel. ${(() => { const c = P().funnel_ch.filter(x => x.channel_group && x.vi > 500).map(x => ({n:x.channel_group, r:x.ps/x.vi})).sort((a,b)=>b.r-a.r); return c.length>1 ? `${c[0].n} turns ${fPct(c[0].r,1)} of viewers into buyers vs ${fPct(c[c.length-1].r,1)} for ${c[c.length-1].n}.` : ''; })()}</div></div>
      ${tag('HTML Content · [04 · 003 Where To Act HTML] · [Session to View Item Rate], best/worst channel by [View Item to Purchase Rate]')}
    </div></div>`;
}

/* ================= PAGE 5 · PRODUCTS ================= */
function page5(){
  const k = P().kpi;
  const it = P().items.filter(i => i.item_name).sort((a,b) => b.r - a.r).slice(0, 10);
  const cat = P().category.filter(c => c.item_category).sort((a,b) => b.r - a.r).slice(0, 8);
  const par = P().pareto, n = par.n, cv = par.curve;
  const half = k['Items for Half of Revenue'];
  const paretoSvg = (W, H) => { const pl = 30, pr = 8, pt = 10, pb = 22;
  const X = i => pl + i / (cv.length - 1) * (W - pl - pr), Y = v => pt + (1 - v) * (H - pt - pb);
  const hx = pl + (half / n) * (W - pl - pr);
  return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">
    <line x1="${pl}" x2="${W-pr}" y1="${Y(.5)}" y2="${Y(.5)}" stroke="${T('acc3')}" stroke-dasharray="3 3"/>
    <line x1="${hx}" x2="${hx}" y1="${Y(.5)}" y2="${H-pb}" stroke="${T('acc')}" stroke-dasharray="3 3"/>
    <path d="M${X(0)},${Y(0)}${cv.map((v,i) => 'L'+X(i).toFixed(1)+','+Y(v).toFixed(1)).join('')}L${X(cv.length-1)},${H-pb}L${X(0)},${H-pb}Z" fill="${T('acc')}" fill-opacity=".12"/>
    <path d="M${X(0)},${Y(0)}${cv.map((v,i) => 'L'+X(i).toFixed(1)+','+Y(v).toFixed(1)).join('')}" fill="none" stroke="${T('acc')}" stroke-width="2"/>
    <circle cx="${hx}" cy="${Y(.5)}" r="4.5" fill="${T('acc')}" stroke="#fff" stroke-width="2"/>
    <text x="${hx+7}" y="${Y(.5)+14}" font-size="9.5" font-weight="800" fill="${T('ink')}">${half} items = 50%</text>
    <text x="${pl-5}" y="${Y(.5)+3}" font-size="9" text-anchor="end" fill="${T('sub')}">50%</text><text x="${pl-5}" y="${Y(1)+3}" font-size="9" text-anchor="end" fill="${T('sub')}">100%</text>
    <text x="${(pl+W)/2}" y="${H-5}" font-size="9" text-anchor="middle" fill="${T('sub')}">${n} items sold, best first</text></svg>`; };
  const mxc = Math.max(...cat.map(c => c.r));
  return `<div class="body" style="grid-template-columns:1.25fr 1fr 0.9fr;grid-template-rows:1fr 120px">
    <div class="card" style="grid-row:span 2">
      <div class="ct"><div><h3>Top 10 items by revenue</h3><p>Bar = item revenue · line below = units × avg price · ${esc(k['Top Item'])} leads</p></div></div>
      <div class="fill" style="overflow:auto">${sortTable('it', it.map((r,i) => ({...r, rank:i+1, _tip:`<b>${esc(r.item_name)}</b><br>${r.item_category}<br>${fUsd(r.r)} · ${fInt(r.u)} units at ${fUsd2(r.p)}<br>${fPct(r.sh,2)} of item revenue`})), [
        {k:'rank',h:'#',f:r=>`<span style="color:${T('muted')};font-weight:700">${r.rank}</span>`},
        {k:'item_name',h:'ITEM',f:r=>`<span class="trunc" style="max-width:170px;text-align:left;display:block">${esc(r.item_name)}</span>`},
        {k:'r',h:'REVENUE',f:r=>`${fUsd(r.r)}<span class="bar" style="width:${r.r/it[0].r*34}px"></span>`},
        {k:'u',h:'UNITS',f:r=>fInt(r.u)},{k:'p',h:'AVG PRICE',f:r=>fUsd2(r.p)}], 'r')}</div>
      <div class="foot">Ten items = ${fPct(k['Top 10 Item Revenue Share'],0)} of item revenue: the catalogue is broad, not hit-driven.</div>
      ${tag('Native table · Items Daily[item_name] · [Item Revenue Rank] [Item Revenue] (data bar) [Units Purchased] [Avg Item Price] [Item Revenue Share] · Top N filter = 10 by [Item Revenue]')}
    </div>
    <div class="card">
      <div class="ct"><div><h3>Revenue by category</h3><p>${esc(k['Top Category'])} is ${fPct(k['Top Category Revenue Share'],0)} of item revenue</p></div></div>
      <div class="fill" style="display:flex;flex-direction:column;justify-content:space-around">${hbars(cat, {label:c=>c.item_category, value:c=>c.r, fmt:fUsd, color:(c)=>c===cat[0]?T('acc'):T('acc3'), max:mxc,
        sub:c=>`${fInt(c.u)} units · ${fUsd2(c.p)} avg`, tipf:c=>`<b>${c.item_category}</b><br>${fUsd(c.r)} (${fPct(c.sh,1)})<br>${fInt(c.u)} units at ${fUsd2(c.p)}`})}</div>
      ${tag('Native bar · Items Daily[item_category] × [Item Revenue] · Top N = 8')}
    </div>
    <div class="card">
      <div class="ct"><div><h3>Revenue concentration</h3><p>Cumulative share of item revenue</p></div></div>
      <div class="fill">${slot('pareto', paretoSvg)}</div>
      ${tag('HTML Content · [05 · 002 Pareto HTML] fed by [Items for Half of Revenue] + cumulative series')}
    </div>
    <div class="card" style="grid-column:span 2;background:#FFF9EC;box-shadow:none;border:1px solid #F5DDA6">
      <div style="display:flex;gap:14px;align-items:center;height:100%">
        <span class="pill warn" style="font-size:11px">DATA NOTE</span>
        <div style="font-size:11px;line-height:1.55;color:#7C4A03">Item-level views are under-counted in gold: add-to-carts (37,262) exceed item views (27,585), so the deployed <b>Add-to-Cart Rate</b> reads 135%. This page uses revenue, units and price only until <code>nb_gold_ga4_marketing</code> keeps <code>view_item</code> rows with a null quantity. Session-level funnel (page 4) is unaffected.</div>
      </div>
      ${tag('Text box bound to [Item Data Check] (blank once the gold fix lands)')}
    </div></div>`;
}

/* ================= PAGE 6 · TIME INTELLIGENCE ================= */
function page6(){
  const k = P().kpi, m = S.p6metric || 'r', {s: rs, e: re} = S.range;
  const td = D.ti_daily.filter(r => r.date).map(r => ({...r, d: r.date.slice(0,10)}));
  const fm = m === 'r' ? fUsd : fInt;
  const rollSvg = (W, H) => { const pl = 42, pr = 12, pt = 26, pb = 22;
    const vals = td.map(r => (DAYMAP[r.d] || {})[m] ?? 0), a7 = td.map(r => r[m+'7']), a28 = td.map(r => r[m+'28']);
    const mx = Math.max(...vals) * 1.06, n = td.length;
    const x = i => pl + i * (W - pl - pr) / (n - 1), y = v => pt + (1 - v / mx) * (H - pt - pb), bw = (W - pl - pr) / n * .7;
    const line = arr => arr.map((v,i) => nz(v) ? '' : `${(i && !nz(arr[i-1])) ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('');
    let grid = ''; for (let g = 0; g <= 3; g++) { const gv = mx * g / 3; grid += `<line x1="${pl}" x2="${W-pr}" y1="${y(gv)}" y2="${y(gv)}" stroke="${T('line')}"/><text x="${pl-8}" y="${y(gv)+3}" font-size="9.5" fill="${T('muted')}" text-anchor="end">${fInt(gv)}</text>`; }
    const inSel = r => r.d >= rs && r.d <= re;
    const bars = td.map((r,i) => `<rect x="${x(i)-bw/2}" y="${y(vals[i])}" width="${bw}" height="${H-pb-y(vals[i])}" rx="1.5" fill="${T('acc3')}" fill-opacity="${inSel(r)?.8:.22}"/>`).join('');
    const last = td.map((r,i) => r.d <= re ? i : -1).filter(i => i >= 0).pop();
    const months = [['Nov',0],['Dec',30],['Jan',61]].map(([t,i]) => `<text x="${x(i)}" y="${H-5}" font-size="10" fill="${T('sub')}" font-weight="600">${t}</text>`).join('');
    const hits = td.map((r,i) => `<rect x="${x(i)-bw/2-1}" y="${pt}" width="${bw+2}" height="${H-pt-pb}" fill="transparent" data-tip="<b>${sd(r.d)}</b><br>Day ${fm(vals[i])}<br>7-day avg ${fm(a7[i])}<br>28-day avg ${fm(a28[i])}"/>`).join('');
    const e7 = a7[last], e28 = a28[last], mom = nz(e28) ? null : (e7 - e28) / e28;
    const lx = Math.max(pl + 64, Math.min(x(last), W - pr - 64));
    const callout = nz(e7) ? '' : `<g><line x1="${x(last)}" x2="${x(last)}" y1="${pt}" y2="${H-pb}" stroke="${T('ink')}" stroke-dasharray="2 3" stroke-opacity=".5"/>
      <rect x="${lx-62}" y="${pt-22}" width="124" height="18" rx="9" fill="${T('ink')}"/>
      <text x="${lx}" y="${pt-9.5}" font-size="9.5" font-weight="800" fill="#fff" text-anchor="middle">${nz(mom)?'7D AVG '+fm(e7):'7D vs 28D  '+(mom>=0?'+':'−')+fPct(Math.abs(mom),0)}</text></g>`;
    return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">${grid}${bars}
      <path d="${line(a28)}" fill="none" stroke="${T('ink')}" stroke-width="1.6" stroke-dasharray="5 4" stroke-opacity=".7"/>
      <path d="${line(a7)}" fill="none" stroke="${T('acc')}" stroke-width="2.4"/>${months}${callout}${hits}</svg>`; };

  const months3 = [['2020-11','Nov'],['2020-12','Dec'],['2021-01','Jan']];
  const focus = re.slice(0,7), prevYm = {'2020-12':'2020-11','2021-01':'2020-12'}[focus];
  const mk = m === 'r' ? 'rmtd' : 'smtd', mname = y => months3.find(z => z[0] === y)[1];
  const paceSvg = (W, H) => { const pl = 42, pr = 36, pt = 10, pb = 22;
    const ser = months3.map(([y,t]) => [y, t, td.filter(r => r.year_month === y)]);
    const mx = Math.max(...td.map(r => r[mk] || 0)) * 1.05;
    const x = d => pl + (d - 1) / 30 * (W - pl - pr), y = v => pt + (1 - v / mx) * (H - pt - pb);
    let grid = ''; for (let g = 0; g <= 3; g++) { const gv = mx * g / 3; grid += `<line x1="${pl}" x2="${W-pr}" y1="${y(gv)}" y2="${y(gv)}" stroke="${T('line')}"/><text x="${pl-8}" y="${y(gv)+3}" font-size="9.5" fill="${T('muted')}" text-anchor="end">${fInt(gv)}</text>`; }
    const col = yy => yy === focus ? T('acc') : yy === prevYm ? T('ink') : T('acc3');
    const ends = ser.map(([yy,t,rs2]) => ({yy, t, ly: y(rs2[rs2.length-1][mk]) + 3})).sort((p,q) => p.ly - q.ly);
    ends.forEach((e2,i) => { if (i && e2.ly - ends[i-1].ly < 12) e2.ly = ends[i-1].ly + 12; });
    const lines = ser.map(([yy,t,rs2]) => { const last = rs2[rs2.length-1], ly = ends.find(e2 => e2.yy === yy).ly;
      return `<path d="${rs2.map((r,i) => (i?'L':'M') + x(r.day_of_month).toFixed(1) + ',' + y(r[mk]).toFixed(1)).join('')}" fill="none" stroke="${col(yy)}" stroke-width="${yy===focus?2.6:1.6}" ${yy===prevYm?'stroke-dasharray="5 3"':''}/>
        <text x="${x(last.day_of_month)+5}" y="${ly}" font-size="10" font-weight="800" fill="${col(yy)}">${t}</text>`; }).join('');
    const hits = Array.from({length:31}, (_,i) => i+1).map(d => { const v = ser.map(([yy,t,rs2]) => [t, (rs2.find(r => r.day_of_month === d) || {})[mk]]);
      return `<rect x="${x(d)-4}" y="${pt}" width="8" height="${H-pt-pb}" fill="transparent" data-tip="<b>Day ${d} of the month</b><br>${v.map(([t,vv]) => `${t}: ${fm(vv)}`).join('<br>')}"/>`; }).join('');
    const ticks = [1,8,15,22,29].map(d => `<text x="${x(d)}" y="${H-5}" font-size="9.5" fill="${T('sub')}" text-anchor="middle">${d}</text>`).join('');
    return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">${grid}${lines}${ticks}${hits}</svg>`; };

  const wd = P().weekday.filter(w => w.day_short);
  const mxi = Math.max(1.3, ...wd.map(w => w.ix || 0));
  const dowSvg = (W, H) => { const pl = 4, pr = 4, pt = 18, pb = 20, n = wd.length, bw = (W - pl - pr) / n;
    const y = v => pt + (1 - v / mxi) * (H - pt - pb);
    const bars = wd.map((w,i) => { const best = w.day_name === k['Best Weekday'];
      return `<g data-tip="<b>${w.day_name}</b> · ${w.days} days<br>${fUsd(w.adr)} revenue per day<br>${(w.ix||0).toFixed(2)}× a typical day · conversion ${fPct(w.cr)}">
      <rect x="${pl+i*bw+bw*.2}" y="${y(w.ix||0)}" width="${bw*.6}" height="${H-pb-y(w.ix||0)}" rx="5" fill="${w.is_weekend?T('muted'):best?T('acc'):T('acc2')}" fill-opacity="${w.is_weekend?.45:1}"/>
      <text x="${pl+i*bw+bw/2}" y="${y(w.ix||0)-5}" font-size="9.5" font-weight="800" text-anchor="middle" fill="${best?T('acc'):T('ink')}">${(w.ix||0).toFixed(2)}×</text>
      <text x="${pl+i*bw+bw/2}" y="${H-5}" font-size="10" font-weight="600" text-anchor="middle" fill="${T('sub')}">${w.day_short}</text></g>`; }).join('');
    return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}"><line x1="${pl}" x2="${W-pr}" y1="${y(1)}" y2="${y(1)}" stroke="${T('ink')}" stroke-dasharray="3 3" stroke-opacity=".35"/>${bars}</svg>`; };

  const mtd = k['Revenue MTD vs PMTD %'];
  return `<div class="body" style="grid-template-columns:1.4fr 1fr .9fr;grid-template-rows:168px 1fr">
    <div class="card" style="grid-column:1;grid-row:1">
      <div class="ct"><div><h3>${m==='r'?'Revenue':'Sessions'} · 7 vs 28-day average</h3></div>
      <div style="display:flex;gap:16px;align-items:center">
      <div class="tog" data-tog="p6metric">${[['r','Revenue'],['s','Sessions']].map(([v,t]) => `<button data-v="${v}" class="${m===v?'on':''}">${t}</button>`).join('')}</div></div></div>
      <div class="fill" style="margin-top:8px">${slot('roll', rollSvg)}</div>
      ${tag('Native combo chart · Date[date] · columns [Revenue] · lines [Revenue 7D Avg], [Revenue 28D Avg] · field parameter for Revenue / Sessions')}
    </div>
    <div class="card" style="grid-column:3;grid-row:1">
      <div class="ct"><div><h3>Day-of-week pattern</h3></div></div>
      <div class="fill">${slot('dow', dowSvg)}</div>
      <div class="foot" style="margin-top:4px">Weekends: ${fPct(k['Weekend Day Share'],0)} of days, ${fPct(k['Weekend Revenue Share'],0)} of revenue.</div>
      ${tag('Native column chart · Date[day_short] × [Weekday Revenue Index] · reference line at 1.0')}
    </div>
    <div class="card" style="grid-column:1 / span 3;grid-row:2">
      <div class="ct"><div><h3>Rolling windows</h3><p>Last 7, 14 and 28 days up to ${sd(re)} vs the window just before</p></div><span class="pill acc">ENDS ${sd(re).toUpperCase()}</span></div>
      <div class="fill" style="margin-top:8px">${rollTable()}</div>
      ${tag('HTML Content · [06 · 003 Rolling Table HTML] · [<metric> L7D / P7D / L7D Δ%] … [L28D] measures in Base\\Time\\Rolling Windows')}
    </div>
    <div class="card" style="grid-column:2;grid-row:1">
      <div class="ct"><div><h3>Month-to-date pacing</h3></div></div>
      <div class="fill" style="margin-top:8px">${slot('pace', paceSvg)}</div>
      <div class="foot" style="margin-top:6px">${nz(mtd) ? 'November has no October to pace against.' : `${mname(focus)} is <b style="color:${mtd>=0?T('good'):T('bad')}">${mtd>=0?'+':'−'}${fPct(Math.abs(mtd),0)}</b> on revenue ${esc(k['MTD Label'])}.`}</div>
      ${tag('Native line chart · Date[day_of_month] × [Revenue MTD] · legend Date[month_short]')}
    </div></div>`;
}


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
