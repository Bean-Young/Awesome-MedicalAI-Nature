#!/usr/bin/env python3
"""Evidence-first npj Digital Medicine enrichment; importable and resumable.

No abstracts/full text are copied into public JSON. Screening uses the article's
abstract AND available Methods/Results, excluding References. Negative lexical
screening without Methods is held for review, never treated as a firm exclusion.
Author/institution associations come from publisher author links or sequential
citation_author/citation_author_institution tags, never affiliation list position.

Run: python3 scripts/npj_enrich.py --input data/cache/npjDigitalMedicine.json
Optional --fetch-pdf downloads open publisher PDF when Methods HTML is absent.
"""
from __future__ import annotations
import argparse, concurrent.futures, html, json, re, sys, time, subprocess
from pathlib import Path
from urllib.parse import urljoin, urlparse
try:
 from bs4 import BeautifulSoup
except ImportError:
 sys.path.insert(0, '/tmp/npj-python')
 from bs4 import BeautifulSoup
import requests
ROOT=Path(__file__).resolve().parents[1]
OLD=Path('/Users/youngbean/Documents/ChatGPT/雅思/npj-digital-medicine')
CACHE=ROOT/'research-cache'/'npj'
AI_RULES=[
 ('Large language models',r'\blarge language models?\b|\bLLMs?\b|\bChatGPT\b|\bGPT[- ]?[345]\b|\bDeepSeek\b|\bGemini\b|\bClaude\b'),
 ('Deep learning / neural networks',r'\bdeep[- ]learning\b|\bneural networks?\b|\bconvolutional\b|\bU-Net\b|\bResNet\b|\bvision transformer\b|\bMamba\b'),
 ('Machine learning',r'\bmachine[- ]learning\b|\brandom forest\b|\bXGBoost\b|\bLightGBM\b|\bsupport vector machine\b|\bgradient boosting\b'),
 ('Foundation models / representation learning',r'\bfoundation models?\b|\bcontrastive learning\b|\bself-supervised\b|\bBERT\b|\bCLIP\b'),
 ('Generative imaging / diffusion models',r'\bdiffusion models?\b|\bgenerative adversarial\b|\blatent diffusion\b|\bGANs?\b'),
 ('Reinforcement learning / adaptive policies',r'\breinforcement learning\b|\bQ-learning\b|\bcontextual bandit\b'),
 ('Federated learning',r'\bfederated learning\b|\bfederated foundation\b'),
 ('Retrieval augmentation / knowledge graphs',r'\bretrieval[- ]augmented\b|\bGraphRAG\b|\bknowledge[- ]grounded\b'),
 ('Natural language processing',r'\bnatural language processing\b|\bNLP\b|\blanguage model\b'),
 ('AI application / AI evidence research',r'\bartificial intelligence\b|\bAI[- ](?:assisted|enabled|powered|driven|generated|based)\b|\bAI systems?\b|\bAI models?\b|\bAI\b')]
