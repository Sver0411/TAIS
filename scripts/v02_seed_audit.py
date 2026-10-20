"""Audit reachable historical experiment manifests and raw metric seed columns."""
import csv, io, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True)
objects={}
for line in git('rev-list','--objects','--all').splitlines():
    fields=line.split(' ',1)
    if len(fields)==2 and fields[1].startswith('results/') and (fields[1].endswith('/manifest.json') or fields[1].endswith('/metrics.csv')):
        objects[fields[0]]=fields[1]
records=[];used=set()
for sha,path in objects.items():
    raw=git('cat-file','blob',sha)
    if path.endswith('manifest.json'):seeds=json.loads(raw).get('seeds',[])
    else:seeds=sorted({int(r['seed']) for r in csv.DictReader(io.StringIO(raw)) if 'seed' in r})
    used.update(seeds);records.append(dict(blob=sha,path=path,seeds=seeds))
out=dict(audited_head=git('rev-parse','HEAD').strip(),records=records,used_experiment_seeds=sorted(used),
         fresh_final_seeds=list(range(50,100)),intersection=sorted(used & set(range(50,100))),
         scope='All reachable committed v0.1 manifest/metrics blobs; current ignored traces also inventoried below. No claim about external/unrecorded runs.')
ignored=[]
for p in (ROOT/'results/traces').glob('*'):
    if p.is_dir():ignored.append(dict(path=str(p.relative_to(ROOT)),seed_directories=sorted(int(s.name) for s in p.iterdir() if s.is_dir() and s.name.isdigit())))
out['local_archives']=ignored
assert not out['intersection']
assert not any(set(r['seed_directories']) & set(range(50,100)) for r in ignored)
p=ROOT/'results/v0.2/seed_audit.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
