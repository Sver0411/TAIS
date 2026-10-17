"""Exact source/blob/hash audit plus fresh representative replays for both suites."""
import sys,argparse,csv,gzip,json,hashlib,subprocess
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
from tais import ROOT
from tais.signals import generate
from tais_rearm.config import load,suite_config
from tais_rearm.replay import run
from run_experiments import canonical

def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--split',required=True);p.add_argument('--traces',action='store_true');p.add_argument('--replay-one',action='store_true');a=p.parse_args();dest=ROOT/f'results/blocked-rearm/{a.split}';m=json.loads((dest/'manifest.json').read_text())
 for name in ['metrics','events']:assert sha((dest/(name+'.csv')).read_bytes())==m[name+'_sha256']
 assert len(list(csv.DictReader((dest/'metrics.csv').open())))==m['runs']
 for name,h in m['source_hashes'].items():
  assert sha((ROOT/name).read_bytes())==h,name
  assert sha(subprocess.check_output(['git','show',m['source_commit']+':'+name]))==h,name
 archive=ROOT/m['archive']
 if a.traces:
  for name,h in m['artifacts'].items():assert sha((archive/name).read_bytes())==h,name
 count=0
 if a.replay_one:
  cfg,spec=load();seed=m['seeds'][0]
  for suite in spec['suites']:
   c,_=suite_config(cfg,spec,suite)
   for method in spec['methods']:
    case='spike_same_long';r=run(generate(c,seed,case),c,method)
    assert canonical(r)==gzip.decompress((archive/f'{suite}/{seed}/{case}/{method}-1.json.gz').read_bytes()),(suite,method)
    count+=1
 print(json.dumps(dict(split=a.split,runs=m['runs'],source_files=len(m['source_hashes']),archive_hashes=len(m['artifacts']) if a.traces else 0,fresh_replays=count,status='passed')))
if __name__=='__main__':main()
