#!/usr/bin/env python3
"""Official Nature source extraction; analysis/screening remains human-reviewed.
Usage: python3 scripts/core_enrich.py data/assigned-core.json
Raw abstract/source text stays in research-cache, not public review output.
"""
import concurrent.futures,json,pathlib,re,sys,time
from urllib.parse import urljoin
sys.path.insert(0,'/tmp/npj-python')
import requests
from bs4 import BeautifulSoup
ROOT=pathlib.Path(__file__).resolve().parents[1]
CACHE=ROOT/'research-cache';CACHE.mkdir(exist_ok=True)

def clean(value):return re.sub(r'\s+',' ',str(value or '')).strip()
def scholarly_object(value):
    if isinstance(value,list):
        for v in value:
            found=scholarly_object(v)
            if found:return found
    elif isinstance(value,dict):
        if 'headline' in value and ('author' in value or 'description' in value):return value
        for key in ['mainEntity','@graph']:
            if key in value:
                found=scholarly_object(value[key])
                if found:return found
    return None

def extract_html(html,url):
    soup=BeautifulSoup(html,'html.parser');ld={}
    for script in soup.select('script[type="application/ld+json"]'):
        try:found=scholarly_object(json.loads(script.string or script.get_text()))
        except (ValueError,TypeError):continue
        if found:ld=found;break
    authors=[]
    for person in ld.get('author',[]):
        if isinstance(person,str):person={'name':person}
        affs=person.get('affiliation') or []
        if isinstance(affs,(dict,str)):affs=[affs]
        affiliations=[]
        for af in affs:
            if isinstance(af,str):affiliations.append({'name':clean(af),'full_address':clean(af)})
            else:
                address=af.get('address') or {}
                if isinstance(address,str):full=address
                else:full=address.get('name') or address.get('streetAddress') or af.get('name')
                affiliations.append({'name':clean(af.get('name')),'full_address':clean(full)})
        authors.append({'name':clean(person.get('name')),'orcid':person.get('url') if 'orcid.org' in str(person.get('url')) else None,'affiliations':affiliations})
    all_affiliations=[]
    for li in soup.select('.c-article-author-affiliation__list > li'):
        address=li.select_one('.c-article-author-affiliation__address')
        names=li.select_one('.c-article-author-affiliation__authors-list')
        if address:all_affiliations.append({'id':li.get('id'),'full_address':address.get_text(' ',strip=True),'authors':names.get_text(' ',strip=True) if names else None})
    if not all_affiliations:
        seen=set()
        for person in authors:
            for af in person['affiliations']:
                if af['full_address'] not in seen:all_affiliations.append(dict(af));seen.add(af['full_address'])
    sections={};section_urls={};section_links={}
    for heading in soup.select('h2'):
        label=heading.get_text(' ',strip=True)
        parent=heading.find_parent(class_='c-article-section') or heading.parent
        if parent:
            sections[label]=parent.get_text(' ',strip=True)
            section_urls[label]=url+'#'+heading.get('id','')
            section_links[label]=[{'label':a.get_text(' ',strip=True),'url':urljoin(url,a['href'])}for a in parent.select('a[href]') if a['href'].startswith(('http','/articles/','/original/'))]
    abstract=sections.get('Abstract') or clean(ld.get('description'))
    # Resolve bibliography anchors used by availability statements, not unrelated reference links.
    for label in ['Code availability','Data availability']:
        heading=next((h for h in soup.select('h2') if h.get_text(' ',strip=True)==label),None)
        if heading:
            parent=heading.find_parent(class_='c-article-section') or heading.parent
            for anchor in parent.select('a[href^="#"]'):
                reference=soup.find(id=anchor['href'][1:])
                if reference:
                    for external_anchor in reference.select('a[href]'):
                        href=external_anchor['href']
                        if href.startswith('http') and not any(z in href for z in ['scholar.google','pubmed.ncbi','search.crossref']):
                            section_links[label].append({'label':external_anchor.get_text(' ',strip=True),'url':href})
    code_links=[];data_links=[]
    for label,links in section_links.items():
        if 'code availability' in label.lower():code_links+=links
        if 'data availability' in label.lower():data_links+=links
    body=soup.find('article') or soup
    external=[]
    for a in body.select('a[href]'):
        href=urljoin(url,a['href'])
        if any(z in href.lower() for z in ['github.com/','zenodo.org/','figshare.com/','doi.org/10.5281','huggingface.co/','osf.io/','physionet.org/','synapse.org/','kaggle.com/']):
            external.append({'label':a.get_text(' ',strip=True),'url':href})
    first=authors[0] if authors else None
    first_af=first['affiliations'][0] if first and first['affiliations'] else None
    date_meta=soup.find('meta',attrs={'name':'citation_online_date'})
    title_meta=soup.find('meta',attrs={'name':'citation_title'})
    return {'url':url,'title':ld.get('headline') or (title_meta.get('content') if title_meta else None),
        'published_date':ld.get('datePublished') or (date_meta.get('content') if date_meta else None),
        'journal':(ld.get('isPartOf') or {}).get('name'),'abstract':abstract,
        'authors':authors,'first_author':first['name'] if first else None,
        'first_author_first_institution':first_af['name'] if first_af else None,
        'first_author_first_affiliation':first_af['full_address'] if first_af else None,
        'first_author_mapping_verified':bool(first_af),'all_affiliations':all_affiliations,
        'sections':sections,'section_urls':section_urls,'section_links':section_links,
        'code_links':code_links,'data_links':data_links,'resource_links':list({a['url']:a for a in external}.values()),
        'article_type': (soup.find('meta',attrs={'name':'citation_article_type'}) or {}).get('content'), 'source_extraction':'official_nature_jsonld_author_affiliation_and_html_sections'}

def enrich(row):
    doi=row.get('doi') or row.get('DOI') or '';article_id=row.get('id') or doi.rsplit('/',1)[-1]
    url=row.get('url') or row.get('URL') or 'https://www.nature.com/articles/'+article_id
    if 'doi.org/' in url:url='https://www.nature.com/articles/'+article_id
    path=CACHE/(article_id+'.html');out=CACHE/(article_id+'-source.json')
    try:
        if out.exists():
            result=json.loads(out.read_text())
            return {'id':article_id,'ok':True,'cached':True}
        if not path.exists():
            session=requests.Session();session.trust_env=False
            response=session.get(url,timeout=50);response.raise_for_status();path.write_text(response.text)
        result=extract_html(path.read_text(),url);result['id']=article_id
        out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
        return {'id':article_id,'ok':True,'abstract_chars':len(result['abstract']),'fulltext_sections':list(result['sections']),
            'first_author_mapping_verified':result['first_author_mapping_verified']}
    except Exception as exc:return {'id':article_id,'ok':False,'error':str(exc)}

if __name__=='__main__':
    rows=json.loads(pathlib.Path(sys.argv[1]).read_text())
    if isinstance(rows,dict):rows=rows.get('articles') or rows.get('candidates') or rows.get('items') or []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        for result in executor.map(enrich,rows):print(json.dumps(result,ensure_ascii=False),flush=True)
