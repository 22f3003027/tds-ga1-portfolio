import os,time,uuid,json,math,base64,asyncio
from collections import defaultdict,deque
from datetime import datetime,timezone
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import JSONResponse,Response
from pydantic import BaseModel,Field
import jwt,redis,httpx
from prometheus_client import Counter,generate_latest,CONTENT_TYPE_LATEST
app=FastAPI()
EMAIL='22f3003027@ds.study.iitm.ac.in'
START=time.monotonic()
logs=deque(maxlen=2000)
buckets=defaultdict(deque)
orders={}
counter=Counter('http_requests_total','Number of HTTP requests')
rdb=redis.Redis.from_url(os.getenv('REDIS_URL','redis://redis:6379/0'),decode_responses=True)
PUBLIC_KEY='''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2okOHspNjgA+2rTLbeuY
cxiP/hG8C6Sb9iwg3yiLAA4HCnpITcbWCSelbvbYGuc3EbNy4xFyf5Cbj5DHJMID
EkryOgyd2giIIIBOUBj8S63uGcnRpOBh9NFatfNwheKuzsPuVNldu6A9cNteNpXc
WyJjG2axVfmq7i6SuKr1JoWYG7xTTAvKPujSl4OtsQfO3h5NepzdfXpr28oNnzfW
ed+zclR6BcmNNo/WVfJ4xyCLSf0BCOgdTgW6PdaChd1l9VDetJZVEgC5tkyvXsfI
SI6iyrYbKR0NEBSqq4XkadEjsCs4F1RncsS4LlgniT7GlkL9Mce3b0wGLs9/7ZIX
dQIDAQAB
-----END PUBLIC KEY-----'''
@app.middleware('http')
async def middleware(req:Request,call_next):
 t=time.monotonic();rid=req.headers.get('x-request-id') or str(uuid.uuid4());req.state.request_id=rid
 counter.inc()
 origin=req.headers.get('origin');path=req.url.path
 allowed=(['https://dash-buxwsa.example.com'] if path=='/stats' else ['https://app-c5c0op.example.com','https://exam.sanand.workers.dev'] if path=='/ping' else ['*'])
 if req.method=='OPTIONS':
  resp=Response(status_code=204 if '*' in allowed or origin in allowed else 400)
 else:
  cap=14 if path=='/ping' else 18 if path=='/orders' else None
  client=req.headers.get('x-client-id')
  if cap and client:
   q=buckets[(path,client)]
   while q and q[0]<=t-10:q.popleft()
   if len(q)>=cap:resp=JSONResponse({'email':EMAIL,'request_id':rid,'detail':'Rate limit exceeded'},status_code=429,headers={'Retry-After':str(max(1,math.ceil(10-(t-q[0]))))})
   else:q.append(t);resp=await call_next(req)
  else:resp=await call_next(req)
 resp.headers['X-Request-ID']=rid;resp.headers['X-Process-Time']=f'{time.monotonic()-t:.6f}'
 if origin and ('*' in allowed or origin in allowed):
  resp.headers['Access-Control-Allow-Origin']='*' if '*' in allowed else origin
  resp.headers['Access-Control-Allow-Methods']='GET,POST,OPTIONS'
  resp.headers['Access-Control-Allow-Headers']='*'
  resp.headers['Access-Control-Expose-Headers']='X-Request-ID,X-Process-Time,Retry-After'
  resp.headers['Vary']='Origin'
 entry={'level':'INFO','ts':datetime.now(timezone.utc).isoformat(),'path':path,'request_id':rid,'status':resp.status_code};logs.append(entry);print(json.dumps(entry),flush=True)
 return resp
@app.get('/stats')
def stats(values:str):
 try:v=[int(x) for x in values.split(',')]
 except ValueError:raise HTTPException(422,'Use comma-separated integers')
 return {'email':EMAIL,'count':len(v),'sum':sum(v),'min':min(v),'max':max(v),'mean':sum(v)/len(v)}
class Token(BaseModel):token:str
@app.post('/verify')
def verify(body:Token):
 try:
  c=jwt.decode(body.token,PUBLIC_KEY,algorithms=['RS256'],audience='tds-yvft7eah.apps.exam.local',issuer='https://idp.exam.local',options={'require':['exp','iss','aud','email','sub']})
  return {'valid':True,'email':c['email'],'sub':c['sub'],'aud':c['aud']}
 except jwt.PyJWTError:return JSONResponse({'valid':False},status_code=401)
