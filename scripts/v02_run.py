"""Independent, process-parallel v0.2 matrix; never writes legacy artifacts."""
import sys,argparse,csv,json,hashlib,platform,subprocess
from pathlib import Path
from copy import copy
from dataclasses import asdict
from concurrent.futures import ProcessPoolExecutor
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
from tais import ROOT
from tais.signals import generate,scenarios
from tais.metrics import evaluate
from tais_v02.config import load
from tais_v02.replay import run
from run_experiments import canonical,save
from simulator.events import match_events

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def sources():
    paths=list((ROOT/'src/tais').glob('*.py'))+list((ROOT/'src/tais').glob('*.c'))+list((ROOT/'src/tais_v02').glob('*.py'))+list((ROOT/'scripts').glob('v02_*.py'))+[ROOT/'configs/v02.yaml',ROOT/'configs/experiment.yaml']
    return {str(p.relative_to(ROOT)):digest(p) for p in sorted(paths)}

def worker(job):
    seed,label,cases=job;cfg,spec=load();archive=ROOT/'results/traces'/('v02-'+label)
    metrics=[];artifacts={};events=[];cache={}
    for case in cases:
        tr=generate(cfg,seed,case)
        name=f'{seed}/{case}/signals.json.gz';artifacts[name]=save(archive/name,tr)
        for method in spec['methods']:
            scales=spec['threshold_multipliers'] if method in ['TAIS','GateOnly','V02','V02-Passive'] else [1.0]
            for scale in scales:
                result=run(tr,cfg,method,scale)
                key=(tr.relationship,tr.profile,method,scale)
                if key not in cache:
                    clean=copy(tr);clean.observed=tr.noisy;clean.faults=[]
                    cache[key]=run(clean,cfg,method,scale)
                    name=f'{seed}/counterfactual/{tr.relationship}-{tr.profile}-{method}-{scale:g}.json.gz'
                    artifacts[name]=save(archive/name,cache[key])
                m=evaluate(tr,result,cfg,cache[key])
                metrics.append(dict(seed=seed,scenario=case,relationship=tr.relationship,profile=tr.profile,method=method,multiplier=scale,**m))
                name=f'{seed}/{case}/{method}-{scale:g}.json.gz';artifacts[name]=save(archive/name,result)
                match=match_events(tr.events,result['reports'],cfg['evaluation']['event_match_tolerance_s'])
                for i,e in enumerate(tr.events):
                    detected=next((m.detected.start_s for m in match.matches if m.ground_truth==e),None)
                    window=[r for r in result['records'] if e.start_s-5<=r['timestamp']<=e.end_s+5]
                    actions=[dict(channel=n,**a) for r in result['records'] for n,h in r.get('evidence',{}).items() for a in h['actions']]
                    erased=any(f.kind in ['range','missing','invalid','stuck'] and f.channel==e.channel and f.start_s<=e.start_s and f.end_s>e.end_s for f in tr.faults)
                    events.append(dict(seed=seed,scenario=case,method=method,multiplier=scale,event_id=i,channel=e.channel,
                                       start_s=e.start_s,end_s=e.end_s,report_s=detected,matched=detected is not None,
                                       information_erased=erased,sampled_times=json.dumps([r['timestamp'] for r in window]),
                                       candidate_actions=json.dumps(actions)))
    return seed,metrics,artifacts,events

def writecsv(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    """Write a versioned split matrix with recorded source identities and separate archives.

    Require committed executable inputs and exact frozen bytes for final test.
    Smoke cannot preview test seeds; existing completed manifests are protected."""
    p=argparse.ArgumentParser();p.add_argument('--split',choices=['development','validation','test'],required=True)
    p.add_argument('--workers',type=int,default=4);p.add_argument('--smoke',action='store_true');a=p.parse_args()
    cfg,spec=load();seeds=spec['splits'][a.split];cases=scenarios();label=a.split+('-smoke' if a.smoke else '')
    if a.smoke:
        if a.split=='test':raise ValueError('Do not preview final seeds via smoke')
        seeds=seeds[:1];cases=['clean_none','range_cross_long','drift_same_long','spike_same_short']
    if a.split=='test':
        frozen=json.loads((ROOT/'results/v0.2/FREEZE.json').read_text())
        assert sources()==frozen['source_hashes'],'Executable/config changed after final freeze'
        assert not set(seeds)&set(range(50))
    dest=ROOT/'results/v0.2'/label
    if (dest/'manifest.json').exists():raise FileExistsError('Completed results protected: choose a new explicit output/version')
    dest.mkdir(parents=True,exist_ok=True)
    manifest=dict(split=label,seeds=seeds,scenarios=cases,command=sys.argv,python=sys.version,platform=platform.platform(),
                  source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_hashes=sources(),
                  legacy_baseline_commit='68af4b6d9df7ed145a237defc4ab920600823373',archive='results/traces/v02-'+label,
                  artifacts={},runs=0)
    # Dirty executable inputs must not be mislabeled as an exact committed SHA.
    changed=subprocess.check_output(['git','status','--porcelain','--','src','scripts','configs'],text=True)
    assert not changed, 'Commit executable inputs before running matrix: '+changed
    allmetrics=[];allevents=[]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        for seed,rows,hashes,events in pool.map(worker,[(s,label,cases) for s in seeds]):
            allmetrics.extend(rows);allevents.extend(events);manifest['artifacts'].update(hashes);manifest['runs']+=len(rows)
            print(label,'seed',seed,'completed runs',manifest['runs'],flush=True)
    writecsv(dest/'metrics.csv',allmetrics);writecsv(dest/'events.csv',allevents)
    manifest['metrics_sha256']=digest(dest/'metrics.csv');manifest['events_sha256']=digest(dest/'events.csv')
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('COMPLETE',manifest['runs'],flush=True)
if __name__=='__main__':main()
