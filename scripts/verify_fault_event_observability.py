#!/usr/bin/env python3
"""Checksum and offline metric recomputation only; never rerun a policy."""
import argparse
from dataclasses import asdict
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from tais.budget_eval import sha
from tais.config import load
from tais.signals import Trace,Fault
from tais.observability_signals import metadata
from tais.observability_eval import extra_metrics,event_rows
from tais.metrics import evaluate
from simulator.events import Event
from run_experiments import canonical
from run_fault_event_observability import RESULTS,ARCHIVE,protect,fingerprints
from analyze_fault_event_observability import read_phase


def history():
    guard=json.loads(gzip.decompress((ARCHIVE/'history-guard.json.gz').read_bytes()))
    pointer=json.loads((RESULTS/'history-protection.json').read_text())
    if sha(ARCHIVE/'history-guard.json.gz')!=pointer['guard_sha256']:raise ValueError('Guard changed')
    for mapping in ('tracked','ignored'):
        for rel,digest in guard[mapping].items():
            if sha(ROOT/rel)!=digest:raise ValueError('Historical bytes changed '+rel)
    protect()
    for r in guard['raw_stats']:
        st=Path(r['path']).stat()
        if st.st_size!=r['bytes'] or st.st_mtime_ns!=r['mtime_ns']:raise ValueError('Raw external data changed')
    return dict(tracked_unchanged=len(guard['tracked']),ignored_unchanged=len(guard['ignored']),submodules_unchanged=True,external_raw_stat_signatures_unchanged=True)


def verify(root,phase,plan):
    m,rows=read_phase(root,phase,plan);archive=Path(m['archive_root']);cfg=load()
    for rel,digest in m['artifacts'].items():
        if sha(archive/rel)!=digest:raise ValueError('Raw archive changed '+rel)
    @lru_cache(maxsize=256)
    def raw(rel):return json.loads(gzip.decompress((archive/rel).read_bytes()))
    def result(rel):
        d=raw(rel);return {**d,'reports':[Event(**x) for x in d['reports']],'detections':[Event(**x) for x in d['detections']]}
    by={};verified_events=[];signatures={}
    for r in rows:
        seed,case,method=r['seed'],r['scenario'],r['method'];relative=f'{seed}/{case}/signals.json.gz';bundle=raw(relative);data=bundle['trace']
        trace=Trace(**{**data,'events':[Event(**x) for x in data['events']],'faults':[Fault(**x) for x in data['faults']]})
        if metadata(trace,cfg)!=bundle['metadata'] or bundle['plan_sha256']!=m['plan_sha256']:raise ValueError('Label metadata mismatch')
        if sha(archive/relative)!=r['signals_sha256']:raise ValueError('Signal pointer mismatch')
        for field in ('latent','noisy','observed','events','faults'):
            if hashlib.sha256(canonical(getattr(trace,field))).hexdigest()!=r[field+'_sha256']:raise ValueError('Input digest mismatch')
        signature=tuple(r[k+'_sha256'] for k in ('latent','noisy','observed','events','faults'))
        if (seed,case) in signatures and signatures[seed,case]!=signature:raise ValueError('Unpaired input')
        signatures[seed,case]=signature
        rel=f'{seed}/{case}/{method}.json.gz'
        if sha(archive/rel)!=r['result_sha256'] or sha(archive/r['counterfactual_path'])!=r['counterfactual_sha256']:raise ValueError('Replay pointer mismatch')
        actual=result(rel);cf=result(r['counterfactual_path']);metrics=evaluate(trace,actual,cfg,cf);metrics.update(extra_metrics(trace,actual,cfg,metrics,cf))
        for field,value in metrics.items():
            expected=r[field]
            if value is None:
                if expected is not None:raise ValueError('Undefined value changed '+field)
            elif expected is None or not math.isclose(value,expected,rel_tol=1e-12,abs_tol=1e-10):raise ValueError('Metric mismatch '+str((seed,case,method,field,value,expected)))
        if not all(cfg['sampling']['min_interval_s']<=x['interval']<=cfg['sampling']['max_interval_s'] for x in actual['records']):raise ValueError('Illegal interval')
        for e in event_rows(trace,actual,cfg):verified_events.append(dict(seed=seed,scenario=case,method=method,**e))
    import csv
    saved=list(csv.DictReader((root/phase/'event_matches.csv').open()))
    def event_key(x):return int(x['seed']),x['scenario'],x['method'],x['channel']
    saved=sorted(saved,key=event_key);verified_events=sorted(verified_events,key=event_key)
    if len(saved)!=len(verified_events):raise ValueError('Event count changed')
    for a,b in zip(saved,verified_events):
        for k,v in b.items():
            if str(v if v is not None else '')!=a[k] and not (isinstance(v,(int,float)) and a[k] and float(v)==float(a[k])):raise ValueError('Event metric mismatch '+k)
    analysis=root/phase/'analysis/manifest.json'
    if analysis.exists():
        for name,digest in json.loads(analysis.read_text())['outputs'].items():
            if sha(analysis.parent/name)!=digest:raise ValueError('Analysis output checksum changed')
    return dict(phase=phase,verified_rows=len(rows),verified_artifacts=len(m['artifacts']),verified_events=len(saved),all_metrics_recomputed=True,inputs_identical_across_methods=True,label_metadata_recomputed=True,no_policy_rerun=True,metrics_sha256=sha(root/phase/'metrics.csv'))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=['smoke','development','validation','test']);p.add_argument('--history',action='store_true');p.add_argument('--root',type=Path,default=RESULTS);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    plan=json.loads((ROOT/'configs/fault-event-observability.json').read_text());output={}
    if args.phase:output.update(verify(args.root,args.phase,plan))
    if args.history:output['history']=history()
    output['verifier_sha256']=sha(Path(__file__));args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(output,f,indent=2);f.write('\n')
    print(json.dumps(output,indent=2),flush=True)
if __name__=='__main__':main()
