from collect import *
js=json.loads((D/'journals.json').read_text());allrows=json.loads((D/'metadata-all.json').read_text());known={p['doi'] for p in allrows}
for j in js:
 if j.get('retrieval_status')!='error':continue
 if j['id'].startswith('natprog'):
  html=(C/(j['id']+'-home.html')).read_text();txt=BeautifulSoup(html,'html.parser').get_text(' ',strip=True)
  if re.search(r'[Ll]aunch.{0,100}2027|2027.{0,80}[Ll]aunch',txt):j.update(retrieval_status='not_launched_2026',retrieved_records=0,source_note='Publisher homepage announces 2027 launch');print(j['id'],'not launched2026',flush=True);continue
 time.sleep(4);jj,items=journal(j)
 print(j['id'],jj.get('retrieved_records'),jj.get('retrieval_error',''),flush=True)
 for x in items:
  p=normalize(x,jj)
  if p['doi'] not in known:allrows.append(p);known.add(p['doi'])
 save(D/'journals.json',js);save(D/'metadata-all.json',allrows)
save(D/'journals.json',js);save(D/'metadata-all.json',allrows)
