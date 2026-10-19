import urllib.request,json,concurrent.futures,hashlib
from pathlib import Path
r=Path(__file__).resolve().parents[1];out=r/'results/tais-paper/literature';out.mkdir(exist_ok=True)
items={'rao2019adaptive':'10.3390/s19122654','masoum2012quality':'10.1109/UIC-ATC.2012.156','harb2024clara':'10.1016/j.iot.2024.101345','algabroun2020dsra':'10.1007/s00542-019-04631-9','sharma2010faults':'10.1145/1754414.1754419','dias2017dual':'10.1016/j.comcom.2017.08.002','arnaiz2024energy':'10.1016/j.vlsi.2023.102097','yim2010fault':'10.3390/s100302332'}
def get(item):
 key,doi=item;url='https://api.crossref.org/works/'+doi
 req=urllib.request.Request(url,headers={'User-Agent':'TAIS-research-literature-audit/1.0'})
 cache=out/(key+'.json')
 if cache.exists():b=cache.read_bytes()
 else:
  import time
  for attempt in range(4):
   try:b=urllib.request.urlopen(req,timeout=30).read();break
   except Exception:
    if attempt==3:raise
    time.sleep(5*(attempt+1))
  cache.write_bytes(b)
 m=json.loads(b)['message']
 return key,doi,m,url,hashlib.sha256(b).hexdigest()
records=list(concurrent.futures.ThreadPoolExecutor(1).map(get,items.items()));bib=[];audit=[]
for key,doi,m,url,h in records:
 authors=' and '.join(x['family']+', '+x.get('given','') for x in m['author']);title=m['title'][0]+(': '+m['subtitle'][0] if m.get('subtitle') else '');venue=m['container-title'][0];year=m.get('published-print',m.get('published'))['date-parts'][0][0]
 if key=='masoum2012quality':authors='Masoum, Alireza and Meratnia, Nirvana and Havinga, Paul J. M.'
 if key=='harb2024clara':authors='Harb, Hassan and {Abou Nader}, Clara and Jaber, Ali and Hakem, Mourad and Charr, Jean-Claude and {Abou Jaoude}, Chady and Zaki, Chamseddine'
 typ='inproceedings' if m['type']=='proceedings-article' else 'article';fields={'title':title,'author':authors,'year':str(year),'doi':doi,('booktitle' if typ=='inproceedings' else 'journal'):venue}
 for source,target in [('volume','volume'),('issue','number'),('page','pages'),('article-number','eid')]:
  if m.get(source):fields[target]=str(m[source]).replace('–','--')
 bib.append('@'+typ+'{'+key+',\n'+''.join('  '+k+' = {'+v+'},\n' for k,v in fields.items())+'}\n')
 audit.append(dict(key=key,doi=doi,title=title,authors=authors,year=year,venue=venue,metadata_url=url,metadata_sha256=h,status='DOI_REGISTRATION_METADATA_VERIFIED',checked='2026-10-19'))
 print(key,year,authors,title)
p=r/'papers/tais';p.mkdir(parents=True,exist_ok=True);(p/'references.bib').write_text('\n'.join(bib));(out/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
