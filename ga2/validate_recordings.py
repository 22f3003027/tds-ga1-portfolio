import json,re,pathlib,tarfile
root=pathlib.Path(__file__).parent/'recordings'
def load(name,file):
 es=[json.loads(x) for x in (root/name/file).read_text().splitlines()[1:]]
 assert any(e[1]=='x' for e in es)
 s=''.join(e[2] for e in es if e[1]=='o').replace('\r','')
 s=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',s)
 return s
s=load('httpbin','httpbin.cast')
out={}
for task in ['GET','POST','FORM','AUTH','REDIRECT','COOKIES','STATUS']:
 matches=re.findall(r'\nHTTPBIN_BEGIN http-509c628c '+task+r'\n(.*?)\nHTTPBIN_END http-509c628c '+task,s,re.S)
 assert matches,task
 out[task]=matches[-1].strip() if task=='STATUS' else json.loads(matches[-1])
assert out['GET']['args']=={'course':'TDS','tag':'http-509c628c'}
assert out['GET']['headers']['X-Exam-Tag']=='http-509c628c'
assert out['POST']['json']=={'tag':'http-509c628c','quantity':8,'active':True}
assert type(out['POST']['json']['quantity']) is int
assert out['FORM']['form']=={'tag':'http-509c628c','quantity':'8'}
assert out['AUTH']['authenticated'] is True and out['AUTH']['token']=='http-509c628c'
assert out['REDIRECT']['args']['tag']=='http-509c628c'
assert out['COOKIES']['cookies']['exam']=='http-509c628c'
assert out['STATUS']=='400'
print('HTTPBin: all seven captures verified; exit event present.')
s=load('model','model.cast')
parts=re.findall(r'\nMODELFILE_BEGIN ga2-assistant-509c628c\n(.*?)\nMODELFILE_END ga2-assistant-509c628c',s,re.S)
assert parts,'Model markers missing'
m=parts[-1]
for key,val in [('temperature','0.1'),('num_ctx','2048'),('seed','994'),('num_predict','113')]:
 assert len(re.findall(r'(?m)^PARAMETER\s+'+key+r'\s+'+re.escape(val)+r'\s*$',m))==1,(key,m)
assert 'You are the deployment assistant for project 509c628c. Give concise answers and never invent commands.' in m
print('Ollama: exact SYSTEM and four unique parameters verified; exit event present.')
for name,file in [('httpbin','httpbin.cast'),('model','model.cast')]:
 archive=root/name/'submission.tar.gz'
 with tarfile.open(archive,'w:gz') as t:
  t.add(root/name/file,arcname=file);t.add(root/name/(file+'.jwt'),arcname=file+'.jwt')
 assert archive.stat().st_size<1000000
 print(name+' archive: '+str(archive.stat().st_size)+' bytes')
