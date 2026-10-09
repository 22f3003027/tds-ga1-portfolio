import os,re,json,calendar
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import defaultdict
from decimal import Decimal,ROUND_HALF_UP
import yaml
from dotenv import dotenv_values
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
app=FastAPI()
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
ROOT=Path(__file__).parent
@app.get('/effective-config')
def config(request:Request):
 c=dict(port=8000,workers=1,debug=False,log_level='info',api_key='default-secret-000')
 c.update(yaml.safe_load((ROOT/'config.development.yaml').read_text()) or {})
 for layer in (dotenv_values(ROOT/'.env'),os.environ):
  for k,v in layer.items():
   if k=='NUM_WORKERS' and layer is not os.environ:c['workers']=v
   elif k.startswith('APP_'):c[k[4:].lower()]=v
 for arg in request.query_params.getlist('set'):
  if '=' in arg:k,v=arg.split('=',1);c[k]=v
 for k,v in list(c.items()):
  if k in ('port','workers'):c[k]=int(v)
  elif k=='debug':c[k]=str(v).lower() in ('true','1','yes','on')
  else:c[k]=str(v)
 c['api_key']='****'
 return c

rates={k:Decimal(str(v)) for k,v in json.loads((ROOT/'rates.json').read_text())['usd_per_unit'].items()}
latest={}
for line in (ROOT/'ledger.jsonl').read_text().splitlines():
 r=json.loads(line);old=latest.get(r['id'])
 if old is None or datetime.fromisoformat(r['updated_at'].replace('Z','+00:00'))>datetime.fromisoformat(old['updated_at'].replace('Z','+00:00')):latest[r['id']]=r
orders=list(latest.values())
for r in orders:
 r['date']=datetime.fromisoformat(r['created_at'].replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Kolkata')).date()
 r['usd']=Decimal(str(r['amount']))*rates[r['currency']]
products=sorted({r['product'] for r in orders},key=len,reverse=True)
def money(v):return float(v.quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
def solve(question):
 q=question.lower().replace('at least one','one');rows=orders[:]
 for region in sorted({r['region'] for r in orders}):
  if re.search(r'\b'+region.lower()+r'\b',q):rows=[r for r in rows if r['region']==region];break
 for p in products:
  if p.lower() in q:rows=[r for r in rows if r['product']==p];break
 customer=re.search(r'\bc\d{3,}\b',q)
 if customer:rows=[r for r in rows if r['customer'].lower()==customer.group()]
 year_match=re.search(r'\b202[0-9]\b',q);year=int(year_match.group()) if year_match else 2026
 month=None
 for i,m in enumerate(calendar.month_name):
  if m and re.search(r'\b'+m.lower()+r'\b',q):month=i;break
 for i,m in enumerate(calendar.month_abbr):
  if month is None and m and re.search(r'\b'+m.lower()+r'\b',q):month=i
 iso=re.findall(r'202\d-\d\d-\d\d',q)
 if len(iso)>=2:rows=[r for r in rows if iso[0]<=str(r['date'])<=iso[1]]
 elif len(iso)==1:rows=[r for r in rows if str(r['date'])==iso[0]]
 elif month:rows=[r for r in rows if r['date'].year==year and r['date'].month==month]
 elif re.search(r'q[1-4]|[1-4](?:st|nd|rd|th) quarter',q):
  n=int(re.search(r'q([1-4])|([1-4])(?:st|nd|rd|th) quarter',q).group(1) or re.search(r'q([1-4])|([1-4])(?:st|nd|rd|th) quarter',q).group(2));rows=[r for r in rows if r['date'].year==year and (r['date'].month-1)//3+1==n]
 elif year_match:rows=[r for r in rows if r['date'].year==year]
 refund='refund' in q
 status='refunded' if refund else ('cancelled' if 'cancel' in q else 'paid')
 chosen=[r for r in rows if r['status']==status]
 if 'rate' in q or 'percentage' in q or 'percent' in q:
  return round(100*len(chosen)/len(rows),2) if rows else 0
 ranking=any(w in q for w in ('highest','most','top','best','largest','leading','lowest','least'))
 if ranking:
  group='product' if 'product' in q else ('customer' if 'customer' in q else ('region' if 'region' in q else None))
  if group:
   totals=defaultdict(Decimal)
   for r in chosen:totals[r[group]]+=Decimal(r['qty']) if ('unit' in q or 'quantity' in q or 'volume' in q) else (Decimal(1) if 'number of orders' in q or 'order count' in q else r['usd'])
   if not totals:return ''
   return sorted(totals,key=lambda k:((-totals[k] if not any(w in q for w in ('lowest','least')) else totals[k]),k))[0]
 if ('unique' in q or 'distinct' in q or 'different' in q) and 'customer' in q:return len({r['customer'] for r in chosen})
 if ('unique' in q or 'distinct' in q or 'different' in q) and 'product' in q:return len({r['product'] for r in chosen})
 if not any(w in q for w in ('average','mean')) and any(w in q for w in ('how many','count','number of')) and 'order' in q:return len(chosen)
 if 'units' in q or 'quantity' in q:return sum(r['qty'] for r in chosen)
 total=sum((r['usd'] for r in chosen),Decimal(0))
 if 'net' in q:total=sum((r['usd'] for r in rows if r['status']=='paid'),Decimal(0))-sum((r['usd'] for r in rows if r['status']=='refunded'),Decimal(0))
 if 'average' in q or 'mean' in q:total=total/len(chosen) if chosen else Decimal(0)
 return money(total)
@app.post('/answer')
async def answer(request:Request):
 body=await request.json();question=body.get('question','');result=solve(question)
 print('QUESTION',question,'ANSWER',result,flush=True)
 return {'answer':result}
