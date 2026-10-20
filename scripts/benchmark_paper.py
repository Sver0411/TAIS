#!/usr/bin/env python3
"""Paper-only evaluation: independent schedules, shared detector and native views."""
import argparse,csv,hashlib,json,multiprocessing,subprocess,sys
from pathlib import Path
from copy import copy
from dataclasses import asdict
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from tais.config import load
from tais.signals import generate,scenarios
from tais.replay import run
from tais.metrics import evaluate
from tais.paper_baselines import run_independent,decorate
from benchmark_su import replay as su_replay
from benchmark_joint_optimization import canon,save,sha,write_csv,metrics as old_metrics
from paper_metrics import metrics
OUT=ROOT/'results/tais-paper';RAW=ROOT/'results/traces/tais-paper'
TAIS=['AdaptiveSense','AdaptiveSense+TrustLog','GateOnly','GateOnly+U','JO-S','JO-SU-20','JO-SU-30','JO-SU-40']
CAPS=[20,25,30,35,40,45,50,55,60]
KINDS=['Delta','Variance','Rao-inspired']
FILES=['src/tais/paper_baselines.py','scripts/benchmark_paper.py','scripts/paper_metrics.py','scripts/analyze_paper.py','tests/test_paper_baselines.py','configs/tais-paper.json','docs/TAIS_PAPER_PROTOCOL.md']
def fingerprints():
    paths=FILES+[str(p.relative_to(ROOT)) for p in sorted((ROOT/'src/tais').glob('*.py'))]+['configs/experiment.yaml','scripts/benchmark_su.py','scripts/benchmark_joint_optimization.py','vendor/AdaptiveSense/simulator/scoring.py','vendor/SensorTrust/core/sensor_trust.c','vendor/SensorTrust/core/sensor_trust.h']
    return {p:sha(ROOT/p) for p in sorted(set(paths))}
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def native(trace,cfg,spec):
    m=spec['id']
    if spec['kind']=='TAIS':return run(trace,cfg,m) if m in TAIS[:2] else su_replay(trace,cfg,m)
    return run_independent(trace,cfg,spec)
def trial(seed,specs):
    cfg=load();rows=[]
    for case in scenarios():
        tr=generate(cfg,seed,case)
        for spec in specs:
            r=native(tr,cfg,spec);m=evaluate(tr,r,cfg)
            rows.append(dict(seed=seed,scenario=case,method=spec['id'],kind=spec['kind'],cap=spec.get('cap',0),threshold=spec.get('threshold',0),minimum=spec.get('minimum',5),**{k:m[k] for k in ['n_events','tp','false_reports','samples','local_tp']}))
    return rows
def pool_trials(seeds,specs,out,workers):
    out.mkdir(parents=True,exist_ok=False);rows=[]
    with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as p:
        for s,r in zip(seeds,p.map(trial,seeds,[specs]*len(seeds))):rows+=r;print(out.name,s,len(r),flush=True)
    write_csv(out/'metrics.csv',rows);dump(out/'manifest.json',dict(seeds=seeds,specs=specs,runs=len(rows),metrics_sha256=sha(out/'metrics.csv')))
    return rows

def select_thresholds(workers):
    """Choose each independent threshold on development micro F1 at cap 40 only."""
    plan=json.loads((ROOT/'configs/tais-paper.json').read_text());seeds=plan['seeds']['development']
    specs=[dict(id=f'{k}-t{t}',kind=k,cap=40,threshold=t) for k in KINDS for t in ([4,8,12] if k=='Rao-inspired' else [2,4,8])]
    rows=pool_trials(seeds,specs,OUT/'threshold-development',workers)
    totals=[];chosen={}
    for spec in specs:
        rr=[r for r in rows if r['method']==spec['id']];tp=sum(r['tp'] for r in rr);n=sum(r['n_events'] for r in rr);fp=sum(r['false_reports'] for r in rr)
        totals.append(dict(**spec,f1=2*tp/(n+tp+fp),recall=tp/n,samples=sum(r['samples'] for r in rr)))
    for k in KINDS:
        best=min([r for r in totals if r['kind']==k],key=lambda r:(-r['f1'],-r['recall'],r['samples'],r['threshold']))
        chosen[k]=best['threshold']
    dump(OUT/'threshold-selection.json',dict(rule='at cap40 maximize development micro F1, then recall, fewer samples, smaller threshold',chosen=chosen,candidates=totals))