@app.get('/effective-config')
def config(req:Request):
 c={'port':8368,'workers':3,'debug':False,'log_level':'error','api_key':'****'}
 for override in req.query_params.getlist('set'):
  k,sep,v=override.partition('=')
  if sep:
   if k in ['port','workers']:
    try:v=int(v)
    except ValueError:raise HTTPException(422,'Invalid integer')
   elif k=='debug':v=v.lower() in ('true','1','yes','on')
   c[k]=v
 c['api_key']='****';return c
@app.post('/hit/{key}')
def hit(key:str):return {'key':key,'count':rdb.incr('ga2:'+key)}
@app.get('/count/{key}')
def count(key:str):return {'key':key,'count':int(rdb.get('ga2:'+key) or 0)}
@app.get('/healthz')
def health():
 try:rdb.ping()
 except redis.RedisError:return JSONResponse({'status':'error','redis':'down','uptime_s':time.monotonic()-START},status_code=503)
 return {'status':'ok','redis':'up','uptime_s':time.monotonic()-START}
@app.post('/analytics')
async def analytics(req:Request):
 if req.headers.get('x-api-key')!='ak_jtocf3653ynr0r3y96g5pdbq':raise HTTPException(401,'Invalid API key')
 b=await req.json();events=b.get('events',[]);totals=defaultdict(float)
 for e in events:totals[e['user']]+=max(0,float(e['amount']))
 return {'email':EMAIL,'total_events':len(events),'unique_users':len(totals),'revenue':sum(totals.values()),'top_user':max(totals,key=totals.get) if totals else None}
@app.get('/work')
def work(n:int=1):return {'email':EMAIL,'done':n}
@app.get('/metrics')
def metrics():return Response(generate_latest(),media_type=CONTENT_TYPE_LATEST)
@app.get('/logs/tail')
def tail(limit:int=10):return list(logs)[-max(0,min(limit,2000)):] if limit>0 else []
@app.get('/ping')
def ping(req:Request):return {'email':EMAIL,'request_id':req.state.request_id}
@app.post('/orders')
async def create_order(req:Request):
 key=req.headers.get('idempotency-key')
 if not key:raise HTTPException(400,'Missing Idempotency-Key')
 if key in orders:return orders[key]
 order={'id':str(uuid.uuid4())};orders[key]=order;return JSONResponse(order,status_code=201)
@app.get('/orders')
def list_orders(limit:int=10,cursor:str|None=None):
 try:offset=int(base64.urlsafe_b64decode(cursor).decode()) if cursor else 0
 except Exception:raise HTTPException(400,'Invalid cursor')
 size=max(1,min(limit,48));end=min(offset+size,48)
 return {'items':[{'id':i} for i in range(offset+1,end+1)],'next_cursor':base64.urlsafe_b64encode(str(end).encode()).decode() if end<48 else None}
class InvoiceText(BaseModel):text:str=Field(min_length=1)
class Invoice(BaseModel):vendor:str;amount:float;currency:str;date:str
@app.post('/extract',response_model=Invoice)
async def extract(b:InvoiceText):
 prompt='Extract invoice vendor name, total amount due, uppercase currency code and payment due date YYYY-MM-DD. Return JSON with exactly vendor, amount, currency, date. Invoice: '+b.text
 async with httpx.AsyncClient(timeout=120) as client:
  r=await client.post('http://127.0.0.1:11434/api/generate',json={'model':'qwen2.5:0.5b','prompt':prompt,'format':Invoice.model_json_schema(),'stream':False,'options':{'temperature':0}})
 try:return Invoice.model_validate_json(r.json()['response'])
 except Exception:raise HTTPException(422,'Cannot extract invoice')
@app.post('/v1/chat/completions')
async def chat(req:Request):
 async with httpx.AsyncClient(timeout=120) as client:
  r=await client.post('http://127.0.0.1:11434/v1/chat/completions',json=await req.json())
 return JSONResponse(r.json(),status_code=r.status_code)
