from pathlib import Path
import json, ast, subprocess
ROOT=Path(__file__).resolve().parents[1]
W=1432; X=128; gap=20
def rect(id,title,x,y,w,h,kind='visual',measures=None,scope=None):
 return {'id':id,'title':title,'kind':kind,'rect':{'x':x,'y':y,'width':w,'height':h},'visualRect':{'x':x+18,'y':y+(12 if kind=='kpi' else 44),'width':w-36,'height':h-(24 if kind=='kpi' else 60)},'measures':measures or [],'filterScope':scope or ['Date','Channel','Device']}
def kpis(names):
 width=(W-(len(names)-1)*gap)/len(names)
 return [rect('kpi-'+str(i),name,round(X+i*(width+gap),1),168,round(width,1),128,'kpi',[name]) for i,name in enumerate(names)]
shared=['Revenue','Sessions','Conversion Rate','Purchases','Revenue per Session']
pages={
'overview':{'title':'Executive overview','cards':kpis(shared)+[
rect('trend','Revenue over time',128,316,924,250,measures=['Revenue','Sessions']),
rect('channel-mix','Revenue by channel',1072,316,488,250,measures=['Revenue']),
rect('channel-table','Channel performance',128,586,924,250,measures=shared),
rect('device-mix','Sessions by device',1072,586,488,250,measures=['Sessions'])]},
'acquisition':{'title':'Acquisition','cards':kpis(shared)+[
rect('source-matrix','Which sources bring value?',128,316,924,280,measures=shared+['Engagement Rate']),
rect('channel-rank','Channel ranking',1072,316,488,280,measures=['Revenue','Revenue per Session']),
rect('geo-device','Revenue by country & device',128,616,706,220,measures=['Revenue']),
rect('device-conversion','Device conversion',854,616,706,220,measures=['Conversion Rate'])]},
'content':{'title':'Content & landing pages','cards':kpis(['Sessions','Engagement Rate','Conversion Rate','Revenue per Session'])+[
rect('traffic-value','Traffic quality by landing page',128,316,924,230,measures=['Sessions','Revenue per Session'],scope=['Date','Page Type']),
rect('type-revenue','Revenue by page type',1072,316,488,230,measures=['Revenue'],scope=['Date','Page Type']),
rect('landing-table','Landing-page performance',128,566,1432,270,measures=['Sessions','Engagement Rate','Conversion Rate','Revenue','Revenue per Session'],scope=['Date','Page Type'])]},
'funnel':{'title':'Funnel & products','cards':kpis(['View Item Sessions','Begin Checkout Sessions','Purchase Sessions','Checkout to Purchase Ratio'])+[
rect('event-reach','Shopping event reach',128,316,706,245,measures=['View Item Sessions','Add to Cart Sessions','Begin Checkout Sessions','Add Payment Info Sessions','Purchase Sessions']),
rect('device-event-reach','Event reach by device',854,316,706,245,measures=['View Item Sessions','Add to Cart Sessions','Begin Checkout Sessions','Purchase Sessions','Sessions']),
rect('products','Product performance',128,581,1432,255,measures=['Item Views','Add to Carts','Add-to-Cart Rate','Item Revenue'],scope=['Date','Category'])]},
'welcome':{'title':'Welcome','cards':[rect('chapter-'+str(i+1),title,128+i*363,630,343,206,'chapter',scope=[]) for i,title in enumerate(['The big picture','Where visits begin','What earns attention','The path to purchase'])]}}
for c in pages['content']['cards']: c['filterScope']=['Date','Page Type']
navigation=[{'page':page,'label':label,'icon':icon,'rect':{'x':12,'y':130+i*85,'width':64,'height':64}} for i,(page,label,icon) in enumerate([('welcome','Welcome','house-door'),('overview','Overview','grid-1x2'),('acquisition','Acquisition','diagram-3'),('content','Content','file-earmark-bar-graph'),('funnel','Funnel','funnel')])]
layout={'canvas':{'width':1600,'height':900,'background':'#F5F4FA'},'header':{'x':128,'y':25,'width':1432,'height':70},'filters':{'x':128,'y':112,'width':1432,'height':40},'footer':{'x':128,'y':858,'width':1432,'height':24},'navigation':navigation,'pages':pages,'note':'Coordinates in pixels. Card title remains live native text; PNG contains card surfaces and decorative rail icons only.'}
(ROOT/'specs/page-layouts.json').write_text(json.dumps(layout,indent=2))
notebook=json.loads((ROOT.parent/'notebooks/nb_semantic_model_ga4.ipynb').read_text())
measure_defs=[]
for cell in notebook['cells']:
 source=''.join(cell['source'])
 if 'MEASURES = [' not in source:continue
 tree=ast.parse(source)
 for node in tree.body:
  if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MEASURES' for t in node.targets):
   for entry in node.value.elts:
    measure={}
    for key,value in zip(entry.keys,entry.values):
     if isinstance(key,ast.Constant) and key.value in ['name','expr','description','format']:
      measure[key.value]=ast.literal_eval(value)
    measure_defs.append(measure)
bindings={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT.parent,text=True).strip(),'source':'notebooks/nb_semantic_model_ga4.ipynb','model':'GA4 Ecommerce','existing_measures':measure_defs,'additional_measures_required':[{'name':'Previous Calendar Month Revenue','status':'design specification only; not installed','expression':"CALCULATE([Revenue], PREVIOUSMONTH('Date'[date]))"},{'name':'Revenue MoM %','status':'design specification only; not installed','expression':'DIVIDE([Revenue] - [Previous Calendar Month Revenue], [Previous Calendar Month Revenue])'},{'name':'Checkout to Purchase Ratio','status':'design specification only; not installed','expression':'DIVIDE([Purchase Sessions], [Begin Checkout Sessions])','warning':'Independent event count ratio; not ordered conversion.'}],'additional_series_required':['Device event reach percentages = each event session measure / [Sessions], evaluated per Device.'],'scopes':{'overview':['Date','Channel','Device'],'acquisition':['Date','Channel','Device'],'content':['Date','Page Type'],'funnel':['Date','Channel','Device'],'products':['Date','Items Daily.item_category']},'production_cautions':['Additional month-over-month comparisons for Sessions, Conversion Rate, Purchases and Revenue per Session still need implementation.','Guard comparisons to exactly one complete calendar month; November and full-window return BLANK.','Category uses the verified Items Daily[item_category] field from the gold schema.','HTML country fixture is illustrative; native use Sessions[country].','Product conversion is not a modeled measure; show item views, add-to-cart rate and item revenue.']}
(ROOT/'specs/model-bindings.json').write_text(json.dumps(bindings,indent=2))
print('Wrote 5 page plans and',len(measure_defs),'existing measure definitions')