def calibrate(workers):
    """Choose closest development sample totals and retain all native schedule points.

    This initial cap-only search is historical; calibrate_bounds records the
    subsequent development-only minimum-bound search without test reselection."""
    plan=json.loads((ROOT/'configs/tais-paper.json').read_text());thresholds=json.loads((OUT/'threshold-selection.json').read_text())['chosen']
    specs=[dict(id=f'{k}-c{c}',kind=k,cap=c,threshold=thresholds[k]) for k in KINDS for c in CAPS]+[dict(id=m,kind='TAIS') for m in ['GateOnly','JO-SU-40']]
    rows=pool_trials(plan['seeds']['development'],specs,OUT/'budget-development',workers)
    samples={s['id']:sum(r['samples'] for r in rows if r['method']==s['id']) for s in specs};selected=[]
    for k in KINDS:
        for target in ['GateOnly','JO-SU-40']:
            best=min([s for s in specs if s['kind']==k],key=lambda s:(abs(samples[s['id']]/samples[target]-1),-s['cap']))
            selected.append(dict(kind=k,target=target,cap=best['cap'],threshold=thresholds[k],development_samples=samples[best['id']],target_samples=samples[target],relative_gap=samples[best['id']]/samples[target]-1))
    schedules=[dict(id=m,kind='TAIS') for m in TAIS]+[dict(id=f'Fixed-{c}',kind='Fixed',cap=c) for c in [5,10,20,30,40,60]]
    schedules += [dict(id=f'{k}-c{c}',kind=k,cap=c,threshold=thresholds[k]) for k in KINDS for c in [20,40,60]]
    # Keep named matches even when identical to a native curve point; no reselection.
    schedules += [dict(id=f"{s['kind']}-budget-{'Gate' if s['target']=='GateOnly' else 'SU40'}",kind=s['kind'],cap=s['cap'],threshold=s['threshold']) for s in selected]
    dump(OUT/'operating-points.json',dict(thresholds=thresholds,budget_selection=selected,schedules=schedules,rule='closest development sample total; tie larger cap. No test adjustment. Native caps20/40/60 and all fixed periods retained.'))

def calibrate_bounds(workers):
    """Search independent interval bounds on development data and preserve the earlier plan.

    Within the 5% development budget band prefer F1, then gap and declared
    ties; if infeasible choose closest budget. This does not guarantee matching
    on held-out data. Write selected points for a separate pre-test freeze."""
    plan=json.loads((ROOT/'configs/tais-paper.json').read_text());thresholds=json.loads((OUT/'threshold-selection.json').read_text())['chosen']
    specs=[dict(id=f'{k}-c{c}-min{lo}',kind=k,cap=c,minimum=lo,threshold=thresholds[k]) for k in KINDS for c in CAPS for lo in [10,15,20,25,30,35] if lo<=c]+[dict(id=m,kind='TAIS') for m in ['GateOnly','JO-SU-40']]
    rows=pool_trials(plan['seeds']['development'],specs,OUT/'budget-bound-development',workers)
    stats={}
    for spec in specs:
        rr=[r for r in rows if r['method']==spec['id']];tp=sum(r['tp'] for r in rr);fp=sum(r['false_reports'] for r in rr);n=sum(r['n_events'] for r in rr)
        stats[spec['id']]=dict(samples=sum(r['samples'] for r in rr),f1=2*tp/(n+tp+fp))
    selected=[]
    for k in KINDS:
        for target in ['GateOnly','JO-SU-40']:
            total=stats[target]['samples'];candidates=[s for s in specs if s['kind']==k]
            qualified=[s for s in candidates if abs(stats[s['id']]['samples']/total-1)<=.05]
            best=min(qualified,key=lambda s:(-stats[s['id']]['f1'],abs(stats[s['id']]['samples']/total-1),-s['cap'],s['minimum'])) if qualified else min(candidates,key=lambda s:abs(stats[s['id']]['samples']/total-1))
            selected.append(dict(kind=k,target=target,cap=best['cap'],minimum=best['minimum'],threshold=thresholds[k],development_samples=stats[best['id']]['samples'],target_samples=total,relative_gap=stats[best['id']]['samples']/total-1))
    initial=json.loads((OUT/'operating-points.json').read_text())
    dump(OUT/'cap-only-operating-points.json',initial)
    schedules=[s for s in initial['schedules'] if '-budget-' not in s['id']]
    schedules += [dict(id=f"{s['kind']}-budget-{'Gate' if s['target']=='GateOnly' else 'SU40'}",kind=s['kind'],cap=s['cap'],minimum=s['minimum'],threshold=s['threshold']) for s in selected]
    dump(OUT/'operating-points.json',dict(thresholds=thresholds,budget_selection=selected,schedules=schedules,rule='Cap-only matching failed on DEVELOPMENT (retained). Search independent minimum bound10/15/20/25/30/35 and cap20..60 step5 at selected threshold. Among development gaps within5% maximize F1, then closest budget, larger cap, smaller minimum. No test adjustment. All native points retained.'))

