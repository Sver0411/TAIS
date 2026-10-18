#!/usr/bin/env python3
"""Protect historical bytes and independently recompute archived BM-1 metrics.

Never invokes a scheduler: final policy execution is not repeated.
"""
import argparse
import csv
from dataclasses import fields
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from tais.budget_eval import BASE,sha,COUNT_FIELDS
from tais.config import load
from tais.signals import Trace,Fault
from tais.metrics import evaluate
from tais.wire_codec import encode,envelope_from_record
from simulator.events import Event


def protect_snapshot(output):
    if output.exists():raise FileExistsError('Guard exists')
    source={};gitlinks={}
    for item in subprocess.check_output(['git','ls-tree','-rz',BASE],cwd=ROOT).split(b'\0'):
        if not item:continue
        meta,path=item.split(b'\t',1);mode,kind,oid=meta.split();path=path.decode()
        if kind==b'commit':
            actual=subprocess.check_output(['git','-C',str(ROOT/path),'rev-parse','HEAD']).strip()
            if actual!=oid:raise ValueError('Upstream revision changed')
            if subprocess.check_output(['git','-C',str(ROOT/path),'status','--porcelain']).strip():raise ValueError('Dirty upstream')
            gitlinks[path]=oid.decode()
        else:
            raw=(ROOT/path).read_bytes();actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest().encode()
            if actual!=oid:raise ValueError('Baseline file changed '+path)
            source[path]=hashlib.sha256(raw).hexdigest()
    ignored={}
    for directory in (ROOT/'results/traces',ROOT/'results/scratch'):
        for path in sorted(directory.rglob('*')):
            if not path.is_file() or 'budget-matched' in path.parts or any(x.startswith('budget-') for x in path.relative_to(directory).parts):continue
            ignored[str(path.relative_to(ROOT))]=sha(path)
    snapshot=dict(base=BASE,baseline_sha256=source,submodules=gitlinks,old_ignored_sha256=ignored)
    raw=json.dumps(snapshot,sort_keys=True,separators=(',',':')).encode();data=gzip.compress(raw,mtime=0)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as f:f.write(data)
    print(dict(base=BASE,baseline_files=len(source),old_ignored_files=len(ignored),snapshot_sha256=sha(output)),flush=True)


def verify_history(path):
    before=json.loads(gzip.decompress(path.read_bytes()))
    for mapping in ('baseline_sha256','old_ignored_sha256'):
        for relative,digest in before[mapping].items():
            if sha(ROOT/relative)!=digest:raise ValueError('Historical bytes changed '+relative)
    for relative,expected in before['submodules'].items():
        actual=subprocess.check_output(['git','-C',str(ROOT/relative),'rev-parse','HEAD'],text=True).strip()
        if actual!=expected or subprocess.check_output(['git','-C',str(ROOT/relative),'status','--porcelain']).strip():raise ValueError('Upstream changed')
    audit=json.loads((ROOT/'results/budget-matched/seed-audit.json').read_text())
    for raw in audit['raw_file_stat_signatures']:
        stat=Path(raw['path']).stat()
        if stat.st_size!=raw['bytes'] or stat.st_mtime_ns!=raw['mtime_ns']:raise ValueError('External raw file changed '+raw['path'])
    return dict(protected_base_files=len(before['baseline_sha256']),protected_old_ignored_files=len(before['old_ignored_sha256']),
                submodules_unchanged=True,external_raw_stat_signatures_unchanged=True)


def verify_phase(root,phase):
    path=root/phase;m=json.loads((path/'manifest.json').read_text());archive=Path(m['archive_root'])
    if sha(path/'metrics.csv')!=m['metrics_sha256'] or sha(path/'event_matches.csv')!=m['event_matches_sha256']:raise ValueError('Phase CSV changed')
    if m['status']!='COMPLETE':raise ValueError('Incomplete phase')
    for relative,digest in m['artifacts'].items():
        if sha(archive/relative)!=digest:raise ValueError('Raw artifact changed '+relative)
    @lru_cache(maxsize=128)
    def raw(relative):return json.loads(gzip.decompress((archive/relative).read_bytes()))
    cfg=load();rows=list(csv.DictReader((path/'metrics.csv').open()));seen=set();inputs={}
    for r in rows:
        seed,case,method,mult=int(r['seed']),r['scenario'],r['method'],float(r['multiplier'])
        key=(seed,case,method,mult)
        if key in seen:raise ValueError('Duplicate metric row')
        seen.add(key)
        input_hash=(r['signals_sha256'],r['observed_sha256'],r['events_sha256'],r['faults_sha256'])
        if (seed,case) in inputs and inputs[seed,case]!=input_hash:raise ValueError('Unpaired method inputs')
        inputs[seed,case]=input_hash
        data=raw(f'{seed}/{case}/signals.json.gz');data={**data,'events':[Event(**e) for e in data['events']],'faults':[Fault(**f) for f in data['faults']]}
        trace=Trace(**data)
        def result(relative):
            d=raw(relative);return {**d,'reports':[Event(**e) for e in d['reports']],'detections':[Event(**e) for e in d['detections']]}
        original=result(f'{seed}/{case}/{method}-{mult:g}.json.gz')
        cf=result(f"{seed}/counterfactuals/{r['relationship']}-{r['profile']}/{method}-{mult:g}.json.gz")
        metrics=evaluate(trace,original,cfg,cf)
        metrics['binary_v1_bytes']=sum(len(encode(envelope_from_record(x))) for x in original['records'] if x['upload'])
        for field,value in metrics.items():
            expected=None if r[field]=='' else float(r[field])
            if value is None:
                if expected is not None:raise ValueError('Undefined metric changed '+field)
            elif expected is None or not math.isclose(value,expected,rel_tol=1e-12,abs_tol=1e-10):raise ValueError('Metric mismatch '+str((key,field,value,expected)))
    matrix={(s,c,method,float(mult)) for s in m['seeds'] for c in m['cases'] for method,mult in m['points']}
    if seen!=matrix or len(rows)!=m['runs']:raise ValueError('Incomplete run matrix')
    return dict(phase=phase,verified_rows=len(rows),verified_artifacts=len(m['artifacts']),input_pairs_identical=True,
                every_original_metric_recomputed_from_saved_artifacts=True,no_policy_rerun=True,metrics_sha256=sha(path/'metrics.csv'))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--snapshot',type=Path);p.add_argument('--history',type=Path)
    p.add_argument('--phase',choices=['smoke','development','validation','test']);p.add_argument('--root',type=Path,default=ROOT/'results/budget-matched')
    p.add_argument('--output',type=Path);args=p.parse_args()
    if args.snapshot:protect_snapshot(args.snapshot);return
    if args.output is None:raise ValueError('Verification requires a new output path')
    result={}
    if args.history:result['history']=verify_history(args.history)
    if args.phase:result['phase']=verify_phase(args.root,args.phase)
    result['verifier_sha256']=sha(Path(__file__))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
