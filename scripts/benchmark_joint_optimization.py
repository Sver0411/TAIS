#!/usr/bin/env python3
"""JO-1 finite causal replays, one frozen final test, real stateless v1 frames."""
import argparse,csv,gzip,hashlib,json,multiprocessing,subprocess,sys
from pathlib import Path
from copy import copy,deepcopy
from dataclasses import asdict
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
import yaml
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from tais.config import load
from tais.signals import generate,scenarios
from tais.joint_policy import JointSender
from tais.replay import run
from tais.metrics import evaluate
from tais.wire_codec import encode,decode,envelope_from_record
from simulator.events import Event,match_events
OUT=ROOT/'results/tais-joint';RAW=ROOT/'results/traces/tais-joint'
CASES=['clean_short','clean_event','drift_none_long','drift_same_long','drift_cross_long','spike_same_long','missing_cross_long','range_same_long','stable_offset_none_long']
FILES=['src/tais/joint_policy.py','src/tais/joint_sampling.py','src/tais/joint_upload.py','configs/tais-joint.yaml','scripts/benchmark_joint_optimization.py','scripts/analyze_joint_optimization.py','docs/TAIS_JO_PROTOCOL.md','src/tais/scheduler.py','src/tais/signals.py','src/tais/replay.py','src/tais/metrics.py','src/tais/wire_codec.py','configs/experiment.yaml']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fingerprints():return {p:sha(ROOT/p) for p in FILES}
def clean(x):
 if isinstance(x,float) and not np.isfinite(x):return None
 if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [clean(v) for v in x]
 if hasattr(x,'__dataclass_fields__'):return clean(asdict(x))
 return x
