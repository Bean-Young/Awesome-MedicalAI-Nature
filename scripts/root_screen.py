"""High-precision rule-assisted screen over publisher abstracts; extracted facts are labeled."""
import json,re,sys
from pathlib import Path
from core_enrich import extract_html
R=Path(__file__).resolve().parents[1];D=R/'data';C=R/'research-cache'
rows=json.loads((D/'assigned-root.json').read_text())
AI=re.compile(r'artificial intelligence|machine[- ]learning|deep[- ]learning|deep neural|neural networks?|large language|language models?|foundation models?|generative (?:ai|model|adversarial)|reinforcement learning|self[- ]supervis|contrastive learning|graph neural|computer vision|transfer learning|representation learning|diffusion models?|alphafold|alphagenome|protein language|transformers?|random forests?|support vector machine|xgboost|autoencoders?|convolutional|physics.informed neural|deep (?:model|network|survival)|learning[- ]based',re.I)
BIO=re.compile(r'biomedical|bioinformatics?|clinical|patients?|healthcare|disease|cancer|tumou?r|diagnos|radiolog|medical|surg|therap|drugs?|pharmac|protein|peptides?|antibod|enzym|genom|transcript|\bgenes?\b|\brna\b|\bdna\b|single.cell|cellular|cell lines?|cell segmentation|microscop|neuroscien|neuronal|neurons?|\bbrain\b|eeg|\becg\b|cardia|biomarker|epidemic|pandemic|pathogen|microbiom|metagenom|immun|metabolom|chromatin|receptor|proteom|amino.acid|biolog|bioactiv',re.I)
NONBIO=re.compile(r'agricultur|crop|soil|climate|weather|wildlife|biodiversity|ecosystem|carbon|photovoltaic|solar cell|battery|batteries|superconduct|quantum|galax|cosmolog|gravity|particle physics',re.I)
allowed=re.compile(r'^(?:Article|Review|Review Article|Analysis|Resource|Brief Communication|Technical Report|Letter|Protocol|Registered Report|Research)$',re.I)
def load_source(p):
 path=C/(p['id']+'-source.json')
 if path.exists():return json.loads(path.read_text())
 path=C/'other'/(p['id']+'-source.json')
 if path.exists():return json.loads(path.read_text())
 path=C/(p['id']+'.html')
 if path.exists():return extract_html(path.read_text(),p['url'])
 return {}
def excerpt(a):
 sentences=re.split(r'(?<=[.!?])\s+',re.sub(r'\s+',' ',a));chosen=next((s for s in sentences if re.search(r'\b(?:we (?:propose|present|develop|introduce|show|demonstrate|design)|here|this study|our (?:model|method|framework))\b',s,re.I)),sentences[0]);words=chosen.split();return ' '.join(words[:20])+('…' if len(words)>20 else '')
