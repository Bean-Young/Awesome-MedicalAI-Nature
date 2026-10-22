"""Private-source extraction for bounded Nature/Communications medical-AI review.
Does not automatically include papers, infer patient counts or publish abstracts.
"""
import json,re,sys,time,os
from pathlib import Path
from urllib.parse import urljoin,urlparse
import requests
try:
 from bs4 import BeautifulSoup
except ImportError:
 sys.path.insert(0,'/tmp/npj-python')
 from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'cache'/'other'
CACHE.mkdir(parents=True,exist_ok=True)

def fetch_html(url, ident):
 path=CACHE/(ident+'.html')
 if path.exists() and path.stat().st_size>3000:return path.read_text()
 session=requests.Session();session.trust_env=False
 last=None
 for attempt in range(3):
  try:
   response=session.get(url,timeout=50,headers={'User-Agent':'Mozilla/5.0'})
   response.raise_for_status()
   if '<html' not in response.text[:1000].lower():raise ValueError('not HTML')
   path.write_text(response.text);return response.text
  except Exception as exc:
   last=exc
   if attempt<2:time.sleep(1+attempt)
 raise last

def extract_source(record):
 ident=record.get('id') or record.get('doi','').split('/')[-1]
 url=record.get('url') or ('https://www.nature.com/articles/'+ident)
 soup=BeautifulSoup(fetch_html(url,ident),'html.parser')
 def meta(name):
  tag=soup.find('meta',attrs={'name':name});return tag.get('content') if tag else None
 entities=[]
 for script in soup.select('script[type="application/ld+json"]'):
  try:
   parsed=json.loads(script.string or script.get_text());entities.extend(parsed if isinstance(parsed,list) else [parsed])
  except (ValueError,TypeError):pass
 article=next((v.get('mainEntity',v) for v in entities if isinstance(v,dict) and ('mainEntity' in v or 'headline' in v)),{})
 sections={};section_links={};section_ids={}
 for section in soup.select('.c-article-section'):
  h=section.select_one('h2')
  if not h:continue
  name=h.get_text(' ',strip=True)
  sections[name]=section.get_text(' ',strip=True)
  section_ids[name]=h.get('id') or section.get('id')
  links=[]
  for a in section.find_all('a',href=True):
   href=urljoin(url,a['href'])
   if not href.startswith(url+'#') and not href.startswith('https://www.nature.com/search'):
    links.append({'label':a.get_text(' ',strip=True),'url':href})
  section_links[name]=list({v['url']:v for v in links}.values())
 # Author superscripts provide the explicit author-to-affiliation mapping.
 affiliations=[]
 for li in soup.select('.c-article-author-affiliation__list > li'):
  address=li.select_one('.c-article-author-affiliation__address')
  names=li.select_one('.c-article-author-affiliation__authors-list')
  affiliations.append({'id':li.get('id'),'address':address.get_text(' ',strip=True) if address else None,'authors':names.get_text(' ',strip=True) if names else None})
 author_node=soup.select_one('.c-article-author-list__item')
 first_author=None;aff_ids=[]
 if author_node:
  name_node=author_node.select_one('[data-test="author-name"]') or author_node.find('a')
  first_author=name_node.get_text(' ',strip=True) if name_node else None
  aff_ids=list(dict.fromkeys(a['href'][1:] for a in author_node.select('sup a[href]') if re.fullmatch(r'#Aff\d+',a['href'])))
 first_mapped=next((a for a in affiliations if aff_ids and a['id']==aff_ids[0]),None)
 ld_authors=article.get('author',[])
 if isinstance(ld_authors,dict):ld_authors=[ld_authors]
 ld_first=ld_authors[0] if ld_authors else {}
 ld_affs=ld_first.get('affiliation',[]) if isinstance(ld_first,dict) else []
 if isinstance(ld_affs,dict):ld_affs=[ld_affs]
 pdf_links=[urljoin(url,a['href']) for a in soup.find_all('a',href=True) if re.search(r'/articles/[^/]+(?:_reference)?\.pdf$',a['href'])]
 result={'id':ident,'url':url,'title':meta('citation_title') or article.get('headline') or record.get('title'),
  'doi':meta('citation_doi') or record.get('doi'),'date':meta('citation_publication_date') or article.get('datePublished'),
  'journal':meta('citation_journal_title') or (article.get('isPartOf') or {}).get('name'),
  'article_type':meta('citation_article_type') or record.get('article_type') or record.get('type'),
  'sections':sections,'section_links':section_links,'section_ids':section_ids,
  'source_abstract':sections.get('Abstract') or article.get('description'),
  'fulltext_available':any(re.search('method',k,re.I) for k in sections),
  'first_author':first_author,'first_author_affiliation_ids':aff_ids,
  'first_author_first_affiliation':first_mapped,'jsonld_first_author':ld_first,
  'first_author_first_institution':(ld_affs[0].get('name') if ld_affs and isinstance(ld_affs[0],dict) else None),
  'affiliation_mapping_verified':bool(first_author and first_mapped and isinstance(ld_first,dict) and first_author==ld_first.get('name')),
  'first_author_institution_verified':bool(first_mapped and ld_affs and isinstance(ld_affs[0],dict) and ld_affs[0].get('name') and ld_affs[0]['name'].casefold() in (first_mapped.get('address') or '').casefold()),
  'other_affiliations':affiliations[1:] if first_mapped and affiliations and first_mapped['id']==affiliations[0]['id'] else [a for a in affiliations if not first_mapped or a['id']!=first_mapped['id']],
  'all_affiliations':affiliations,'pdf_urls':list(dict.fromkeys(pdf_links)),'extracted_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 (CACHE/(ident+'.source.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
 return result

if __name__=='__main__':
 import argparse
 from concurrent.futures import ThreadPoolExecutor,as_completed
 parser=argparse.ArgumentParser();parser.add_argument('input');parser.add_argument('--workers',type=int,default=6);parser.add_argument('--start',type=int,default=0);parser.add_argument('--limit',type=int,default=100)
 args=parser.parse_args();raw=json.loads(Path(args.input).read_text());rows=raw if isinstance(raw,list) else raw.get('papers',raw.get('candidates',raw.get('items',[])))
 rows=rows[args.start:args.start+args.limit];done=0
 with ThreadPoolExecutor(max_workers=args.workers) as executor:
  futures={executor.submit(extract_source,r):r for r in rows}
  for future in as_completed(futures):
   r=futures[future];done+=1
   try:
    result=future.result();print(json.dumps({'id':result['id'],'status':'fulltext' if result['fulltext_available'] else 'abstract','author_mapping':result['affiliation_mapping_verified'],'done':done,'total':len(rows)},ensure_ascii=False),flush=True)
   except Exception as exc:print(json.dumps({'id':r.get('id',r.get('doi')),'status':'error','error':str(exc),'done':done,'total':len(rows)},ensure_ascii=False),flush=True)
