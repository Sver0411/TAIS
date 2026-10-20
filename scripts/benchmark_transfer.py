#!/usr/bin/env python3
"""Single frozen G2 campaign; same causal policies, codec and event scorer as G1."""
import argparse,hashlib,json,multiprocessing,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from dataclasses import asdict
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from tais.config import load
from tais.transfer_signals import generate,scenarios,counterfactual
from tais.paper_baselines import decorate
from benchmark_paper import native,dump
from benchmark_joint_optimization import canon,save,sha,write_csv,metrics as codec_metrics
from transfer_metrics import metrics
OUT=ROOT/'results/tais-transfer';RAW=ROOT/'results/traces/tais-transfer'
BASE='0170196dda10f78b85d5e4b685d56331a0021083'
NEW_FILES=['src/tais/transfer_signals.py','configs/tais-transfer.json','scripts/benchmark_transfer.py','scripts/transfer_metrics.py','scripts/analyze_transfer.py','tests/test_transfer_signals.py','tests/test_transfer_benchmark.py','docs/TAIS_CROSS_GENERATOR_PROTOCOL.md']

def plan():return json.loads((ROOT/'configs/tais-transfer.json').read_text())
def specs():
    chosen=plan()['methods'];source=json.loads((ROOT/'results/tais-paper/operating-points.json').read_text())['schedules'];by={r['id']:r for r in source}
    return [by[m] for m in chosen]
def policy(trace,cfg,spec):
    # Strong interface: policy cannot access labels, hidden parameters, scenario,
    # seed, latent/noisy arrays or even the original Trace object.
    """Expose observed rows only, excluding truth, seed, scenario and hidden process state."""
    r=native(SimpleNamespace(observed=trace.observed),cfg,spec)
    return r if spec['kind']=='TAIS' else decorate(r,cfg)
def name(spec):return spec['id']+('' if spec['kind']=='TAIS' else '+C11')
def inherited():
    """Require exact byte identity for every G1 pre-test source-lock entry.

    Comments/docstrings alter these hashes even when executable behavior matches;
    this historical guard intentionally does not accept semantic equivalence."""
    lock=json.loads((ROOT/'results/tais-paper/selection.json').read_text())
    # This freeze predates the G1 final test; all old runtime/config sources are
    # still verified. G2 lives in separate files and is excluded from that list.
    files=lock['sources'];assert all(sha(ROOT/p)==h for p,h in files.items())
    return files

def freeze():
    assert not (OUT/'selection.json').exists()
    assert json.loads((OUT/'smoke/manifest.json').read_text())['status']=='COMPLETE'
    assert json.loads((OUT/'seed-audit.json').read_text())['collisions']==[]
    sources={p:sha(ROOT/p) for p in NEW_FILES}
    dump(OUT/'selection.json',dict(status='FROZEN_BEFORE_G2',base=BASE,inherited_sources=inherited(),sources=sources,specs=specs(),operating_points_sha256=sha(ROOT/'results/tais-paper/operating-points.json'),engineering_metrics_sha256=sha(OUT/'smoke/metrics.csv'),seed_audit_sha256=sha(OUT/'seed-audit.json')))
def check_freeze():
    """Require inherited/new source hashes, operating points and committed G2 lock to match."""
    p=OUT/'selection.json';lock=json.loads(p.read_text())
    assert inherited()==lock['inherited_sources']
    assert {k:sha(ROOT/k) for k in lock['sources']}==lock['sources']
    assert specs()==lock['specs']
    assert subprocess.check_output(['git','show','HEAD:results/tais-transfer/selection.json'],cwd=ROOT)==p.read_bytes(),'Commit freeze before formal execution'
    return lock

