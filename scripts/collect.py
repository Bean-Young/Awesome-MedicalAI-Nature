import requests,json,sys,re,threading,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
sys.path.insert(0,'/tmp/npj-python')
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];C=ROOT/'research-cache';C.mkdir(exist_ok=True);D=ROOT/'data';(D/'cache').mkdir(exist_ok=True)
local=threading.local()
def session():
 if not hasattr(local,'s'):local.s=requests.Session();local.s.trust_env=False
 return local.s
def get(url,params=None):
 for i in range(3):
  try:
   r=session().get(url,params=params,timeout=55);r.raise_for_status();return r
  except Exception:
   if i==2:raise
   time.sleep(1+i)
def save(p,v):
 tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2));tmp.replace(p)
def registry():
 soup=BeautifulSoup(Path('/tmp/nature-siteindex.html').read_text(),'html.parser');out={}
 omit={'Nature Africa','Nature India','Nature Italy','Nature Digest'}
 for a in soup.select('a[href]'):
  title=a.get_text(' ',strip=True);u=a['href']
  if not u.startswith('/') or u.count('/')!=2:continue
  if title in omit:continue
  if title=='Nature' or title.startswith('Nature ') or title=='npj Digital Medicine':
   group='Nature' if title=='Nature' else 'Nature Communications' if title=='Nature Communications' else 'Communications' if title.startswith('Communications ') else 'npj Digital Medicine' if title=='npj Digital Medicine' else 'Nature Reviews' if title.startswith('Nature Reviews ') else 'Nature Progress' if title.startswith('Nature Progress ') else 'Nature Research'
   out[u.strip('/')]=dict(id=u.strip('/'),name=title,group=group,url='https://www.nature.com'+u,registry_source='https://www.nature.com/siteindex')
 return list(out.values())
def journal(j):
 path=C/(j['id']+'-home.html')
 try:
  html=path.read_text() if path.exists() else get(j['url']).text
  if not path.exists():path.write_text(html)
  soup=BeautifulSoup(html,'html.parser');text=soup.get_text(' ',strip=True)
  issns=[]
  for meta in soup.select('meta[content]'):
   if 'issn' in (meta.get('name','')+' '+meta.get('property','')).lower():issns+=re.findall(r'\d{4}-[\dX]{4}',meta.get('content',''))
  # The footer explicitly labels the current journal's online/print ISSNs.
  if not issns:
   m=re.search(r'ISSN.*?(\d{4}-[\dX]{4})',text)
   if m:issns=[m.group(1)]
  if not issns:raise ValueError('ISSN not present in publisher homepage')
  j['issns']=list(dict.fromkeys(issns));j['issn']=j['issns'][0];cache=D/'cache'/(j['id']+'.json')
  if cache.exists():items=json.loads(cache.read_text());j['retrieval_status']='retrieved';j['retrieved_records']=len(items);return j,items
  url=f'https://api.crossref.org/journals/{j["issn"]}/works'
  params={'filter':'from-online-pub-date:2026-01-01,until-online-pub-date:2026-10-23','rows':1000,'cursor':'*','select':'DOI,title,author,published-online,published,type,link,abstract,publisher'}
  items=[];expected=None
  while True:
   result=get(url,params).json()['message'];expected=result['total-results'];batch=result['items'];items+=batch
   if not batch or len(items)>=expected:break
   nxt=result.get('next-cursor')
   if nxt==params['cursor']:break
   params['cursor']=nxt
  items=list({x['DOI'].lower():x for x in items}.values())
  save(cache,items);j.update(retrieval_status='retrieved',retrieved_records=len(items),source_total=expected,source_query=url+'?filter=from-online-pub-date:2026-01-01,until-online-pub-date:2026-10-23',retrieval_complete=len(items)==expected)
  return j,items
 except Exception as e:j.update(retrieval_status='error',retrieval_error=str(e));return j,[]
def normalize(x,j):
 date=x.get('published-online',x.get('published',{})).get('date-parts',[[]])[0];d='-'.join(str(n).zfill(2) for n in date)
 return dict(doi=x['DOI'].lower(),id=x['DOI'].split('/')[-1],title=' '.join(x.get('title',[])),date=d,year=2026,journal=j['name'],journal_id=j['id'],journal_group=j['group'],url='https://www.nature.com/articles/'+x['DOI'].split('/')[-1],abstract=re.sub('<[^>]+>',' ',x.get('abstract','')),authors=[dict(name=' '.join([a.get('given',''),a.get('family','')]).strip(),affiliations=[f['name'] for f in a.get('affiliation',[])],orcid=a.get('ORCID')) for a in x.get('author',[])],type=x.get('type'),crossref_url='https://api.crossref.org/works/'+x['DOI'],publisher=x.get('publisher'),resources=x.get('link',[]))
if __name__=='__main__':
 js=registry();save(D/'journals.json',js);rows=[];done=[]
 print('REGISTRY',len(js),flush=True)
 with ThreadPoolExecutor(max_workers=7) as ex:
  for f in as_completed([ex.submit(journal,j) for j in js]):
   j,items=f.result();done.append(j);rows +=[normalize(x,j) for x in items];save(D/'journals.json',sorted(done,key=lambda j:j['name']));print(j['name'],j.get('retrieved_records',0),j['retrieval_status'],flush=True)
   save(D/'metadata-all.json',rows)
 save(D/'metadata-all.json',rows);print('DONE',len(rows),sum(j['retrieval_status']=='retrieved' for j in done),'/',len(js),flush=True)
