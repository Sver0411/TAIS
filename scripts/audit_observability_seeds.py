#!/usr/bin/env python3
"""Reaudit accessible histories and freeze protection bytes for FO-1, no simulation."""
import gzip,hashlib,json,os,re,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_budget_seeds import parse_text
ROOT=Path(__file__).resolve().parents[1]
BASE='5b06d2feae44db2b3503697d246f51c43e5d8f2e'
OUT=ROOT/'results/fault-event-observability';RAW=ROOT/'results/traces/fault-event-observability'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 if (OUT/'seed-audit.json').exists():raise FileExistsError('Audit exists')
 OUT.mkdir(parents=True,exist_ok=True);RAW.mkdir(parents=True,exist_ok=True)
 used=set(range(200));evidence=[];inventory=[];errors=[];raw=[];count=0
 roots=[ROOT,Path('/Users/mac/Documents/TAIS-external-data')]
 for root in roots:
  if not root.exists():continue
  for parent,dirs,names in os.walk(root):
   dirs[:]=[d for d in dirs if d not in ('.git','.venv','__pycache__','build','node_modules')]
   for name in names:
    p=Path(parent)/name
    if RAW in p.parents or OUT in p.parents:continue
    if name.endswith('.gz'):
     rel=str(p.relative_to(root));inventory.append(str(p));s={int(x) for x in re.findall(r'(?:^|/)(\d+)(?:/|[-_])',rel)}
     if s:used.update(s)
    if p.suffix in ('.xlsx','.zip','.tar','.bz2') or name in ('data.txt','data.txt.gz'):
     st=p.stat();raw.append(dict(path=str(p),bytes=st.st_size,mtime_ns=st.st_mtime_ns))
    try:
     if p.suffix in ('.json','.yaml','.yml','.csv'):
      data=p.read_bytes();s=parse_text(data.decode('utf-8-sig'),p.suffix);h=hashlib.sha256(data).hexdigest()
     elif name.endswith('.csv.gz'):
      data=gzip.decompress(p.read_bytes());s=parse_text(data.decode('utf-8-sig'),'.csv');h=hashlib.sha256(data).hexdigest()
     elif name.endswith('.jsonl.gz'):
      s=set();hs=hashlib.sha256()
      with gzip.open(p,'rb') as f:
       for line in f:
        hs.update(line);s.update(int(x) for x in re.findall(rb'"(?:seed|link_seed)":\s*(\d+)',line))
      h=hs.hexdigest()
     else:continue
     count+=1
     if s:used.update(s);evidence.append(dict(path=str(p),seeds=sorted(s),sha256=h))
    except (OSError,ValueError,UnicodeError) as exc:errors.append(dict(path=str(p),error=repr(exc)))
 blobs=0
 for line in subprocess.check_output(['git','rev-list','--all','--objects','--','results','configs','src','scripts','tests','docs'],cwd=ROOT,text=True).splitlines():
  parts=line.split(' ',1)
  if len(parts)!=2:continue
  oid,path=parts;suffix=Path(path).suffix
  if suffix not in ('.json','.yaml','.yml','.csv'):continue
  try:s=parse_text(subprocess.check_output(['git','cat-file','blob',oid],cwd=ROOT).decode('utf-8-sig'),suffix)
  except (ValueError,UnicodeError) as exc:errors.append(dict(path='git:'+line,error=repr(exc)));continue
  blobs+=1
  if s:used.update(s);evidence.append(dict(path='git:'+line,seeds=sorted(s)))
 start=200
 while set(range(start,start+100))&used:start+=100
 split={k:list(range(a,b)) for k,a,b in [('development',start,start+20),('validation',start+20,start+40),('test',start+40,start+100)]}
 full=RAW/'before-run-path-inventory.json.gz';full.write_bytes(gzip.compress(json.dumps(inventory,sort_keys=True).encode(),mtime=0))
 audit=dict(base=BASE,status='PASS' if not errors else 'REVIEW_REQUIRED',reserved_0_199=True,scope_roots=list(map(str,roots)),structured_files=count,historical_blobs=blobs,gzip_paths=len(inventory),inventory_sha256=sha(full),inventory_path=str(full),proposed_200_299_collisions=sorted(set(range(200,300))&used),allocated=split,all_observed_seed_values=sorted(used),evidence=evidence,raw_file_stat_signatures=raw,errors=errors,limitations='All accessible local refs/Git histories, ignored archives and TAIS-external-data. Not inaccessible external machines. Numeric measurements are not seeds; gzip replay directory identities, compressed CSV and full link JSONL seed fields audited.')
 (OUT/'seed-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 if errors:raise RuntimeError('Resolve audit read/parse errors')
 tracked={};links={};ignored={}
 for item in subprocess.check_output(['git','ls-tree','-rz',BASE],cwd=ROOT).split(b'\0'):
  if not item:continue
  meta,name=item.split(b'\t');mode,kind,oid=meta.split();name=name.decode()
  if kind==b'commit':
   assert subprocess.check_output(['git','-C',str(ROOT/name),'rev-parse','HEAD']).strip()==oid
   assert not subprocess.check_output(['git','-C',str(ROOT/name),'status','--porcelain']).strip()
   links[name]=oid.decode()
  else:
   data=(ROOT/name).read_bytes();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest().encode()==oid
   tracked[name]=sha(ROOT/name)
 for directory in (ROOT/'results/traces',ROOT/'results/scratch'):
  for p in directory.rglob('*'):
   if p.is_file() and RAW not in p.parents:ignored[str(p.relative_to(ROOT))]=sha(p)
 guard=dict(base=BASE,tracked=tracked,submodules=links,ignored=ignored,raw_stats=raw)
 p=RAW/'history-guard.json.gz';p.write_bytes(gzip.compress(json.dumps(guard,sort_keys=True).encode(),mtime=0))
 summary=dict(base=BASE,guard_sha256=sha(p),guard_path=str(p),tracked=len(tracked),ignored=len(ignored),submodules=links)
 (OUT/'history-protection.json').write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps(dict(status=audit['status'],collisions=audit['proposed_200_299_collisions'],split=split,structured=count,historical_blobs=blobs,gzip_paths=len(inventory),protection=summary),indent=2),flush=True)
if __name__=='__main__':main()