BIO_RULES=[('Clinical medicine',r'patient|clinical|diagnos|therap|disease|hospital|physician|medical|healthcare|health care|radiolog|patholog|surger|nurs'),('Biomedicine / omics',r'biomed|biolog|genom|proteom|transcriptom|molecular|protein|cellular|biomarker|bioinformatic'),('Drug discovery',r'drug|pharma|compound|ligand|peptide|drug.target|antibio|immunotherap'),('Public / mental health',r'public health|mental health|depress|anxiety|cogniti|epidemi|pandemic|wearable|sleep')]
DATASETS={
 'MIMIC-IV':'https://physionet.org/content/mimiciv/', 'MIMIC-III':'https://physionet.org/content/mimiciii/', 'MIMIC-CXR':'https://physionet.org/content/mimic-cxr/',
 'UK Biobank':'https://www.ukbiobank.ac.uk/', 'TCGA':'https://portal.gdc.cancer.gov/', 'CPTAC':'https://proteomics.cancer.gov/programs/cptac',
 'ADNI':'https://adni.loni.usc.edu/', 'OASIS':'https://sites.wustl.edu/oasisbrains/', 'All of Us':'https://www.researchallofus.org/',
 'HAM10000':'https://doi.org/10.7910/DVN/DBW86T', 'ISIC':'https://www.isic-archive.com/', 'CheXpert':'https://stanfordmlgroup.github.io/competitions/chexpert/',
 'AmsterdamUMCdb':'https://amsterdammedicaldatascience.nl/amsterdamumcdb/', 'LIDC-IDRI':'https://www.cancerimagingarchive.net/collection/lidc-idri/',
 'LNDb':'https://lndb.grand-challenge.org/', 'EHRSHOT':'https://github.com/som-shahlab/ehrshot-benchmark', 'DRIAMS':'https://github.com/BorgwardtLab/DRIAMS',
 'HyperKvasir':'https://datasets.simula.no/hyper-kvasir/', 'Fitzpatrick17k':'https://github.com/mattgroh/fitzpatrick17k',
 'BCN20000':'https://www.isic-archive.com/', 'PubMed':'https://pubmed.ncbi.nlm.nih.gov/'}
COUNT_RE=re.compile(r'(?P<n>\d{1,3}(?:,\d{3})+|\d{2,8}(?:\.\d+)?)\s*(?:(?P<multiplier>million|billion|thousand)\s+)?(?P<unit>(?:CT\s+)?volumes?|(?:coded\s+)?events?|patients?|participants?|individuals?|subjects?|adults?|children|infants?|cases?|records?|images?|slides?|scans?|videos?|recordings?|samples?|hospitals?|cent(?:er|re)s?|institutions?|studies|trials|articles?|physicians?|radiologists?|pathologists?|clinicians?|transcripts?|queries|questions|proteins?|compounds?)\b',re.I)
UNIT_ZH={'patient':'患者','participant':'参与者','individual':'个体','subject':'受试者','adult':'成人','children':'儿童','infant':'婴儿','case':'病例','record':'记录','image':'影像','slide':'切片','scan':'扫描','video':'视频','recording':'录制记录','sample':'样本','hospital':'医院','center':'中心','centre':'中心','institution':'机构','studies':'研究','trial':'试验','article':'文献','physician':'医生','radiologist':'放射科医师','pathologist':'病理医师','clinician':'临床人员','transcript':'对话转录','query':'问题','queries':'问题','question':'问题','protein':'蛋白','compound':'化合物'}
ROLE_RULES=[('External validation',r'external|independent|out.of.distribution'),('Prospective evaluation',r'prospective|real.world evaluation'),('Training / development',r'train|develop|derivation'),('Internal validation / testing',r'internal|test|validation|held.out'),('Reader / human evaluation',r'reader|radiologist|pathologist|physician|clinician'),('Review inclusion',r'included stud|systematic review|meta.analysis')]

def squash(s):return re.sub(r'\s+',' ',s or '').strip()
def jread(p,default=None):
 try:return json.loads(Path(p).read_text())
 except (OSError,json.JSONDecodeError):return default

def session():
 s=requests.Session();s.trust_env=False;s.headers.update({'User-Agent':'Mozilla/5.0 (compatible; scholarly metadata reader)'})
 return s

def cached_html(pid,url,fetch=True):
 f=CACHE/(pid+'.html');old=OLD/'research-cache'/(pid+'.html')
 if f.exists():return f.read_text()
 if old.exists():return old.read_text()
 if not fetch:return ''
 for attempt in range(3):
  try:
   res=session().get(url,timeout=45);res.raise_for_status()
   if len(res.content)<3000:raise ValueError('Publisher response too short')
   f.parent.mkdir(parents=True,exist_ok=True);f.write_text(res.text);return res.text
  except Exception:
   if attempt==2:raise
   time.sleep(1+attempt)

