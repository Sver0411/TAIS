#!/usr/bin/env python3
"""SU-1: seven fixed policies, real receiver edges, old matcher and new paths."""
import argparse,csv,gzip,hashlib,json,multiprocessing,subprocess,sys
from copy import copy
from dataclasses import asdict
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from tais.config import load
from tais.signals import generate,scenarios
from tais.core_stream import CoreSender,CoreReceiver
from tais.joint_policy import JointSender
from tais.su_policy import SUSender
from tais.replay import run
from tais.metrics import evaluate
from tais.wire_codec import decode
from simulator.events import Event,match_events
from benchmark_joint_optimization import canon,save,sha,write_csv,metrics as old_metrics
OUT=ROOT/'results/tais-su';RAW=ROOT/'results/traces/tais-su'
FILES=['src/tais/su_policy.py','scripts/benchmark_su.py','scripts/analyze_su.py','tests/test_su_policy.py','configs/tais-su.json','docs/TAIS_SU_PROTOCOL.md','examples/tais-core/run.py','src/tais/scheduler.py','src/tais/joint_policy.py','src/tais/joint_sampling.py','src/tais/joint_upload.py','src/tais/core_stream.py','src/tais/config.py','src/tais/replay.py','src/tais/metrics.py','src/tais/signals.py','src/tais/trust.py','src/tais/trust_bridge.c','src/tais/wire_codec.py','configs/experiment.yaml','scripts/benchmark_joint_optimization.py','scripts/analyze_joint_optimization.py','vendor/SensorTrust/core/sensor_trust.c','vendor/SensorTrust/core/sensor_trust.h','vendor/AdaptiveSense/simulator/scoring.py','vendor/AdaptiveSense/simulator/adaptive.py']
def fingerprints():return {p:sha(ROOT/p) for p in FILES}
def build_sender(cfg,method,layout=1):
 """Map public research mode names to GateOnly, JO-S or SU sender adapters."""
 if method=='GateOnly':return CoreSender(cfg,layout)
 if method=='JO-S':return JointSender(cfg,dict(idle_interval_s=20,trend_slope=.005,heartbeat_s=120),layout,'JO-S')
 if method=='GateOnly+U':return SUSender(cfg,layout_id=layout,sampling='gateonly')
 if method.startswith('JO-SU-'):return SUSender(cfg,int(method.rsplit('-',1)[1]),layout)
 raise ValueError(method)

def replay(trace,cfg,method):
 if method=='AdaptiveSense+TrustLog':return run(trace,cfg,method)
 s=build_sender(cfg,method);records=[];reports=[]
 try:
  for row in trace.observed:
   r=s.push(row)
   if r:records.append(r['record']);reports.extend(Event(**x) for x in r['reports'])
 finally:s.close()
 detections=[]
 for n in cfg['channels']:
  start=last=None
  for r in records:
   if r['active'][n]:
    if start is None:start=r['timestamp']
    last=r['timestamp']
   elif start is not None:detections.append(Event(n,start,last));start=None
  if start is not None:detections.append(Event(n,start,last))
 return dict(records=records,reports=reports,detections=detections)

def receiver_result(result,frames):
 """Decode emitted frames independently and report only received false-to-true edges.

 Assume ordered ideal delivery and require every frame to update receiver
 state. Return a scoring view replacing reports, plus the decoded history;
 health/local diagnostics remain the original sampled records."""
 rx=CoreReceiver();previous={n:False for n in ('temperature','humidity')};reports=[];history=[]
 for frame in frames:
  data=bytes.fromhex(frame['frame_hex']);x=rx.receive(data);assert x['status']=='updated'
  envelope=x['envelope'];t=envelope['timestamp']
  for n,active in envelope['environment_active'].items():
   if active and not previous[n]:reports.append(Event(n,t,t))
  previous=dict(envelope['environment_active']);history.append(dict(timestamp=t,**x))
 # Only event matching is taken from evaluate on this view; raw diagnostics remain local.
 return dict(result,reports=reports),history

