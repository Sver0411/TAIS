"""Experiment-only selection/statistics helpers; never imported by a scheduler."""
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
BASE='97feccb36acb6790b40be31e3cee1661e8811a61'
GRID_METHODS=('GateOnly','TAIS')
COUNT_FIELDS=('n_events','tp','missed','local_tp','false_reports','redundant_reports',
              'fault_associated_false','fault_induced_false','samples','uploads','payload_bytes','binary_v1_bytes',
              'fault_episodes','fault_detected','fault_type_detected','confirmation_samples',
              'diagnostic_samples','diagnostic_only_samples','duration_s','latency_sum_s','latency_n','fault_latency_sum_s')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def numeric_rows(rows):
    metadata={'seed','scenario','relationship','profile','method','multiplier','fault_kind',
              'signals_sha256','observed_sha256','events_sha256','faults_sha256','result_sha256','counterfactual_sha256'}
    out=[]
    for r in rows:
        row={}
        for k,v in r.items():
            if k in metadata:
                row[k]=int(v) if k=='seed' else float(v) if k=='multiplier' else v
            else:row[k]=None if v in ('',None) else float(v)
        out.append(row)
    return out


def aggregate(rows):
    out={k:sum(float(r.get(k) or 0) for r in rows) for k in COUNT_FIELDS}
    out['runs']=len(rows)
    def ratio(n,d):return n/d if d else None
    out['recall']=ratio(out['tp'],out['n_events'])
    out['precision']=ratio(out['tp'],out['tp']+out['false_reports'])
    out['f1']=ratio(2*out['tp'],2*out['tp']+out['false_reports']+out['missed'])
    out['false_per_hour']=ratio(3600*out['false_reports'],out['duration_s'])
    out['latency_mean_s']=ratio(out['latency_sum_s'],out['latency_n'])
    out['fault_detection_rate']=ratio(out['fault_detected'],out['fault_episodes'])
    out['fault_type_detection_rate']=ratio(out['fault_type_detected'],out['fault_episodes'])
    out['fault_latency_mean_s']=ratio(out['fault_latency_sum_s'],out['fault_detected'])
    for name in ('temperature','humidity'):
        for source in ('sample','upload'):
            weighted=[(r,float(r.get(f'{source}_coverage_{name}') or 0)*float(r.get('duration_s') or 0)) for r in rows]
            n=sum(w for r,w in weighted)
            out[f'{source}_coverage_{name}']=ratio(n,out['duration_s'])
            out[f'{source}_mae_{name}']=ratio(sum((r.get(f'{source}_mae_{name}') or 0)*w for r,w in weighted),n)
            mse=ratio(sum((r.get(f'{source}_rmse_{name}') or 0)**2*w for r,w in weighted),n)
            out[f'{source}_rmse_{name}']=math.sqrt(mse) if mse is not None else None
    return out


def groups(row):
    names=['overall','kind:'+row['fault_kind'],'scenario:'+row['scenario'],'profile:'+row['profile']]
    if row['n_events']==0:
        names.append('no_event')
        if row['fault_kind']!='clean':names.append('fault_no_event')
    elif row['fault_kind']=='clean':names.append('clean_event')
    elif row['relationship']=='same':names.append('same_channel')
    elif row['relationship']=='cross':names.append('cross_channel')
    return names


def resources(rows):
    a=aggregate(rows)
    return dict(samples=a['samples'],uploads=a['uploads'],runs=a['runs'],
                samples_per_run=a['samples']/a['runs'],uploads_per_run=a['uploads']/a['runs'])


def gap(gate,tais,field):return abs(tais[field]-gate[field])/gate[field] if gate[field] else math.inf