def parse_publisher(raw,url):
 s=BeautifulSoup(raw,'html.parser');sections={};anchors={}
 for h in s.select('.c-article-section__title'):
  name=squash(h.get_text(' ',strip=True));key=name.lower()
  if key.startswith(('references','acknowledge','author information','ethics declarations','additional information','rights','about this')):continue
  node=h.find_parent(class_='c-article-section') or h.parent
  sections[name]=squash(node.get_text(' ',strip=True));anchors[name]=url+'#'+(h.get('id') or '')
 # Fallback JSON-LD supplies abstract only; never claim Methods were inspected.
 if not any('abstract' in k.lower() for k in sections):
  for script in s.select('script[type="application/ld+json"]'):
   try:
    d=json.loads(script.string or script.get_text());d=d if isinstance(d,list) else [d]
    for q in d:
     if isinstance(q,dict) and q.get('description'):sections.setdefault('Abstract',squash(q['description']))
   except Exception:pass
 if not any('abstract' in k.lower() for k in sections):
  desc=s.find('meta',attrs={'name':'description'})
  if desc and desc.get('content'):
   lead=re.sub(r'^npj Digital Medicine\s*[-–:]\s*','',desc['content']);sections['Abstract']=squash(lead)
 auth=[];affs=[];by_id={} 
 for li in s.select('.c-article-author-affiliation__list > li'):
  a=li.select_one('.c-article-author-affiliation__address');names=li.select_one('.c-article-author-affiliation__authors-list')
  if a:
   text=squash(a.get_text(' ',strip=True));by_id[li.get('id')]=text;affs.append({'id':li.get('id'),'institution':text,'authors':squash(names.get_text(' ',strip=True)) if names else None})
 for li in s.select('.c-article-author-list > li'):
  a=li.select_one('[data-test="author-name"]')
  if not a:continue
  name=squash(a.get_text(' ',strip=True));ids=[n.get('href','')[1:] for n in li.select('sup a[href^="#Aff"]')];mapped=[by_id[k] for k in ids if k in by_id]
  if not any(q['name']==name for q in auth):auth.append({'name':name,'affiliation_ids':ids,'institutions':mapped,'mapping_verified':bool(mapped),'mapping_source':'publisher_author_superscripts' if mapped else None})
 # Publisher citation tags occur sequentially, mapping each institution to the
 # immediately preceding author. This also verifies missing superscript maps.
 tag_auth=[];current=None
 for m in s.select('meta[name]'):
  key=m.get('name','').lower();v=squash(m.get('content',''))
  if key=='citation_author':current={'name':v,'institutions':[],'mapping_verified':False,'mapping_source':'publisher_sequential_citation_tags'};tag_auth.append(current)
  elif key=='citation_author_institution' and current and v:current['institutions'].append(v);current['mapping_verified']=True
 if not auth:auth=tag_auth
 elif tag_auth:
  for i,a in enumerate(auth):
   if not a['institutions'] and i<len(tag_auth):
    norm=lambda n:re.sub(r'[^a-z]','',n.lower())
    if sorted(norm(a['name']))==sorted(norm(tag_auth[i]['name'])):a.update(institutions=tag_auth[i]['institutions'],mapping_verified=tag_auth[i]['mapping_verified'],mapping_source=tag_auth[i]['mapping_source'])
 links=[]
 for a in s.select('.c-article-section a[href], a[data-test="download-pdf"]'):
  href=urljoin(url,a.get('href',''));label=squash(a.get_text(' ',strip=True))
  if href.startswith('http'):links.append({'label':label[:100],'url':href})
 pdf=next((urljoin(url,a['href']) for a in s.select('a[data-test="download-pdf"][href]')),url+'_reference.pdf')
 # Stable direct availability anchors remain useful even if no resource URL.
 availability={k:v for k,v in sections.items() if 'availability' in k.lower()}
 typemeta=s.find('meta',attrs={'name':'citation_article_type'}) or s.find('meta',attrs={'name':'dc.type'})
 publisher_type=typemeta.get('content','') if typemeta else ''
 availability_links=[]
 for h in s.select('.c-article-section__title'):
  label=squash(h.get_text(' ',strip=True)).lower()
  if 'availability' in label:
   for a in h.parent.select('a[href]'):availability_links.append({'section':label,'url':urljoin(url,a['href'])})
 return {'availability_links':availability_links,'article_type':publisher_type,'sections':sections,'anchors':anchors,'authors':auth,'affiliations':affs,'links':links,'pdf':pdf,'availability':availability}

