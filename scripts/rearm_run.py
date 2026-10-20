"""Two separate preregistered suites; clean committed source and protected outputs."""
import sys,argparse,csv,json,hashlib,platform,subprocess
from pathlib import Path
from copy import copy
from concurrent.futures import ProcessPoolExecutor
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
from tais import ROOT
from tais.signals import generate
from tais.metrics import evaluate
from tais_rearm.config import load,suite_config
from tais_rearm.replay import run
from run_experiments import canonical,save
from simulator.events import match_events
BASE='96170fcb5df0534ca58e44827b2fcb214e7892ef'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sources():
 paths=[]
 for package in ['tais','tais_v02','tais_rearm']:
  paths+=list((ROOT/'src'/package).glob('*.py'))+list((ROOT/'src'/package).glob('*.c'))
 paths+=list((ROOT/'scripts').glob('rearm_*.py'))+[ROOT/'scripts/run_experiments.py',ROOT/'scripts/summarize_results.py',ROOT/'scripts/v02_summarize.py']
 paths+=[ROOT/'configs'/x for x in ['experiment.yaml','v02.yaml','blocked_rearm.yaml']]
 paths+=list((ROOT/'tests').glob('*.py'))
 return {str(p.relative_to(ROOT)):digest(p) for p in sorted(paths)}

def worker(job):
 seed,split=job;cfg,spec=load();archive=ROOT/f'results/traces/blocked-rearm/{split}'
 rows=[];events=[];hashes={}
 for suite in spec['suites']:
  c,cases=suite_config(cfg,spec,suite);cache={}
  for case in cases:
   tr=generate(c,seed,case);name=f'{suite}/{seed}/{case}/signals.json.gz';hashes[name]=save(archive/name,tr)
   for method in spec['methods']:
    scales=[1.] if method=='AdaptiveSense' else spec['threshold_multipliers']
    for scale in scales:
     result=run(tr,c,method,scale);key=(tr.relationship,tr.profile,method,scale)
     if key not in cache:
      clean=copy(tr);clean.observed=tr.noisy;clean.faults=[];cache[key]=run(clean,c,method,scale)
      name=f'{suite}/{seed}/counterfactual/{tr.relationship}-{tr.profile}-{method}-{scale:g}.json.gz';hashes[name]=save(archive/name,cache[key])
     rows.append(dict(suite=suite,seed=seed,scenario=case,relationship=tr.relationship,profile=tr.profile,method=method,multiplier=scale,**evaluate(tr,result,c,cache[key])))
     name=f'{suite}/{seed}/{case}/{method}-{scale:g}.json.gz';hashes[name]=save(archive/name,result)
     match=match_events(tr.events,result['reports'],c['evaluation']['event_match_tolerance_s'])
     for i,e in enumerate(tr.events):
      det=next((m.detected.start_s for m in match.matches if m.ground_truth==e),None)
      actions=[dict(channel=n,**a) for r in result['records'] for n,x in r.get('evidence',{}).items() for a in x['actions']]
      events.append(dict(suite=suite,seed=seed,scenario=case,method=method,multiplier=scale,event_id=i,channel=e.channel,start_s=e.start_s,end_s=e.end_s,report_s=det,matched=det is not None,
        sampled_times=json.dumps([r['timestamp'] for r in result['records'] if e.start_s-5<=r['timestamp']<=e.end_s+5]),actions=json.dumps(actions)))
 return seed,rows,events,hashes

def writecsv(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
 """Run the two declared repair suites without overwriting an existing split directory.

 Require committed inputs; formal test checks original source/config hashes.
 Those byte identities include comments, separately from behavior equivalence."""
 p=argparse.ArgumentParser();p.add_argument('--split',choices=['development','validation','test'],required=True);p.add_argument('--workers',type=int,default=4);a=p.parse_args()
 cfg,spec=load();seeds=spec['splits'][a.split];dest=ROOT/f'results/blocked-rearm/{a.split}'
 assert not subprocess.check_output(['git','status','--porcelain','--','src','scripts','configs','tests'],text=True),'Commit executable inputs first'
 if a.split=='test':
  frozen=json.loads((ROOT/'results/blocked-rearm/FREEZE.json').read_text());assert frozen['source_hashes']==sources(),'Source changed after freeze'
  assert seeds==list(range(120,150))
 if dest.exists():raise FileExistsError('Protect published and partial results; rerun in a fresh pre-result source checkout')
 dest.mkdir(parents=True)
 manifest=dict(split=a.split,seeds=seeds,command=sys.argv,python=sys.version,platform=platform.platform(),baseline_commit=BASE,
  source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_hashes=sources(),suites=spec['suites'],methods=spec['methods'],multipliers=spec['threshold_multipliers'],
  archive=f'results/traces/blocked-rearm/{a.split}',artifacts={},runs=0)
 allrows=[];allevents=[]
 with ProcessPoolExecutor(max_workers=a.workers) as pool:
  for seed,rows,ev,hashes in pool.map(worker,[(s,a.split) for s in seeds]):
   allrows.extend(rows);allevents.extend(ev);manifest['artifacts'].update(hashes);manifest['runs']+=len(rows)
   print(a.split,'seed',seed,'runs',manifest['runs'],flush=True)
 writecsv(dest/'metrics.csv',allrows);writecsv(dest/'events.csv',allevents)
 manifest['metrics_sha256']=digest(dest/'metrics.csv');manifest['events_sha256']=digest(dest/'events.csv')
 (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('COMPLETE',manifest['runs'],flush=True)
if __name__=='__main__':main()