def views(trace,cfg,spec):
    """Return labeled native/decorated/common views without feeding changes into schedules.

    +C11 adds raw diagnostics; +C11+U also shares TAIS emission. Common view
    shares detector/emission at each schedule actual sample time, isolating
    scheduling rather than comparing fully independent end-to-end systems."""
    r=native(trace,cfg,spec);out={('native',spec['id']):r}
    if spec['kind']!='TAIS':
        out['native',spec['id']+'+C11']=decorate(r,cfg)
        if spec['kind'] in KINDS and spec['id'].endswith('-c40'):
            out['native',spec['id']+'+C11+U']=decorate(r,cfg,upload=True)
    out['common',spec['id']]=decorate(r,cfg,common=True)
    return out

def worker(seed,phase,schedules,archive,cases):
    cfg=load();cache={};rows=[];events=[];artifacts={};ages={};archive=Path(archive)/phase
    def store(rel,obj):
        h=save(archive/rel,obj);artifacts[str(rel)]=h;return h
    for case in cases:
        tr=generate(cfg,seed,case);sh=store(Path(str(seed))/case/'signals.json.gz',asdict(tr));ih=hashlib.sha256(canon(tr.observed)).hexdigest()
        for spec in schedules:
            key=(tr.relationship,tr.profile,spec['id'])
            if key not in cache:
                cf=copy(tr);cf.observed=tr.noisy;cf.faults=[];vv=views(cf,cfg,spec);cache[key]={}
                for (view,name),cr in vv.items():
                    _,ff=old_metrics(cf,cr,cfg,cr)
                    fh=store(Path(str(seed))/'counterfactuals'/f'{tr.relationship}-{tr.profile}-{view}-{name}.json.gz',dict(result=cr,frames=ff))
                    cache[key][view,name]=(cr,ff,fh)
            for (view,name),rr in views(tr,cfg,spec).items():
                cr,ff,fh=cache[key][view,name];m,frames,rx,ev,hist=metrics(tr,rr,cfg,cr,ff)
                rh=store(Path(str(seed))/case/f'{view}-{name}.json.gz',dict(result=rr,frames=frames,receiver=rx,age_histogram=hist.tolist()))
                rows.append(dict(seed=seed,scenario=case,relationship=tr.relationship,profile=tr.profile,fault_kind=tr.faults[0].kind if tr.faults else 'clean',view=view,method=name,schedule=spec['id'],kind=spec['kind'],cap=spec.get('cap',0),minimum=spec.get('minimum',5),**m,observed_sha256=ih,signals_sha256=sh,result_sha256=rh,counterfactual_sha256=fh))
                events.extend(dict(seed=seed,scenario=case,view=view,method=name,**e) for e in ev)
                ages.setdefault((view,name),np.zeros(1800,dtype=np.int64));ages[view,name]+=hist
    write_csv(archive/str(seed)/'metrics.csv',rows);write_csv(archive/str(seed)/'events.csv',events)
    return seed,rows,events,artifacts,{'|'.join(k):v.tolist() for k,v in ages.items()}

