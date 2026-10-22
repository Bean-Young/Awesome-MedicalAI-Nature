import json,pathlib,sys,re
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from core_enrich import extract_html
R=pathlib.Path(__file__).resolve().parents[1]
rows=json.loads((R/'data/assigned-core.json').read_text());en=json.loads((R/'data/core-manual-en.json').read_text());zh=json.loads((R/'data/core-manual-notes.json').read_text());reviews=[];screen=[]
allowed={'Article','Review Article','Review','Analysis','Resource','Technical Report','Brief Communication','Letter','Protocol','Registered Report','Matters Arising'}
units={'来源研究':'source studies','影像—报告对':'image-report pairs','外部数据集':'external datasets','胸部病变类型':'pathology types','TB组学数据':'TB of omics data','重点候选蛋白':'candidate proteins','抽样视频帧':'video frames','图像':'images','代码任务':'coding tasks','LLM':'models','医学研究者':'medical researchers','高光谱图像':'hyperspectral images','MRI检查':'MRI examinations','放射学诊断':'diagnostic categories','阴性肽':'negative peptides','阳性肽':'positive peptides','候选肽':'candidate peptides','视频片段':'video clips','手术类型':'procedure types','下游任务':'tasks','外科医生':'surgeons','患者':'patients','癌种':'cancer types','来源临床试验':'source clinical trials','T细胞':'T cells','血清标志测量':'serum-marker measurements','参与者':'individuals','视频':'videos','诊断类别':'diagnostic categories','生物医学数据任务':'benchmark tasks','乳腺超声图像':'ultrasound images','认证放射科医生':'radiologists','表型':'phenotypes','氨基酸变异预测':'variant predictions'}
name_map={'四家美国学术医疗机构心脏MRI':'Four-US-institution cardiac MRI cohorts'}
for row in rows:
 id=row['id'];p=R/'research-cache'/f'{id}-source.json';source=json.loads(p.read_text()) if p.exists() else {}
 kind=source.get('article_type') or row.get('article_type')
 base={'id':id,'doi':row['doi'],'title':row['title'],'journal':row['journal'],'date':row['date'],'url':row['url']}
 if id in en:
  if (R/'research-cache'/f'{id}.html').exists():source=extract_html((R/'research-cache'/f'{id}.html').read_text(),row['url'])
  n=en[id];z=zh.get(id,{})
  out=dict(base,article_type=source.get('article_type') or kind,**{k:v for k,v in n.items()if k!='contexts'})
  out.update(first_author=source.get('first_author'),first_institution=source.get('first_author_first_institution'),first_author_first_institution=source.get('first_author_first_institution'),first_author_affiliations=(source.get('authors')or[{}])[0].get('affiliations',[]),all_affiliations=source.get('all_affiliations',[]),authors=source.get('authors',[]),first_author_mapping_verified=source.get('first_author_mapping_verified',False))
  scales=[]
  for j,sc in enumerate(z.get('experiment_scale',[])):
   c=dict(sc);c['unit']=units.get(c['unit'],c['unit']);c['context']=n.get('contexts',[])[j] if j<len(n.get('contexts',[])) else 'As reported in the original study'
   if 'qualifier'in c:c['qualifier']={'超过':'more than','约':'approximately'}.get(c['qualifier'],c['qualifier'])
   scales.append(c)
  out['experiment_scale']=n.get('experiment_scale',scales)
  datasets=[]
  for ds in n.get('datasets',z.get('datasets',[])):
   d=dict(ds)
   if id in en and ds in n.get('datasets',[]):datasets.append(d);continue
   d['name']=name_map.get(d['name'],d['name']);d['source']='Original study and linked dataset provider';ac=d.get('access','')
   d['access']='Restricted; not publicly shared'if any(t in ac for t in ['不公开','不能再分发']) else 'Controlled or licensed access'if any(t in ac for t in ['申请','受控','协议','许可']) else 'Mixed access; see dataset-specific conditions'if '限制'in ac else 'Publicly accessible under source terms'if'公开'in ac else 'See the linked data-availability statement'
   datasets.append(d)
  if not datasets:out['dataset_reporting_note']='No dataset name has been manually verified yet; consult the linked data-availability statement.'
  out['datasets']=datasets
  out['code_urls']=list(dict.fromkeys(a['url']for a in source.get('code_links',[]) if a.get('url')))
  out['data_urls']=list(dict.fromkeys(a['url']for a in source.get('data_links',[])if a.get('url')))
  links=[{'label':'Publisher article','url':row['url']}]
  for label in ['Methods','Data availability','Code availability']:
   if label in source.get('section_urls',{}):links.append({'label':label,'url':source['section_urls'][label]})
  links.append({'label':'Author affiliations','url':row['url']+'#author-information'});out['evidence_links']=links
  out['review_level']='fulltext'if source.get('sections',{}).get('Methods') else'abstract'
  out['scope_reason']=out['scope_evidence'];reviews.append(out);screen.append(dict(base,status='included',reason=out['scope_reason'],review_level=out['review_level']))
 elif kind and kind not in allowed:
  screen.append(dict(base,status='excluded',reason='Publisher labels this item '+kind+'; the research/review catalogue excludes this publication type.',article_type=kind,review_level='metadata'))
 elif id=='s41551-026-01659-x':
  screen.append(dict(base,status='excluded',reason='The accessible abstract describes electroactive cardiac patches, animal experiments and monodomain cardiac simulation, without a verified AI method.',article_type=kind,review_level='abstract'))
 else:
  screen.append(dict(base,status='pending',reason='Abstract and AI-biomedical scope have not yet been individually reviewed.',article_type=kind,review_level=None))
(R/'data/reviews/core.json').write_text(json.dumps(reviews,ensure_ascii=False,indent=2));(R/'data/screening/core.json').write_text(json.dumps(screen,ensure_ascii=False,indent=2))
from collections import Counter
print('reviews',len(reviews),'screen',Counter(a['status']for a in screen))
