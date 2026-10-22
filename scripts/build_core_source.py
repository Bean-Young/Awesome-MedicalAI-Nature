"""Build a disclosed source-extracted catalogue; raw abstracts stay offline."""
import json,pathlib,re,html,collections,sys
R=pathlib.Path(__file__).resolve().parents[1]
# Preserve the authored highlight profiles assembled separately.
sys.path.insert(0,str(R/'scripts'))
import assemble_core
manual=json.loads((R/'data/reviews/core.json').read_text());manual={x['id']:x for x in manual}
rows=json.loads((R/'data/assigned-core.json').read_text()); rows={x['id']:x for x in rows}
screen=json.loads((R/'data/core-screen-decisions.json').read_text())

def topics_for(text):
 rules=[('Oncology',r'cancer|tumou?r|carcinoma|leukemia|lymphoma|myeloma|oncolog'),('Cardiovascular medicine',r'cardia|cardiov|heart|arrhythm|vascular|blood pressure'),('Neurology and neuroscience',r'brain|neuro|Alzheimer|Parkinson|epilepsy|EEG|fMRI|cortical|cortex'),('Mental health',r'psychi|depress|schizoph|autism|psychotherap|mental health|anxiety'),('Infectious disease and antimicrobials',r'infect|antimicro|antibiotic|SARS|virus|viral|bacter|phage'),('Imaging and computational pathology',r'imag|patholog|microscop|radiolog|tomograph|ultrasound'),('Genomics and single-cell analysis',r'genom|single.cell|transcript|epigen|chromatin|gene regulat'),('Protein and molecular design',r'protein|peptide|enzyme|antibod|molecul|drug|ligand|receptor'),('Clinical decision support',r'clinical decision|diagnos|triage|medical agent|health agent'),('Medical devices and physiological monitoring',r'wearable|monitor|electrocardio|ECG|sensor|neuroprosthe|biosens')]
 return [lab for lab,pat in rules if re.search(pat,text,re.I)] or ['Biomedical data methods']

def institution(source):
 first=(source.get('authors') or [{}])[0];afs=first.get('affiliations') or [];af=afs[0] if afs else {};name=af.get('name');full=af.get('full_address') or ''
 cue=r'university|universit[äé]|college|institute|hospital|academy|academia|school|centre|center|laborator|research|Google|Microsoft|DeepMind|Meta|Amazon|OpenAI|Stanford|Harvard|Helmholtz|UCSF|MIT\b|ETH\b|EPFL|Charit|Inserm|CNRS|Genentech|Roche|Novartis|AstraZeneca|Pfizer|NVIDIA|Merck|Regeneron|Biogen|Illumina|Broad|Bayer|Sanger|Allen|Janelia|Cleveland|Mayo|Sinai|Technion|Insilico|Tsinghua|Peking|Fudan|Zhejiang|Westlake'
 if name and re.search(cue,name,re.I):return name,'publisher_jsonld'
 if name in {'Fondazione IRCCS Istituto Nazionale dei Tumori di Milano','Rambam Health Care Campus','Specifica, an IQVIA Business','Johnson & Johnson','Paige','KAIST','Keiji AI','Virginia Tech','Human Technopole','Universidad Carlos III de Madrid','IRCCS Ospedale San Raffaele','NYU Langone Health','UNSW Sydney','FutureHouse','Fondazione Human Technopole','CUHK','Valence Labs','Tencent','JURA Bio','Limbic','CYBO','Mass General Brigham','Profluent Bio'}:return name,'publisher_jsonld_name_manually_checked'
 if full.startswith('Centro Nacional de Análisis Genómico,'):return 'Centro Nacional de Análisis Genómico','publisher_affiliation_address_segment_manually_checked'
 # Find a literal organization-bearing address segment; never treat a city as institution.
 parts=[x.strip() for x in full.split(',')]
 for part in parts:
  if re.search(cue,part,re.I) and not re.match(r'^(Department|Division|Faculty|School)\b',part,re.I):return part,'publisher_affiliation_address_segment'
 return None,'unresolved_organization_name'

DATASETS=[('UK Biobank',r'UK[ -]Biobank|UKBB'),('The Cancer Genome Atlas (TCGA)',r'\bTCGA\b|The Cancer Genome Atlas'),('CPTAC',r'\bCPTAC\b'),('ADNI',r'\bADNI\b|Alzheimer.s Disease Neuroimaging Initiative'),('All of Us',r'All of Us'),('MIMIC',r'\bMIMIC(?:[- ](?:III|IV|CXR))?\b'),('NHANES',r'\bNHANES\b|National Health and Nutrition Examination Survey'),('TCIA',r'\bTCIA\b|The Cancer Imaging Archive'),('GEO',r'Gene Expression Omnibus|\bGEO\b'),('GTEx',r'\bGTEx\b'),('Human Protein Atlas',r'Human Protein Atlas'),('Protein Data Bank (PDB)',r'Protein Data Bank|\bPDB\b'),('ChEMBL',r'\bChEMBL\b'),('PubChem',r'\bPubChem\b'),('BindingDB',r'BindingDB'),('DrugBank',r'DrugBank'),('LINCS',r'\bLINCS\b'),('Cell Painting',r'Cell Painting'),('BRACS',r'\bBRACS\b'),('CheXpert',r'CheXpert'),('PadChest',r'PadChest'),('ISIC',r'\bISIC\b'),('BraTS',r'\bBraTS\b'),('PhysioNet',r'PhysioNet'),('OpenNeuro',r'OpenNeuro'),('Human Connectome Project',r'Human Connectome Project|\bHCP\b'),('Allen Brain Atlas',r'Allen Brain Atlas'),('SCOP',r'\bSCOP\b'),('UniProt',r'UniProt'),('UniRef',r'UniRef\d*'),('Pfam',r'\bPfam\b'),('Ensembl',r'Ensembl'),('Gene Ontology',r'Gene Ontology')]
scale_pattern=re.compile(r'(?P<qual>more than|over|approximately|about|up to|>)?\s*(?P<num>\d[\d,]*(?:\.\d+)?)\s*(?P<mag>million|billion|thousand|m|k)?\s*(?P<unit>patients|participants|individuals|subjects|women|children|adults|infants|neonates|images|scans|videos|frames|slides|whole.slide images|cells|nuclei|proteins|peptides|molecules|compounds|sequences|variants|genes|datasets|cohorts|centers|centres|hospitals|models|benchmarks|tasks|radiologists|clinicians|surgeons|experts|hours|trials)\b',re.I)

