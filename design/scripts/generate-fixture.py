"""Deterministic DESIGN FIXTURE. No observed dimension or daily values are implied."""
from pathlib import Path
import json, random, math, datetime
random.seed(44)
ROOT = Path(__file__).resolve().parents[1]
channels = ['Direct','Organic Search','Referral','Paid Search','Organic Social','Unassigned']
devices = ['desktop','mobile','tablet']
countries = ['United States','Canada','United Kingdom','Germany','India','Australia']
pages = [('/', 'home'),('/Google+Redesign/Apparel','category'),('/Google+Redesign/Drinkware','category'),('/Google+Redesign/Accessories','category'),('/Google+Redesign/Shop+by+Brand/YouTube','category'),('/Google+Redesign/Apparel/Google+Tee','product'),('/Google+Redesign/search','search'),('/other','other')]
def allocate(total, weights):
    nums = [total*w/sum(weights) for w in weights]
    base = [int(n) for n in nums]
    for i in sorted(range(len(nums)),key=lambda i:nums[i]-base[i],reverse=True)[:total-sum(base)]: base[i]+=1
    return base
rows=[]; weights=[]
for day in range(92):
    date=datetime.date(2020,11,1)+datetime.timedelta(days=day)
    holiday=1+1.4*math.exp(-((day-26)/3)**2)+.9*math.exp(-((day-42)/6)**2)
    for ci,ch in enumerate(channels):
      for di,device in enumerate(devices):
       for pi,(path,typ) in enumerate(pages):
        weights.append([.40,.27,.16,.09,.04,.04][ci]*[.59,.38,.03][di]*[.34,.18,.12,.10,.09,.06,.06,.05][pi]*holiday*(.9+.16*math.sin(day*.7)+random.random()*.4))
        rows.append({'date':date.isoformat(),'channel':ch,'device':device,'country':countries[(day+ci+di+pi)%6],'source':{'Direct':'(direct)','Organic Search':'google','Referral':'shop.googlemerchandisestore.com','Paid Search':'google','Organic Social':'youtube.com','Unassigned':'(not set)'}[ch],'medium':{'Direct':'(none)','Organic Search':'organic','Referral':'referral','Paid Search':'cpc','Organic Social':'social','Unassigned':'(not set)'}[ch],'path':path,'page_type':typ})
sessions=allocate(360129,weights)
purchase=[0]*len(rows)
for i in random.choices(range(len(rows)),weights=[n*[.016,.012,.019,.015,.006,.004][channels.index(r['channel'])]*[1.25,.55,.8][devices.index(r['device'])] for n,r in zip(sessions,rows)],k=4848): purchase[i]+=1
assert all(p<=n for p,n in zip(purchase,sessions))
revenue=allocate(36216500,[p*(60+random.random()*40) for p in purchase])
events=allocate(4896,purchase)
checkout=allocate(11106,[p+sessions[i]*.013 for i,p in enumerate(purchase)])
views=allocate(1350428,[n*(2.6+random.random()*2) for n in sessions])
for i,r in enumerate(rows):
    n=sessions[i]; p=purchase[i]
    r.update(sessions=n,purchase_sessions=p,purchases=events[i],revenue=revenue[i]/100,engaged=round(n*(.47+random.random()*.24)),pageviews=views[i],view_item=round(n*.35),add_to_cart=round(n*.087),begin_checkout=checkout[i],add_payment=round(checkout[i]*.66))
items=[]
names=[('Google Crewneck Sweatshirt','Apparel'),('Google Eco Tee','Apparel'),('YouTube Logo Hoodie','Apparel'),('Google Camp Mug','Drinkware'),('Chrome Insulated Bottle','Drinkware'),('Google Campus Backpack','Accessories'),('Google Cotton Tote','Accessories'),('Android Mini Collectible','Lifestyle'),('Google Notebook Set','Stationery'),('YouTube Sticker Pack','Stationery')]
for day in range(92):
 date=(datetime.date(2020,11,1)+datetime.timedelta(days=day)).isoformat()
 for i,(name,cat) in enumerate(names):
  v=round((160-i*12)*(.6+random.random()*.8)); cart=round(v*(.09+random.random()*.12)); units=round(cart*(.3+random.random()*.4))
  items.append({'date':date,'item_id':f'DEMO-{i+1:03}','item_name':name,'category':cat,'item_views':v,'add_to_carts':cart,'units':units,'item_revenue':round(units*[54,24,58,18,32,45,15,12,16,5][i],2)})
fixture={'metadata':{'classification':'synthetic-design-fixture','warning':'All preview observations are synthetic, including dates, trends, segments, items and comparisons. Some full-window totals deliberately match README validation checkpoints for scale only. Not connected to Fabric.','source_commit':'REPLACE_AT_GENERATION','period':['2020-11-01','2021-01-31'],'verified_repo_checkpoints':{'sessions':360129,'revenue_usd':362165,'pageviews':1350428,'purchase_sessions':4848,'begin_checkout_sessions':11106},'fixture_only':True},'sessions':rows,'items':items}
import subprocess
fixture['metadata']['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT.parent,text=True).strip()
(ROOT/'data/preview-fixture.json').write_text(json.dumps(fixture,separators=(',',':')))
print(f'Wrote {len(rows)} session aggregate fixture rows and {len(items)} item fixture rows')
