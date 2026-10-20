"""Verify recorded source, metrics, optional archives and an actual fresh replay."""
import sys,argparse,json,hashlib,gzip,subprocess,csv
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
from tais import ROOT
from tais_v02.config import load
from tais_v02.replay import run
from tais.signals import generate
from run_experiments import canonical

def main():
    """Verify saved v0.2 bytes and optionally perform one deterministic replay.

    Original source hashes include comments/docstrings; preserving experiment
    artifacts does not imply the annotated source still has its original hash."""
    p=argparse.ArgumentParser();p.add_argument('--split',required=True);p.add_argument('--traces',action='store_true');p.add_argument('--replay-one',action='store_true');a=p.parse_args()
    dest=ROOT/'results/v0.2'/a.split;m=json.loads((dest/'manifest.json').read_text())
    sha=lambda b:hashlib.sha256(b).hexdigest()
    assert sha((dest/'metrics.csv').read_bytes())==m['metrics_sha256']
    assert sha((dest/'events.csv').read_bytes())==m['events_sha256']
    assert sum(1 for _ in csv.DictReader((dest/'metrics.csv').open()))==m['runs']
    for name,h in m['source_hashes'].items():
        assert sha((ROOT/name).read_bytes())==h,name
        assert sha(subprocess.check_output(['git','show',m['source_commit']+':'+name]))==h,name+' not exact source commit'
    archive=ROOT/m['archive']
    if a.traces:
        for name,h in m['artifacts'].items():assert sha((archive/name).read_bytes())==h,name
    if a.replay_one:
        cfg,_=load();seed=m['seeds'][0];case='range_cross_long'
        for method in ['AdaptiveSense','GateOnly','TAIS','V02','V02-Passive']:
            actual=run(generate(cfg,seed,case),cfg,method)
            assert canonical(actual)==gzip.decompress((archive/f'{seed}/{case}/{method}-1.json.gz').read_bytes()),method
    print(json.dumps(dict(split=a.split,runs=m['runs'],source_files=len(m['source_hashes']),
                          archive_hashes=len(m['artifacts']) if a.traces else 0,fresh_replays=5 if a.replay_one else 0,status='passed')))
if __name__=='__main__':main()
