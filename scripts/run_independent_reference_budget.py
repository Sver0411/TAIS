#!/usr/bin/env python3
"""IRB-1: resource-only development cap calibration and locked causal execution."""
import argparse,csv,hashlib,json,multiprocessing,platform,subprocess,sys
from concurrent.futures import ProcessPoolExecutor,as_completed
from copy import copy
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from tais.config import load
from tais.reference_signals import generate,scenario_specs,main_config
from tais.reference_policy import run
from tais.reference_metrics import evaluate_reference
from tais.trust import library
from tais.budget_eval import sha
from run_budget_matched_experiment import csv_write,write_gzip
from run_experiments import canonical
from simulator.events import match_events

BASE='89aa8341181aa42791f9a4de80739bb7c10fa9e5'
DEST=ROOT/'results/independent-reference-budget';RAW=ROOT/'results/traces/independent-reference-budget'
FILES=('src/tais/reference_signals.py','src/tais/reference_policy.py','src/tais/reference_metrics.py',
'scripts/run_independent_reference_budget.py','scripts/analyze_independent_reference_budget.py','scripts/verify_independent_reference_budget.py',
'scripts/audit_reference_budget.py','tests/test_reference_budget.py','configs/independent-reference-budget.json','docs/INDEPENDENT_REFERENCE_BUDGET_PREREGISTRATION.md')


def fingerprints():
    old=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'--','src/tais','scripts/run_experiments.py','scripts/run_budget_matched_experiment.py','configs/experiment.yaml'],cwd=ROOT,text=True).splitlines()
    return {p:sha(ROOT/p) for p in sorted(set(old)|set(FILES))}


def protect():
    for entry in subprocess.check_output(['git','ls-tree','-rz',BASE],cwd=ROOT).split(b'\0'):
        if not entry:continue
        meta,path=entry.split(b'\t');mode,kind,oid=meta.split();path=path.decode()
        if kind==b'commit':
            if subprocess.check_output(['git','-C',str(ROOT/path),'rev-parse','HEAD']).strip()!=oid or subprocess.check_output(['git','-C',str(ROOT/path),'status','--porcelain']).strip():raise ValueError('Upstream changed')
        else:
            data=(ROOT/path).read_bytes()
            if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest().encode()!=oid:raise ValueError('Historical file changed '+path)