def source_record(d,s):
 row=rows[d['id']];text=html.unescape(re.sub(r'<[^>]+>',' ',s.get('abstract') or row.get('epmc_abstract') or row.get('abstract') or ''));text=re.sub(r'\s+',' ',text).removeprefix('Abstract ').strip();title=html.unescape(row['title'])
 ai=d.get('ai_evidence_labels') or []
 if not ai:ai=['Method identified in manual source screening; see scope rationale']
 tops=topics_for(title+' '+text)
 # No invented outcome or paraphrase: clearly mark the only verbatim excerpt.
 sentences=re.split(r'(?<=[.!?])\s+',text)
 focus=next((x for x in sentences if re.search(r'\b(?:we present|we introduce|we developed|we propose|here we|our (?:model|framework|method))\b',x,re.I)),sentences[0] if sentences else '')
 excerpt=' '.join(focus.split()[:24]);inst,instbasis=institution(s)
 scales=[];seen=set()
 for m in scale_pattern.finditer(text):
  key=m.group().strip()
  if key in seen:continue
  seen.add(key)
  val=m['num'].replace(',','');val=float(val) if '.'in val else int(val)
  mag=(m['mag'] or '').lower()
  if mag:val*= {'million':1000000,'m':1000000,'billion':1000000000,'thousand':1000,'k':1000}[mag]
  scales.append({'value':val,'unit':m['unit'].lower().replace('centres','centers'),'context':'Count stated in the publisher abstract; cohort overlap and training/test stage require source-level interpretation.','qualifier':(m['qual'] or 'as reported').lower(),'verification':'literal_abstract_count'})
 scales=scales[:15]
 sections=s.get('sections')or{};avail=sections.get('Data availability','');ds=[]
 for name,pat in DATASETS:
  if re.search(pat,text+' '+avail,re.I):ds.append({'name':name,'source':'Named in the publisher abstract or data-availability section','access':'Consult the linked source for dataset-specific access and reuse conditions','url':s.get('section_urls',{}).get('Data availability',row['url'])})
 ds+= [{'name':m,'source':'Accession reported in publisher data availability','access':'Consult the repository record for access conditions','url':('https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc='+m if m.startswith('GSE') else 'https://www.ncbi.nlm.nih.gov/bioproject/'+m)}for m in list(dict.fromkeys(re.findall(r'\b(?:GSE\d+|PRJNA\d+|PRJEB\d+)\b',avail)))[:12]]
 links=[{'label':'Publisher article and abstract','url':row['url']},{'label':'Author affiliations','url':row['url']+'#author-information'}]
 for label in ['Methods','Data availability','Code availability','Supplementary information']:
  if label in s.get('section_urls',{}):links.append({'label':label,'url':s['section_urls'][label]})
 out={k:row[k]for k in ['id','doi','journal','date','url']};out.update(title=title,article_type=d.get('article_type'),research_problem='Research target: '+title,ai_method='; '.join(ai),study_summary='SOURCE EXCERPT (publisher abstract, up to 24 words): “'+excerpt+'”',topics=tops,scope_evidence=d['reason'],scope_reason=d['reason'],experiment_scale=scales,datasets=ds,first_author=s.get('first_author'),first_institution=inst,first_author_first_institution=inst,first_author_affiliations=(s.get('authors')or[{}])[0].get('affiliations',[]),all_affiliations=s.get('all_affiliations',[]),authors=s.get('authors',[]),first_author_mapping_verified=s.get('first_author_mapping_verified',False),institution_extraction_basis=instbasis,first_institution_manually_verified='manually_checked' in instbasis,code_urls=list(dict.fromkeys(x['url']for x in s.get('code_links',[])if x.get('url'))),data_urls=list(dict.fromkeys(x['url']for x in s.get('data_links',[])if x.get('url'))),evidence_links=links,review_level=d.get('review_level','abstract'),curation_level='source_extracted',screening_method=d['screening_method'],source_fields_verified={'publisher_abstract_available':bool(text),'publisher_author_affiliation_mapping':s.get('first_author_mapping_verified',False),'numeric_unit_literal_match':bool(scales),'numeric_denominator_manually_verified':False,'dataset_names_manually_verified':False,'research_problem_manually_paraphrased':False,'outcomes_manually_interpreted':False})
 return out
out=[]
for d in screen:
 if d['status']!='included':continue
 s=json.loads((R/'research-cache'/f"{d['id']}-source.json").read_text())
 if d['id']in manual:
  x=manual[d['id']];x['curation_level']='human_curated';x['screening_method']='manual_source_review';inst,basis=institution(s);x['first_institution']=x['first_author_first_institution']=inst;x['institution_extraction_basis']=basis
 else:x=source_record(d,s)
 out.append(x)
(R/'data/reviews/core.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));(R/'data/screening/core.json').write_text(json.dumps(screen,ensure_ascii=False,indent=2));print('Saved',len(out),'reviews;',collections.Counter(x['curation_level']for x in out),collections.Counter(x['status']for x in screen))
