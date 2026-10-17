"""Deterministic full seed matrix; raw trace/labels and sampled decisions retained."""
import argparse,csv,gzip,hashlib,json,math,platform,subprocess,sys
from copy import copy
from dataclasses import asdict
from pathlib import Path
from tais import ROOT
from tais.config import load
from tais.signals import generate,scenarios
from tais.replay import run
from tais.metrics import evaluate


def canonical(value):
    # Canonical gzip (mtime=0) makes archived trace hashes reproducible.
    def clean(v):
        if hasattr(v,'__dataclass_fields__'):return clean(asdict(v))
        if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
        if isinstance(v,(list,tuple)):return [clean(x) for x in v]
        if isinstance(v,float) and not math.isfinite(v):return None
        return v
    return json.dumps(clean(value),sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def save(path,value):
    data=gzip.compress(canonical(value),mtime=0);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--split',choices=['development','validation','test'],required=True)
    p.add_argument('--smoke',action='store_true');args=p.parse_args()
    cfg=load();key={'development':'development_seeds','validation':'validation_seeds','test':'held_out_test_seeds'}[args.split]
    seeds=cfg['evaluation'][key];cases=scenarios()
    if args.smoke:seeds=seeds[:1];cases=['clean_none','range_cross_long','spike_same_short']
    label=args.split+('-smoke' if args.smoke else '')
    dest=ROOT/'results'/label;dest.mkdir(exist_ok=True)
    archive=ROOT/'results/traces'/label
    manifest={'split':label,'seeds':seeds,'scenarios':cases,'command':sys.argv,'python':sys.version,'platform':platform.platform(),
              'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'config_sha256':hashlib.sha256((ROOT/'configs/experiment.yaml').read_bytes()).hexdigest(),'artifacts':{},'runs':0}
    # Counterfactual cache per seed/relationship/profile/method: same latent/noise.
    all_metrics=[]
    for seed in seeds:
        counterfactuals={}
        for case in cases:
            trace=generate(cfg,seed,case)
            relative=f'{seed}/{case}/signals.json.gz'
            manifest['artifacts'][relative]=save(archive/relative,asdict(trace))
            for method in cfg['evaluation']['methods']:
                scales=cfg['evaluation']['threshold_multipliers'] if method in ['TAIS','GateOnly'] else [1.0]
                for scale in scales:
                    result=run(trace,cfg,method,scale)
                    cache_key=(trace.relationship,trace.profile,method,scale)
                    if cache_key not in counterfactuals:
                        clean=copy(trace);clean.observed=trace.noisy;clean.faults=[]
                        counterfactuals[cache_key]=run(clean,cfg,method,scale)
                    row=evaluate(trace,result,cfg,counterfactuals[cache_key])
                    row={'seed':seed,'scenario':case,'relationship':trace.relationship,'profile':trace.profile,'method':method,'multiplier':scale,**row}
                    all_metrics.append(row)
                    relative=f'{seed}/{case}/{method}-{scale:g}.json.gz'
                    manifest['artifacts'][relative]=save(archive/relative,result);manifest['runs']+=1
        print(label,'seed',seed,'runs',len(all_metrics),flush=True)
    path=dest/'metrics.csv'
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(all_metrics[0]));w.writeheader();w.writerows(all_metrics)
    manifest['metrics_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Saved',path,'runs',len(all_metrics),flush=True)
if __name__=='__main__':main()