def get_pdf_text(pid,pdf_url,fetch=False):
 for base in [CACHE,OLD/'research-cache']:
  p=base/(pid+'.txt')
  if p.exists():
   if base!=CACHE and (base/(pid+'.pdf')).exists():
    # Preserve layout locally so section headings remain detectable. Never edit
    # or re-extract the previous project's evidence archive in place.
    target=CACHE/(pid+'.txt');CACHE.mkdir(parents=True,exist_ok=True)
    try:
     subprocess.run(['pdftotext','-layout',str(base/(pid+'.pdf')),str(target)],check=True,capture_output=True)
     return target.read_text(errors='replace')
    except (OSError,subprocess.CalledProcessError):pass
   return p.read_text(errors='replace')
 if not fetch:return ''
 p=CACHE/(pid+'.pdf');out=p.with_suffix('.txt')
 if not p.exists():
  res=session().get(pdf_url,timeout=70);res.raise_for_status()
  if not res.content.startswith(b'%PDF'):raise ValueError('PDF URL did not return PDF')
  p.write_bytes(res.content)
 subprocess.run(['pdftotext','-layout',str(p),str(out)],check=True,capture_output=True)
 return out.read_text(errors='replace')

def extract_core(parsed,pdf_text=''):
 sections=parsed['sections'];keys=[k for k in sections if re.search(r'abstract|introduction|method|result|discussion|conclusion',k,re.I)]
 full=any(re.search(r'method',k,re.I) for k in keys)
 if full:return '\n'.join(sections[k] for k in keys),True,'publisher_html'
 if pdf_text:
  # Remove reference bibliography while retaining genuine later Methods.
  t=re.split(r'\b(?:References|REFERENCES|Code availability|Data availability|Author contributions|Acknowledgements)\b',pdf_text)[0]
  t=re.sub(r'\b(?:ARTICLE IN PRESS|Article in Press)\b','',t)
  return squash(t),True,'publisher_pdf'
 return '\n'.join(sections[k] for k in keys),False,'publisher_abstract'

def classify(text,fulltext,article_type):
 methods=[name for name,pat in AI_RULES if re.search(pat,text,re.I)]
 bio=[name for name,pat in BIO_RULES if re.search(pat,text,re.I)]
 if article_type and re.search(r'correction|retract|editorial|reply|comment|news|perspective|viewpoint|matters arising',article_type,re.I):return 'excluded','Not an eligible research or review article type',methods,bio
 if methods and bio:return 'included','Source confirms substantive AI methods or AI evidence analysis addressing medicine, biomedicine or drug development',methods,bio
 if fulltext and not methods:return 'excluded','Source methods inspected: no substantive AI method or AI evaluation; digital health or conventional statistics alone does not qualify',methods,bio
 if fulltext and not bio:return 'excluded','Source inspected: the AI application does not address medicine, biomedicine, bioinformatics or drug development',methods,bio
 return 'needs_review','Abstract-only or incomplete source; absence of keywords is insufficient for exclusion',methods,bio

