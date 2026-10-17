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
    for relation in ['all','clean','none','cross','same','cross_sequential','same_sequential']:
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
        for mult in cfg['evaluation']['threshold_multipliers']:
            a=seed[(seed.method=='TAIS')&(seed.multiplier==mult)].set_index('seed')
            b=seed[(seed.method=='GateOnly')&(seed.multiplier==mult)].set_index('seed')
            for metric in ['recall','uploads','samples','fault_induced_false','false_reports']:
                delta=(a[metric]-b[metric]).dropna().to_numpy()
                if not len(delta):continue
                boot=delta[rng.integers(0,len(delta),size=(cfg['evaluation']['bootstrap_replicates'],len(delta)))].mean(axis=1)
                low,high=np.quantile(boot,[.025,.975])
                output.append(dict(relationship=relation,method='TAIS-minus-GateOnly',multiplier=mult,metric=metric,paired_mean_difference=delta.mean(),ci_low=low,ci_high=high,seeds=len(delta)))
    return pd.DataFrame(output)

def main():
    p=argparse.ArgumentParser();p.add_argument('--split',required=True);args=p.parse_args();cfg=load()
    dest=ROOT/'results'/args.split;df=pd.read_csv(dest/'metrics.csv')
    # Separate true temporal overlap from clean controls and sequential spike cases.
    clean=df.scenario.str.startswith('clean_')
    sequential=df.scenario.str.startswith('spike_') & df.relationship.isin(['cross','same'])
    df.loc[sequential,'relationship']=df.loc[sequential,'relationship']+'_sequential'
    df.loc[clean,'relationship']='clean'
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
    fig,axes=plt.subplots(2,3,figsize=(14,8),constrained_layout=True)
    byrel=aggregate(df,['relationship','method','multiplier'])
    markers={'AdaptiveSense':'s','AdaptiveSense+TrustLog':'+','GateOnly':'o','TAIS':'^'}
    for column,relation in enumerate(['all','cross','same']):
        sub=summary if relation=='all' else byrel[byrel.relationship==relation]
        for row in [0,1]:
            ax=axes[row,column]
            for method,g in sub.groupby('method'):
                ax.plot(g.uploads_per_run,g.recall*100,marker=markers.get(method,'d'),linestyle='-' if len(g)>1 else '',label=method,markersize=6,alpha=.85)
                if row==1:
                    for _,r in g.iterrows():
                        if len(g)>1:ax.annotate(f'{r.multiplier:g}',(r.uploads_per_run,r.recall*100),fontsize=7,xytext=(3,7 if method=='TAIS' else -10),textcoords='offset points')
            if row==1:
                policies=sub[~sub.method.str.startswith('Fixed-')].uploads_per_run
                low,high=policies.min(),policies.max();margin=max(2,(high-low)*.2)
                ax.set_xlim(low-margin,high+margin)
            title=('All scenarios' if relation=='all' else relation.capitalize()+'-channel temporal overlap')
            ax.set(title=title+(' (policy zoom)' if row else ''),xlabel='Application upload requests / 30-min run',ylabel='Reported event recall (%)',ylim=(-3,103));ax.grid(alpha=.2)
    fig.legend(*axes[0,0].get_legend_handles_labels(),fontsize=9,loc='lower center',bbox_to_anchor=(.5,-.05),ncol=5)
    fig.savefig(dest/'tradeoff.png',dpi=160,bbox_inches='tight');plt.close(fig)
    # Compare actual closest upload budgets; no interpolation or selected favorable point.
    budget=[]
    for _,r in summary[summary.method.isin(['TAIS','GateOnly'])].iterrows():
        other=summary[summary.method.str.startswith('Fixed-') | (summary.method=='AdaptiveSense')]
        nearest=other.iloc[(other.uploads_per_run-r.uploads_per_run).abs().argsort().iloc[0]]
        budget.append(dict(method=r.method,multiplier=r.multiplier,uploads=r.uploads_per_run,recall=r.recall,nearest_baseline=nearest.method,baseline_uploads=nearest.uploads_per_run,baseline_recall=nearest.recall,relative_budget_gap=abs(nearest.uploads_per_run-r.uploads_per_run)/r.uploads_per_run))
    pd.DataFrame(budget).to_csv(dest/'budget_comparison.csv',index=False)
    print(summary[['method','multiplier','recall','tp','missed','false_reports','fault_induced_false','samples','uploads']].to_string(index=False))
if __name__=='__main__':main()
