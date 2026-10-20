#!/usr/bin/env python3
"""Run BM-1 frozen existing policies; new paths only, one locked final execution."""
from concurrent.futures import ProcessPoolExecutor,as_completed
from copy import copy
import argparse
import csv
from dataclasses import asdict
from datetime import datetime,timezone
import gzip
import hashlib
import json
import multiprocessing
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from tais.budget_eval import BASE,sha
from tais.config import load
from tais.signals import generate,scenarios
from tais.replay import run
from tais.metrics import evaluate
from tais.trust import library
from tais.wire_codec import encode,envelope_from_record
from simulator.events import match_events
from run_experiments import canonical

FROZEN_FILES=('src/tais/budget_eval.py','scripts/run_budget_matched_experiment.py',
              'scripts/analyze_budget_matched_results.py','scripts/verify_budget_matched_experiment.py','tests/test_budget_matched.py',
              'configs/budget-matched.json','docs/BUDGET_MATCHED_EXPERIMENT_PREREGISTRATION.md',
              'configs/experiment.yaml','src/tais/scheduler.py','src/tais/replay.py','src/tais/metrics.py',
              'src/tais/signals.py','src/tais/trust.py','src/tais/trust_bridge.c','src/tais/config.py',
              'src/tais/wire_codec.py')


def fingerprints():return {p:sha(ROOT/p) for p in FROZEN_FILES}


def protect_original_sources():
    """Require original blob identities and clean pinned submodules before the historical campaign.

    This is a byte freeze, not a semantic-equivalence test; comments change its
    source identity. Do not weaken it or refresh recorded experiments for maintenance."""
    entries=subprocess.check_output(['git','ls-tree','-rz',BASE,'--','src','configs','vendor'],cwd=ROOT)
    for entry in entries.split(b'\0'):
        if not entry:continue
        meta,path=entry.split(b'\t',1);mode,kind,expected=meta.split();path=path.decode()
        if kind==b'commit':
            actual=subprocess.check_output(['git','-C',str(ROOT/path),'rev-parse','HEAD']).strip()
            if actual!=expected or subprocess.check_output(['git','-C',str(ROOT/path),'status','--porcelain']).strip():raise ValueError('Upstream changed '+path)
        else:
            data=(ROOT/path).read_bytes();actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest().encode()
            if actual!=expected:raise ValueError('Original source/config changed '+path)


def write_gzip(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True);data=gzip.compress(canonical(obj),mtime=0)
    with path.open('xb') as f:f.write(data)
    return hashlib.sha256(data).hexdigest()