def scales(text,section='Abstract / Methods / Results'):
 out=[];seen=set()
 # Intro prevalence and citations can contaminate full text extraction. Prefer
 # abstract facts; source excerpt is kept only in private cache, public numeric
 # evidence is marked candidate until reviewed.
 for m in COUNT_RE.finditer(text):
  num=m.group('n');u=m.group('unit').lower();n=float(num.replace(',',''));n*=dict(million=1e6,billion=1e9,thousand=1e3).get(m.groupdict().get('multiplier'),1);n=int(n) if n.is_integer() else n
  unit=u;context=text[max(0,m.start()-100):m.end()+100]
  role=next((label for label,pat in ROLE_RULES if re.search(pat,context,re.I)),'Reported scale; units must not be pooled')
  key=(n,unit,role)
  if key in seen:continue
  seen.add(key);out.append({'value':n,'unit':unit,'role':role,'source_section':section,'verified':False})
  if len(out)>=10:break
 for m in re.finditer(r'\b[nN]\s*=\s*(\d{1,3}(?:,\d{3})+|\d{2,8})',text):
  n=int(m.group(1).replace(',',''));ctx=text[max(0,m.start()-100):m.end()+40]
  role=next((label for label,pat in ROLE_RULES if re.search(pat,ctx,re.I)),'Reported n; original unit requires review')
  units=list(re.finditer(r'patients?|participants?|individuals?|subjects?|images?|records?|samples?|admissions?|studies|hospitals?|centers?|children|infants?',ctx,re.I))
  unit=units[-1].group().lower() if units else 'reported n'
  if any(z['value']==n for z in out):continue
  out.append({'value':n,'unit':unit,'role':role,'context':role,'source_section':section,'verified':False})
  if len(out)>=12:break
 return out

def dataset_info(text,parsed,url):
 out=[]
 for name,access in DATASETS.items():
  if re.search(r'(?<![A-Za-z0-9])'+re.escape(name)+r'(?![A-Za-z0-9])',text,re.I):out.append({'name':name,'source':'Named in source Abstract/Methods; exact usage role requires review','access_url':access,'access_note':'A public landing page does not imply unrestricted access; check source permissions and registration requirements.','verified':True})
 # Direct data links are verified as publisher-linked, not verified access.
 data_links=[];code_links=[]
 for item in parsed['links']:
  u=item['url'];label=item['label'];host=urlparse(u).netloc.lower()
  if any(x in host for x in ['github.com','gitlab.com','codeberg.org']) and any(x['url']==u and 'code' in x['section'] for x in parsed.get('availability_links',[])):code_links.append(u)
  elif any(x in host for x in ['zenodo.org','figshare.com','physionet.org','dataverse','synapse.org','osf.io','huggingface.co','ncbi.nlm.nih.gov/geo']):data_links.append(u)
 return out,list(dict.fromkeys(code_links)),list(dict.fromkeys(data_links))

def source_objective(title,abstract):
 # A short attributed source excerpt is preferable to pretending that a title
 # prefixed with "Investigate" is an independently curated research problem.
 t=re.sub(r'^Abstract\s*','',squash(abstract),flags=re.I)
 if not t:return None
 sentences=re.split(r'(?<=[.!?])\s+',t)
 first=next((z for z in sentences if re.search(r'\b(?:we|this study|our study|this review)\b',z,re.I) and re.search(r'aim|develop|evaluat|investigat|assess|examin|propos|introduc|present|explor|analy|review|synthesi',z,re.I)),sentences[0])
 words=first.split();excerpt=' '.join(words[:20])
 if len(words)>20:excerpt+='…'
 return excerpt

