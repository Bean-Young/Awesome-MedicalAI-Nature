"""Build public data from screened decisions and curated notes; keep raw source text private."""
import json,re,sys,shutil
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'data';OUT=ROOT/'dist/data';OUT.mkdir(parents=True,exist_ok=True)
def read(p,default=None):
 try:return json.loads(p.read_text())
 except (FileNotFoundError,json.JSONDecodeError):return [] if default is None else default
def english(t):return isinstance(t,str) and not re.search(r'[\u4e00-\u9fff]',t)
def url(v):return isinstance(v,str) and v.startswith(('https://','http://'))
def links(v):
 out=[]
 for x in v or []:
  if isinstance(x,str):x={'label':'Original resource','url':x}
  if isinstance(x,dict) and url(x.get('url')):out.append({'label':x.get('label') if english(x.get('label')) else 'Original resource','url':x['url']})
 return list({x['url']:x for x in out}.values())
def institution(p):
 raw=p.get('first_author_first_affiliation') or p.get('first_affiliation') or ''
 first=p.get('first_institution') or p.get('first_author_first_institution') or ''
 verified=p.get('first_author_institution_verified',p.get('first_author_mapping_verified',p.get('mapping_verified',False)))
 if not verified:return None,False,raw
 org=r'universit|institut|inc\.|ltd\b|gmbh|hôpital|charit|csic|kaist|truveta|Complexity Science Hub|institut |hospital|school|centre|center|college|clinic|academy|council|laborator|foundation|research|technology|politecnico|polytechnic|ETH Z|EPFL|CNRS|INSERM|OpenAI|DeepMind|Google|Microsoft|NVIDIA|Genentech|AstraZeneca|Roche|Novartis|Pfizer|IBM|Meta AI|Baidu|Tencent|Alibaba|Fudan|Stanford|Harvard|MIT|Siemens|Philips|Huawei'
 if len(first)<160 and re.search(org,first,re.I) and not first.lower().startswith(('department ','division ')):return first,True,raw
 parts=[x.strip() for x in (raw or first).split(',')]
 for pattern in [r'university|universit[ae]|hospital|clinic|academy|politecnico|polytechnic|ETH Z|EPFL',org]:
  for part in parts:
   if re.search(pattern,part,re.I) and not part.lower().startswith(('department ','division ','faculty ')):return part,True,raw or first
 if re.search(org,first,re.I):return first,True,raw
 return None,False,raw or first

def source(p):
 id=p['id'];path=ROOT/'research-cache'/(id+'-source.json')
 if path.exists():return read(path,{})
 path=ROOT/'research-cache/other'/(id+'-source.json')
 return read(path,{})
def excerpt(abstract):
 text=re.sub(r'\s+',' ',abstract or '').strip();sentences=re.split(r'(?<=[.!?])\s+',text)
 chosen=next((s for s in sentences if re.search(r'\b(?:we|here|this study|this work|our study)\b',s,re.I)),sentences[0] if sentences else '')
 words=chosen.split();return ' '.join(words[:20])+('…' if len(words)>20 else '')

