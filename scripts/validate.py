"""Validate the public snapshot and denominator identities (standard library only)."""
import json,re
from pathlib import Path
from collections import Counter
R=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text())
papers=read(R/'dist/data/papers.json');coverage=read(R/'dist/data/coverage.json');decisions=read(R/'data/screening-decisions.json')
assert len(papers)==len({p['doi'] for p in papers})==coverage['indexed']
assert len(decisions)==coverage['recall_candidates']
for p in papers:
 assert '2026-01-01'<=p['date']<='2026-10-23',p['id']
 assert p['journal']=='npj Digital Medicine' or p['journal']=='Nature' or p['journal'].startswith('Nature ')
 assert all(p.get(k) for k in ['title','doi','url','research_problem','ai_method','study_summary','limitations','scope_reason']),p['id']
 assert not re.search(r'[\u4e00-\u9fff]', ' '.join(str(p.get(k,'')) for k in ['research_problem','ai_method','study_summary','scope_reason'])),p['id']
 assert not set(p)&{'abstract','epmc_abstract','previous_review','data_availability','code_availability'}
 assert p['curation_level'] in ['curated','source_extracted']
 assert all(v in [True,False,None] for v in p['study_design'].values())
 assert all(x.get('unit','').lower() not in ['reported n','unknown','n'] for x in p['experiment_scale']),p['id']
 for key in ['evidence_links','code_links','data_links']:
  assert all(x['url'].startswith(('https://','http://')) for x in p[key]),p['id']
 assert not p['problem_is_excerpt'] or len(p['research_problem'].split())<=20,p['id']
for j in coverage['ledger']:
 assert 0<=j['indexed']<=j['reviewed']<=j['candidates'],j
 assert j['pending']==j['candidates']-j['reviewed'],j
assert sum(j['indexed'] for j in coverage['ledger'])==len(papers)
assert sum(j['candidates'] for j in coverage['ledger'])==len(decisions)
assert sum(x['status']=='included' for x in decisions)==len(papers)
html=(R/'dist/index.html').read_text();ids=re.findall(r'id="([^"]+)"',html)
assert len(ids)==len(set(ids))
assert (R/'dist/METHODOLOGY.md').is_file()
assert all(not x.name.endswith(('.pdf','.html')) for x in (R/'dist/data').iterdir())
print(f'Validated {len(papers):,} papers, {len(decisions):,} decisions and {len(coverage["ledger"])} journal ledgers.')
print(dict(Counter(x['status'] for x in decisions)))