def worker(seed,specs,archive,plan_sha,budgets=None):
    cfg=load();archive=Path(archive);artifacts={};rows=[];events=[];cache={}
    def save(rel,obj):artifacts[rel]=write_gzip(archive/rel,obj);return artifacts[rel]
    for spec in specs:
        case=spec['id'];trace,meta=generate(cfg,seed,case)
        signal_sha=save(f'{seed}/{case}/signals.json.gz',dict(trace=asdict(trace),metadata=meta,plan_sha256=plan_sha))
        if budgets is None:
            from tais.replay import run as historical_run
            r=historical_run(trace,main_config(cfg),'GateOnly',1.)
            rh=save(f'{seed}/{case}/calibration.json.gz',r)
            rows.append(dict(seed=seed,scenario=case,reads=len(r['records']),uploads=sum(x['upload'] for x in r['records']),bytes=sum(x['payload_bytes'] for x in r['records']),signals_sha256=signal_sha,result_sha256=rh));continue
        digests={k+'_sha256':hashlib.sha256(canonical(getattr(trace,k))).hexdigest() for k in ('latent','noisy','observed','events','faults')}
        clean=copy(trace);clean.observed=[{**o,'temperature':n['temperature']} for n,o in zip(trace.noisy,trace.observed)];clean.faults=[]
        cf_key=hashlib.sha256(canonical([clean.observed,trace.events])).hexdigest()
        for level,caps in sorted(budgets.items(),key=lambda x:float(x[0])):
            for method in ('GateOnly','TAIS','ReferenceGate'):
                result=run(trace,cfg,method,caps)
                key=cf_key,method,level
                if key not in cache:
                    cf=run(clean,cfg,method,caps);rel=f'{seed}/counterfactuals/{cf_key}/{method}-{level}.json.gz'
                    cf_sha=save(rel,cf);cache[key]=(dict(reports=cf['reports'],supported_reports=cf['supported_reports']),cf_sha,rel)
                cf,cf_sha,cf_rel=cache[key]
                metrics=evaluate_reference(trace,result,cfg,cf)
                rel=f'{seed}/{case}/{method}-{level}.json.gz';result_sha=save(rel,result)
                rows.append(dict(seed=seed,scenario=case,method=method,budget=float(level),cohort=spec['cohort'],alpha=spec['alpha'],shape=spec['shape'],duration_scenario=spec['duration_s'],offset_s=spec['offset_s'],reference=spec['reference'],temporal=meta['temporal'],
                    **metrics,cap_reads=caps['reads'],cap_uploads=caps['uploads'],cap_bytes=caps['bytes'],signals_sha256=signal_sha,**digests,result_sha256=result_sha,counterfactual_sha256=cf_sha,counterfactual_path=cf_rel))
                for label,reports in [('candidate',result['reports']),('supported',result['supported_reports'])]:
                    matched=match_events(trace.events,reports,cfg['evaluation']['event_match_tolerance_s']);by_truth={m.ground_truth:m.detected for m in matched.matches}
                    for e in trace.events:
                        d=by_truth.get(e);events.append(dict(seed=seed,scenario=case,method=method,budget=level,label=label,channel=e.channel,truth_start=e.start_s,truth_end=e.end_s,matched=d is not None,report_time=d.start_s if d else None,latency_s=max(0,d.start_s-e.start_s) if d else None))
    csv_write(archive/f'{seed}/metrics.csv',rows)
    if events:csv_write(archive/f'{seed}/event_matches.csv',events)
    return dict(seed=seed,rows=str(archive/f'{seed}/metrics.csv'),events=str(archive/f'{seed}/event_matches.csv') if events else None,artifacts=artifacts,runs=len(rows),counterfactuals=len(cache))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=['calibrate','development','validation','test'],required=True);p.add_argument('--workers',type=int,default=4);p.add_argument('--results-root',type=Path,default=DEST);p.add_argument('--archive-root',type=Path,default=RAW);a=p.parse_args()
    if not 1<=a.workers<=4:raise ValueError('Workers1-4 only')
    plan=json.loads((ROOT/'configs/independent-reference-budget.json').read_text());sources=fingerprints();protect()
    if plan['scenarios']!=scenario_specs() or sha(DEST/'seed-audit.json')!=plan['seed_audit_sha256']:raise ValueError('Plan or audit changed')
    cap_path=a.results_root/'budget-lock.json';lock=None;budgets=None
    if a.phase!='calibrate':
        lock=json.loads(cap_path.read_text());budgets=lock['budgets']
        if lock['frozen_files']!=sources:raise ValueError('Source changed after cap calibration')
    if a.phase=='test':
        path=a.results_root/'final-lock.json';final=json.loads(path.read_text())
        if final['frozen_files']!=sources or sha(cap_path)!=final['budget_lock_sha256']:raise ValueError('Final source/cap lock mismatch')
        if subprocess.check_output(['git','show','HEAD:'+str(path.resolve().relative_to(ROOT))],cwd=ROOT)!=path.read_bytes():raise ValueError('Final lock must be committed')
        for rel,digest in final['calibration_files'].items():
            if sha(ROOT/rel)!=digest:raise ValueError('Calibration changed')
    specs=plan['scenarios'] if budgets else [s for s in plan['scenarios'] if s['cohort'] in ('mixed','event_only','drift_only','clean')]
    seeds=plan['seeds']['development' if a.phase=='calibrate' else a.phase]
    out=a.results_root/a.phase;archive=a.archive_root/a.phase
    if out.exists() or archive.exists():raise FileExistsError('Refuse overwrite/repeat; preserve initial attempt')
    out.mkdir(parents=True);archive.mkdir(parents=True)
    start=dict(phase=a.phase,seeds=seeds,cases=[s['id'] for s in specs],methods=plan['methods'] if budgets else ['GateOnly-uncapped'],budgets=budgets,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),created_utc=datetime.now(timezone.utc).isoformat(),frozen_files=sources,plan_sha256=sha(ROOT/'configs/independent-reference-budget.json'),
        budget_lock_sha256=sha(cap_path) if budgets else None,final_lock_sha256=sha(a.results_root/'final-lock.json') if a.phase=='test' else None,workers=a.workers,command=sys.argv)
    (out/'run_started.json').write_text(json.dumps(start,indent=2)+'\n');library();chunks=[]
    try:
        with ProcessPoolExecutor(max_workers=a.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            jobs=[pool.submit(worker,s,specs,str(archive),start['plan_sha256'],budgets) for s in seeds]
            for job in as_completed(jobs):
                c=job.result();chunks.append(c);print(f"{a.phase}: seed{c['seed']}, {len(chunks)}/{len(seeds)}, {c['runs']} runs",flush=True)
    except BaseException as exc:
        (out/'failure.json').write_text(json.dumps(dict(status='INCOMPLETE',error=repr(exc),completed=[c['seed'] for c in chunks]),indent=2));raise
    rows=[];events=[];artifacts={}
    for c in sorted(chunks,key=lambda x:x['seed']):
        rows.extend(csv.DictReader(open(c['rows'])));artifacts.update(c['artifacts'])
        if c['events']:events.extend(csv.DictReader(open(c['events'])))
    csv_write(out/'metrics.csv',rows)
    if events:csv_write(out/'event_matches.csv',events)
    expected=len(seeds)*len(specs)*(9 if budgets else 1)
    if len(rows)!=expected:raise ValueError('Incomplete matrix')
    protect()
    if sources!=fingerprints():raise ValueError('Source changed during execution')
    m={**start,'status':'COMPLETE','runs':len(rows),'counterfactual_runs':sum(c['counterfactuals'] for c in chunks),'archive_root':str(archive.resolve()),'artifacts':dict(sorted(artifacts.items())),
       'python':sys.version,'platform':platform.platform(),'csv_sha256':{p.name:sha(p) for p in out.glob('*.csv')}}
    with (out/'manifest.json').open('x') as f:json.dump(m,f,indent=2);f.write('\n')
    if not budgets:
        fields=('reads','uploads','bytes');means={k:sum(int(r[k]) for r in rows)/len(rows) for k in fields}
        import math
        b={str(float(level)):{k:math.floor(level*means[k]) for k in fields} for level in plan['budget_levels']}
        cap=dict(status='FROZEN_CAPS',development_mean=means,budgets=b,frozen_files=sources,calibration_manifest_sha256=sha(out/'manifest.json'),calibration_metrics_sha256=sha(out/'metrics.csv'))
        with cap_path.open('x') as f:json.dump(cap,f,indent=2);f.write('\n')
    print(f"Complete {a.phase}: {len(rows)} scored, {m['counterfactual_runs']} offline counterfactuals",flush=True)
if __name__=='__main__':main()
