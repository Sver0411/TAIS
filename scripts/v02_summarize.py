"""All operating points, descriptive seed-paired CIs and two tradeoff figures."""
import sys,argparse,json
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
from tais import ROOT
from tais_v02.config import load
from summarize_results import aggregate
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def classify(df):
    df=df.copy()
    clean=df.scenario.str.startswith('clean_')
    sequential=df.scenario.str.startswith('spike_')&df.relationship.isin(['same','cross'])
    df.loc[sequential,'relationship']=df.loc[sequential,'relationship']+'_sequential'
    df.loc[clean,'relationship']='clean'
    df['fault_type']=df.scenario.str.replace(r'_(none|cross|same)_(short|long)$','',regex=True)
    df.loc[clean,'fault_type']='clean'
    df['information_class']='other'
    same=df.relationship=='same'
    erased=df.fault_type.isin(['range','missing','invalid','stuck'])
    df.loc[same&erased,'information_class']='same_erased'
    df.loc[same&~erased,'information_class']='same_additive'
    return df

def groups(df):
    yield 'all',df
    for k in ['relationship','fault_type','profile','information_class']:
        for name,g in df.groupby(k):
            if k=='information_class' and name=='other':continue
            yield k+':'+name,g

def paired(df,spec):
    rng=np.random.default_rng(spec['bootstrap_seed']);out=[];absolute=[]
    metrics=['recall','samples','uploads','payload_bytes','fault_induced_false','false_reports','false_per_hour','latency_mean_s',
             'fault_detection_rate','fault_latency_mean_s','confirmation_samples','diagnostic_only_samples',
             'sample_mae_temperature','sample_rmse_temperature','sample_mae_humidity','sample_rmse_humidity',
             'upload_mae_temperature','upload_rmse_temperature','upload_mae_humidity','upload_rmse_humidity']
    for group,sub in groups(df):
        a=aggregate(sub,['seed','method','multiplier'])
        for mult in spec['threshold_multipliers']:
            target=a[(a.method=='V02')&(a.multiplier==mult)].set_index('seed')
            for reference in ['AdaptiveSense','GateOnly','TAIS','V02-Passive']:
                ref=a[(a.method==reference)&(a.multiplier==(1 if reference=='AdaptiveSense' else mult))].set_index('seed')
                for metric in metrics:
                    delta=(target[metric]-ref[metric]).dropna().to_numpy()
                    if not len(delta):continue
                    boot=delta[rng.integers(len(delta),size=(spec['bootstrap_replicates'],len(delta)))].mean(axis=1)
                    lo,hi=np.quantile(boot,[.025,.975])
                    out.append(dict(group=group,multiplier=mult,reference=reference,metric=metric,
                                    mean_difference=delta.mean(),ci_low=lo,ci_high=hi,seeds=len(delta)))
        for (method,mult),g in a.groupby(['method','multiplier']):
            for metric in ['recall','uploads','samples','fault_induced_false']:
                values=g[metric].dropna().to_numpy()
                if not len(values):continue
                boot=values[rng.integers(len(values),size=(spec['bootstrap_replicates'],len(values)))].mean(axis=1)
                lo,hi=np.quantile(boot,[.025,.975])
                absolute.append(dict(group=group,method=method,multiplier=mult,metric=metric,mean=values.mean(),ci_low=lo,ci_high=hi))
    return pd.DataFrame(out),pd.DataFrame(absolute)

def figures(df,dest):
    for kind in ['recall_uploads','faultfalse_recall']:
        fig,axes=plt.subplots(2,3,figsize=(16,9),constrained_layout=True)
        for column,relation in enumerate(['all','cross','same']):
            sub=df if relation=='all' else df[df.relationship==relation]
            if sub.empty:
                for ax in axes[:,column]:ax.set_axis_off()
                continue
            summary=aggregate(sub,['method','multiplier'])
            for row in [0,1]:
                ax=axes[row,column]
                for i,(method,g) in enumerate(summary.groupby('method')):
                    g=g.sort_values('multiplier');x=g.uploads_per_run if kind=='recall_uploads' else g.recall*100
                    y=g.recall*100 if kind=='recall_uploads' else g.fault_induced_false/(g.duration_s/1800)
                    ax.plot(x,y,marker=['o','s','^','d','v','x','+','*','p','h','<'][i],linestyle='-' if len(g)>1 else '',label=method)
                    if row==1 and len(g)>1:
                        for xx,yy,m in zip(x,y,g.multiplier):ax.annotate(f'{m:g}',(xx,yy),fontsize=7,xytext=(3,4),textcoords='offset points')
                if row==1 and kind=='recall_uploads':
                    v=summary[~summary.method.str.startswith('Fixed-')].uploads_per_run
                    margin=max(2,(v.max()-v.min())*.15);ax.set_xlim(v.min()-margin,v.max()+margin)
                if row==1 and kind=='faultfalse_recall':
                    # Zoom to policy recall range; full row above retains every baseline.
                    v=summary[~summary.method.str.startswith('Fixed-')].recall*100
                    margin=max(2,(v.max()-v.min())*.15);ax.set_xlim(v.min()-margin,v.max()+margin)
                ax.set_title(relation+(' / policy zoom' if row else ' / all points'))
                ax.set_xlabel('Uploads / 30-min run' if kind=='recall_uploads' else 'Reported event recall (%)')
                ax.set_ylabel('Reported event recall (%)' if kind=='recall_uploads' else 'Fault false reports / 30-min run')
                ax.grid(alpha=.25)
        fig.legend(*axes[0,0].get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.5,-.05),ncol=6,fontsize=9)
        fig.savefig(dest/(kind+'.png'),dpi=150,bbox_inches='tight');plt.close(fig)

def main():
    p=argparse.ArgumentParser();p.add_argument('--split',required=True);a=p.parse_args();_,spec=load()
    dest=ROOT/'results/v0.2'/a.split;df=classify(pd.read_csv(dest/'metrics.csv'))
    for keys,name in [(['method','multiplier'],'summary'),(['relationship','method','multiplier'],'by_relationship'),
                      (['scenario','method','multiplier'],'by_scenario'),(['fault_type','method','multiplier'],'by_fault_type'),
                      (['profile','method','multiplier'],'by_profile'),(['information_class','method','multiplier'],'by_information_class')]:
        aggregate(df,keys).to_csv(dest/(name+'.csv'),index=False)
    ci,absolute=paired(df,spec);ci.to_csv(dest/'paired_bootstrap.csv',index=False);absolute.to_csv(dest/'confidence_intervals.csv',index=False)
    figures(df,dest)
    print(aggregate(df,['method','multiplier'])[['method','multiplier','recall','tp','missed','fault_induced_false','false_reports','samples','uploads','payload_bytes']].to_string(index=False))
if __name__=='__main__':main()
