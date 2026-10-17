"""Offline sampled trace export. Before mode is usable before any repair exists."""
import sys,argparse,csv,gzip,json
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
from tais import ROOT
from tais_v02.config import load
from tais_v02.replay import run as v02_run
from tais_v02.forensics import inspect_run
from tais.signals import generate
from simulator.events import match_events
from run_experiments import canonical,save

def main():
 p=argparse.ArgumentParser();p.add_argument('--after',action='store_true');a=p.parse_args();cfg,_=load()
 trace=generate(cfg,91,'spike_same_long');out=ROOT/'results/blocked-rearm/diagnosis';out.mkdir(parents=True,exist_ok=True)
 methods=['TAIS','V02']+(['V02-Rearm'] if a.after else []);rows=[];summary={}
 for method in methods:
  if method=='TAIS':result,ev=inspect_run(trace,cfg,method)
  elif method=='V02':
   result=v02_run(trace,cfg,method);stored=json.loads(gzip.decompress((ROOT/'results/v0.2/cases/91-spike_same_long-1.json.gz').read_bytes()))
   assert json.loads(canonical(result))==stored['runs']['V02'][0]
  else:
   from tais_rearm.replay import run
   result=run(trace,cfg,method)
  match=match_events(trace.events,result['reports'],5)
  summary[method]=dict(tp=match.true_positives,reports=[e.start_s for e in result['reports']],samples=len(result['records']),uploads=sum(r['upload'] for r in result['records']))
  save(out/(method+'.json.gz'),dict(trace=trace,result=result))
  for i,r in enumerate(result['records']):
   for n in cfg['channels']:
    x=r.get('evidence',{}).get(n,{})
    if method=='TAIS':
     old=ev[i]['channels'][n];score=max([c['raw_score'] for c in old['raw_calls']],default=0);raw=any(c['raw_active'] for c in old['raw_calls']);phase=old['ladder_state'];blocked=old['blocked'];actions=old['lifecycle']
    else:score=x['raw_score'];raw=x['raw_active'];phase=x['phase'];blocked=phase=='BLOCKED';actions=x['actions']
    rows.append(dict(method=method,t=r['timestamp'],channel=n,value=r['values'][n],health_state=r['health'][n]['state'],health_score=r['health'][n]['score'],fault_flags=r['health'][n]['flags'],
     raw_score=score,raw_active=raw,phase=phase,blocked=blocked,actions=json.dumps(actions),environment_active=r['active'][n],interval=r['interval'],upload=r['upload'],reasons=json.dumps(r['reasons'])))
 label='after' if a.after else 'before'
 with (out/(label+'-samples.csv')).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 (out/(label+'-summary.json')).write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps(summary,indent=2))
 print('Key V02 samples',[(r['t'],r['health_state'],r['raw_score'],r['phase'],r['raw_active'],r['upload']) for r in rows if r['method']=='V02' and r['channel']=='temperature' and 600<=r['t']<=680])
if __name__=='__main__':main()
