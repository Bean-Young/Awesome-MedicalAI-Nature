import json,sys,re,subprocess
from pathlib import Path
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor,as_completed
sys.path.insert(0,'/tmp/npj-python');from bs4 import BeautifulSoup
import requests
ROOT=Path(__file__).resolve().parents[1]

def fetch(row):
 ident=row['id'];base=ROOT/'research-cache'/ident
 if base.with_suffix('.txt').exists():return ident,'cached'
 html=base.with_suffix('.html')
 if not html.exists():return ident,'no HTML'
 soup=BeautifulSoup(html.read_text(),'html.parser');urls=[]
 for a in soup.select('a[href]'):
  if re.search(r'/articles/[^/]+(?:_reference)?\.pdf$',a['href']):urls.append(urljoin(row['url'],a['href']))
 urls=list(dict.fromkeys(urls));urls.sort(key=lambda u:('_reference.pdf' not in u))
 session=requests.Session();session.trust_env=False
 for url in urls:
  try:
   response=session.get(url,timeout=50)
   if response.status_code==200 and response.content.startswith(b'%PDF'):
    base.with_suffix('.pdf').write_bytes(response.content)
    result=subprocess.run(['pdftotext','-raw',str(base.with_suffix('.pdf')),str(base.with_suffix('.txt'))],capture_output=True,text=True)
    if result.returncode==0:return ident,'downloaded'
  except requests.RequestException:pass
 return ident,'no accessible PDF'
if __name__=='__main__':
 rows=json.loads((ROOT/'data/reviews/other.json').read_text())
 with ThreadPoolExecutor(max_workers=5) as executor:
  for result in executor.map(fetch,rows):print(result,flush=True)
