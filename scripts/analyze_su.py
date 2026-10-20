#!/usr/bin/env python3
"""SU-1 fixed selection, seed-cluster inference, sender and receiver separated."""
import argparse,csv,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from benchmark_su import OUT,sha,write_csv,fingerprints
from analyze_joint_optimization import aggregate as old_aggregate,groups
CONTRASTS=[('GateOnly+U','GateOnly'),('JO-SU-20','JO-S'),('JO-SU-30','JO-SU-20'),('JO-SU-40','JO-SU-20')]+[(f'JO-SU-{c}','GateOnly') for c in (20,30,40)]

def read(root,phase):
 m=json.loads((root/phase/'manifest.json').read_text());assert m['status']=='COMPLETE' and m['metrics_sha256']==sha(root/phase/'metrics.csv')
 meta={'scenario','relationship','profile','fault_kind','method','observed_sha256','signals_sha256','result_sha256','counterfactual_sha256'}
 rows=[{k:(v if k in meta else None if v in ('','None') else float(v)) for k,v in r.items()} for r in csv.DictReader((root/phase/'metrics.csv').open())]
 assert len(rows)==m['runs'];return rows

def aggregate(rows):
 a=old_aggregate(rows)
 for k in ['rx_tp','rx_false_reports','rx_fault_induced_false','rx_missed','rx_latency_sum_s','rx_latency_n','covered_tp','covered_events','uncovered_matched','important_edges','important_edges_unreported']:
  a[k]=sum(r[k] or 0 for r in rows)
 tp,fp,n=a['rx_tp'],a['rx_false_reports'],a['n_events']
 a.update(rx_precision=tp/(tp+fp) if tp+fp else None,rx_recall=tp/n if n else None,rx_f1=2*tp/(n+tp+fp) if n+tp+fp else None,covered_success=a['covered_tp']/a['covered_events'] if a['covered_events'] else None,coverage=a['covered_events']/n if n else None)
 for k in ['important_edge_delay_max_s','event_edge_delay_max_s','health_edge_delay_max_s']:a[k]=max(r[k] for r in rows)
 return a

def select(root):
 """Freeze the development-selected balanced candidate, retaining qualification status.

 If no candidate meets quality gates, the fallback still receives a balanced
 cap for interface continuity. The name is not evidence that gates passed."""
 rows=read(root,'development');by={m:aggregate([r for r in rows if r['method']==m]) for m in {r['method'] for r in rows}};g=by['GateOnly'];s=by['JO-SU-20'];den=s['recall']-g['recall'];candidates=[]
 for cap in [30,40]:
  a=by[f'JO-SU-{cap}'];gain=(a['recall']-g['recall'])/den if den>0 else None;eligible=bool(gain is not None and gain>=.8 and a['recall']>=g['recall']+.05 and a['f1']>=g['f1']+.03)
  candidates.append(dict(cap=cap,eligible=eligible,retained_gain=gain,**a))
 eligible=[x for x in candidates if x['eligible']]
 choice=min(eligible,key=lambda x:(x['samples'],-x['f1'],-x['recall'],-x['cap'])) if eligible else min(candidates,key=lambda x:(-x['recall'],-x['f1'],x['samples'],x['cap']))
 lock=dict(status='FROZEN_BEFORE_VALIDATION',balanced_cap=choice['cap'],development_quality_qualified=bool(eligible),candidates=candidates,high_cap=20,sources=fingerprints(),development_metrics_sha256=sha(root/'development/metrics.csv'))
 with (root/'selection.json').open('x') as f:json.dump(lock,f,indent=2);f.write('\n')
 print(json.dumps({k:lock[k] for k in ['balanced_cap','development_quality_qualified']}))