def canon(x):return json.dumps(clean(x),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(gzip.compress(canon(x),mtime=0))
 return sha(p)
def write_csv(p,rows):
 with p.open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def replay(trace,cfg,method,options):
 """Run JO senders through CoreSender; delegate other methods to legacy replay.

 Always release native health contexts and derive local episodes from sampled
 activity. This replay returns sender reports; receiver scoring is separate."""
 if not method.startswith('JO-'):return run(trace,cfg,method)
 s=JointSender(cfg,options,variant=method);rows=[];reports=[]
 try:
  for row in trace.observed:
   r=s.push(row)
   if r:rows.append(r['record']);reports.extend(Event(**x) for x in r['reports'])
 finally:s.close()
 detections=[]
 for n in cfg['channels']:
  start=last=None
  for r in rows:
   if r['active'][n]:
    if start is None:start=r['timestamp']
    last=r['timestamp']
   elif start is not None:detections.append(Event(n,start,last));start=None
  if start is not None:detections.append(Event(n,start,last))
 return dict(records=rows,reports=reports,detections=detections)
def metrics(trace,result,cfg,cf):
 # Auxiliary bit must never count as raw C11 fault detection.
 """Encode every requested upload and compute offline sender/cost diagnostics.

 Raw C11 health is separated from application trend bit 32. Frame lengths
 are actual Binary v1 bytes; age/errors assume ideal delivery on the dense
 1-Hz grid. Edge delay here means first subsequent frame time; later SU/paper
 metrics additionally require the received signature to preserve the edge."""
 raw=dict(result,records=[dict(r,health={n:r.get('joint',{}).get(n,{}).get('raw_c11',h) for n,h in r['health'].items()}) for r in result['records']])
 out=evaluate(trace,raw,cfg,cf);rows=result['records'];frames=[]
 for r in rows:
  if r['upload']:
   e=envelope_from_record(r);b=encode(e);d=decode(b)
   assert encode(d)==b and d==e
   frames.append(dict(timestamp=r['timestamp'],frame_hex=b.hex(),bytes=len(b)))
 out['binary_v1_bytes']=sum(x['bytes'] for x in frames)
 times=np.array([x['timestamp'] for x in frames]);grid=np.arange(len(trace.observed));ix=np.searchsorted(times,grid,side='right')-1
 ages=grid-times[np.maximum(0,ix)]
 out.update(age_mean_s=float(ages.mean()),age_p95_s=float(np.percentile(ages,95)),age_max_s=float(ages.max()))
 def signature(r,n):
  h=r['health'].get(n,{})
  return r['active'][n],h.get('state'),h.get('flags')
 edges=[r['timestamp'] for i,r in enumerate(rows) if i and any(signature(r,n)!=signature(rows[i-1],n) for n in cfg['channels'])]
 delays=[next((x['timestamp']-t for x in frames if x['timestamp']>=t),None) for t in edges]
 out['state_edge_upload_delay_max_s']=max((x for x in delays if x is not None),default=0)
 out['state_edges_never_uploaded']=sum(x is None for x in delays)
 for n in cfg['channels']:
  latest=[decode(bytes.fromhex(x['frame_hex']))['values'][n] for x in frames]
  held=np.array([np.nan if latest[i] is None else latest[i] for i in ix]);target=np.array([r[n] for r in trace.latent]);mask=np.isfinite(held)
  out['receiver_coverage_'+n]=float(mask.mean());out['receiver_mae_'+n]=float(np.mean(abs(held[mask]-target[mask]))) if mask.any() else None
  out['receiver_rmse_'+n]=float(np.sqrt(np.mean((held[mask]-target[mask])**2))) if mask.any() else None
 aux=[r for r in rows if r.get('joint',{}).get('temperature',{}).get('app_suspect_drift')]
 drift=[f for f in trace.faults if f.kind=='drift'];hits=[next((r['timestamp']-f.start_s for r in aux if f.start_s<=r['timestamp']<f.end_s),None) for f in drift]
 out.update(aux_drift_episodes=len(drift),aux_drift_detected=sum(h is not None for h in hits),aux_latency_sum_s=sum(h for h in hits if h is not None),aux_off_target_samples=sum(not any(f.start_s<=r['timestamp']<f.end_s for f in drift) for r in aux))
 out['sampled_event_opportunities']=sum(any(e.start_s<=r['timestamp']<=e.end_s for r in rows) for e in trace.events)
 out['local_candidate_events']=sum(any(e.start_s<=r['timestamp']<=e.end_s and (r['scores'].get(e.channel,0)>=8 or r.get('joint',{}).get(e.channel,{}).get('candidate_start') is not None) for r in rows) for e in trace.events)
 return out,frames

def worker(seed,phase,cases,points):
 cfg=load();cache={};rows=[];events=[];artifacts={}
 for case in cases:
  tr=generate(cfg,seed,case);signal=save(RAW/phase/str(seed)/case/'signals.json.gz',asdict(tr));ih=hashlib.sha256(canon(tr.observed)).hexdigest()
  for method,op in points:
   key=(method,op['idle_interval_s'],op['trend_slope']);name=f"{method}-{op['idle_interval_s']}-{op['trend_slope']}"
   ck=(tr.relationship,tr.profile,key)
   if ck not in cache:
    cf=copy(tr);cf.observed=tr.noisy;cf.faults=[];cache[ck]=replay(cf,cfg,method,op)
   result=replay(tr,cfg,method,op);m,frames=metrics(tr,result,cfg,cache[ck]);file=RAW/phase/str(seed)/case/(name+'.json.gz')
   rh=save(file,dict(result=result,frames=frames));artifacts[str(file.relative_to(ROOT))]=rh
   rows.append(dict(seed=seed,scenario=case,relationship=tr.relationship,profile=tr.profile,fault_kind=tr.faults[0].kind if tr.faults else 'clean',method=method,cap=op['idle_interval_s'],slope=op['trend_slope'],**m,observed_sha256=ih,signals_sha256=signal,result_sha256=rh))
   mat=match_events(tr.events,result['reports'],5);by={p.ground_truth:p.detected for p in mat.matches}
   for e in tr.events:
    d=by.get(e);events.append(dict(seed=seed,scenario=case,method=method,cap=op['idle_interval_s'],slope=op['trend_slope'],channel=e.channel,start=e.start_s,end=e.end_s,matched=d is not None,report_time=d.start_s if d else None))
 write_csv(RAW/phase/str(seed)/'metrics.csv',rows);write_csv(RAW/phase/str(seed)/'events.csv',events)
 return seed,rows,events,artifacts

def main():
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['development','validation','test'],required=True);p.add_argument('--workers',type=int,default=4);a=p.parse_args();plan=yaml.safe_load((ROOT/'configs/tais-joint.yaml').read_text())
 out=OUT/a.phase;out.mkdir(parents=True,exist_ok=False)
 if a.phase=='development':
  points=[(m,dict(idle_interval_s=c,trend_slope=s,heartbeat_s=120)) for m in ['JO-S','JO-HS','JO-Full'] for c in plan['idle_candidates'] for s in (plan['trend_candidates'] if m!='JO-S' else [.005])]
 else:
  sel=json.loads((OUT/'selection.json').read_text());assert sel['frozen_files']==fingerprints(),'Frozen sources changed'
  if a.phase=='test':assert subprocess.check_output(['git','show','HEAD:results/tais-joint/selection.json'],cwd=ROOT)==(OUT/'selection.json').read_bytes()
  points=[(m,sel['options']) for m in ['JO-S','JO-HS','JO-Full']]
 points=[(m,dict(idle_interval_s=0,trend_slope=0.,heartbeat_s=120)) for m in ['GateOnly','AdaptiveSense+TrustLog','AdaptiveSense']]+points
 cases=CASES if a.phase=='development' else scenarios();seeds=plan['seeds'][a.phase]
 manifest=dict(status='STARTED',phase=a.phase,seeds=seeds,cases=cases,points=points,sources=fingerprints(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 rows=[];events=[];artifacts={}
 with ProcessPoolExecutor(max_workers=a.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
  tasks=[pool.submit(worker,s,a.phase,cases,points) for s in seeds]
  for f in as_completed(tasks):
   s,r,e,hs=f.result();rows+=r;events+=e;artifacts.update(hs);print(a.phase,s,len(r),flush=True)
 rows.sort(key=lambda r:(r['seed'],r['scenario'],r['method'],r['cap'],r['slope']));write_csv(out/'metrics.csv',rows);write_csv(out/'events.csv',events)
 assert len(rows)==len(seeds)*len(cases)*len(points)
 manifest.update(status='COMPLETE',runs=len(rows),metrics_sha256=sha(out/'metrics.csv'),events_sha256=sha(out/'events.csv'),artifacts=artifacts)
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()
