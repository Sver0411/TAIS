#!/usr/bin/env python3
"""FO-1 immutable original policies on an isolated versioned timing matrix."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import copy
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'), str(ROOT/'scripts')]
from tais.budget_eval import sha
from tais.config import load
from tais.observability_signals import generate, metadata, scenarios
from tais.observability_eval import extra_metrics, event_rows
from tais.replay import run
from tais.metrics import evaluate
from tais.trust import library
from run_experiments import canonical
from run_budget_matched_experiment import write_gzip, csv_write

BASE='5b06d2feae44db2b3503697d246f51c43e5d8f2e'
RESULTS=ROOT/'results/fault-event-observability'
ARCHIVE=ROOT/'results/traces/fault-event-observability'
NEW_FILES=('src/tais/observability_signals.py','src/tais/observability_eval.py',
 'scripts/run_fault_event_observability.py','scripts/analyze_fault_event_observability.py',
 'scripts/verify_fault_event_observability.py','scripts/audit_observability_seeds.py',
 'tests/test_observability.py','configs/fault-event-observability.json',
 'docs/FAULT_EVENT_OBSERVABILITY_PREREGISTRATION.md')


def fingerprints():
    paths=list(NEW_FILES)+[str(p.relative_to(ROOT)) for p in (ROOT/'src/tais').glob('*.py')]
    paths+=['src/tais/trust_bridge.c','configs/experiment.yaml','scripts/run_experiments.py','scripts/run_budget_matched_experiment.py']
    return {p:sha(ROOT/p) for p in sorted(set(paths))}


def protect():
    for item in subprocess.check_output(['git','ls-tree','-rz',BASE],cwd=ROOT).split(b'\0'):
        if not item:continue
        meta,name=item.split(b'\t');mode,kind,oid=meta.split();name=name.decode()
        if kind==b'commit':
            if subprocess.check_output(['git','-C',str(ROOT/name),'rev-parse','HEAD']).strip()!=oid or subprocess.check_output(['git','-C',str(ROOT/name),'status','--porcelain']).strip():raise ValueError('Changed upstream '+name)
        else:
            data=(ROOT/name).read_bytes()
            if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest().encode()!=oid:raise ValueError('Changed historical file '+name)


def worker(seed,cases,archive,plan_sha):
    cfg=load();archive=Path(archive);artifacts={};metrics=[];events=[];reports=[];cache={}
    def save(relative,obj):
        artifacts[relative]=write_gzip(archive/relative,obj);return artifacts[relative]
    for case in cases:
        trace=generate(cfg,seed,case);meta=metadata(trace,cfg)
        signal_sha=save(f'{seed}/{case}/signals.json.gz',dict(trace=asdict(trace),metadata=meta,plan_sha256=plan_sha))
        digests={k+'_sha256':hashlib.sha256(canonical(getattr(trace,k))).hexdigest() for k in ('latent','noisy','observed','events','faults')}
        shared=dict(seed=seed,scenario=case,relationship=trace.relationship,profile=trace.profile,
                    fault_kind=meta['fault_kind'],cohort=meta['cohort'],offset_s=meta['offset_s'],temporal=meta['temporal'],event_start_order=meta['event_start_order'],
                    overlap_duration_s=meta['overlap']['duration_s'],overlap_points=meta['overlap']['observation_points'],
                    fault_start_s=trace.faults[0].start_s if trace.faults else None,fault_end_s=trace.faults[0].end_s if trace.faults else None,
                    event_start_s=trace.events[0].start_s if trace.events else None,event_end_s=trace.events[0].end_s if trace.events else None)
        for method in ('AdaptiveSense','GateOnly','TAIS'):
            result=run(trace,cfg,method,1.)
            key=digests['noisy_sha256'],digests['events_sha256'],method
            if key not in cache:
                clean=copy(trace);clean.observed=trace.noisy;clean.faults=[]
                cf=run(clean,cfg,method,1.)
                rel=f'{seed}/counterfactuals/{key[0]}-{method}.json.gz'
                digest=save(rel,cf);cache[key]=(dict(reports=cf['reports'],samples=len(cf['records']),uploads=sum(r['upload'] for r in cf['records']),payload_bytes=sum(r['payload_bytes'] for r in cf['records'])),digest,rel)
            cf,cf_sha,cf_path=cache[key]
            values=evaluate(trace,result,cfg,cf)
            values.update(extra_metrics(trace,result,cfg,values,cf))
            result_sha=save(f'{seed}/{case}/{method}.json.gz',result)
            metrics.append(dict(**shared,method=method,multiplier=1.,**values,signals_sha256=signal_sha,**digests,result_sha256=result_sha,counterfactual_sha256=cf_sha,counterfactual_path=cf_path))
            for e in event_rows(trace,result,cfg):events.append(dict(seed=seed,scenario=case,method=method,**e))
            for report in result['reports']:
                index=next(i for i,r in enumerate(result['records']) if r['timestamp']==report.start_s)
                current=result['records'][index]
                reports.append(dict(seed=seed,scenario=case,method=method,channel=report.channel,time=report.start_s,
                    preceding_interval_s=result['records'][index-1]['interval'] if index else None,
                    report_next_interval_s=current['interval'],health_state=current['health'].get(report.channel,{}).get('state'),health_flags=current['health'].get(report.channel,{}).get('flags')))
    for name,rows in [('metrics',metrics),('event_matches',events),('reports',reports)]:csv_write(archive/f'{seed}/{name}.csv',rows)
    return dict(seed=seed,runs=len(metrics),artifacts=artifacts,paths={name:str(archive/f'{seed}/{name}.csv') for name in ('metrics','event_matches','reports')},counterfactuals=len(cache))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=['smoke','development','validation','test'],required=True)
    p.add_argument('--results-root',type=Path,default=RESULTS);p.add_argument('--archive-root',type=Path,default=ARCHIVE);p.add_argument('--workers',type=int,default=4);args=p.parse_args()
    if not 1<=args.workers<=4:raise ValueError('Workers must be1-4')
    plan=json.loads((ROOT/'configs/fault-event-observability.json').read_text());sources=fingerprints();protect()
    if sha(RESULTS/'seed-audit.json')!=plan['seed_audit_sha256']:raise ValueError('Seed audit changed')
    if plan['scenarios']!=scenarios() or plan['methods']!=['AdaptiveSense','GateOnly','TAIS'] or plan['multiplier']!=1.:raise ValueError('Plan matrix changed')
    lock=None
    if args.phase=='test':
        lock_path=args.results_root/'final-lock.json';lock=json.loads(lock_path.read_text())
        if lock['frozen_files']!=sources:raise ValueError('Source changed since final lock')
        if subprocess.check_output(['git','show','HEAD:'+str(lock_path.resolve().relative_to(ROOT))],cwd=ROOT)!=lock_path.read_bytes():raise ValueError('Final lock not committed')
        for rel,digest in lock['calibration_files'].items():
            if sha(ROOT/rel)!=digest:raise ValueError('Calibration/verification changed')
    seeds=plan['seeds'].get(args.phase,[20]);cases=scenarios()
    if args.phase=='smoke':cases=['clean_none','range_same_long','spike_same_short_dt_m10','drift_cross_long_dt_p650']
    out=args.results_root/args.phase;archive=args.archive_root/args.phase
    if out.exists() or archive.exists():raise FileExistsError('Never overwrite/repeat a phase; retain first attempt')
    out.mkdir(parents=True);archive.mkdir(parents=True)
    start=dict(phase=args.phase,created_utc=datetime.now(timezone.utc).isoformat(),seeds=seeds,cases=cases,methods=plan['methods'],multiplier=1.,
               source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),frozen_files=sources,plan_sha256=sha(ROOT/'configs/fault-event-observability.json'),
               final_lock_sha256=sha(args.results_root/'final-lock.json') if lock else None,workers=args.workers,command=sys.argv)
    (out/'run_started.json').write_text(json.dumps(start,indent=2)+'\n');library();chunks=[]
    try:
        with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            tasks=[pool.submit(worker,s,cases,str(archive),start['plan_sha256']) for s in seeds]
            for f in as_completed(tasks):
                r=f.result();chunks.append(r);print(f"{args.phase}: seed {r['seed']}, {len(chunks)}/{len(seeds)}, {r['runs']} scored runs",flush=True)
    except BaseException as exc:
        (out/'failure.json').write_text(json.dumps(dict(status='INCOMPLETE',error=repr(exc),completed_seeds=[r['seed'] for r in chunks]),indent=2));raise
    import csv
    artifacts={}
    for name in ('metrics','event_matches','reports'):
        rows=[]
        for chunk in sorted(chunks,key=lambda x:x['seed']):rows.extend(csv.DictReader(open(chunk['paths'][name])))
        csv_write(out/(name+'.csv'),rows)
    for chunk in chunks:artifacts.update(chunk['artifacts'])
    actual=sum(c['runs'] for c in chunks)
    if actual!=len(seeds)*len(cases)*3:raise ValueError('Incomplete run matrix')
    protect()
    if fingerprints()!=sources:raise ValueError('Sources changed during execution')
    manifest={**start,'status':'COMPLETE','runs':actual,'counterfactual_runs':sum(c['counterfactuals'] for c in chunks),'archive_root':str(archive.resolve()),'python':sys.version,'platform':platform.platform(),
              'artifacts':dict(sorted(artifacts.items())),'csv_sha256':{p.name:sha(p) for p in out.glob('*.csv')}}
    with (out/'manifest.json').open('x') as f:json.dump(manifest,f,indent=2);f.write('\n')
    print(f"Complete {args.phase}: {actual} scored runs, {manifest['counterfactual_runs']} offline counterfactuals",flush=True)

if __name__=='__main__':main()
