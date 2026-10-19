#!/usr/bin/env python3
"""JO-1 predefined selection, seed-clustered comparisons and honest charts."""
import argparse,csv,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from benchmark_joint_optimization import OUT,RAW,sha,fingerprints,write_csv

def read(phase):
 m=json.loads((OUT/phase/'manifest.json').read_text());assert m['status']=='COMPLETE'
 assert m['metrics_sha256']==sha(OUT/phase/'metrics.csv')
 rows=list(csv.DictReader((OUT/phase/'metrics.csv').open()))
 meta={'scenario','relationship','profile','fault_kind','method','observed_sha256','signals_sha256','result_sha256'}
 return [{k:(v if k in meta else float(v) if v not in ('','None') else None) for k,v in r.items()} for r in rows]

def aggregate(rows):
 sums={k:sum(r[k] or 0 for r in rows) for k in ['n_events','tp','missed','false_reports','fault_induced_false','samples','uploads','binary_v1_bytes','fault_episodes','fault_detected','fault_type_detected','fault_latency_sum_s','aux_drift_episodes','aux_drift_detected','aux_latency_sum_s','aux_off_target_samples','sampled_event_opportunities','local_tp','latency_sum_s','latency_n']}
 tp,n,fp=sums['tp'],sums['n_events'],sums['false_reports'];sums.update(precision=tp/(tp+fp) if tp+fp else None,recall=tp/n if n else None,f1=2*tp/(n+tp+fp) if n+tp+fp else None,event_delay_s=sums['latency_sum_s']/sums['latency_n'] if sums['latency_n'] else None,fault_detection_rate=sums['fault_detected']/sums['fault_episodes'] if sums['fault_episodes'] else None)
 for k in ['age_mean_s','age_p95_s','age_max_s','receiver_mae_temperature','receiver_rmse_temperature','receiver_coverage_temperature','receiver_mae_humidity','receiver_rmse_humidity','receiver_coverage_humidity']:
  values=[r[k] for r in rows if r[k] is not None];sums[k]=float(np.mean(values)) if values else None
 sums['age_absolute_max_s']=max(r['age_max_s'] for r in rows)
 return sums

def groups(r):
 return ['overall','scenario:'+r['scenario'],'fault:'+r['fault_kind'],'relation:'+r['relationship'],'profile:'+r['profile']]+(['no_events'] if not r['n_events'] else [])

def analyze(phase):
 rows=read(phase);out=OUT/phase/'analysis';out.mkdir(exist_ok=False)
 by={}
 for r in rows:
  for g in groups(r):by.setdefault((r['method'],r['cap'],r['slope'],g),[]).append(r)
 summary=[dict(method=m,cap=c,slope=s,group=g,**aggregate(v)) for (m,c,s,g),v in sorted(by.items())];write_csv(out/'summary.csv',summary)
 if phase=='development':return
 contrasts=[('JO-S','GateOnly'),('JO-HS','JO-S'),('JO-Full','JO-HS'),('JO-Full','GateOnly')]
 fields=['precision','recall','f1','fault_induced_false','samples','uploads','binary_v1_bytes','event_delay_s','fault_detection_rate','age_mean_s','receiver_mae_temperature','receiver_mae_humidity']
 ci=[];seeds=sorted(set(r['seed'] for r in rows));rng=np.random.default_rng(2026101903);draws=rng.integers(0,len(seeds),(5000,len(seeds)))
 # Aggregate within each seed before resampling, maintaining all scenario dependence.
 for a,b in contrasts:
  for g in ['overall','fault:drift','profile:short','relation:cross','relation:same','no_events']:
   aa=[r for r in rows if r['method']==a and g in groups(r)];bb=[r for r in rows if r['method']==b and g in groups(r)]
   if not aa or not bb:continue
   A=aggregate(aa);B=aggregate(bb)
   perA=[aggregate([r for r in aa if r['seed']==s]) for s in seeds];perB=[aggregate([r for r in bb if r['seed']==s]) for s in seeds]
   def bootstrap(per,k):
    def arr(name):return np.array([p[name] or 0 for p in per])[draws].sum(axis=1)
    if k in ['precision','recall','f1']:
     tp=arr('tp');n=arr('n_events');fp=arr('false_reports');den={'precision':tp+fp,'recall':n,'f1':n+tp+fp}[k];return np.divide(tp*(2 if k=='f1' else 1),den,out=np.full(5000,np.nan),where=den>0)
    if k=='fault_detection_rate':return arr('fault_detected')/arr('fault_episodes')
    if k=='event_delay_s':return arr('latency_sum_s')/arr('latency_n')
    return arr(k)/(len(seeds) if k.startswith(('age_','receiver_')) else 1)
   for k in fields:
    if A[k] is None or B[k] is None:continue
    delta=bootstrap(perA,k)-bootstrap(perB,k);lo,hi=np.nanpercentile(delta,[2.5,97.5]);ci.append(dict(contrast=a+' minus '+b,group=g,metric=k,difference=A[k]-B[k],ci95_low=lo,ci95_high=hi))
 write_csv(out/'paired_intervals.csv',ci)
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 methods=['AdaptiveSense','AdaptiveSense+TrustLog','GateOnly','JO-S','JO-HS','JO-Full'];overall=[next(r for r in summary if r['method']==m and r['group']=='overall') for m in methods]
 fig,ax=plt.subplots(1,3,figsize=(12,4))
 for i,k in enumerate(['samples','uploads','binary_v1_bytes']):
  ax[i].bar(range(6),[r[k] for r in overall]);ax[i].set_xticks(range(6),methods,rotation=65,fontsize=8);ax[i].set_title(k);ax[i].ticklabel_format(axis='y',style='plain')
 fig.suptitle(phase+' | same inputs, actual stateless v1 bytes');fig.tight_layout();fig.savefig(out/'costs.png',dpi=150);plt.close(fig)
 print(json.dumps(overall,indent=2))

def select():
 rows=read('development');keys=sorted(set((r['cap'],r['slope']) for r in rows if r['method']=='JO-Full'));candidates=[]
 for c,s in keys:
  a=aggregate([r for r in rows if r['method']=='JO-Full' and r['cap']==c and r['slope']==s]);dr=aggregate([r for r in rows if r['method']=='JO-Full' and r['cap']==c and r['slope']==s and r['fault_kind']=='drift']);candidates.append(dict(cap=c,slope=s,**a,drift_induced=dr['fault_induced_false']))
 candidates.sort(key=lambda r:(-r['recall'],-r['f1'],r['drift_induced'],r['binary_v1_bytes'],-r['cap'],-r['slope']))
 best=candidates[0];lock=dict(status='FROZEN_BEFORE_VALIDATION_AND_TEST',options=dict(idle_interval_s=int(best['cap']),trend_slope=best['slope'],heartbeat_s=120),development_sha256=sha(OUT/'development/metrics.csv'),frozen_files=fingerprints(),candidates=candidates)
 with (OUT/'selection.json').open('x') as f:json.dump(lock,f,indent=2);f.write('\n')
 print(json.dumps(lock['options']))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['development','validation','test']);p.add_argument('--select',action='store_true');a=p.parse_args()
 if a.select:select()
 else:analyze(a.phase)
