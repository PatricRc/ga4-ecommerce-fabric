export const channels=['Direct','Organic Search','Referral','Paid Search','Organic Social','Unassigned'];
export const colors=['#6550d9','#9887eb','#b8a9ed','#423293','#628fe8','#d9d3ed'];
export const periods={all:['2020-11-01','2021-01-31'],nov:['2020-11-01','2020-11-30'],dec:['2020-12-01','2020-12-31'],jan:['2021-01-01','2021-01-31']};
export const periodLabels={all:'Nov 2020 – Jan 2021',nov:'November 2020',dec:'December 2020',jan:'January 2021'};
export const num=x=>new Intl.NumberFormat('en-US',{maximumFractionDigits:0}).format(x);
export const money=x=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(x);
export const dollars=x=>Number.isFinite(x)?new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',minimumFractionDigits:2,maximumFractionDigits:2}).format(x):'—';
export const compact=x=>new Intl.NumberFormat('en-US',{notation:'compact',maximumFractionDigits:1}).format(x);
export const pct=x=>Number.isFinite(x)?(x*100).toFixed(2)+'%':'—';
export const ratio=(a,b)=>b?a/b:null;
export const sum=(rows,key)=>rows.reduce((s,r)=>s+(Number(r[key])||0),0);
export function metrics(rows){const m=Object.fromEntries(['sessions','revenue','purchases','purchase_sessions','engaged','pageviews','view_item','add_to_cart','begin_checkout','add_payment'].map(k=>[k,sum(rows,k)]));return {...m,cvr:ratio(m.purchase_sessions,m.sessions),engagement:ratio(m.engaged,m.sessions),rps:ratio(m.revenue,m.sessions),aov:ratio(m.revenue,m.purchases)};}
export function grouped(rows,key){const groups=new Map();for(const r of rows){const k=typeof key==='function'?key(r):r[key];if(!groups.has(k))groups.set(k,[]);groups.get(k).push(r);}return [...groups].map(([name,values])=>({name,rows:values,...metrics(values)}));}
export function filtered(rows,state,{session=true,content=false,product=false}={}){const [start,end]=periods[state.period];return rows.filter(r=>r.date>=start&&r.date<=end&&(!session||!state.channel||r.channel===state.channel)&&(!session||!state.device||r.device===state.device)&&(!content||!state.type||r.page_type===state.type)&&(!content||!state.search||r.path.toLowerCase().includes(state.search.toLowerCase()))&&(!product||!state.category||r.category===state.category));}
export function comparison(fixture,state,options={}){if(state.period==='all'||state.period==='nov')return null;const prior={...state,period:state.period==='jan'?'dec':'nov'};return metrics(filtered(fixture.sessions,prior,options));}
export function delta(current,previous,kind='relative'){if(!Number.isFinite(current)||!Number.isFinite(previous)||previous===0)return null;return kind==='points'?(current-previous)*100:100*(current-previous)/previous;}
export function safe(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
