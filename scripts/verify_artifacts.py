"""Check committed hashes, optional trace archives and a fresh deterministic replay."""
import argparse,csv,gzip,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from tais import ROOT
from tais.config import load
from tais.signals import generate
from tais.replay import run


def main():
    """Verify a legacy split, optionally checking archives and replaying one case.

    The source check requires original bytes, including comments, for current
    TAIS source paths. It is stricter than runtime behavior equivalence and
    can fail after source additions or annotation-only maintenance."""
    p=argparse.ArgumentParser();p.add_argument('--split',required=True);p.add_argument('--traces',action='store_true');p.add_argument('--replay-one',action='store_true');args=p.parse_args()
    dest=ROOT/'results'/args.split;manifest=json.loads((dest/'manifest.json').read_text())
    assert hashlib.sha256((dest/'metrics.csv').read_bytes()).hexdigest()==manifest['metrics_sha256']
    assert hashlib.sha256((ROOT/'configs/experiment.yaml').read_bytes()).hexdigest()==manifest['config_sha256']
    with (dest/'metrics.csv').open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==manifest['runs']
    # Executable experiment files must match the recorded frozen commit.
    for path in sorted((ROOT/'src/tais').glob('*')):
        if path.suffix not in ['.py','.c']:continue
        relative=str(path.relative_to(ROOT))
        frozen=subprocess.check_output(['git','show',f'{manifest["source_commit"]}:{relative}'],cwd=ROOT)
        assert path.read_bytes()==frozen,relative+' changed since experiment freeze'
    archive=ROOT/'results/traces'/args.split
    if args.traces:
        for name,digest in manifest['artifacts'].items():
            assert hashlib.sha256((archive/name).read_bytes()).hexdigest()==digest,name
    if args.replay_one:
        spec=importlib.util.spec_from_file_location('runner',ROOT/'scripts/run_experiments.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        seed=manifest['seeds'][0];case='range_cross_long';method='TAIS';scale=1.0
        result=run(generate(load(),seed,case),load(),method,scale)
        path=archive/f'{seed}/{case}/{method}-{scale:g}.json.gz'
        assert mod.canonical(result)==gzip.decompress(path.read_bytes())
    print(json.dumps({'split':args.split,'metric_rows':len(rows),'trace_hashes_checked':len(manifest['artifacts']) if args.traces else 0,'fresh_replay_checked':args.replay_one,'status':'passed'}))
if __name__=='__main__':main()