def analysis(root,phase):
 """Write all fixed-mode summaries, whole-seed intervals and explicit GO/NO-GO checks.

 Receiver metrics and age remain separate from sender outcomes. Common-hit
 delay compares only events detected by both methods; misses stay separate."""
 rows=read(root,phase);out=root/phase/'analysis';out.mkdir(exist_ok=False);by={}
 for r in rows:
  for group in groups(r):by.setdefault((r['method'],group),[]).append(r)
 summary=[dict(method=m,group=g,**aggregate(rs)) for (m,g),rs in sorted(by.items())];write_csv(out/'summary.csv',summary)
 if phase not in ['validation','test']:return
 seeds=sorted({r['seed'] for r in rows});rng=np.random.default_rng(2026101904);draw=rng.integers(0,len(seeds),(5000,len(seeds)));cis=[]
 metrics=['precision','recall','f1','fault_induced_false','samples','uploads','binary_v1_bytes','event_delay_s','fault_detection_rate','rx_precision','rx_recall','rx_f1','rx_fault_induced_false','age_mean_s','coverage','covered_success','receiver_mae_temperature','receiver_mae_humidity']
 for A,B in CONTRASTS:
  for group in ['overall','profile:short','profile:long','relation:same','relation:cross','fault:drift','fault:stable_offset','no_events']:
   aa=[r for r in rows if r['method']==A and group in groups(r)];bb=[r for r in rows if r['method']==B and group in groups(r)]
   a,b=aggregate(aa),aggregate(bb);pa=[aggregate([r for r in aa if r['seed']==s]) for s in seeds];pb=[aggregate([r for r in bb if r['seed']==s]) for s in seeds]
   def boots(p,k):
    def summed(x):return np.array([r[x] or 0 for r in p])[draw].sum(axis=1)
    def ratio(x,y):return np.divide(x,y,out=np.full(5000,np.nan),where=y>0)
    rx=k.startswith('rx_');kk=k[3:] if rx else k;prefix='rx_' if rx else ''
    if kk in ['precision','recall','f1']:
     tp=summed(prefix+'tp');fp=summed(prefix+'false_reports');n=summed('n_events');den={'precision':tp+fp,'recall':n,'f1':n+tp+fp}[kk];return ratio(tp*(2 if kk=='f1' else 1),den)
    if k=='event_delay_s':return ratio(summed('latency_sum_s'),summed('latency_n'))
    if k=='fault_detection_rate':return ratio(summed('fault_detected'),summed('fault_episodes'))
    if k=='coverage':return ratio(summed('covered_events'),summed('n_events'))
    if k=='covered_success':return ratio(summed('covered_tp'),summed('covered_events'))
    return summed(k)/(len(seeds) if k.startswith(('age_','receiver_')) else 1)
   for k in metrics:
    if a[k] is None or b[k] is None:continue
    delta=boots(pa,k)-boots(pb,k);lo,hi=np.nanpercentile(delta,[2.5,97.5]);cis.append(dict(contrast=A+' minus '+B,group=group,metric=k,difference=a[k]-b[k],ci95_low=lo,ci95_high=hi))
   if b['fault_induced_false']:
    base=boots(pb,'fault_induced_false');delta=boots(pa,'fault_induced_false')/base-1;lo,hi=np.nanpercentile(delta,[2.5,97.5]);cis.append(dict(contrast=A+' minus '+B,group=group,metric='fault_induced_relative',difference=a['fault_induced_false']/b['fault_induced_false']-1,ci95_low=lo,ci95_high=hi))
 write_csv(out/'paired_intervals.csv',cis)
 events=list(csv.DictReader((root/phase/'events.csv').open()));common=[]
 for A,B in CONTRASTS:
  def idx(method):return {(int(r['seed']),r['scenario'],r['channel'],r['truth_start'],r['truth_end']):r for r in events if r['method']==method}
  a,b=idx(A),idx(B);assert a.keys()==b.keys();per={s:[] for s in seeds}
  for key in a:
   if a[key]['matched']=='True' and b[key]['matched']=='True':per[key[0]].append(float(a[key]['report_time'])-float(b[key]['report_time']))
  sums=np.array([sum(per[s]) for s in seeds]);counts=np.array([len(per[s]) for s in seeds]);den=counts[draw].sum(axis=1);val=np.divide(sums[draw].sum(axis=1),den,out=np.full(5000,np.nan),where=den>0)
  common.append(dict(contrast=A+' minus '+B,events=int(counts.sum()),mean_delay_difference=float(sums.sum()/counts.sum()) if counts.sum() else None,ci95_low=float(np.nanpercentile(val,2.5)),ci95_high=float(np.nanpercentile(val,97.5))))
 write_csv(out/'common_event_delays.csv',common)
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 methods=json.loads((ROOT/'configs/tais-su.json').read_text())['methods'];overall={r['method']:r for r in summary if r['group']=='overall'}
 fig,axes=plt.subplots(1,2,figsize=(12,4.5))
 colors=plt.cm.tab10(np.arange(len(methods)))
 for ax,k in zip(axes,['recall','f1']):
  for i,m in enumerate(methods):
   r=overall[m];ax.scatter(r['samples'],r[k]*100,label=m,color=colors[i],s=42,marker=['o','s','x','^','D','P','v'][i])
  su=[overall[f'JO-SU-{c}'] for c in [20,30,40]];ax.plot([r['samples'] for r in su],[r[k]*100 for r in su],color='gray',alpha=.6)
  ax.set_xlabel('Actual sample cycles (all runs)');ax.set_ylabel(k+' (%)');ax.ticklabel_format(axis='x',style='plain');ax.grid(alpha=.2)
 axes[1].legend(fontsize=8,loc='best');fig.suptitle(phase+' | no H layer; native operating points, not matched budgets');fig.tight_layout();fig.savefig(out/'detection_cost.png',dpi=160);plt.close(fig)
 ages={r['method']:r for r in csv.DictReader((root/phase/'pooled_age.csv').open())};fig,axes=plt.subplots(1,2,figsize=(12,4.8));xs=np.arange(len(methods))
 axes[0].bar(xs,[overall[m]['binary_v1_bytes'] for m in methods],color=colors);axes[0].set_ylabel('Actual stateless Binary v1 bytes')
 axes[1].bar(xs,[float(ages[m]['p95_age_s']) for m in methods],color=colors,label='pooled P95');axes[1].plot(xs,[float(ages[m]['max_age_s']) for m in methods],'k^--',label='maximum');axes[1].set_ylabel('Receiver data age (s)');axes[1].legend()
 for ax in axes:ax.set_xticks(xs,methods,rotation=55,ha='right',fontsize=8)
 fig.suptitle(phase+' | fewer uploads can mean older state');fig.tight_layout();fig.savefig(out/'bytes_age.png',dpi=160);plt.close(fig)
 if (root/'selection.json').exists():
  lock=json.loads((root/'selection.json').read_text());candidate='JO-SU-'+str(lock['balanced_cap']);g=overall['GateOnly'];high=overall['JO-SU-20'];b=overall[candidate];trust=overall['AdaptiveSense+TrustLog']
  def interval(metric):
   return next(x for x in cis if x['contrast']==candidate+' minus GateOnly' and x['group']=='overall' and x['metric']==metric)
  den=high['recall']-g['recall'];retention=(b['recall']-g['recall'])/den if den>0 else None
  checks=dict(retention_at_least_80pct=retention is not None and retention>=.8,
   recall_plus_5pp=b['recall']>=g['recall']+.05,f1_plus_3pp=b['f1']>=g['f1']+.03,
   recall_ci_positive=interval('recall')['ci95_low']>0,f1_ci_positive=interval('f1')['ci95_low']>0,
   receiver_recall_better=b['rx_recall']>g['rx_recall'],receiver_f1_better=b['rx_f1']>g['rx_f1'],
   bytes_below_gate=b['binary_v1_bytes']<g['binary_v1_bytes'],samples_near_trust=b['samples']<=1.10*trust['samples'],
   fault_false_point_noninferior=b['fault_induced_false']<=1.05*g['fault_induced_false'],fault_false_ci_noninferior=interval('fault_induced_relative')['ci95_high']<=.05,
   c11_not_materially_worse=interval('fault_detection_rate')['ci95_low']>-.01,
   every_edge_uploaded=b['important_edges_unreported']==0,edges_immediate=b['important_edge_delay_max_s']==0,
   age_p95_limit=float(ages[candidate]['p95_age_s'])<=120,age_max_limit=float(ages[candidate]['max_age_s'])<180)
  checks={k:bool(v) for k,v in checks.items()}
  decision=dict(status='GO' if all(checks.values()) else 'NO-GO',scope='final same-generator test' if phase=='test' else 'validation only',balanced_method=candidate,retained_gain=retention,checks=checks,default='selected balanced' if all(checks.values()) and phase=='test' else 'GateOnly',high_detection_optional=True,samples_actually_below_trust=b['samples']<=trust['samples'])
  (out/'decision.json').write_text(json.dumps(decision,indent=2)+'\n')
 print(json.dumps([overall[m] for m in methods],indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['engineering','development','validation','test']);p.add_argument('--select',action='store_true');p.add_argument('--root',type=Path,default=OUT);a=p.parse_args()
 if a.select:select(a.root)
 else:analysis(a.root,a.phase)
