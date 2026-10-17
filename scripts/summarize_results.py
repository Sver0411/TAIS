"""Micro counts; seed-cluster paired bootstrap; all operating points plotted."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from tais import ROOT
from tais.config import load

COUNTS=['n_events','tp','missed','local_tp','false_reports','redundant_reports','fault_induced_false','fault_associated_false','samples','uploads','payload_bytes','fault_episodes','fault_detected','fault_type_detected','confirmation_samples','diagnostic_samples','diagnostic_only_samples','duration_s','latency_sum_s','latency_n','fault_latency_sum_s']

def aggregate(df,keys):
    counts=df.groupby(keys,dropna=False)[COUNTS].sum()
    means=df.groupby(keys,dropna=False)[[c for c in df if '_mae_' in c or '_rmse_' in c]].mean()
    a=counts.join(means).reset_index()
    a['recall']=a.tp/a.n_events.replace(0,np.nan)
    a['fault_detection_rate']=a.fault_detected/a.fault_episodes.replace(0,np.nan)
    a['latency_mean_s']=a.latency_sum_s/a.latency_n.replace(0,np.nan)
    a['fault_latency_mean_s']=a.fault_latency_sum_s/a.fault_detected.replace(0,np.nan)
    a['false_per_hour']=a.false_reports/a.duration_s*3600
    a['uploads_per_run']=a.uploads/df.groupby(keys).size().values
    return a

def paired(df,cfg):
    output=[];rng=np.random.default_rng(cfg['evaluation']['bootstrap_seed'])
    for relation in ['all','none','cross','same']:
        sub=df if relation=='all' else df[df.relationship==relation]
        seed=aggregate(sub,['seed','method','multiplier'])
        ref=seed[(seed.method=='AdaptiveSense')&(seed.multiplier==1)].set_index('seed')
        for method in ['TAIS','GateOnly']:
            for mult in cfg['evaluation']['threshold_multipliers']:
                target=seed[(seed.method==method)&(seed.multiplier==mult)].set_index('seed')
                for metric in ['recall','uploads','samples','fault_induced_false','false_reports']:
                    a=target[metric]-ref[metric];a=a.dropna().to_numpy()
                    if not len(a):continue
                    boot=a[rng.integers(0,len(a),size=(cfg['evaluation']['bootstrap_replicates'],len(a)))].mean(axis=1)
                    low,high=np.quantile(boot,[.025,.975])
                    output.append(dict(relationship=relation,method=method,multiplier=mult,metric=metric,paired_mean_difference=a.mean(),ci_low=low,ci_high=high,seeds=len(a)))
    return pd.DataFrame(output)

def main():
    p=argparse.ArgumentParser();p.add_argument('--split',required=True);args=p.parse_args();cfg=load()
    dest=ROOT/'results'/args.split;df=pd.read_csv(dest/'metrics.csv')
    summary=aggregate(df,['method','multiplier']);summary.to_csv(dest/'summary.csv',index=False)
    aggregate(df,['relationship','method','multiplier']).to_csv(dest/'by_relationship.csv',index=False)
    aggregate(df,['scenario','method','multiplier']).to_csv(dest/'by_scenario.csv',index=False)
    paired(df,cfg).to_csv(dest/'paired_bootstrap.csv',index=False)
    # Absolute CIs, cluster bootstrap over whole seeds, preserving scenario correlations.
    rng=np.random.default_rng(cfg['evaluation']['bootstrap_seed']);cis=[]
    for (method,mult),group in df.groupby(['method','multiplier']):
        s=group.groupby('seed')[['tp','n_events','uploads']].sum().to_numpy();index=rng.integers(0,len(s),size=(cfg['evaluation']['bootstrap_replicates'],len(s)))
        boot=s[index].sum(axis=1)
        for metric,values in [('recall',boot[:,0]/boot[:,1]),('uploads_per_seed',boot[:,2]/len(s))]:
            low,high=np.quantile(values,[.025,.975]);cis.append(dict(method=method,multiplier=mult,metric=metric,ci_low=low,ci_high=high))
    pd.DataFrame(cis).to_csv(dest/'confidence_intervals.csv',index=False)
    fig,axes=plt.subplots(1,3,figsize=(14,4),constrained_layout=True)
    byrel=aggregate(df,['relationship','method','multiplier'])
    for ax,relation in zip(axes,['all','cross','same']):
        sub=summary if relation=='all' else byrel[byrel.relationship==relation]
        for method,g in sub.groupby('method'):
            ax.plot(g.uploads_per_run,g.recall*100,'o-' if len(g)>1 else 'o',label=method)
            for _,r in g.iterrows():
                if len(g)>1:ax.annotate(f'{r.multiplier:g}',(r.uploads_per_run,r.recall*100),fontsize=7,xytext=(3,4),textcoords='offset points')
        ax.set(title=relation+' scenarios',xlabel='Application upload requests / 30-min run',ylabel='Reported event recall (%)',ylim=(-3,103));ax.grid(alpha=.2)
    axes[-1].legend(fontsize=7,loc='lower right');fig.savefig(dest/'tradeoff.png',dpi=160);plt.close(fig)
    # Compare actual closest upload budgets; no interpolation or selected favorable point.
    budget=[]
    for _,r in summary[summary.method.isin(['TAIS','GateOnly'])].iterrows():
        other=summary[summary.method.str.startswith('Fixed-') | (summary.method=='AdaptiveSense')]
        nearest=other.iloc[(other.uploads_per_run-r.uploads_per_run).abs().argsort().iloc[0]]
        budget.append(dict(method=r.method,multiplier=r.multiplier,uploads=r.uploads_per_run,recall=r.recall,nearest_baseline=nearest.method,baseline_uploads=nearest.uploads_per_run,baseline_recall=nearest.recall,relative_budget_gap=abs(nearest.uploads_per_run-r.uploads_per_run)/r.uploads_per_run))
    pd.DataFrame(budget).to_csv(dest/'budget_comparison.csv',index=False)
    print(summary[['method','multiplier','recall','tp','missed','false_reports','fault_induced_false','samples','uploads']].to_string(index=False))
if __name__=='__main__':main()
