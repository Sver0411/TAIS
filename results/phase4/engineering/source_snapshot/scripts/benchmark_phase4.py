#!/usr/bin/env python3
"""Phase4 engineering/freeze/final and exact fresh-path reproduction."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from dataclasses import asdict
import gzip
import hashlib
import importlib.metadata
import json
import multiprocessing
from pathlib import Path
import platform
import shutil
import subprocess
import sys

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from tais.config import load
from tais.transfer_signals import counterfactual
from tais.adaptive.sampling_metrics import sampling_metrics
from phase4_support import make_trace,replay,cases,methods,new_methods
from ablation_support import supplement_metrics
from benchmark_ablation import sources as inherited_sources
from benchmark_joint_optimization import canon,save,sha,metrics as codec_metrics
from paper_metrics import metrics
from diagnose_phase4 import annotated,event_rows

OUT=ROOT/'results/phase4'
PLAN=ROOT/'configs/phase4.json'


def dump(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def sources():
    paths=list((ROOT/'src/tais/adaptive').glob('*.py'))+[PLAN,ROOT/'docs/PHASE4_PROTOCOL.md',ROOT/'docs/PHASE4_ALGORITHM_DESIGN.md',ROOT/'tests/test_phase4_sampling.py']
    paths += [ROOT/'scripts'/p for p in ('phase4_support.py','benchmark_phase4.py','analyze_phase4.py','diagnose_phase4.py')]
    return {**inherited_sources(),**{str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}}


def frame_csv(path,rows):
    data=pd.DataFrame(rows).to_csv(index=False).encode()
    if path.suffix=='.gz':data=gzip.compress(data,mtime=0)
    with path.open('xb') as f:f.write(data)


def worker(seed,plan,archive):
    cfg=load();cache={};rows=[];events=[];forensics=[];inputs=[];artifacts={};histograms=[];timelines=[]
    for case in cases(plan):
        tr=make_trace(plan,seed,case);cf=counterfactual(tr)
        signal=Path(str(seed))/case/'signals.json.gz';artifacts[str(signal)]=save(archive/signal,asdict(tr))
        ih=hashlib.sha256(canon(tr.observed)).hexdigest()
        cid=hashlib.sha256(canon(dict(observed=cf.observed,events=cf.events))).hexdigest()
        inputs.append(dict(seed=seed,scenario=case,n_events=len(tr.events),n_faults=len(tr.faults),observed_sha256=ih,signals_sha256=artifacts[str(signal)]))
        for method in methods(plan):
            key=(cid,method)
            if key not in cache:
                cr=replay(cf,cfg,method,plan);_,ff=codec_metrics(cf,cr,cfg,cr)
                rel=Path(str(seed))/'counterfactuals'/f'{cid}-{method}.json.gz'
                artifacts[str(rel)]=save(archive/rel,dict(result=cr,frames=ff))
                cache[key]=cr,ff
            cr,ff=cache[key];r=replay(tr,cfg,method,plan)
            native,frames,rx,_,_=metrics(tr,r,cfg,cr,ff)
            extra,ee=supplement_metrics(tr,r,frames,cfg,plan,cr,ff)
            sample,evsample,hh,used=sampling_metrics(r,tr.events,len(tr.observed),plan['pre_window_s'],plan['common']['min_interval_s'],plan['fast_window_s'])
            by={(e['channel'],e['truth_start']):e for e in evsample}
            identity=dict(seed=seed,scenario=case,method=method)
            rel=Path(str(seed))/case/(method+'.json.gz')
            artifacts[str(rel)]=save(archive/rel,dict(result=r,frames=frames))
            keep=['samples','uploads','binary_v1_bytes','important_edges','important_edges_unreported',
                  'duration_s','n_events','tp','false_reports','rx_tp','rx_false_reports','fault_induced_false']
            rows.append(dict(**identity,cohort='ma54' if case in cases(plan)[:54] else 'factor_sweep',
                             fault_kind=('multi_' if case.startswith('multi_') else '')+tr.faults[0].kind if tr.faults else 'clean',
                             **{k:native[k] for k in keep},**extra,**sample,
                             finite_covered_events=sum(e['finite_sample_coverage'] for e in ee if e['side']=='sender'),
                             observed_sha256=ih,sample_schedule_sha256=hashlib.sha256(canon([x['timestamp'] for x in r['records']])).hexdigest(),
                             result_sha256=artifacts[str(rel)]))
            for e in ee:events.append(dict(**identity,**e,**{k:v for k,v in by[e['channel'],e['truth_start']].items() if k not in ('channel','truth_start')}))
            rx_by={(e['channel'],e['truth_start']):e['matched'] for e in ee if e['side']=='receiver'}
            sender=[dict(**identity,**e,receiver_matched=rx_by[e['channel'],e['truth_start']]) for e in ee if e['side']=='sender']
            fr=event_rows(annotated(r['records'],cfg,method),sender,cfg)
            forensics.extend(fr)
            histograms.extend(dict(**identity,**h) for h in hh)
            if seed in (plan['representative_seed'],plan['engineering_seeds'][0]) and case in plan['representative_cases'] and method in ('A0','A5','A7','Robust-T1-U1','Risk-T1-U1'):
                for record,fast_used in zip(r['records'],used):
                    for channel in cfg['channels']:
                        timelines.append(dict(**identity,channel=channel,timestamp=record['timestamp'],value=record['values'][channel],
                                              interval_s=record['interval'],active=record['active'][channel],health_state=record['health'][channel]['state'],
                                              upload=record['upload'],fast_used=fast_used,adaptive_state=record.get('adaptive',{}).get('state','native')))
    return seed,rows,events,forensics,inputs,artifacts,histograms,timelines


def freeze(out):
    eng=json.loads((out/'engineering/manifest.json').read_text());plan=json.loads(PLAN.read_text())
    assert eng['status']=='COMPLETE' and eng['sources']==sources()
    audit=json.loads((OUT/'seed-audit.json').read_text())
    assert audit['collisions']==[] and audit['directory_collisions']==[]
    assert audit['final_candidates']==plan['final_seeds'] and audit['engineering_candidates']==plan['engineering_seeds']
    assert set(plan['final_seeds']).isdisjoint(plan['engineering_seeds'])
    assert min(plan['final_seeds'])>=920
    assert not (out/'freeze.json').exists()
    for name in sources():
        target=out/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    dump(out/'freeze.json',dict(status='FROZEN_BEFORE_FINAL',sources=sources(),seeds=plan['final_seeds'],cases=cases(plan),methods=methods(plan),
                               engineering_manifest_sha256=sha(out/'engineering/manifest.json'),seed_audit_sha256=sha(OUT/'seed-audit.json'),
                               code_base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()))


def execute(out,phase,workers):
    plan=json.loads(PLAN.read_text())
    if phase=='test':
        lock=json.loads((out/'freeze.json').read_text());assert lock['sources']==sources()
    dest=out/phase;dest.mkdir(parents=True,exist_ok=False)
    archive=ROOT/'results/traces'/out.name/phase
    if archive.exists():raise FileExistsError(archive)
    seeds=plan['final_seeds'] if phase=='test' else plan['engineering_seeds']
    manifest=dict(status='STARTED',phase=phase,seeds=seeds,cases=cases(plan),methods=methods(plan),sources=sources(),archive_root=str(archive),
                  code_base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  freeze_sha256=sha(out/'freeze.json') if phase=='test' else None,
                  python=platform.python_version(),packages={n:importlib.metadata.version(n) for n in ('numpy','pandas','matplotlib','PyYAML')})
    dump(dest/'manifest.json',manifest)
    accum=[[],[],[],[],{},[],[]]
    with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        tasks=[pool.submit(worker,s,plan,archive) for s in seeds]
        for f in as_completed(tasks):
            s,*parts=f.result()
            for i,p in enumerate(parts):
                if isinstance(accum[i],dict):accum[i].update(p)
                else:accum[i].extend(p)
            print(phase,s,len(parts[0]),'runs complete',flush=True)
    names=['metrics.csv','events.csv','forensics.csv.gz','inputs.csv','archives.json','interval_histograms.csv.gz','timelines.csv']
    for name,values in zip(names,accum):
        if isinstance(values,dict):dump(dest/name,dict(sorted(values.items())))
        else:
            if values:values.sort(key=lambda r:tuple(str(r.get(k,'')) for k in ['seed','scenario','method','side','channel','truth_start','timestamp','interval_s']))
            frame_csv(dest/name,values)
    assert len(accum[0])==len(seeds)*len(cases(plan))*len(methods(plan))
    assert sources()==manifest['sources'],'Sources changed during execution'
    manifest.update(status='COMPLETE',runs=len(accum[0]),outputs={name:sha(dest/name) for name in names})
    dump(dest/'manifest.json',manifest)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['engineering','freeze','test','replicate'])
    p.add_argument('--out',type=Path,default=OUT);p.add_argument('--workers',type=int,default=4)
    a=p.parse_args()
    if not 1<=a.workers<=4:raise ValueError('workers1..4')
    a.out.mkdir(parents=True,exist_ok=True)
    if a.phase=='freeze':freeze(a.out)
    elif a.phase=='replicate':
        assert json.loads((OUT/'freeze.json').read_text())['sources']==sources()
        shutil.copytree(OUT/'sources',a.out/'sources');shutil.copyfile(OUT/'freeze.json',a.out/'freeze.json')
        execute(a.out,'test',a.workers)
    else:execute(a.out,a.phase,a.workers)