def primary_methods(abstract,method_text,article_type):
 sentences=re.split(r'(?<=[.!?])\s+',abstract)
 primary=[z for z in sentences if re.search(r'\b(?:we|our|this study|here)\b',z,re.I) and re.search(r'develop|introduc|propos|present|train|evaluat|compar|investigat|assess',z,re.I)]
 own=' '.join(primary)
 matched=[name for name,pat in AI_RULES if re.search(pat,own,re.I)]
 if not matched:
  matched=[name for name,pat in AI_RULES if re.search(pat,abstract,re.I)]
 if not matched:
  # Actual Methods only; do not use introductory literature or bibliography.
  own=' '.join(z for z in re.split(r'(?<=[.!?])\s+',method_text) if re.search(r'we (?:used|trained|developed|implemented|applied)|model architecture|our (?:model|framework)',z,re.I))
  matched=[name for name,pat in AI_RULES if re.search(pat,own,re.I)]
 if not matched:matched=[name for name,pat in AI_RULES if re.search(pat,method_text,re.I)]
 names=[]
 for name in ['Aidoc','GPT-4o','GPT-4','GPT-5','DeepSeek-R1','DeepSeek','Qwen','Gemini','Claude','BERT','ResNet','U-Net','YOLO','XGBoost','LightGBM','random forest','Transformer','LSTM','CNN','Stable Diffusion','SAM','CLIP']:
  if re.search(r'(?<![A-Za-z])'+re.escape(name)+r'(?![A-Za-z])',own or abstract,re.I):names.append(name)
 if re.search(r'systematic review|meta-analysis|scoping review',abstract,re.I):label='Evidence synthesis of '
 elif re.search(r'survey|interview|governance|regulatory',abstract,re.I) and matched==['AI application / AI evidence research']:label='Empirical analysis of '
 else:label=''
 return label+'; '.join(names or matched[:3]),matched,names

def normalize(raw):
 doi=raw.get('doi') or raw.get('DOI') or '';title=raw.get('title','');title=title[0] if isinstance(title,list) else title
 pid=raw.get('id') or doi.rsplit('/',1)[-1]
 date=raw.get('date') or raw.get('published_date')
 if not date:
  for key in ['published-online','published','issued','published-print']:
   parts=raw.get(key,{}).get('date-parts',[[]])[0]
   if parts:date='-'.join(str(q).zfill(2) for q in (parts+[1,1])[:3]);break
 return {**raw,'id':pid,'doi':doi,'title':title,'date':date,'url':raw.get('url') or raw.get('URL') or 'https://www.nature.com/articles/'+pid,'articleType':raw.get('articleType') or raw.get('article_type') or raw.get('subtype') or ''}

def load_previous():
 rows=jread(OLD/'dist/analysis.json',[]) or []
 return {q['id']:q for q in rows}

