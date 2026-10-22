import json,re,time,hashlib
from collect import ROOT,get,save
D=ROOT/'data'
AI=r'artificial intelligence|machine[- ]learning|deep[- ]learning|neural[- ]network|large language|language model|foundation model|generative (?:ai|model|adversarial)|reinforcement learning|self[- ]supervis|contrastive learning|graph neural|computer vision|transfer learning|representation learning|diffusion model|alphafold|alphagenome|protein language|transformer|random forest|support vector machine|xgboost|autoencoder|few[- ]shot|zero[- ]shot|digital twin|bayesian optim|active learning|multimodal model|convolutional|learning[- ]based|data[- ]driven|deep model'
TERMS=['machine learning','deep learning','artificial intelligence','neural network','language model','foundation model','reinforcement learning','generative model','AlphaFold','AlphaGenome','diffusion model','self-supervised','graph neural','representation learning','contrastive learning','computer vision','transfer learning','random forest','support vector machine','transformer','autoencoder']
CORE={'nature','nm','nmeth','natmachintell','nbt','natbiomedeng','ng','neuro','natcomputsci','nsmb'}
def epmc():
 journals=json.loads((D/'journals.json').read_text());issns=sorted({i for j in journals for i in j.get('issns',[])})
 query='FIRST_PDATE:[2026-01-01 TO 2026-10-23] AND ('+' OR '.join('ISSN:'+i for i in issns)+') AND ('+' OR '.join('TITLE_ABS:"'+t+'"' for t in TERMS)+')'
 params=dict(query=query,format='json',resultType='core',pageSize=1000,cursorMark='*');out=[]
 while True:
  r=get('https://www.ebi.ac.uk/europepmc/webservices/rest/search',params).json();rows=r.get('resultList',{}).get('result',[]);out+=rows;print('EPMC',len(out),'/',r.get('hitCount'),flush=True)
  if not rows or len(out)>=r.get('hitCount',0):break
  mark=r.get('nextCursorMark')
  if not mark or mark==params['cursorMark']:break
  params['cursorMark']=mark
 save(D/'cache/epmc.json',out);save(D/'epmc-search.json',dict(query=query,hit_count=r.get('hitCount'),retrieved=len(out),source='https://www.ebi.ac.uk/europepmc/webservices/rest/search',date='2026-10-23'))
 return out
def build():
 meta=json.loads((D/'metadata-all.json').read_text());ep=json.loads((D/'cache/epmc.json').read_text()) if (D/'cache/epmc.json').exists() else []
 bydoi={p['doi'].lower():p for p in ep if p.get('doi')};cand=[];skipped=[]
 for p in meta:
  doi=p['doi'].lower();e=bydoi.get(doi)
  if e:
   p['epmc_abstract']=re.sub('<[^>]+>',' ',e.get('abstractText',''));p['epmc_id']=e.get('id');p['pmcid']=e.get('pmcid');p['epmc_source']='https://europepmc.org/article/'+e.get('source','MED')+'/'+e.get('id','')
  text=' '.join([p['title'],p.get('abstract',''),p.get('epmc_abstract','')]);matched=re.search(AI,text,re.I)
  if p['id'].startswith('d'):
   skipped.append(dict(doi=doi,title=p['title'],journal=p['journal'],reason='Nature news/report DOI series; not primary journal research'));continue
  if matched or e:
   p['candidate_reason']='EuropePMC title/abstract AI query' if e else 'AI method phrase: '+matched.group(0)
   p['partition']='npj' if p['journal_id']=='npjdigitalmed' else 'core' if p['journal_id'] in CORE or (p['journal_id']=='ncomms' and int(hashlib.sha1(doi.encode()).hexdigest(),16)%2==0) else 'other';cand.append(p)
 save(D/'candidates.json',sorted(cand,key=lambda p:(p['date'],p['doi']),reverse=True));save(D/'screening/metadata-exclusions.json',skipped)
 print('CANDIDATES',len(cand),{k:sum(p['partition']==k for p in cand) for k in ['core','other','npj']},'EPMC joined',sum(bool(p.get('epmc_id')) for p in cand),flush=True)
if __name__=='__main__':
 import sys
 if '--epmc' in sys.argv:epmc()
 build()