def choose_pairs(dev,val,plan):
    """Only method/point/sample/upload fields may influence the chosen pair."""
    def index(rows):
        out={}
        for method in GRID_METHODS:
            for m in plan['grid']:
                used=[r for r in rows if r['method']==method and r['multiplier']==m]
                if not used:raise ValueError('Incomplete calibration matrix')
                out[method,m]=resources(used)
        return out
    d,v=index(dev),index(val);choices=[];candidates=[]
    for anchor in plan['anchors']:
        target=d['GateOnly',anchor];ranked=[]
        for gm in plan['grid']:
            for tm in plan['grid']:
                dg,dt=d['GateOnly',gm],d['TAIS',tm];vg,vt=v['GateOnly',gm],v['TAIS',tm]
                dev_gap={f:gap(dg,dt,f) for f in ('samples','uploads')}
                val_gap={f:gap(vg,vt,f) for f in ('samples','uploads')}
                distances=[abs(r[f+'_per_run']/target[f+'_per_run']-1) for r in (dg,dt) for f in ('samples','uploads')]
                feasible=max(*dev_gap.values(),*val_gap.values())<=plan['pair_relative_tolerance'] and max(distances)<=plan['development_target_band']
                rank=(int(gm!=tm),max(distances),max(*dev_gap.values(),*val_gap.values()),abs(gm-anchor)+abs(tm-anchor),gm,tm)
                item=dict(budget=f'B{anchor:.2f}',anchor=anchor,gate_multiplier=gm,tais_multiplier=tm,
                          development_samples_gap=dev_gap['samples'],development_uploads_gap=dev_gap['uploads'],
                          validation_samples_gap=val_gap['samples'],validation_uploads_gap=val_gap['uploads'],
                          worst_target_deviation=max(distances),calibration_matched=feasible,rank=list(rank))
                candidates.append(item)
                if feasible:ranked.append((rank,item))
        if ranked:chosen=min(ranked,key=lambda x:x[0])[1]
        else:chosen=next(c for c in candidates if c['budget']==f'B{anchor:.2f}' and c['gate_multiplier']==anchor and c['tais_multiplier']==anchor)
        choices.append({**chosen,'target':target,'fallback':not bool(ranked)})
    return choices,candidates


def paired_rows(rows,gm,tm):
    gate={(r['seed'],r['scenario']):r for r in rows if r['method']=='GateOnly' and r['multiplier']==gm}
    tais={(r['seed'],r['scenario']):r for r in rows if r['method']=='TAIS' and r['multiplier']==tm}
    if gate.keys()!=tais.keys():raise ValueError('Unpaired scenario/seed keys')
    result=[]
    for key in sorted(gate):
        g,t=gate[key],tais[key]
        for field in ('signals_sha256','observed_sha256','events_sha256','faults_sha256'):
            if field in g and g[field]!=t[field]:raise ValueError('Unpaired input '+field)
        result.append((g,t))
    return result


def paired_bootstrap(pairs,replicates,seed,alpha=.05,family=3):
    if not pairs:return []
    seeds=sorted({g['seed'] for g,t in pairs});by_seed={s:(aggregate([g for g,t in pairs if g['seed']==s]),aggregate([t for g,t in pairs if g['seed']==s])) for s in seeds}
    rng=np.random.default_rng(seed);idx=rng.integers(0,len(seeds),size=(replicates,len(seeds)))
    def totals(method,field):return np.array([by_seed[s][method][field] for s in seeds],dtype=float)
    counts={k:(totals(0,k),totals(1,k)) for k in COUNT_FIELDS}
    def divide(a,b):
        with np.errstate(divide='ignore',invalid='ignore'):
            return np.where(b>0,a/b,np.nan)
    metrics={}
    def derived(mode):
        a={k:(x[idx].sum(axis=1) if mode else np.array([x.sum()])) for k,(x,y) in counts.items()}
        b={k:(y[idx].sum(axis=1) if mode else np.array([y.sum()])) for k,(x,y) in counts.items()}
        r={k:b[k]-a[k] for k in COUNT_FIELDS}
        for label,formula in {
            'recall':lambda x:divide(x['tp'],x['n_events']),
            'precision':lambda x:divide(x['tp'],x['tp']+x['false_reports']),
            'f1':lambda x:divide(2*x['tp'],2*x['tp']+x['false_reports']+x['missed']),
            'latency_mean_s':lambda x:divide(x['latency_sum_s'],x['latency_n']),
            'fault_detection_rate':lambda x:divide(x['fault_detected'],x['fault_episodes']),
            'fault_type_detection_rate':lambda x:divide(x['fault_type_detected'],x['fault_episodes']),
            'fault_latency_mean_s':lambda x:divide(x['fault_latency_sum_s'],x['fault_detected'])}.items():r[label]=formula(b)-formula(a)
        for field in ('fault_induced_false','samples','uploads','payload_bytes','binary_v1_bytes'):
            r[field+'_relative_difference']=divide(b[field]-a[field],a[field])
        return r
    point,draws=derived(False),derived(True)
    out=[]
    for metric,values in draws.items():
        valid=values[np.isfinite(values)];estimate=float(point[metric][0])
        if not math.isfinite(estimate):estimate=None
        ci=np.quantile(valid,[alpha/2,1-alpha/2,alpha/(2*family),1-alpha/(2*family)]) if len(valid) else [None]*4
        out.append(dict(metric=metric,tais_minus_gate=estimate,per_seed_difference=estimate/len(seeds) if estimate is not None and metric in COUNT_FIELDS else None,
                        ci95_low=ci[0],ci95_high=ci[1],familywise_low=ci[2],familywise_high=ci[3],
                        seeds=len(seeds),valid_draws=len(valid),replicates=replicates))
    return out