def csv_write(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def worker(seed,cases,points,archive):
    """Archive one seed policy matrix and score against paired clean observations.

    Record independent input/result fingerprints, actual Binary lengths and
    sender event matches. TrustLog must preserve the raw baseline schedule."""
    cfg=load();archive=Path(archive);artifacts={};metrics=[];events=[];counterfactuals={}
    def save(relative,obj):
        artifacts[relative]=write_gzip(archive/relative,obj);return artifacts[relative]
    for case in cases:
        trace=generate(cfg,seed,case);signal_sha=save(f'{seed}/{case}/signals.json.gz',asdict(trace))
        observed_sha=hashlib.sha256(canonical(trace.observed)).hexdigest()
        events_sha=hashlib.sha256(canonical(trace.events)).hexdigest();faults_sha=hashlib.sha256(canonical(trace.faults)).hexdigest()
        baseline_schedule={}
        for method,m in points:
            result=run(trace,cfg,method,m)
            key=trace.relationship,trace.profile,method,m
            if key not in counterfactuals:
                clean=copy(trace);clean.observed=trace.noisy;clean.faults=[]
                cf=run(clean,cfg,method,m)
                rel=f'{seed}/counterfactuals/{trace.relationship}-{trace.profile}/{method}-{m:g}.json.gz'
                cf_sha=save(rel,cf);counterfactuals[key]=({'reports':cf['reports']},cf_sha)
            cf,cf_sha=counterfactuals[key]
            values=evaluate(trace,result,cfg,cf)
            values['binary_v1_bytes']=sum(len(encode(envelope_from_record(r))) for r in result['records'] if r['upload'])
            actual_sha=save(f'{seed}/{case}/{method}-{m:g}.json.gz',result)
            row=dict(seed=seed,scenario=case,relationship=trace.relationship,profile=trace.profile,
                     fault_kind=trace.faults[0].kind if trace.faults else 'clean',method=method,multiplier=m,
                     **values,signals_sha256=signal_sha,observed_sha256=observed_sha,events_sha256=events_sha,
                     faults_sha256=faults_sha,result_sha256=actual_sha,counterfactual_sha256=cf_sha)
            metrics.append(row)
            matched=match_events(trace.events,result['reports'],cfg['evaluation']['event_match_tolerance_s'])
            by_truth={x.ground_truth:x.detected for x in matched.matches}
            for e in trace.events:
                d=by_truth.get(e)
                events.append(dict(seed=seed,scenario=case,method=method,multiplier=m,channel=e.channel,
                    truth_start=e.start_s,truth_end=e.end_s,truth_type=e.event_type,matched=d is not None,
                    report_time=d.start_s if d else None,latency_s=max(0,d.start_s-e.start_s) if d else None))
            if method in ('AdaptiveSense','AdaptiveSense+TrustLog'):
                schedule=hashlib.sha256(canonical([(r['timestamp'],r['interval'],r['upload'],r['active']) for r in result['records']])).hexdigest()
                baseline_schedule[method]=schedule
        if len(baseline_schedule)==2 and len(set(baseline_schedule.values()))!=1:raise AssertionError('TrustLog altered baseline decisions')
    metrics_path=archive/f'{seed}/metrics.csv';csv_write(metrics_path,metrics)
    events_path=archive/f'{seed}/event_matches.csv';csv_write(events_path,events)
    return dict(seed=seed,metrics=str(metrics_path),events=str(events_path),artifacts=artifacts,runs=len(metrics))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase',choices=['smoke','development','validation','test'],required=True)
    p.add_argument('--results-root',type=Path,default=ROOT/'results/budget-matched')
    p.add_argument('--archive-root',type=Path,default=ROOT/'results/traces/budget-matched')
    p.add_argument('--selection',type=Path)
    p.add_argument('--workers',type=int,default=4)
    args=p.parse_args()
    if not 1<=args.workers<=4:raise ValueError('Use1-4 workers; parallelism changes no policy')
    plan=json.loads((ROOT/'configs/budget-matched.json').read_text());protect_original_sources()
    if sha(ROOT/'results/budget-matched/seed-audit.json')!=plan['seed_audit_sha256']:raise ValueError('Seed audit changed')
    sources=fingerprints();selection=None
    if args.phase=='test':
        lock_path=args.selection or args.results_root/'selection.json'
        selection=json.loads(lock_path.read_text())
        if selection['frozen_files']!=sources:raise ValueError('Frozen code/protocol/config changed after selection')
        if selection['plan_sha256']!=sha(ROOT/'configs/budget-matched.json'):raise ValueError('Plan mismatch')
        relative=str(lock_path.resolve().relative_to(ROOT))
        committed=subprocess.check_output(['git','show','HEAD:'+relative],cwd=ROOT)
        if committed!=lock_path.read_bytes():raise ValueError('Final selection must be committed, not just staged')
        for path,digest in selection['calibration_files'].items():
            if sha(ROOT/path)!=digest:raise ValueError('Calibration changed '+path)
        points=[(x['method'],x['multiplier']) for x in selection['final_points']]
    else:
        points=[(method,m) for method in ('AdaptiveSense','AdaptiveSense+TrustLog','GateOnly','TAIS') for m in (plan['grid'] if method in ('GateOnly','TAIS') else [1.])]
    cases=scenarios();seeds=plan['seeds'].get(args.phase,[20])
    if args.phase=='smoke':
        cases=['clean_none','range_cross_long','spike_same_short'];points=[(m,1.) for m in ('AdaptiveSense','AdaptiveSense+TrustLog','GateOnly','TAIS')]
    out=args.results_root/args.phase;archive=args.archive_root/args.phase
    if out.exists() or archive.exists():raise FileExistsError('Never overwrite/repeat a phase; preserve its first attempt')
    out.mkdir(parents=True);archive.mkdir(parents=True)
    start=dict(phase=args.phase,seeds=seeds,cases=cases,points=points,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
               plan_sha256=sha(ROOT/'configs/budget-matched.json'),frozen_files=sources,
               selection_sha256=sha(args.selection or args.results_root/'selection.json') if selection else None,
               command=sys.argv,created_utc=datetime.now(timezone.utc).isoformat(),workers=args.workers)
    with (out/'run_started.json').open('x') as f:json.dump(start,f,indent=2);f.write('\n')
    library()  # Compile once before spawned workers, using the actual C11 core.
    completed=[]
    try:
        with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            tasks={pool.submit(worker,s,cases,points,str(archive)):s for s in seeds}
            for future in as_completed(tasks):
                result=future.result();completed.append(result)
                print(f"{args.phase}: seed{result['seed']} complete, {result['runs']} scored runs; {len(completed)}/{len(seeds)} seeds",flush=True)
    except BaseException as exc:
        with (out/'failure.json').open('x') as f:json.dump(dict(error=repr(exc),completed_seeds=[r['seed'] for r in completed],status='INCOMPLETE_DO_NOT_SELECT'),f,indent=2)
        raise
    metrics=[];events=[];artifacts={}
    for chunk in sorted(completed,key=lambda r:r['seed']):
        metrics.extend(csv.DictReader(Path(chunk['metrics']).open()));events.extend(csv.DictReader(Path(chunk['events']).open()));artifacts.update(chunk['artifacts'])
    expected=len(seeds)*len(cases)*len(points)
    if len(metrics)!=expected:raise AssertionError('Incomplete method/seed/scenario matrix')
    csv_write(out/'metrics.csv',metrics);csv_write(out/'event_matches.csv',events)
    protect_original_sources()
    if sources!=fingerprints():raise ValueError('Implementation changed during run')
    result={**start,'status':'COMPLETE','runs':len(metrics),'python':sys.version,'platform':platform.platform(),
            'base_source':BASE,'original_config_sha256':sha(ROOT/'configs/experiment.yaml'),
            'archive_root':str(archive.resolve()),'artifacts':artifacts,
            'metrics_sha256':sha(out/'metrics.csv'),'event_matches_sha256':sha(out/'event_matches.csv')}
    with (out/'manifest.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(f'Completed {args.phase}: {len(metrics)} actual runs, {len(artifacts)} archived artifacts',flush=True)

if __name__=='__main__':main()