def worker(seed,phase,selected,cases,archive):
    """Run one seed with exact counterfactual identities and independent receiver scoring.

    Cache keys include clean observations and event labels, avoiding G1-style
    relationship/profile assumptions under independently timed G2 interventions."""
    cfg=load();p=plan();path=Path(archive)/phase;cache={};rows=[];events=[];faults=[];artifacts={};ages={name(s):np.zeros(p['duration_s'],dtype=np.int64) for s in selected}
    def store(rel,x):
        h=save(path/rel,x);artifacts[str(rel)]=h;return h
    for case in cases:
        tr=generate(p,seed,case);signal=store(Path(str(seed))/case/'signals.json.gz',asdict(tr));observed_hash=hashlib.sha256(canon(tr.observed)).hexdigest();cf=counterfactual(tr)
        # Exact identity of fault-free observations AND labels, no relation/profile cache.
        cf_identity=hashlib.sha256(canon(dict(observed=cf.observed,events=cf.events))).hexdigest()
        for spec in selected:
            method=name(spec);key=(cf_identity,method)
            if key not in cache:
                cr=policy(cf,cfg,spec);_,ff=codec_metrics(cf,cr,cfg,cr)
                fh=store(Path(str(seed))/'counterfactuals'/f'{cf_identity}-{method}.json.gz',dict(observed_sha256=hashlib.sha256(canon(cf.observed)).hexdigest(),result=cr,frames=ff))
                cache[key]=cr,ff,fh
            cr,ff,fh=cache[key];r=policy(tr,cfg,spec);m,frames,rx,ee,dd,hist=metrics(tr,r,cfg,cr,ff)
            rh=store(Path(str(seed))/case/f'{method}.json.gz',dict(result=r,frames=frames,receiver=rx,age_histogram=hist.tolist()))
            identity=dict(seed=seed,scenario=case,method=method)
            rows.append(dict(**identity,view='native',relationship=tr.relationship,profile='mixed',fault_kind=tr.faults[0].kind if tr.faults else 'clean',fault_channel=tr.faults[0].channel if tr.faults else 'none',**m,observed_sha256=observed_hash,signals_sha256=signal,result_sha256=rh,counterfactual_identity=cf_identity,counterfactual_sha256=fh))
            events.extend(dict(**identity,**e) for e in ee);faults.extend(dict(**identity,**d) for d in dd);ages[method]+=hist
    return seed,rows,events,faults,artifacts,{k:v.tolist() for k,v in ages.items()}

def execute(phase,workers,output=OUT,archive=RAW):
    """Write G2 engineering or held-out outputs under fixed inherited operating points.

    Formal test checks the original source freeze. Artifact directories are
    exclusive; a new source annotation is not permission to overwrite a campaign."""
    if phase=='test':check_freeze()
    p=plan();selected=specs();seeds=p['final_seeds'] if phase=='test' else p['engineering_seeds']
    cases=scenarios() if phase=='test' else ['clean_none','clean_both']+[f'{k}_{c}_same' for k in ['range','spike','stuck','drift','missing','invalid','stable_offset'] for c in ['temperature','humidity']]
    out=output/phase;out.mkdir(parents=True,exist_ok=False)
    manifest=dict(status='STARTED',generator=p['version'],source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),phase=phase,seeds=seeds,cases=cases,specs=selected,source_hashes={k:sha(ROOT/k) for k in NEW_FILES},archive_root=str(archive),replication=output.resolve()!=OUT.resolve(),rng='stream SHA256 first128bits')
    dump(out/'manifest.json',manifest);rows=[];events=[];faults=[];artifacts={};ages={}
    with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        tasks=[pool.submit(worker,s,phase,selected,cases,str(archive)) for s in seeds]
        for f in as_completed(tasks):
            seed,rr,ee,dd,aa,hh=f.result();rows+=rr;events+=ee;faults+=dd;artifacts.update(aa)
            for k,h in hh.items():ages.setdefault(k,np.zeros(p['duration_s'],dtype=np.int64));ages[k]+=h
            print(phase,seed,len(rr),'runs',flush=True)
    for kind,rr in [('metrics',rows),('events',events),('faults',faults)]:
        rr.sort(key=lambda r:(r['seed'],r['scenario'],r['method'],r.get('truth_start',r.get('start_s',0))));write_csv(out/(kind+'.csv'),rr)
    age_rows=[]
    for method,h in sorted(ages.items()):
        total=int(h.sum());age_rows.append(dict(method=method,mean_age_s=float(np.arange(len(h))@h/total),p95_age_s=int(np.searchsorted(np.cumsum(h),.95*total)),max_age_s=int(np.flatnonzero(h)[-1]),source_seconds=total))
    write_csv(out/'pooled_age.csv',age_rows);dump(out/'age_histograms.json',{k:v.tolist() for k,v in ages.items()})
    manifest.update(status='COMPLETE',runs=len(rows),artifacts=artifacts,outputs={f:sha(out/f) for f in ['metrics.csv','events.csv','faults.csv','pooled_age.csv','age_histograms.json']})
    dump(out/'manifest.json',manifest)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('phase',choices=['smoke','freeze','test']);a.add_argument('--workers',type=int,default=4);a.add_argument('--output-root',type=Path,default=OUT);a.add_argument('--archive-root',type=Path,default=RAW);v=a.parse_args()
    if v.phase=='freeze':freeze()
    else:execute(v.phase,v.workers,v.output_root,v.archive_root)