def normalize(p,m):
 q=dict(m);q.update(p);s=source(q)
 q['date']=q.get('date','')[:10];q['year']=2026;q['journal_group']=m.get('journal_group','');q['journal_id']=m.get('journal_id','')
 q['family']='Nature' if q['journal']=='Nature' else 'Nature Communications' if q['journal']=='Nature Communications' else 'npj Digital Medicine' if q['journal']=='npj Digital Medicine' else 'Nature journals'
 q['article_type']=p.get('article_type') or p.get('articleType') or s.get('article_type') or 'Article'
 if not english(str(q['article_type'])):q['article_type']='Article'
 q['research_problem']=p.get('research_problem') if english(p.get('research_problem')) else ''
 q['problem_is_excerpt']=p.get('problem_is_excerpt',False)
 if not q['research_problem']:
  q['research_problem']=excerpt(s.get('abstract') or m.get('epmc_abstract') or m.get('abstract'));q['problem_is_excerpt']=True
 q['ai_method']=p.get('ai_method') if english(p.get('ai_method')) else 'See the source methods for the learning approach.'
 q['study_summary']=p.get('study_summary') or p.get('outcome_summary') or p.get('outcomes') or ''
 if not english(q['study_summary']):q['study_summary']=''
 q['authors']=p.get('authors') or s.get('authors') or m.get('authors') or []
 q['first_author']=p.get('first_author') or s.get('first_author') or (q['authors'][0].get('name') if q['authors'] and isinstance(q['authors'][0],dict) else '')
 for field in ['first_author_first_affiliation','first_author_first_institution','first_author_mapping_verified']:
  if field not in q and s.get(field) is not None:q[field]=s[field]
 q['first_institution'],q['institution_verified'],q['first_affiliation']=institution(q)
 q['all_affiliations']=p.get('all_affiliations') or s.get('all_affiliations') or p.get('affiliations') or []
 q['experiment_scale']=[x for x in p.get('experiment_scale',[]) if isinstance(x,dict) and not (str(x.get('unit','')).lower() in ['reported n','n','unknown'] and x.get('verified') is not True) and english(str(x.get('unit',''))) and english(str(x.get('context','')))]
 q['datasets']=[x if isinstance(x,dict) else {'name':x} for x in p.get('datasets',[]) if isinstance(x,(dict,str))]
 q['code_links']=links(p.get('code_urls') or p.get('code_links') or s.get('code_links'))
 q['data_links']=links(p.get('data_urls') or p.get('data_links') or s.get('data_links'))
 q['evidence_links']=links((p.get('evidence_links') or p.get('source_urls') or [])+(p.get('additional_evidence') or []))
 if not q['evidence_links']:q['evidence_links']=[{'label':'Original article','url':q['url']}]
 q['review_level']=p.get('review_level') or p.get('evidence_level') or 'abstract'
 q['curation_level']='curated' if p.get('curation_level','curated') in ['curated','human_curated','manually_curated'] else 'source_extracted'
 q['scale_status']='source_extracted' if q['curation_level']!='curated' or any(x.get('verified') is False for x in q['experiment_scale']) else 'curated'
 for item in q['experiment_scale']:
  item['context']=item.get('context') or item.get('role') or 'Source-reported count; see original methods'
 if q['research_problem'].startswith('Research target:'):
  q['research_problem']=excerpt(s.get('abstract') or m.get('epmc_abstract') or m.get('abstract'));q['problem_is_excerpt']=True;q['study_summary']=''
 previous=p.get('previous_review') or {}
 q['study_design']={k:previous.get(k) if isinstance(previous.get(k),bool) else None for k in ['collection','validation','patient_rct','reader']}
 disease_text=' '.join([q['title'],q['research_problem']]).lower()
 disease_rules=[('Cancer',r'cancer|carcinoma|tumou?r|oncolog|leukemia|lymphoma|melanoma'),('Cardiovascular',r'cardiovascular|cardiac|heart|coronary|arrhyth|atrial|hypertension'),('Neurological',r'alzheimer|parkinson|dementia|epilep|stroke|multiple sclerosis|neurological'),('Mental health',r'depress|psychiatr|mental health|anxiety|schizophrenia|autism'),('Metabolic & endocrine',r'diabet|metabolic|obesity|endocrine|insulin'),('Infectious disease',r'infectio|covid|sars.cov|tuberculosis|malaria|sepsis|hiv'),('Respiratory',r'pulmonary|lung|respiratory|asthma|copd'),('Ophthalmology',r'retina|ophthalm|glaucoma|macular|ocular'),('Skin disease',r'dermatolog|skin disease|psoriasis|eczema'),('Musculoskeletal',r'musculoskeletal|osteoarthrit|rheumatoid|osteoporosis|fracture'),('Gastrointestinal & liver',r'gastrointestinal|liver|hepatic|cirrhosis|bowel|colorectal'),('Kidney & urinary',r'kidney|renal|urinary|urolog') ]
 q['diseases']=[label for label,pattern in disease_rules if re.search(pattern,disease_text)]
 q['scope_reason']=p.get('scope_reason') or p.get('scope_evidence') or ''
 if not q['scope_reason'] or not english(q['scope_reason']):q['scope_reason']='AI methods or AI evaluation are central to a biomedical task; see the linked source evidence.'
 text=' '.join([q['title'],q['research_problem'],q['ai_method'],q['study_summary'],' '.join(str(t) for t in p.get('topics',[]))]).lower()
 domains=[('Clinical medicine',r'patient|clinical|diagnos|radiolog|patholog|healthcare|medical|hospital|surg|disease'),('Bioinformatics & omics',r'bioinformat|omics|genom|transcript|sequenc|variant|single.cell|rna|dna|genetic'),('Molecular & cellular biology',r'protein|cellular|molecular|enzyme|antibod|peptide|receptor|cell biology'),('Drug discovery & therapeutics',r'drug|therapeutic|ligand|compound|pharmac|molecul.*design|peptide.*design'),('Biomedical imaging',r'imag|microscop|radiograph|tomograph|mri|ultrasound|optical'),('Neuroscience & mental health',r'brain|neuro|cognit|mental|depress|psychiatr|parkinson|alzheimer'),('Biomedical engineering',r'prosthe|robot|wearable|sensor|biomechan|biomedical engineering|implant')]
 q['domains']=[name for name,pat in domains if re.search(pat,text)] or ['Biomedical research']
 methods=[('Language models',r'language model|\bllm\b|gpt|chatbot|generative language'),('Foundation models',r'foundation model|pretrained|pre-trained|protein language|alphafold|alphagenome'),('Generative AI',r'generative|diffusion|\bgan\b|denoising'),('Deep learning',r'deep learning|neural network|convolution|transformer|autoencoder'),('Machine learning',r'machine learning|random forest|xgboost|support vector|gradient boost'),('Reinforcement learning',r'reinforcement learning|policy optim'),('Self-supervised learning',r'self.supervis|contrastive learning'),('Federated & distributed learning',r'federated|continual learning|distributed learning')]
 q['methods']=[name for name,pat in methods if re.search(pat,q['ai_method'].lower())] or ['Other AI approaches']
 allowed=['id','doi','title','date','year','journal','journal_id','journal_group','family','url','article_type','research_problem','problem_is_excerpt','ai_method','study_summary','authors','first_author','first_institution','institution_verified','first_affiliation','all_affiliations','experiment_scale','datasets','code_links','data_links','evidence_links','review_level','curation_level','scope_reason','domains','methods','field_status','scale_status','datasets_status','scope_evidence','study_design','diseases']
 return {k:q[k] for k in allowed if k in q}

