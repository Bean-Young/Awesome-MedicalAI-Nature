from pathlib import Path
import json,shutil,collections
R=Path(__file__).resolve().parents[1];D=R/'data'
r=json.loads((R/'dist/data/papers.json').read_text());coverage=json.loads((R/'dist/data/coverage.json').read_text());shutil.copy(R/'dist/data/papers.json',D/'catalogue.json');shutil.copy(R/'dist/data/coverage.json',D/'coverage.json');shutil.copy(R/'METHODOLOGY.md',R/'dist/METHODOLOGY.md')
decisions={}
for name in ['core','other','root','npj-excluded','npj-pending','supplemental']:
 path=D/'screening'/(name+'.json')
 for x in json.loads(path.read_text()):
  k=x.get('id') or x.get('doi','').split('/')[-1];state=x.get('status') or x.get('decision');state='pending' if state in ['pending','needs_review'] else state
  if name=='npj-excluded':state='excluded'
  if name=='npj-pending':state='pending'
  if k not in decisions or state!='pending':decisions[k]={'id':k,'doi':x.get('doi') or '10.1038/'+k,'status':state,'reason':x.get('reason') or x.get('screening') or 'Source screening; see original article','url':'https://www.nature.com/articles/'+k}
for k,x in json.loads((D/'curation/final-scope-adjudications.json').read_text()).items():decisions[k]={'id':k,'doi':'10.1038/'+k,'status':x['status'],'reason':x['reason'],'url':x.get('source_url','https://www.nature.com/articles/'+k)}
for p in r:decisions[p['id']]={'id':p['id'],'doi':p['doi'],'status':'included','reason':p['scope_reason'],'url':p['url']}
candidates={x['id'] for x in json.loads((D/'candidates.json').read_text())};assert not(candidates-decisions.keys()),candidates-decisions.keys();decisions=[decisions[k] for k in sorted(candidates)]
(D/'screening-decisions.json').write_text(json.dumps(decisions,ensure_ascii=False,indent=2))
text=['# Paper catalogue','',f"Snapshot: **2026-10-23** · **{len(r):,}** confirmed records across **{coverage['journals_with_indexed_papers']}** journals.",'','[Interactive website](https://awesome-medicalai-nature.grandowlet6.chatgpt.site/) · [Methodology](METHODOLOGY.md) · [JSON](data/catalogue.json)','','This is the confirmed catalogue, not an exhaustive estimate of journal-wide biomedical AI publication shares. Every indexed publication has a paper-specific interpretation; source and field verification levels remain explicit.','']
for journal,rows in sorted(collections.defaultdict(list,((j,[p for p in r if p['journal']==j]) for j in {p['journal'] for p in r})).items()):
 text+=['## '+journal,'',f'{len(rows)} publications.','','| Online date | Paper | First institution | Record |','| --- | --- | --- | --- |']
 for p in rows:
  clean=lambda s:str(s or '—').replace('|','/').replace('\n',' ')
  text.append(f"| {p['date']} | [{clean(p['title'])}]({p['url']}) | {clean(p['first_institution'])} | {'Curated' if p['curation_level']=='curated' else 'Source-extracted'} |")
 text+=['']
(R/'CATALOGUE.md').write_text('\n'.join(text))
print(collections.Counter(x['status'] for x in decisions));print('curated',coverage['curated'])