def execute(phase,workers,output=OUT,archive=RAW):
    """Write a fresh phase directory using saved schedules and actual encoded frames.

    Formal test requires the committed source/parameter lock byte for byte.
    Output overrides redirect artifacts but do not bypass that freeze check."""
    plan=json.loads((ROOT/'configs/tais-paper.json').read_text());schedules=json.loads((OUT/'operating-points.json').read_text())['schedules']
    seeds=plan['seeds'].get(phase,[20]);cases=scenarios() if phase!='smoke' else ['clean_none','clean_short','missing_cross_long','drift_same_long']
    if phase=='test':
        lock=json.loads((OUT/'selection.json').read_text());assert lock['sources']==fingerprints(),'source freeze mismatch'
        assert lock['operating_points_sha256']==sha(OUT/'operating-points.json'),'parameter freeze mismatch'
        assert subprocess.check_output(['git','show','HEAD:results/tais-paper/selection.json'],cwd=ROOT)==(OUT/'selection.json').read_bytes(),'Commit freeze before final test'
    out=output/phase;out.mkdir(parents=True,exist_ok=False)
    manifest=dict(status='STARTED',seeds=seeds,cases=cases,schedules=schedules,sources=fingerprints(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),archive_root=str(archive),replication=output.resolve()!=OUT.resolve())
    dump(out/'manifest.json',manifest);rows=[];events=[];artifacts={};hist={}
    with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        tasks=[pool.submit(worker,s,phase,schedules,str(archive),cases) for s in seeds]
        for f in as_completed(tasks):
            seed,rr,ee,aa,hh=f.result();rows+=rr;events+=ee;artifacts.update(aa)
            for k,v in hh.items():hist.setdefault(k,np.zeros(1800,dtype=np.int64));hist[k]+=v
            print(phase,seed,len(rr),flush=True)
    rows.sort(key=lambda r:(r['seed'],r['scenario'],r['view'],r['method']));write_csv(out/'metrics.csv',rows);write_csv(out/'events.csv',events)
    ag=[]
    for k,h in sorted(hist.items()):
        view,name=k.split('|');total=int(h.sum());ag.append(dict(view=view,method=name,mean_age_s=float(np.arange(1800)@h/total),p95_age_s=int(np.searchsorted(np.cumsum(h),total*.95)),max_age_s=int(np.flatnonzero(h)[-1])))
    write_csv(out/'pooled_age.csv',ag)
    manifest.update(status='COMPLETE',runs=len(rows),metrics_sha256=sha(out/'metrics.csv'),events_sha256=sha(out/'events.csv'),artifacts=artifacts)
    dump(out/'manifest.json',manifest)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['thresholds','calibrate','bounds','smoke','development','freeze','test']);p.add_argument('--workers',type=int,default=4);p.add_argument('--output-root',type=Path,default=OUT);p.add_argument('--archive-root',type=Path,default=RAW);a=p.parse_args()
    if a.phase=='thresholds':select_thresholds(a.workers)
    elif a.phase=='calibrate':calibrate(a.workers)
    elif a.phase=='bounds':calibrate_bounds(a.workers)
    elif a.phase=='freeze':
        assert json.loads((OUT/'development/manifest.json').read_text())['status']=='COMPLETE'
        dump(OUT/'selection.json',dict(status='FROZEN_BEFORE_TEST',sources=fingerprints(),operating_points_sha256=sha(OUT/'operating-points.json'),development_metrics_sha256=sha(OUT/'development/metrics.csv')))
    else:execute(a.phase,a.workers,a.output_root,a.archive_root)