def extended_metrics(trace,result,cfg,counterfactual,cf_frames):
 """Keep sender and decoded-receiver scores separate and check sampled edge delivery.

 The first later snapshot must carry the same edge signature; later return
 to that state cannot recover a missed intermediate edge. Zero edge delay
 is sample-to-upload software delay, not physical event latency. Age counts
 seconds since the latest decoded sample timestamp, even for null values."""
 out,frames=old_metrics(trace,result,cfg,counterfactual)
 rx_result,rxlog=receiver_result(result,frames);rx_cf,_=receiver_result(counterfactual,cf_frames)
 rxeval=evaluate(trace,rx_result,cfg,rx_cf)
 for k in ['tp','false_reports','fault_induced_false','missed','latency_sum_s','latency_n']:
  out['rx_'+k]=rxeval[k]
 grid=np.arange(len(trace.observed));times=np.array([f['timestamp'] for f in frames]);index=np.searchsorted(times,grid,side='right')-1
 assert np.all(index>=0),'No silently filled pre-first-frame time'
 ages=grid-times[index];hist=np.bincount(ages.astype(int),minlength=len(grid))
 # Exact signature delivered at each observed edge; later different state does not count.
 rows=result['records'];sent={x['envelope']['timestamp']:x['envelope'] for x in rxlog};edges=0;missed=0;delays=[];event_delays=[];health_delays=[]
 for i,r in enumerate(rows):
  if not i:continue
  for n in cfg['channels']:
   h=r['health'][n];old=rows[i-1]['health'][n]
   for field,changed in [('event',r['active'][n]!=rows[i-1]['active'][n]),('health',(h['state'],h['flags'])!=(old['state'],old['flags']))]:
    if not changed:continue
    edges+=1;t=r['timestamp'];delay=None
    for tx,env in sent.items():
     if tx<t:continue
     same=(env['environment_active'][n]==r['active'][n] if field=='event' else (env['health'][n]['state'],env['health'][n]['flags'])==(h['state'],h['flags']))
     if same:delay=tx-t
     # A different received signature cannot recover this edge later.
     break
    if delay is None:missed+=1
    else:
     delays.append(delay);(event_delays if field=='event' else health_delays).append(delay)
 out.update(important_edges=edges,important_edges_unreported=missed,important_edge_delay_max_s=max(delays,default=0),event_edge_delay_max_s=max(event_delays,default=0),health_edge_delay_max_s=max(health_delays,default=0))
 match=match_events(trace.events,result['reports'],5);rxmatch=match_events(trace.events,rx_result['reports'],5)
 by={p.ground_truth:p.detected for p in match.matches};by_rx={p.ground_truth:p.detected for p in rxmatch.matches};events=[]
 for e in trace.events:
  covered=any(e.start_s<=r['timestamp']<=e.end_s for r in rows)
  padded=any(e.start_s-5<=r['timestamp']<=e.end_s+5 for r in rows)
  detected=by.get(e);received=by_rx.get(e)
  events.append(dict(channel=e.channel,truth_start=e.start_s,truth_end=e.end_s,covered=covered,padded_covered=padded,matched=detected is not None,rx_matched=received is not None,report_time=detected.start_s if detected else None,rx_report_time=received.start_s if received else None))
 out.update(covered_tp=sum(e['covered'] and e['matched'] for e in events),covered_events=sum(e['covered'] for e in events),uncovered_matched=sum(not e['covered'] and e['matched'] for e in events))
 return out,frames,rxlog,events,hist