def enrich(raw,previous=None,fetch=True,fetch_pdf=False):
 q=normalize(raw);pid=q['id'];url='https://www.nature.com/articles/'+pid
 parsed=parse_publisher(cached_html(pid,url,fetch),url)
 has_methods=any(re.search('method',k,re.I) for k in parsed['sections'])
 pdf=get_pdf_text(pid,parsed['pdf'],fetch_pdf) if not has_methods else ''
 text,full,source=extract_core(parsed,pdf)
 abstract=next((v for k,v in parsed['sections'].items() if 'abstract' in k.lower()),'')
 method_text='\n'.join(v for k,v in parsed['sections'].items() if re.search('method|result|availability',k,re.I))
 if pdf and not method_text:
  # The last standalone Methods heading normally follows Discussion in Nature
  # PDFs. Search the actual heading, not incidental introductory mentions of AI.
  hits=list(re.finditer(r'(?im)^\s*(?:\d+[. ]+)?(?:Materials and )?Methods\b[^\n]*$',pdf))
  if hits:method_text=re.split(r'\b(?:Data availability|Code availability|References|Received:|Author contributions|Acknowledgements)\b',pdf[hits[-1].end():])[0]
 substantive=squash(abstract+' '+method_text)
 # Some PDFs use unconventional headings; absence then stays pending unless
 # article abstract establishes substantive AI. Existing human analysis supports
 # scope, but cannot turn an absent AI signal into an inclusion.
 q['articleType']=parsed.get('article_type') or q['articleType']
 state,why,methods,bio=classify(substantive,full and bool(method_text),q['articleType'])
 old=(previous or {}).get(pid,{})
 # Existing full-paper analysis is reusable evidence, not an automatic AI pass.
 ds,code,data=dataset_info(substantive,parsed,url)
 if pdf:
  flat=squash(pdf)
  flat=re.sub(r'(github|gitlab|zenodo|figshare)\.\s+(com|org)',r'\1.\2',flat)
  for label,target in [('Code availability',code),('Data availability',data)]:
   av=re.search(re.escape(label)+r'\s+(.*?)(?:Code availability|Data availability|Received:|References|Acknowledg|Author contribution|Funding|$)',flat,re.I)
   if av:
    for candidate in re.findall(r'https?://[^\s<>]+',av.group(1)):
     candidate=candidate.rstrip('.,;)')
     if candidate.startswith('https://github.com/') and len(candidate.split('/'))>=5:target.append(candidate)
     elif label=='Data availability' and any(host in candidate for host in ['zenodo.org','figshare.com','physionet.org','synapse.org','osf.io','dataverse']):target.append(candidate)
  code=list(dict.fromkeys(code));data=list(dict.fromkeys(data))
 author=parsed['authors'][0] if parsed['authors'] else None
 first_inst=(author['institutions'][0] if author and author['mapping_verified'] and author['institutions'] else None)
 ev=[{'label':k,'url':v} for k,v in parsed['anchors'].items() if re.search('abstract|method|result|availability',k,re.I)]
 if source=='publisher_pdf':ev.append({'label':'Open full-text PDF, including Methods and Results','url':parsed['pdf']})
 # Topic fallback is explicitly an indexing summary, never a fabricated result.
 problem=source_objective(q['title'],abstract)
 method_description,primary_tags,model_names=primary_methods(abstract,method_text,q['articleType'])
 outcome=None
 row={
  **{k:q[k] for k in ['id','doi','title','date','articleType']},'url':url,'journal':'npj Digital Medicine','status':state,
  'research_problem':problem,'problem_is_excerpt':True,'problem_source_url':url+'#Abs1','ai_method':method_description or None,'ai_methods':primary_tags,'model_names':model_names,
  'experiment_scale':scales(abstract or text[:5500], 'Abstract' if abstract else 'Article research sections'),
  'datasets':ds,'first_author':author['name'] if author else None,'first_institution':first_inst,
  'first_author_first_institution':first_inst,'first_author_first_affiliation':first_inst,'first_author_mapping_verified':bool(first_inst),
  'first_author_institutions':author['institutions'] if author and author['mapping_verified'] else [],
  'authors':parsed['authors'],'affiliations':[x['institution'] for x in parsed['affiliations']],
  'code_urls':code,'data_urls':data,'outcome_summary':outcome,
  'data_availability':{'reported':any('data' in k.lower() for k in parsed['availability']),'url':next((parsed['anchors'][k] for k in parsed['availability'] if 'data' in k.lower()),parsed['pdf'] if pdf else None)},
  'code_availability':{'reported':any('code' in k.lower() for k in parsed['availability']),'url':next((parsed['anchors'][k] for k in parsed['availability'] if 'code' in k.lower()),None)},
  'evidence_links':ev,'evidence_level':'fulltext' if full else 'abstract',
  'screening':{'decision':state,'reason':why,'ai_signals':methods,'biomedical_signals':bio,'source':source,'reviewed_date':'2026-10-23'},
  'previous_review':{k:old[k] for k in ['design_group','collection','validation','patient_rct','reader'] if k in old},
  'field_status':{'research_problem':'attributed_source_excerpt_max20_words','outcome_summary':'not_curated','experiment_scale':'source_numeric_candidates_need_role_review','datasets':'named_dataset_matching_needs_usage_role_review','first_institution':'publisher_mapping_verified' if first_inst else 'not_verified'},
 }
 manual=jread(ROOT/'data/curation/npj-manual-overrides.json',jread(CACHE/'manual-overrides.json',{})).get(pid)
 if manual:
  row.update({k:v for k,v in manual.items() if k in ['research_problem','ai_method','outcome_summary','experiment_scale']})
  row['problem_is_excerpt']=False
  row['field_status'].update(research_problem='manually_paraphrased_from_source',ai_method='manually_paraphrased_from_source',outcome_summary='manually_paraphrased_from_source')
  if manual.get('experiment_scale'):row['field_status']['experiment_scale']='source_counts_manually_checked_with_separate_roles'
  if manual.get('scope_override')=='excluded':row['status']='excluded';row['screening'].update(decision='excluded',reason=manual['scope_reason'])
 scope=jread(ROOT/'data/curation/npj-scope-overrides.json',jread(CACHE/'scope-overrides.json',{})).get(pid)
 if scope:
  row['status']=scope['decision'];row['screening'].update(decision=scope['decision'],reason=scope['reason'],scope_review='Manual inspection of Abstract and relevant Methods/Results')
 row['curation_level']='curated' if manual else 'source_extracted'
 row['review_level']='Manually paraphrased source summary' if manual else 'Source-extracted; not manually interpreted'
 if row['status']=='included' and (not row['ai_method'] or not row['research_problem']):
  row['status']='needs_review';row['screening'].update(decision='needs_review',reason='A specific research objective and substantive AI method were not resolved from Abstract/Methods; manual review required')
 # Avoid inadvertently carrying Crossref's copyrighted full abstract into public.
 for key in ['abstract','abstract_text','summary','description']:row.pop(key,None)
 return row

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',type=Path);ap.add_argument('--output',type=Path,default=ROOT/'data/reviews/npj.json');ap.add_argument('--workers',type=int,default=6);ap.add_argument('--limit',type=int);ap.add_argument('--no-fetch',action='store_true');ap.add_argument('--fetch-pdf',action='store_true');ap.add_argument('--bootstrap',action='store_true');args=ap.parse_args()
 if args.input:raw=jread(args.input,[])
 elif args.bootstrap:raw=jread(OLD/'research-cache/inventory-all-2026.json',[])
 else:
  src=next((q for q in [ROOT/'data/cache/npjDigitalMedicine.json',ROOT/'data/cache/npjdigitalmed.json',ROOT/'data/cache/metadata-all.json'] if q.exists()),None)
  if not src:ap.error('Await rawmetadata data/cache/npjDigitalMedicine.json (or use --bootstrap)')
  raw=jread(src,[])
 if isinstance(raw,dict):raw=raw.get('items') or raw.get('records') or raw.get('message',{}).get('items',[])
 rows=[normalize(q) for q in raw if 's41746-' in str(q.get('doi') or q.get('DOI') or q.get('id',''))]
 rows=[q for q in rows if q.get('date') and '2026-01-01'<=q['date']<='2026-10-23']
 rows=list({q['id']:q for q in rows}.values());rows.sort(key=lambda x:(x['date'],x['id']),reverse=True)
 if args.limit:rows=rows[:args.limit]
 CACHE.mkdir(parents=True,exist_ok=True);previous=load_previous();out=[];errors=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
  jobs={ex.submit(enrich,q,previous,not args.no_fetch,args.fetch_pdf):q for q in rows}
  for n,f in enumerate(concurrent.futures.as_completed(jobs),1):
   q=jobs[f]
   try:out.append(f.result())
   except Exception as e:errors.append({'id':q['id'],'doi':q['doi'],'title':q['title'],'status':'needs_review','reason':'Source acquisition or parsing failed; no content exclusion inferred','error':str(e)})
   if n%25==0:print(f'{n}/{len(rows)} enriched; {len(errors)} pending source errors',flush=True)
 out.sort(key=lambda x:(x.get('date',''),x['id']),reverse=True)
 included=[q for q in out if q['status']=='included'];excluded=[q for q in out if q['status']=='excluded'];pending=[q for q in out if q['status']=='needs_review']+errors
 for path,content in [(args.output,included),(ROOT/'data/screening/npj-excluded.json',excluded),(ROOT/'data/screening/npj-pending.json',pending),(CACHE/'all-enriched.json',out)]:
  path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(content,ensure_ascii=False,indent=2))
 print(json.dumps({'input':len(rows),'included':len(included),'excluded':len(excluded),'pending':len(pending),'fulltext':sum(x['evidence_level']=='fulltext' for x in out)},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
