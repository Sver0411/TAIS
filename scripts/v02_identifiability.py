"""Offline equality proof for event-erasing interventions, across all old seeds."""
import sys,json,gzip
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
from tais import ROOT
from tais.config import load
from tais.signals import generate
from run_experiments import canonical
import pandas as pd
cfg=load();pairs=[]
for seed in range(50):
 for kind in ['range','missing','invalid','stuck']:
  for profile in ['short','long']:
   a=generate(cfg,seed,f'{kind}_same_{profile}');b=generate(cfg,seed,f'{kind}_none_{profile}')
   assert canonical(a.observed)==canonical(b.observed)
   pairs.append(dict(seed=seed,kind=kind,profile=profile,observations_equal=True,events_same=len(a.events),events_none=len(b.events)))
summary=[]
for split in ['development','validation','test']:
 d=pd.read_csv(ROOT/f'results/{split}/metrics.csv');d=d[(d.multiplier==1)&d.method.isin(['AdaptiveSense','GateOnly','TAIS'])]
 s=d[(d.relationship=='same') & ~d.scenario.str.startswith(('clean_','spike_'))].copy()
 s['erased']=s.scenario.str.startswith(('range_','missing_','invalid_','stuck_'))
 for (method,erased),g in s.groupby(['method','erased']):summary.append(dict(split=split,method=method,erased=bool(erased),tp=int(g.tp.sum()),events=int(g.n_events.sum())))
# A matched report under range has identical timestamp in event-free trace.
matched=0
from simulator.events import match_events
for seed in range(20,50):
 for profile in ['short','long']:
  a=json.loads(gzip.decompress((ROOT/f'results/traces/test/{seed}/range_same_{profile}/AdaptiveSense-1.json.gz').read_bytes()))
  b=json.loads(gzip.decompress((ROOT/f'results/traces/test/{seed}/range_none_{profile}/AdaptiveSense-1.json.gz').read_bytes()))
  assert canonical(a)==canonical(b)
  tr=generate(cfg,seed,f'range_same_{profile}')
  from simulator.events import Event
  matched+=match_events(tr.events,[Event(**e) for e in a['reports']],5).true_positives
out=dict(pairs=pairs,old_split_same_channel_breakdown=summary,range_same_artifact_matches=matched,
 note='Equality concerns observed streams; latent signals and truth differ. Matcher TP alone does not establish event sensitivity.')
(ROOT/'results/v0.2/forensics/identifiability.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='pairs'},indent=2))
