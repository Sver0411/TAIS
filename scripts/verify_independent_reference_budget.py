#!/usr/bin/env python3
"""IRB-1 independent ledger/JSON checks and offline metric recomputation."""
import argparse,csv,gzip,json,math,sys,hashlib,multiprocessing
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from tais.config import load
from tais.signals import Trace,Fault
from tais.reference_policy import json_bytes
from tais.reference_metrics import evaluate_reference
from simulator.events import Event
from tais.budget_eval import sha
from run_independent_reference_budget import DEST,RAW,protect
from run_experiments import canonical
from analyze_independent_reference_budget import read_phase


def check_ledger(trace,result):
    """Recompute admitted individual reads and exact JSON upload charges from the ledger.

    Verify observed values correspond to charged A/B reads and never exceed caps.
    No scheduler or physical power model is run during this accounting check."""
    used=dict(reads=0,uploads=0,bytes=0);a=[];b=[];frames=iter(result['envelopes']);uploads=0
    for x in result['ledger']:
        if x['accepted']:
            if x['operation']=='read':
                used['reads']+=1;(a if x['sensor']=='A' else b).append(x['time'])
            else:
                envelope=next(frames);assert envelope['timestamp']==x['time'];cost=len(json_bytes(envelope));assert cost==x['cost'];used['uploads']+=1;used['bytes']+=cost;uploads+=1
        assert used==x['used'] and all(used[k]<=result['caps'][k] for k in used)
    assert used==result['used'] and len(result['records'])==len(a) and len(result['reference_reads'])==len(b)
    assert len(result['envelopes'])==uploads
    assert all(r['timestamp']==t and r['values']['temperature']==trace.observed[int(t)]['temperature'] for r,t in zip(result['records'],a))
    assert all(r['timestamp']==t and r['value']==trace.observed[int(t)]['reference_temperature'] for r,t in zip(result['reference_reads'],b))
    assert all(5<=r['interval']<=60 for r in result['records'])
    assert len(result['reports'])==sum('report_time' in e for e in result['episodes'])


def verify_chunk(task):
    """Read bounded cached archive chunks and independently recompute offline metrics.

    Restore event objects for matching; no online policy is rerun or tuned."""
    rows,archive,phase=task;archive=Path(archive);cfg=load()
    @lru_cache(maxsize=256)
    def raw(rel):return json.loads(gzip.decompress((archive/rel).read_bytes()))
    def result(rel):
        r=raw(rel)
        for key in ('reports','detections','supported_reports'):
            if key in r:r={**r,key:[Event(**x) for x in r[key]]}
        return r
    @lru_cache(maxsize=128)
    def trace_info(rel):
        data=raw(rel)['trace']
        trace=Trace(**{**data,'events':[Event(**x) for x in data['events']],'faults':[Fault(**x) for x in data['faults']]})
        digests={k+'_sha256':hashlib.sha256(canonical(getattr(trace,k))).hexdigest() for k in ('latent','noisy','observed','events','faults')}
        return trace,digests
    inputs={}
    for r in rows:
        seed,case=r['seed'],r['scenario'];rel=f'{seed}/{case}/signals.json.gz';trace,digests=trace_info(rel)
        if sha(archive/rel)!=r['signals_sha256']:raise ValueError('Signal pointer changed')
        if phase=='calibrate':
            actual=raw(f'{seed}/{case}/calibration.json.gz')
            values=dict(reads=len(actual['records']),uploads=sum(x['upload'] for x in actual['records']),bytes=sum(x['payload_bytes'] for x in actual['records']))
            for row in actual['records']:
                frame=dict(timestamp=row['timestamp'],values=row['values'],environment_active=row['active'],health=row['health'])
                if row['payload_bytes']!=(len(json_bytes(frame)) if row['upload'] else 0):raise ValueError('Calibration JSON mismatch')
        else:
            for k,h in digests.items():
                if r[k]!=h:raise ValueError('Input SHA mismatch '+k)
            method=r['method'];level=str(float(r['budget']));rel=f'{seed}/{case}/{method}-{level}.json.gz'
            if sha(archive/rel)!=r['result_sha256'] or sha(archive/r['counterfactual_path'])!=r['counterfactual_sha256']:raise ValueError('Replay pointer changed')
            actual=result(rel);cf=result(r['counterfactual_path']);check_ledger(trace,actual);values=evaluate_reference(trace,actual,cfg,cf)
            signature=tuple(r[k+'_sha256'] for k in ('latent','noisy','observed','events','faults'))
            if (seed,case) in inputs and inputs[seed,case]!=signature:raise ValueError('Unpaired input')
            inputs[seed,case]=signature
        for key,value in values.items():
            expected=r[key]
            if value is None:
                if expected is not None:raise ValueError('Undefined metric changed '+key)
            elif expected is None or not math.isclose(value,expected,rel_tol=1e-12,abs_tol=1e-10):raise ValueError('Recomputed metric mismatch '+str((seed,case,key,value,expected)))
    return len(rows)


def verify(root,phase,plan):
    manifest,rows=read_phase(root,phase,plan);archive=Path(manifest['archive_root'])
    for rel,h in manifest['artifacts'].items():
        if sha(archive/rel)!=h:raise ValueError('Raw checksum changed '+rel)
    tasks=[([r for r in rows if r['seed']==seed],str(archive),phase) for seed in manifest['seeds']]
    if len(tasks)==1:verified=verify_chunk(tasks[0])
    else:
        with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:verified=sum(pool.map(verify_chunk,tasks))
    assert verified==len(rows)
    analysis=root/phase/'analysis/manifest.json'
    if analysis.exists():
        for name,h in json.loads(analysis.read_text())['outputs'].items():
            if sha(analysis.parent/name)!=h:raise ValueError('Analysis hash changed')
    return dict(phase=phase,verified_rows=len(rows),verified_artifacts=len(manifest['artifacts']),all_metrics_recomputed=True,no_policy_rerun=True,independent_ledger_and_json_checks=True,paired_inputs_identical=True,metrics_sha256=sha(root/phase/'metrics.csv'))


def history():
    """Require archived tracked/ignored byte hashes and external raw-file stat signatures.

    Source files are included, so comments can fail this guard without changing
    experiment data. Preserve the guard as the original identity record."""
    p=RAW/'history-guard.json.gz';pointer=json.loads((DEST/'history-protection.json').read_text());assert sha(p)==pointer['guard_sha256'];guard=json.loads(gzip.decompress(p.read_bytes()))
    for name in ('tracked','ignored'):
        for rel,h in guard[name].items():
            if sha(ROOT/rel)!=h:raise ValueError('Historical bytes changed '+rel)
    protect()
    for r in guard['raw_stats']:
        st=Path(r['path']).stat();assert st.st_size==r['bytes'] and st.st_mtime_ns==r['mtime_ns']
    return dict(original_files_unchanged=len(guard['tracked']),ignored_files_unchanged=len(guard['ignored']),submodules_unchanged=True,external_raw_stat_signatures_unchanged=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=['calibrate','development','validation','test']);p.add_argument('--root',type=Path,default=DEST);p.add_argument('--history',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args();plan=json.loads((ROOT/'configs/independent-reference-budget.json').read_text());out={}
    if a.phase:out.update(verify(a.root,a.phase,plan))
    if a.history:out['history']=history()
    out['verifier_sha256']=sha(Path(__file__));a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(out,indent=2),flush=True)
if __name__=='__main__':main()
