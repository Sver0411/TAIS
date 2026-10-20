#!/usr/bin/env python3
"""Post-freeze descriptive diagnostics; no tuning, selection or policy reruns."""
import csv,gzip,json,sys,collections
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import tais  # provision pinned upstream import path
from simulator.events import Event,match_events
R=ROOT/'results/tais-joint';RAW=ROOT/'results/traces/tais-joint/test';rows=list(csv.DictReader((R/'test/metrics.csv').open()));hist={};diag=[];errors=collections.Counter();seen={}
for rr in rows:
 method=rr['method'];p=RAW/rr['seed']/rr['scenario']/(f"{method}-{int(rr['cap'])}-{float(rr['slope'])}.json.gz")
 x=json.loads(gzip.decompress(p.read_bytes()));records=x['result']['records'];times=np.array([f['timestamp'] for f in x['frames']]);grid=np.arange(1800);index=np.searchsorted(times,grid,side='right')-1;ages=grid-times[index]
 hist.setdefault(method,np.zeros(1800,dtype=np.int64));hist[method]+=np.bincount(ages.astype(int),minlength=1800)
 k=(rr['seed'],rr['scenario'])
 if k not in seen:seen[k]=json.loads(gzip.decompress(p.with_name('signals.json.gz').read_bytes()))
 signal=seen[k]
 if rr['fault_kind']=='drift':
  f=signal['faults'][0];first=lambda pred:next((r['timestamp'] for r in records if f['start_s']<=r['timestamp']<f['end_s'] and pred(r)),None)
  typed=first(lambda r:r['health'].get('temperature',{}).get('flags',0)&8);aux=first(lambda r:r['health'].get('temperature',{}).get('flags',0)&32)
  diag.append(dict(seed=rr['seed'],scenario=rr['scenario'],method=method,fault_start=f['start_s'],fault_end=f['end_s'],first_raw_drift=typed,first_app_suspect=aux,raw_drift_delay=typed-f['start_s'] if typed is not None else None,app_delay=aux-f['start_s'] if aux is not None else None))
  match=match_events([Event(**e) for e in signal['events']],[Event(**e) for e in x['result']['reports']],5)
  for e in match.unmatched_detections:
   if e.channel!='temperature':continue
   phase=('before_raw_drift' if typed is None or e.start_s<typed else 'after_raw_drift') if f['start_s']<=e.start_s<f['end_s'] else 'recovery_120s' if f['end_s']<=e.start_s<f['end_s']+120 else 'outside_attribution'
   errors[method,phase]+=1
out=[]
for method,h in hist.items():
 total=int(h.sum());c=np.cumsum(h)
 out.append(dict(method=method,mean_age_s=float(np.arange(1800)@h/total),pooled_p95_age_s=int(np.searchsorted(c,total*.95)),maximum_age_s=int(np.flatnonzero(h)[-1])))
def write(p,rs):
 with p.open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
write(R/'test/analysis/pooled_age.csv',out);write(R/'test/analysis/drift_diagnosis.csv',diag);write(R/'test/analysis/drift_false_phases.csv',[dict(method=m,phase=p,strict_unmatched=n) for (m,p),n in sorted(errors.items())]);print(json.dumps(out,indent=2))
