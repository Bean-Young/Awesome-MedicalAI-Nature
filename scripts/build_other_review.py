import json,re,sys
from pathlib import Path
sys.path.insert(0,'/tmp/npj-python');from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
rows=json.loads((ROOT/'data/assigned-other-current.json').read_text());manual=json.loads((ROOT/'data/reviews/other-nature-notes.json').read_text());confirmed=[];screen=[]
for p in rows:
 i=p['id'];m=manual.get(i)
 if not m:screen.append({'id':i,'decision':'pending','reason':'Recall candidate; substantive AI × biomedical source screening has not yet been completed.','review_level':'metadata'});continue
 if m['decision']!='included':screen.append({'id':i,**m});continue
 f=ROOT/'research-cache'/(i+'-source.json');s=json.loads(f.read_text()) if f.exists() else {};url=p['url'];sec=s.get('section_urls',{})
 # Match first author superscripts to the author-information affiliation addresses.
 first_aff=None;verified=False
 html=ROOT/'research-cache'/(i+'.html')
 if html.exists():
  soup=BeautifulSoup(html.read_text(),'html.parser');node=soup.select_one('.c-article-author-list__item');affids=[]
  if node:affids=list(dict.fromkeys(a['href'][1:] for a in node.select('sup a[href]') if re.fullmatch(r'#Aff\d+',a['href'])))
  for af in s.get('all_affiliations',[]):
   if affids and af.get('id')==affids[0]:first_aff=af;break
  verified=bool(first_aff and s.get('first_author_first_institution') and s['first_author_first_institution'].casefold() in (first_aff.get('full_address') or '').casefold())
 def clean_links(values):
  return list(dict.fromkeys(v['url'] for v in values if v.get('url') and not re.search(r'#(?:ref-|Fig|Tab)',v['url']) and '/figures/' not in v['url'] and '/tables/' not in v['url']))
 dataurls=clean_links(s.get('data_links',[]));codeurls=clean_links(s.get('code_links',[]));evidence=[{'label':'Original article','url':url}]
 for label in ['Abstract','Methods','Data availability','Code availability']:
  if label in sec:evidence.append({'label':label,'url':sec[label]})
 datasets=[]
 for name in m.get('dataset_names',[]):
  target=next((u for u in dataurls if any(word.lower() in u.lower() for word in name.split() if len(word)>=5)),None)
  datasets.append({'name':name,'source':'Original article and its data-availability statement','access':m.get('dataset_access','See the linked original availability statement; access conditions are not inferred from repository presence.'),'url':target or sec.get('Data availability',url)})
 record={k:v for k,v in p.items() if k in ['id','doi','title','date','year','journal','journal_id','journal_group','url']}
 record.update({k:v for k,v in m.items() if k not in ['decision','dataset_names','verification','placeholder']})
 record.update({'first_author':s.get('first_author'),'first_institution':s.get('first_author_first_institution'),
  'first_author_first_affiliation':first_aff.get('full_address') if first_aff else s.get('first_author_first_affiliation'),
  'first_author_institution_verified':verified,'all_affiliations':s.get('all_affiliations',[]),'authors':s.get('authors',[]),
  'datasets':datasets,'data_urls':dataurls,'code_urls':codeurls,'evidence_links':evidence,
  'scope_reason':'Manually confirmed substantive AI methods or AI evaluation applied to medicine, biomedical research, bioinformatics, drug discovery or biological imaging.',
  'review_level':m.get('review_level','abstract')})
 confirmed.append(record)
(ROOT/'data/reviews/other.json').write_text(json.dumps(confirmed,ensure_ascii=False,indent=2));(ROOT/'data/screening/other.json').write_text(json.dumps(screen,ensure_ascii=False,indent=2))
print(json.dumps({'confirmed':len(confirmed),'screened_excluded':sum(r['decision']=='excluded' for r in screen),'pending':sum(r['decision']=='pending' for r in screen),'mapped_first_institution':sum(r['first_author_institution_verified'] for r in confirmed)}))