def build():
 meta=read(D/'metadata-all.json');
 if not meta:
  rows=read(D/'catalogue.json');coverage=read(D/'coverage.json',{});assert rows and coverage.get('indexed')==len(rows),'Missing public snapshot';
  (OUT/'papers.json').write_text(json.dumps(rows,ensure_ascii=False,separators=(',',':')));(OUT/'coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2));
  js=read(D/'journals.json');(OUT/'journals.json').write_text(json.dumps([{k:j[k] for k in ['id','name','group','url']} for j in js],ensure_ascii=False,indent=2));print('Restored public snapshot',len(rows));return
 byid={p['id']:p for p in meta};candidates=read(D/'candidates.json');js=read(D/'journals.json');records={};screen=[]
 for part in ['core','other','npj','root']:
  for p in read(D/'reviews'/f'{part}.json'):
   if p.get('id') not in byid:continue
   if p.get('status') in ['excluded','pending']:continue
   records[p['id']]=normalize(p,byid[p['id']])
  p=read(D/'screening'/f'{part}.json')
  if isinstance(p,dict):p=p.get('records') or p.get('screening') or []
  screen+=p
 for filename in ['npj-excluded.json','npj-pending.json']:
  for d in read(D/'screening'/filename):
   d=dict(d);d['status']='pending' if filename=='npj-pending.json' else 'excluded';screen.append(d)
 decisions={}
 for d in screen:
  ident=d.get('id') or str(d.get('doi','')).split('/')[-1];state=d.get('status') or d.get('decision')
  if state not in ['pending','needs_review',None] or ident not in decisions:decisions[ident]=d
 rows=sorted(records.values(),key=lambda p:(p['date'],p['doi']),reverse=True)
 scopeids={j['id'] for j in js}
 rows=[p for p in rows if p['journal_id'] in scopeids and '2026-01-01'<=p['date']<='2026-10-23']
 for p in rows:
  for key in ['research_problem','ai_method','study_summary']:
   assert english(p[key]),(p['id'],key)
 ledger=[]
 for j in js:
  candidate_ids={p['id'] for p in candidates if p['journal_id']==j['id']};included={p['id'] for p in rows if p['journal_id']==j['id']}
  reviewed={id for id in candidate_ids if id in decisions and (decisions[id].get('status') or decisions[id].get('decision')) not in ['pending','needs_review',None]}
  reviewed |= included
  ledger.append(dict(id=j['id'],name=j['name'],group=j['group'],url=j['url'],metadata_records=j.get('retrieved_records'),metadata_status=j.get('retrieval_status'),candidates=len(candidate_ids),reviewed=len(reviewed),indexed=len(included),pending=len(candidate_ids-reviewed),source=j.get('source_query') or j['url'],source_note=j.get('source_note')))
 coverage=dict(snapshot_date='2026-10-23',start_date='2026-01-01',end_date='2026-10-23',journals_in_scope=len(js),journals_with_indexed_papers=len({p['journal'] for p in rows}),metadata_records=len(meta),recall_candidates=len(candidates),indexed=len(rows),curated=sum(p['curation_level']=='curated' for p in rows),source_extracted=sum(p['curation_level']!='curated' for p in rows),verified_institutions=sum(p['institution_verified'] for p in rows),ledger=ledger,limitations=['Scope covers Nature-branded journals, Nature Communications and npj Digital Medicine; the separate Communications series, other npj titles and Scientific Reports are excluded.','Title/abstract recall uses Crossref metadata, Europe PMC and source checks. A pending record is not treated as an included paper or a negative result.','Charts describe currently indexed records, not complete journal biomedical-AI shares. Source extraction and curated analyses are labeled separately.','Sample sizes keep their units and roles; no pooled patient totals are computed. Original institutional mappings and availability statements remain linked.'])
 (OUT/'papers.json').write_text(json.dumps(rows,ensure_ascii=False,separators=(',',':')))
 (OUT/'coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2))
 (OUT/'journals.json').write_text(json.dumps([{k:j[k] for k in ['id','name','group','url']} for j in js],ensure_ascii=False,indent=2))
 print('BUILT',len(rows),'papers;',coverage['verified_institutions'],'mapped institutions;',coverage['journals_with_indexed_papers'],'journals; candidates',len(candidates))
if __name__=='__main__':build()
