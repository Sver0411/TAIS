"""Never pool controlled exposure with the original distribution. All points/CIs."""
import sys,argparse,json
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
import pandas as pd
import numpy as np
from tais import ROOT
from tais_rearm.config import load
from summarize_results import aggregate
from v02_summarize import classify,groups
from rearm_plot import tradeoffs
METRICS=['recall','missed','samples','uploads','payload_bytes','fault_induced_false','false_reports','false_per_hour','latency_mean_s','fault_detection_rate','fault_latency_mean_s','confirmation_samples','diagnostic_only_samples']

def paired(df,spec):
 rng=np.random.default_rng(spec['bootstrap_seed']);out=[];absolute=[]
 for group,sub in groups(df):
  seed=aggregate(sub,['seed','method','multiplier'])
  for mult in spec['threshold_multipliers']:
   target=seed[(seed.method=='V02-Rearm')&(seed.multiplier==mult)].set_index('seed')
   for ref in ['AdaptiveSense','TAIS','V02','V02-Passive']:
    base=seed[(seed.method==ref)&(seed.multiplier==(1 if ref=='AdaptiveSense' else mult))].set_index('seed')
    for metric in METRICS:
     delta=(target[metric]-base[metric]).dropna().to_numpy()
     if not len(delta):continue
     bootstrap=delta[rng.integers(len(delta),size=(spec['bootstrap_replicates'],len(delta)))].mean(axis=1)
     lo,hi=np.quantile(bootstrap,[.025,.975]);out.append(dict(group=group,multiplier=mult,reference=ref,metric=metric,mean_difference=delta.mean(),ci_low=lo,ci_high=hi,seeds=len(delta)))
  for (method,mult),g in seed.groupby(['method','multiplier']):
   for metric in ['recall','uploads','samples','payload_bytes','fault_induced_false','false_reports']:
    values=g[metric].dropna().to_numpy()
    if not len(values):continue
    b=values[rng.integers(len(values),size=(spec['bootstrap_replicates'],len(values)))].mean(axis=1);lo,hi=np.quantile(b,[.025,.975])
    absolute.append(dict(group=group,method=method,multiplier=mult,metric=metric,mean=values.mean(),ci_low=lo,ci_high=hi))
 return pd.DataFrame(out),pd.DataFrame(absolute)

def main():
 p=argparse.ArgumentParser();p.add_argument('--split',required=True);a=p.parse_args();_,spec=load();dest=ROOT/f'results/blocked-rearm/{a.split}'
 df=classify(pd.read_csv(dest/'metrics.csv'));ev=pd.read_csv(dest/'events.csv');keys=['suite','seed','scenario','multiplier','event_id']
 fixed=ev[ev.method=='V02-Rearm'].set_index(keys);base=ev[ev.method=='V02'].set_index(keys)
 changes=fixed[fixed.matched!=base.matched].copy();changes['unfixed_matched']=base.loc[changes.index,'matched'];changes['unfixed_report_s']=base.loc[changes.index,'report_s'];changes.reset_index().to_csv(dest/'changed_events.csv',index=False)
 for suite,sub in df.groupby('suite'):
  out=dest/suite;out.mkdir(exist_ok=True)
  for k,name in [(['method','multiplier'],'summary'),(['relationship','method','multiplier'],'by_relationship'),(['scenario','method','multiplier'],'by_scenario'),(['fault_type','method','multiplier'],'by_fault_type'),(['profile','method','multiplier'],'by_profile'),(['information_class','method','multiplier'],'by_information_class')]:aggregate(sub,k).to_csv(out/(name+'.csv'),index=False)
  ci,absolute=paired(sub,spec);ci.to_csv(out/'paired_bootstrap.csv',index=False);absolute.to_csv(out/'confidence_intervals.csv',index=False)
  tradeoffs(sub,out,suite)
  print(suite);print(aggregate(sub,['method','multiplier'])[['method','multiplier','tp','n_events','recall','fault_induced_false','false_reports','samples','uploads','payload_bytes']].to_string(index=False))
if __name__=='__main__':main()