def robustness(pairs):
    deletions=[('seed',s) for s in sorted({g['seed'] for g,t in pairs})]
    deletions += [('scenario',s) for s in sorted({g['scenario'] for g,t in pairs})]
    deletions += [('fault_kind',s) for s in sorted({g['fault_kind'] for g,t in pairs})]
    out=[]
    for field,value in deletions:
        kept=[(g,t) for g,t in pairs if g[field]!=value]
        g=aggregate([x for x,y in kept]);t=aggregate([y for x,y in kept])
        delta=t['fault_induced_false']-g['fault_induced_false']
        recall=t['recall']-g['recall'] if t['recall'] is not None and g['recall'] is not None else None
        passed=g['fault_induced_false']>0 and delta<0 and recall is not None and recall>=-.01
        out.append(dict(deleted_field=field,deleted_value=value,fault_induced_difference=delta,
                        fault_induced_relative_difference=delta/g['fault_induced_false'] if g['fault_induced_false'] else None,
                        recall_difference=recall,passes=passed))
    return out


def decision(choice,pairs,intervals,robust,plan):
    g,t=aggregate([g for g,t in pairs]),aggregate([t for g,t in pairs])
    matched=all(gap(g,t,k)<=plan['pair_relative_tolerance'] for k in ('samples','uploads'))
    ci={r['metric']:r for r in intervals};recall=ci['recall'];fault=ci['fault_induced_false_relative_difference']
    recall_ok=all(recall[k] is not None and recall[k]>plan['recall_noninferiority_margin'] for k in ('ci95_low','familywise_low'))
    fault_ok=fault['tais_minus_gate'] is not None and fault['tais_minus_gate']<=-plan['minimum_fault_induced_reduction'] and all(fault[k] is not None and fault[k]<0 for k in ('ci95_high','familywise_high'))
    robust_ok=bool(robust) and all(r['passes'] for r in robust)
    go=choice['calibration_matched'] and matched and recall_ok and fault_ok and robust_ok
    return dict(budget=choice['budget'],gate_multiplier=choice['gate_multiplier'],tais_multiplier=choice['tais_multiplier'],
                calibration_matched=choice['calibration_matched'],test_matched=matched,
                samples_gap=gap(g,t,'samples'),uploads_gap=gap(g,t,'uploads'),
                recall_noninferior=recall_ok,fault_improvement=fault_ok,robustness=robust_ok,go=go)


def absolute_bootstrap(rows,replicates,seed):
    seeds=sorted({r['seed'] for r in rows});summaries=[aggregate([r for r in rows if r['seed']==s]) for s in seeds]
    rng=np.random.default_rng(seed);idx=rng.integers(0,len(seeds),size=(replicates,len(seeds)))
    point=aggregate(rows);values={k:np.array([s[k] for s in summaries])[idx].sum(axis=1) for k in COUNT_FIELDS}
    def ratio(n,d):
        with np.errstate(divide='ignore',invalid='ignore'):return np.where(d>0,n/d,np.nan)
    values['recall']=ratio(values['tp'],values['n_events']);values['precision']=ratio(values['tp'],values['tp']+values['false_reports'])
    values['f1']=ratio(2*values['tp'],2*values['tp']+values['false_reports']+values['missed'])
    values['latency_mean_s']=ratio(values['latency_sum_s'],values['latency_n'])
    values['fault_detection_rate']=ratio(values['fault_detected'],values['fault_episodes'])
    values['fault_type_detection_rate']=ratio(values['fault_type_detected'],values['fault_episodes'])
    values['fault_latency_mean_s']=ratio(values['fault_latency_sum_s'],values['fault_detected'])
    out=[]
    for metric,samples in values.items():
        finite=samples[np.isfinite(samples)];lo,hi=np.quantile(finite,[.025,.975]) if len(finite) else (None,None)
        out.append(dict(metric=metric,estimate=point[metric],ci95_low=lo,ci95_high=hi,valid_draws=len(finite),seeds=len(seeds),replicates=replicates))
    return out
