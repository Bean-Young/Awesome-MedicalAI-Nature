import json,pathlib,re,collections
R=pathlib.Path(__file__).resolve().parents[1]
rows=json.loads((R/'data/assigned-core.json').read_text())
allowed={'Article','Review Article','Review','Analysis','Resource','Technical Report','Brief Communication','Letter','Protocol','Registered Report','Matters Arising'}
AI=[(r'large language model|\bLLMs?\b|language model','Language models'),(r'foundation model','Foundation models'),(r'deep[- ]learning|deep[- ]neural|convolutional[- ]neural|\bCNNs?\b','Deep learning'),(r'machine[- ]learning|\bML\b','Machine learning'),(r'neural[- ]network|graph[- ]neural|transformer|autoencoder','Neural networks'),(r'artificial[- ]intelligence|\bAI\b','Artificial intelligence'),(r'reinforcement learning','Reinforcement learning'),(r'\bgenerative\b|diffusion[- ]model|flow.matching','Generative modeling'),(r'AlphaFold|RoseTTAFold|protein language|sequence.to.sequence','Protein/sequence modeling'),(r'random forest|support vector machine|gradient boost|XGBoost','Statistical learning'),(r'computational.{0,15}design|in silico.{0,15}design|inverse design','Computational design')]
BIO=[(r'patient|clinical|healthcare|hospital|medical|disease|therap|cancer|tumou?r|surg|drug|pharmac|antibod|vaccine|patholog|radiolog|biomed|cardiac|cardiov|neurodeg|Alzheimer|Parkinson|schizoph|autism|diabet|psychi|psychedelic','Medicine and health'),(r'genom|transcript|epigen|single.cell|multi.?omic|proteom|protein|peptide|\bRNA\b|\bDNA\b|molecul.*bio|bioinform|cellular|biolog|tissue|brain|neuronal|electroencephal|biomolecular|fluorescence|immunofluorescence|neuroscien|fMRI|zebrafish|Drosophila|enzyme|CRISPR','Biomedical and biological computation')]
manual={}
def add(ids,status,reason):
 for x in ids.split():manual['s41586-026-'+x]={'status':status,'reason':reason,'screening_method':'manual_abstract_review'}
add('11161-8 11162-7 11119-w 10965-y 11160-9 11055-9 11045-x 11044-y 11005-5 11001-9 10979-6 10987-6 10952-3 10975-w 10910-z 10900-1 10687-1','included','The publisher abstract describes a concrete AI method, evaluation, or AI-focused review addressing human health, biological data analysis, molecular design, or biomedical imaging.')
add('11138-7 11126-x 11115-0 10986-7 10898-6 10917-6','excluded','The publisher abstract addresses physical sciences, weather, energy, or fluid control rather than medicine, biomedical research, bioinformatics, or drug discovery.')
add('11111-4 11036-y 10996-5 10950-5','excluded','The publisher abstract evaluates general computing, games, or autonomous driving; any biological or medical examples are contextual rather than evaluated biomedical applications.')
add('11021-5','excluded','The abstract concerns plant salicylic-acid signaling and immune mechanisms; structural prediction is ancillary to plant biology rather than a medical or biomedical AI research target.')
manual['s41551-026-01659-x']={'status':'excluded','reason':'The abstract describes electroactive cardiac patches, animal experiments and monodomain cardiac simulation, without a stated AI method.','screening_method':'manual_abstract_review'}
manual['s41551-026-01806-4']={'status':'excluded','reason':'The review focuses on multi-organ tissue chips; AI is mentioned as a future integration opportunity rather than the central reviewed method.','screening_method':'manual_abstract_review'}
manual['s41551-026-01779-4']={'status':'pending','reason':'The abstract reports normative connectivity biomarkers and atomoxetine-response prediction in ADHD but does not identify the prediction algorithm as an AI method; methods verification is required.','screening_method':'manual_abstract_review'}
manual['s41586-026-10753-8']={'status':'pending','reason':'The systems-vaccinology review mentions emerging AI; the accessible abstract does not establish whether AI methods form a central reviewed theme.','screening_method':'manual_abstract_review'}
manual['s41586-026-10967-w']={'status':'pending','reason':'The abstract explicitly mentions machine-learning-based methods in endocannabinoid reward experiments, but the specific analytic contribution requires methods inspection.','screening_method':'manual_abstract_review'}
manual.update(json.loads((R/'data/core-science-manual.json').read_text()) if (R/'data/core-science-manual.json').exists() else {})
notes=json.loads((R/'data/core-manual-en.json').read_text())
out=[]
for row in rows:
 id=row['id'];s=json.loads((R/'research-cache'/f'{id}-source.json').read_text());abstract=s.get('abstract') or row.get('epmc_abstract') or row.get('abstract') or ''; text=re.sub(r'<[^>]+>',' ',abstract);kind=s.get('article_type');aim=[label for pat,label in AI if re.search(pat,text,re.I)];bio=[label for pat,label in BIO if re.search(pat,text,re.I)]
 d={'id':id,'doi':row['doi'],'title':row['title'],'journal':row['journal'],'date':row['date'],'url':row['url'],'article_type':kind,'review_level':'abstract' if text else 'metadata','source_abstract_available':bool(text),'ai_evidence_labels':aim,'domain_evidence_labels':bio}
 if id in notes:d.update(status='included',reason=notes[id]['scope_evidence'],screening_method='manual_source_review',curation_level='human_curated')
 elif kind and kind not in allowed:d.update(status='excluded',reason=f'Publisher publication type is {kind}; only research, explicit reviews, and protocols are in scope.',screening_method='publisher_type')
 elif id in manual:d.update(manual[id])
 elif not text:d.update(status='pending',reason='No accessible publisher or indexed abstract was recovered; source inspection is incomplete.',screening_method='source_missing')
 elif aim and bio:d.update(status='included',reason='Publisher abstract contains explicit AI-method terminology and a biomedical or biological-data target; this is a source-extracted candidate rather than a manually curated highlight.',screening_method='abstract_evidence_rules',curation_level='source_extracted')
 elif not bio:d.update(status='excluded',reason='The screened abstract does not establish a medical, biomedical, biological-data, or drug-discovery target.',screening_method='abstract_evidence_rules')
 else:d.update(status='pending',reason='The abstract establishes a biological or medical topic but explicit AI-method evidence was not established by the terminology screen; manual methods review is required.',screening_method='abstract_evidence_rules')
 out.append(d)
(R/'data/core-screen-decisions.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(collections.Counter(x['status'] for x in out))
for x in out:
 if x['status']=='pending':
  s=json.loads((R/'research-cache'/f"{x['id']}-source.json").read_text()); print(x['id'],x['title'],'\n',s.get('abstract',''),'\n')
