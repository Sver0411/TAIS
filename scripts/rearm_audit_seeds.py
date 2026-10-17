"""Inventory historical seed-bearing Git blobs and local archive directories."""
import csv,io,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT,text=True)
objects={}
for line in git('rev-list','--objects','--all').splitlines():
 f=line.split(' ',1)
 if len(f)==2 and f[1].startswith('results/') and (f[1].endswith('/manifest.json') or f[1].endswith('/metrics.csv') or f[1].endswith('/events.csv') or f[1].endswith('/FREEZE.json') or f[1].endswith('/seed_audit.json')):objects[f[0]]=f[1]
def seed_fields(obj):
 out=set()
 if isinstance(obj,dict):
  for k,v in obj.items():
   if ('seeds' in k or k=='seed_directories') and isinstance(v,list):out.update(x for x in v if isinstance(x,int))
   if k=='seed' and isinstance(v,int):out.add(v)
   if isinstance(v,(dict,list)):out.update(seed_fields(v))
 elif isinstance(obj,list):
  for v in obj:
   if isinstance(v,(dict,list)):out.update(seed_fields(v))
 return out
used=set();records=[]
for sha,path in objects.items():
 raw=git('cat-file','blob',sha)
 if path.endswith('.csv'):seeds={int(r['seed']) for r in csv.DictReader(io.StringIO(raw)) if r.get('seed','').isdigit()}
 else:seeds=seed_fields(json.loads(raw))
 used.update(seeds);records.append(dict(blob=sha,path=path,seeds=sorted(seeds)))
archives=[]
for p in (ROOT/'results/traces').glob('*'):
 if p.is_dir():
  seeds=sorted(int(x.name) for x in p.iterdir() if x.is_dir() and x.name.isdigit());used.update(seeds)
  archives.append(dict(path=str(p.relative_to(ROOT)),seeds=seeds))
proposed=set(range(100,150));intersection=used&proposed
out=dict(audited_head=git('rev-parse','HEAD').strip(),git_blobs=records,local_archives=archives,used_or_predeclared_seeds=sorted(used),
 splits=dict(development=list(range(100,110)),validation=list(range(110,120)),test=list(range(120,150))),overlap=sorted(intersection),
 scope='All reachable historical result manifest/metrics/events/freeze/audit blobs and local numeric seed directories, before new runs. Cannot attest unrecorded external work. RNG offset100000 is not an experiment seed.')
assert not intersection,intersection
p=ROOT/'results/blocked-rearm/seed_audit.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2)+'\n')
print('Historical objects',len(records),'used/predeclared',min(used),max(used),'new split overlap',sorted(intersection))
