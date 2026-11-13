// Run against the local preview. PLAYWRIGHT_MODULE may point to an existing install.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {resolve}=require('node:path');
const root=resolve(__dirname,'..');
const base=process.env.PREVIEW_URL||'http://localhost:4173';
const results=[];const errors=[];const failedRequests=[];
const fixture=JSON.parse(fs.readFileSync(resolve(root,'data/preview-fixture.json'),'utf8'));
const pathFor=n=>n==='welcome'?'/':n==='components'?'/components/index.html':`/pages/${n}.html`;
async function ready(p){await p.waitForFunction(()=>document.querySelectorAll('.kpi,.cover,.kit-colors').length>0);await p.evaluate(()=>document.fonts.ready);}
async function check(name,fn){await fn();results.push({name,result:'passed'});}
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']});
 const ctx=await browser.newContext({viewport:{width:1600,height:900},acceptDownloads:true});const p=await ctx.newPage();
 p.on('pageerror',e=>errors.push(e.message));p.on('console',m=>{if(m.type()==='error')errors.push(m.text())});p.on('response',r=>{if(r.status()>=400)failedRequests.push({url:r.url(),status:r.status()})});
 for(const page of ['welcome','overview','acquisition','content','funnel','components']){
  await p.goto(base+pathFor(page));await ready(p);
  await check(page+' desktop layout',async()=>{assert.equal(await p.locator('h1').count(),1);assert.equal(await p.locator('.empty').count(),0);assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));});
  await p.screenshot({path:resolve(root,`qa/${page}-desktop.png`),fullPage:true});
 }
 await p.goto(base+'/pages/overview.html');await ready(p);
 await check('period filter recalculates revenue and prior-period delta',async()=>{await p.locator('[data-filter=period]').selectOption('jan');const expected=fixture.sessions.filter(r=>r.date.startsWith('2021-01')).reduce((s,r)=>s+r.revenue,0);assert.equal(await p.locator('.kpi-value').first().textContent(),new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(expected));assert.ok(await p.locator('.delta:not(.neutral)').count()>0)});
 await check('trend chart switch',async()=>{await p.locator('[data-action=trend][data-value=sessions]').click();assert.equal(await p.locator('[data-action=trend][data-value=sessions]').getAttribute('aria-pressed'),'true');assert.equal(await p.locator('h2').first().textContent(),'Sessions over time');});
 await check('navigation retains period filter',async()=>{await p.locator('.nav-item').filter({hasText:'Acquisition'}).click();await ready(p);assert.equal(await p.locator('[data-filter=period]').inputValue(),'jan')});
 await check('channel ranking switch and human-readable geo labels',async()=>{await p.locator('[data-action=rank][data-value=rps]').click();assert.equal(await p.locator('[data-action=rank][data-value=rps]').getAttribute('aria-pressed'),'true');const ticks=await p.evaluate(()=>Chart.getChart('geo-device').scales.x.ticks.map(t=>t.label));assert.ok(ticks.some(t=>String(t).includes('United')));});
 await check('keyboard detail dialog and Escape',async()=>{const row=p.locator('tr[data-detail=channel]').first();await row.focus();await p.keyboard.press('Enter');assert.ok(await p.locator('dialog').isVisible());await p.keyboard.press('Escape');assert.ok(!(await p.locator('dialog').isVisible()));});
 await check('intersected channel/device filters and CSV export',async()=>{await p.locator('[data-filter=channel]').selectOption('Direct');await p.locator('[data-filter=device]').selectOption('mobile');const downloadPromise=p.waitForEvent('download');await p.locator('[data-action=export]').click();const dl=await downloadPromise;const file=resolve(root,'qa/export-filtered.csv');await dl.saveAs(file);const csv=fs.readFileSync(file,'utf8');assert.match(csv,/synthetic-design-fixture/);const lines=csv.trim().split(/\r?\n/);const expected=fixture.sessions.filter(r=>r.date.startsWith('2021-01')&&r.channel==='Direct'&&r.device==='mobile');assert.equal(lines.length,expected.length+1);assert.ok(lines.slice(1).every(l=>l.includes('"Direct"')&&l.includes('"mobile"')));});
 await p.goto(base+'/pages/content.html');await ready(p);
 await check('content excludes unsupported filters',async()=>{assert.equal(await p.locator('[data-filter=channel]').count(),0);assert.equal(await p.locator('[data-filter=device]').count(),0);});
 await check('landing search, empty state, clear and sort',async()=>{await p.locator('#page-search').fill('no-such-landing-page');assert.match(await p.locator('.empty').textContent(),/No landing pages/);assert.equal(await p.locator('.kpi-value').nth(1).textContent(),'—');await p.locator('[data-action=clear-search]').click();await p.locator('#page-search').fill('Apparel');assert.ok(await p.locator('tbody tr').count()>0);assert.ok((await p.locator('tbody tr').allTextContents()).every(t=>t.includes('Apparel')));await p.locator('#page-search').fill('');await p.locator('[data-action=sort][data-value=sessions]').click();assert.equal(await p.locator('th[aria-sort]').getAttribute('aria-sort'),'descending');await p.locator('[data-action=sort][data-value=sessions]').click();assert.equal(await p.locator('th[aria-sort]').getAttribute('aria-sort'),'ascending');});
 await p.goto(base+'/pages/funnel.html');await ready(p);
 await check('products ignore channel/device and respect category',async()=>{await p.locator('[data-action=reset]').click();const value=await p.locator('tr[data-detail=item]').first().textContent();await p.locator('[data-filter=channel]').selectOption('Referral');await p.locator('[data-filter=device]').selectOption('mobile');assert.equal(await p.locator('tr[data-detail=item]').first().textContent(),value);await p.locator('[data-filter=category]').selectOption('Drinkware');assert.equal(await p.locator('tr[data-detail=item]').count(),2);assert.ok((await p.locator('tr[data-detail=item]').allTextContents()).every(t=>t.includes('Drinkware')));});
 await check('local event reach device control',async()=>{await p.locator('[data-action=reset]').click();const before=await p.locator('.journey-step strong').first().textContent();await p.locator('[data-action=funnelDevice][data-value=desktop]').click();const after=await p.locator('.journey-step strong').first().textContent();assert.notEqual(after,before)});
 await check('scoped product CSV export',async()=>{await p.locator('[data-filter=category]').selectOption('Drinkware');const promise=p.waitForEvent('download');await p.locator('[data-action=export-items]').click();const dl=await promise;await dl.saveAs(resolve(root,'qa/export-products.csv'));const csv=fs.readFileSync(resolve(root,'qa/export-products.csv'),'utf8');assert.match(csv,/Drinkware/);assert.ok(!csv.includes('Apparel'));});
 await check('source dialog',async()=>{await p.locator('[data-action=sources]').first().click();assert.match(await p.locator('dialog').textContent(),/synthetic/i);await p.locator('[data-action=close-dialog]').click()});
 await check('reset clears global and local filters',async()=>{await p.locator('[data-action=reset]').click();assert.equal(await p.locator('[data-filter=period]').inputValue(),'all');assert.equal(await p.locator('[data-filter=channel]').inputValue(),'');assert.equal(await p.locator('[data-filter=category]').inputValue(),'');});
 await p.goto(base+'/components/index.html');await ready(p);
 await check('kit downloads and guide links',async()=>{for(const el of await p.locator('.spec-links a').all()){const href=await el.getAttribute('href');if(href.startsWith('http')){const r=await p.request.get(href);assert.ok(r.ok(),href)}}});
 for(const width of [390,768]){
  const mobile=await ctx.newPage();await mobile.setViewportSize({width,height:844});mobile.on('pageerror',e=>errors.push(e.message));
  for(const page of ['welcome','overview','acquisition','content','funnel','components']){await mobile.goto(base+pathFor(page));await ready(mobile);await check(`${page} responsive at ${width}px`,async()=>{assert.ok(await mobile.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'page overflow');assert.ok(await mobile.locator('.nav-item').first().isVisible())});if(width===390)await mobile.screenshot({path:resolve(root,`qa/${page}-mobile.png`),fullPage:true});}
  if(width===390)await check('mobile navigation works',async()=>{await mobile.locator('.nav-item').filter({hasText:'Overview'}).click();await ready(mobile);assert.match(await mobile.locator('h1').textContent(),/Executive/)});
  await mobile.close();
 }
 await check('no browser console errors or failed local resources',async()=>{assert.deepEqual(errors,[]);assert.deepEqual(failedRequests,[])});
 await browser.close();
 fs.writeFileSync(resolve(root,'qa/browser-results.json'),JSON.stringify({testedAt:new Date().toISOString(),base,viewports:[[1600,900],[390,844],[768,844]],checks:results,consoleErrors:errors,failedRequests},null,2));
 console.log(`PASS ${results.length} browser checks.`);
})().catch(e=>{console.error(e);process.exit(1)});