def worker(seed,phase,methods,archive):
 cfg=load();archive=Path(archive);cache={};rows=[];events=[];artifacts={};histograms={m:np.zeros(1800,dtype=np.int64) for m in methods}
 def store(relative,obj):
  p=archive/phase/relative;h=save(p,obj);artifacts[str(relative)]=h;return h
 for case in scenarios():
  trace=generate(cfg,seed,case);signal_sha=store(Path(str(seed))/case/'signals.json.gz',asdict(trace));ih=hashlib.sha256(canon(trace.observed)).hexdigest()
  for method in methods:
   key=(trace.relationship,trace.profile,method)
   if key not in cache:
    cf=copy(trace);cf.observed=trace.noisy;cf.faults=[];cfr=replay(cf,cfg,method);_,cff=old_metrics(cf,cfr,cfg,cfr)
    cfsha=store(Path(str(seed))/'counterfactuals'/f'{trace.relationship}-{trace.profile}-{method}.json.gz',dict(result=cfr,frames=cff))
    cache[key]=(cfr,cff,cfsha)
   cfr,cff,cfsha=cache[key];r=replay(trace,cfg,method);m,frames,rxlog,ev,hist=extended_metrics(trace,r,cfg,cfr,cff)
   resultsha=store(Path(str(seed))/case/(method+'.json.gz'),dict(result=r,frames=frames,receiver=rxlog,age_histogram=hist.tolist()))
   rows.append(dict(seed=seed,scenario=case,relationship=trace.relationship,profile=trace.profile,fault_kind=trace.faults[0].kind if trace.faults else 'clean',method=method,cap=int(method.rsplit('-',1)[1]) if method.startswith('JO-SU-') else 20 if method=='JO-S' else 0,**m,observed_sha256=ih,signals_sha256=signal_sha,result_sha256=resultsha,counterfactual_sha256=cfsha))
   events.extend(dict(seed=seed,scenario=case,method=method,**e) for e in ev);histograms[method]+=hist
 p=archive/phase/str(seed);write_csv(p/'metrics.csv',rows);write_csv(p/'events.csv',events)
 return seed,rows,events,artifacts,{m:h.tolist() for m,h in histograms.items()}

def main():
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['engineering','development','validation','test'],required=True);p.add_argument('--workers',type=int,default=4);p.add_argument('--output-root',type=Path,default=OUT);p.add_argument('--archive-root',type=Path,default=RAW);a=p.parse_args()
 if not 1<=a.workers<=4:raise ValueError('workers1–4')
 plan=json.loads((ROOT/'configs/tais-su.json').read_text());audit=json.loads((OUT/'seed-audit.json').read_text());assert audit['status']=='PASS' and audit['seeds']==plan['seeds']
 if a.phase in ['validation','test']:
  lock=json.loads((OUT/'selection.json').read_text());assert lock['sources']==fingerprints(),'Frozen implementation changed'
  if a.phase=='test':assert subprocess.check_output(['git','show','HEAD:results/tais-su/selection.json'],cwd=ROOT)==(OUT/'selection.json').read_bytes(),'Commit selection before final'
 out=a.output_root/a.phase;out.mkdir(parents=True,exist_ok=False)
 seeds=plan['seeds'].get(a.phase,[20]);methods=plan['methods'];manifest=dict(status='STARTED',phase=a.phase,seeds=seeds,cases=scenarios(),methods=methods,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sources=fingerprints(),archive_root=str(a.archive_root),replication=a.output_root.resolve()!=OUT.resolve(),seed_audit_sha256=sha(OUT/'seed-audit.json'))
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 rows=[];events=[];artifacts={};hist={m:np.zeros(1800,dtype=np.int64) for m in methods}
 with ProcessPoolExecutor(max_workers=a.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
  tasks=[pool.submit(worker,s,a.phase,methods,str(a.archive_root)) for s in seeds]
  for f in as_completed(tasks):
   seed,r,e,h,ages=f.result();rows+=r;events+=e;artifacts.update(h)
   for m,counts in ages.items():hist[m]+=np.array(counts)
   print(a.phase,seed,len(r),flush=True)
 rows.sort(key=lambda r:(r['seed'],r['scenario'],r['method']));write_csv(out/'metrics.csv',rows);write_csv(out/'events.csv',events)
 ages=[]
 for m,h in hist.items():
  total=int(h.sum());ages.append(dict(method=m,mean_age_s=float(np.arange(1800)@h/total),p95_age_s=int(np.searchsorted(np.cumsum(h),total*.95)),max_age_s=int(np.flatnonzero(h)[-1])))
 write_csv(out/'pooled_age.csv',ages)
 assert len(rows)==len(seeds)*45*len(methods)
 manifest.update(status='COMPLETE',runs=len(rows),metrics_sha256=sha(out/'metrics.csv'),events_sha256=sha(out/'events.csv'),artifacts=artifacts)
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()
