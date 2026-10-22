import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def add(rows):
 a=json.load(open(ROOT/'research-cache/npj/manual-new.json'));p=ROOT/'research-cache/npj/manual-overrides.json';out=json.load(open(p)) if p.exists() else {}
 for row in rows:
  i,problem,method,summary,*scale=row;x=a[i]
  item={'research_problem':problem,'ai_method':method,'outcome_summary':summary,'manual_review':'source_abstract_read_2026-10-23','source_evidence':'publisher abstract with source Methods screening'}
  if scale:item['experiment_scale']=[dict(value=n,unit=u,role=r,source_section='Abstract',verified=True) for n,u,r in scale[0]]
  out[x['id']]=item
 p.write_text(json.dumps(out,ensure_ascii=False,indent=2));print('manual',len(out))
if __name__=='__main__':add(json.load(__import__('sys').stdin))