def facts(p,s,a):
 title=p['title'];methods=[]
 for label,pat in [('Large language models',r'large language|language model|\bLLM\b|GPT'),('Foundation models',r'foundation model|alphafold|protein language'),('Generative or diffusion models',r'generative|diffusion model|\bGAN\b'),('Deep learning / neural networks',r'deep learning|neural network|convolution|transformer|autoencoder'),('Machine learning',r'machine learning|random forest|support vector|XGBoost'),('Reinforcement learning',r'reinforcement learning'),('Self-supervised / contrastive learning',r'self.supervis|contrastive')]:
  if re.search(pat,a,re.I):methods.append(label)
 counts=[]
 for m in re.finditer(r'\b(\d[\d,]*(?:\.\d+)?(?:\s*(?:million|billion|thousand))?)\s+(patients?|participants?|individuals?|subjects?|images?|scans?|radiographs?|samples?|cells|proteins?|sequences?|datasets?|cohorts?|hospitals?|cent(?:er|re)s?|countries|molecules|compounds|species|genomes|slides|videos|trials|physicians|doctors|nurses|experts|structures)\b',a,re.I):
  item={'value':m.group(1),'unit':m.group(2).lower(),'context':'Independent source-reported count; cohort role not manually resolved'}
  if item not in counts:counts.append(item)
 ds=[]
 for name,pat in [('TCGA',r'\bTCGA\b|The Cancer Genome Atlas'),('UK Biobank',r'UK Biobank'),('MIMIC-IV',r'MIMIC[- ]IV'),('MIMIC-III',r'MIMIC[- ]III'),('ADNI',r'\bADNI\b'),('GEO',r'Gene Expression Omnibus|\bGEO\b'),('GTEx',r'\bGTEx\b'),('Human Cell Atlas',r'Human Cell Atlas'),('BraTS',r'\bBraTS\b'),('CheXpert',r'CheXpert'),('PhysioNet',r'PhysioNet'),('Protein Data Bank',r'Protein Data Bank|\bPDB\b'),('UniProt',r'\bUniProt\b')]:
  if re.search(pat,a,re.I):ds.append({'name':name,'source':'Named in publisher abstract','access':'Consult the original availability statement; mention alone does not establish open access','url':p['url']+'#data-availability'})
 q=dict(p);q.pop('abstract',None);q.pop('epmc_abstract',None)
 first=s.get('authors',[{}])[0] if s.get('authors') else {};q.update(research_problem=excerpt(a),problem_is_excerpt=True,ai_method='; '.join(methods) or AI.search(a).group(0),study_summary='',article_type=s.get('article_type') or 'Article',experiment_scale=counts[:8],scale_status='source_extracted',datasets=ds,datasets_status='source_mentioned',authors=s.get('authors') or p.get('authors',[]),first_author=s.get('first_author'),first_author_first_institution=s.get('first_author_first_institution'),first_author_first_affiliation=s.get('first_author_first_affiliation'),first_author_mapping_verified=s.get('first_author_mapping_verified',False),all_affiliations=s.get('all_affiliations',[]),code_urls=s.get('code_links',[]),data_urls=s.get('data_links',[]),evidence_links=[{'label':'Original article and abstract','url':p['url']+'#Abs1'}],review_level='abstract',curation_level='source_extracted',scope_reason='Rule-assisted screening found explicit AI method and biomedical task evidence in the publisher abstract. Research type was checked against publisher metadata; extracted experimental fields are labeled.',field_status={'research_problem':'attributed_source_excerpt_max20words','experiment_scale':'source_extracted_role_unresolved','datasets':'source_mentioned','screening':'high_precision_abstract_rules'})
 return q
reviews=[];screen=[];audit=[]
for i,p in enumerate(rows):
 s=load_source(p);a=s.get('abstract') or p.get('epmc_abstract') or p.get('abstract','');typ=s.get('article_type') or ''
 if not allowed.match(typ):decision='excluded';reason='Publisher type is outside the research/review/protocol scope: '+typ
 elif not a:decision='pending';reason='No accessible abstract evidence available'
 elif not AI.search(a):decision='pending';reason='Abstract does not establish a substantive AI method; title-only inclusion avoided'
 elif not BIO.search(a):decision='excluded';reason='Actual abstract describes AI or physical research without a biomedical task'
 elif NONBIO.search(a) and not re.search(r'patient|clinical|disease|health risk|human.*expos|protein|\bRNA\b|\bDNA\b|\bgene\b|biomed|drug|neuron|bioinformatics',a,re.I):decision='excluded';reason='Environmental/agricultural/physical task without a substantive biomedical target'
 else:
  # Avoid incidental biomedical examples in broad vision benchmarks and brain-inspired hardware.
  titlebio=bool(BIO.search(p['title']));hits=len(BIO.findall(a))
  if (not titlebio and hits<3) or (re.search(r'brain.inspired|neuromorphic|synaptic transistor|optical neural|photonic.*comput',p['title'],re.I) and not re.search(r'patient|clinical|disease|\bECG\b|arrhyth|cancer|biomedical|biological neuron',a,re.I)):
   decision='pending';reason='Biomedical context may be incidental; needs methods-based centrality review'
  else:decision='included';reason='Explicit AI and substantive biomedical abstract evidence';reviews.append(facts(p,s,a))
 screen.append(dict(id=p['id'],doi=p['doi'],journal=p['journal'],status=decision,reason=reason,screening_method='publisher_abstract_rule_screen'))
 if decision in ['included','pending']:audit.append(dict(index=i,id=p['id'],title=p['title'],decision=decision,type=typ,abstract=a[:1800]))
(D/'reviews/root.json').write_text(json.dumps(reviews,ensure_ascii=False,indent=2));(D/'screening/root.json').write_text(json.dumps(screen,ensure_ascii=False,indent=2));(C/'root-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2));print('ROOT',len(reviews),'included',sum(x['status']=='excluded' for x in screen),'excluded',sum(x['status']=='pending' for x in screen),'pending')
