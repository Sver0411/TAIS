#!/usr/bin/env python3
"""All Phase4 statistics and12 figures from saved structured observations only."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from analyze_ablation import aggregate as original_aggregate,holm
from phase4_support import methods

MAIN=['A5','A7','Robust-T1-U1','Risk-T1-U1']
COLORS={'A5':'#777777','A7':'#cc3311','Robust-T1-U1':'#228833','Risk-T1-U1':'#4477aa'}
ENDPOINTS=['f1','recall','samples','bytes','restricted_delay_s','precoverage','fast_outside','fault_induced_false']


def aggregate(g):
    a=original_aggregate(g);n=a['n_events'];cycles=a['samples']-len(g)
    a.update(precoverage=g.pre_covered_events.sum()/n if n else np.nan,
             finite_event_coverage=g.finite_covered_events.sum()/n if n else np.nan,
             fast_samples=g.fast_samples.sum(),fast_share=g.fast_samples.sum()/cycles if cycles else 0,
             fast_outside=g.fast_samples_outside_events.sum(),fast_window_max=g.fast_window_max.max(),
             fast_bursts_without_truth=g.fast_bursts_without_truth.sum(),
             fast_bursts_without_local_onset=g.fast_bursts_without_local_onset.sum(),
             fast_budget_blocks=g.fast_budget_blocks.sum(),interval_switches=g.interval_switches.sum(),
             first_observation_delay_s=g.first_observation_delay_sum_s.sum()/g.first_observation_delay_n.sum() if g.first_observation_delay_n.sum() else np.nan,
             first_observation_available=g.first_observation_delay_n.sum(),
             mean_interval_s=np.average(g.mean_sampling_interval_s,weights=g.samples-1),
             finite_value_coverage=np.average(g.finite_value_coverage,weights=g.duration_s))
    return a


def seed_table(frame):
    return pd.DataFrame([dict(seed=s,method=m,**aggregate(g)) for (s,m),g in frame.groupby(['seed','method'])])


def contrasts():
    pairs=[]
    for kind in ['Robust','Risk']:
        pairs += [(kind+'-T0-U0','A0'),(kind+'-T1-U0','A1'),(kind+'-T0-U0','A2'),(kind+'-T1-U0','A4'),
                  (kind+'-T1-U1','A5'),(kind+'-T1-U1','A7'),(kind+'-T1-U1',kind+'-T0-U1'),
                  (kind+'-T1-U1',kind+'-T1-U0')]
    return pairs+[('Risk-T1-U1','Robust-T1-U1')]


def inference(seeds,plan):
    rng=np.random.default_rng(plan['bootstrap_seed']);ids=sorted(seeds.seed.unique());n=len(ids)
    draw=rng.integers(0,n,(plan['bootstrap_draws'],n));signs=rng.choice([-1,1],(plan['permutation_draws'],n));out=[]
    for metric in ENDPOINTS:
        pivot=seeds.pivot(index='seed',columns='method',values=metric).loc[ids]
        for a,b in contrasts():
            delta=(pivot[a]-pivot[b]).to_numpy();assert np.isfinite(delta).all(),metric
            lo,hi=np.percentile(delta[draw].mean(axis=1),[2.5,97.5]);point=delta.mean()
            p=(1+np.count_nonzero(abs(signs@delta/n)>=abs(point)-1e-12))/(len(signs)+1)
            out.append(dict(method=a,reference=b,metric=metric,mean_seed_difference=point,ci95_low=lo,ci95_high=hi,p_signflip=p,seeds=n))
    out=pd.DataFrame(out);out['p_holm']=holm(out.p_signflip);out['holm_below_005']=out.p_holm<.05
    return out


def gates(frame,seeds,effects,plan):
    rng=np.random.default_rng(plan['bootstrap_seed']);out=[];noise=seed_table(frame[frame.scenario=='noisy_none'])
    cfg=plan['default_gates'];ids=sorted(seeds.seed.unique());draw=rng.integers(0,len(ids),(plan['bootstrap_draws'],len(ids)))
    def interval(method,reference,metric,ratio=False,table=seeds):
        p=table.pivot(index='seed',columns='method',values=metric).loc[ids];a=p[method].to_numpy();b=p[reference].to_numpy()
        d=a/b if ratio else a-b
        return float(d.mean()),*map(float,np.percentile(d[draw].mean(axis=1),[2.5,97.5]))
    for kind in ['Robust','Risk']:
        method=kind+'-T1-U1';checks=[]
        for metric,ratio,bound,direction,table,ref in [
            ('f1',False,-cfg['f1_margin'],'lower',seeds,'A5'),('receiver_f1',False,-cfg['f1_margin'],'lower',seeds,'A5'),
            ('recall',False,-cfg['recall_margin'],'lower',seeds,'A5'),('samples',True,cfg['sample_ratio_upper'],'upper',seeds,'A5'),
            ('bytes',True,cfg['byte_ratio_upper'],'upper',seeds,'A5'),('fault_induced_false',True,cfg['fi_ratio_upper'],'upper',seeds,'A5'),
            ('finite_age_mean_s',False,cfg['age_difference_upper_s'],'upper',seeds,'A5'),
            ('precoverage',False,-cfg['precoverage_margin'],'lower',seeds,'A5'),
            ('samples',True,cfg['noisy_sample_ratio_upper'],'upper',noise,'A0')]:
            point,lo,hi=interval(method,ref,metric,ratio,table)
            checks.append(dict(method=method,gate=metric+('_ratio' if ratio else '_difference')+('_noisy_none' if ref=='A0' else ''),
                               estimate=point,ci95_low=lo,ci95_high=hi,criterion=bound,direction=direction,
                               passed=lo>=bound if direction=='lower' else hi<=bound))
        effect=effects[(effects.method==method)&(effects.reference=='A7')&(effects.metric=='f1')].iloc[0]
        checks.append(dict(method=method,gate='positive_f1_vs_A7_Holm',estimate=effect.mean_seed_difference,
                           ci95_low=effect.ci95_low,ci95_high=effect.ci95_high,criterion=.05,direction='positive_and_Holm',
                           passed=effect.mean_seed_difference>0 and effect.p_holm<.05))
        actual=frame[frame.method==method]
        checks.append(dict(method=method,gate='all_important_edges_delivered',estimate=actual.important_edges_unreported.sum(),
                           criterion=0,direction='equal',passed=bool(actual.important_edges_unreported.sum()==0)))
        checks.append(dict(method=method,gate='rolling_fast_bound',estimate=actual.fast_window_max.max(),criterion=plan['common']['fast_limit'],
                           direction='upper',passed=bool(actual.fast_window_max.max()<=plan['common']['fast_limit'])))
        qualified=all(bool(c['passed']) for c in checks)
        for c in checks:c['decision']='QUALIFIED_FOR_FURTHER_VALIDATION' if qualified else 'NO_GO_DEFAULT'
        out+=checks
    return pd.DataFrame(out)


def figures(frame,events,forensics,seeds,effects,timelines,out,plan):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18})
    figure_dir=out/'figures';figure_dir.mkdir(exist_ok=True);order=methods(plan)
    palette={m:plt.get_cmap('tab20')(i%20) for i,m in enumerate(order)};palette.update(COLORS)
    subtitle=f'{frame.seed.nunique()} paired seeds ×66 synthetic conditions; deadline120s; seed clusters'
    def save(fig,n,title,detail=subtitle,bottom=0):
        fig.suptitle(title+'\n'+detail,fontsize=12);fig.tight_layout(rect=(0,bottom,1,.92))
        fig.savefig(figure_dir/f'figure{n:02d}.png',dpi=180,metadata={'Software':'TAIS Phase4'})
        fig.savefig(figure_dir/f'figure{n:02d}.pdf',metadata={'CreationDate':None,'ModDate':None});plt.close(fig)
    def boxes(ax,metric,names=MAIN,label=None):
        bp=ax.boxplot([seeds.loc[seeds.method==m,metric] for m in names],tick_labels=names,patch_artist=True)
        for patch,m in zip(bp['boxes'],names):patch.set_facecolor(palette[m]);patch.set_alpha(.6)
        ax.tick_params(axis='x',rotation=35);ax.set_ylabel(label or metric)
    def ci(values):
        values=np.asarray(values);rng=np.random.default_rng(plan['bootstrap_seed'])
        draw=rng.integers(0,len(values),(plan['bootstrap_draws'],len(values)))
        return values.mean(),*np.percentile(values[draw].mean(axis=1),[2.5,97.5])
    for number,x,y,xlabel,ylabel,title in [
        (1,'bytes','f1','Application MB per seed (1MB=10^6 bytes)','Sender F1','F1 vs communication: all24 operating points'),
        (2,'samples','recall','Actual samples per seed','Deadline Recall','Recall vs acquired samples: all24 operating points')]:
        fig,ax=plt.subplots(figsize=(12,7))
        for m in order:
            g=seeds[seeds.method==m];scale=1e6 if x=='bytes' else 1
            ax.scatter(g[x]/scale,g[y],s=8,color=palette[m],alpha=.15)
            ax.scatter(g[x].mean()/scale,g[y].mean(),color=palette[m],marker='o' if m in MAIN else 's',label=m,s=30)
        ax.set(xlabel=xlabel,ylabel=ylabel,ylim=(0,1));ax.legend(bbox_to_anchor=(1.01,1),loc='upper left',fontsize=7,frameon=False)
        save(fig,number,title)
    fig,axes=plt.subplots(3,1,figsize=(12,9),sharex=True)
    t=timelines[(timelines.scenario=='noisy_none')&(timelines.channel=='temperature')]
    for m in MAIN:
        g=t[t.method==m];axes[0].step(g.timestamp,g.interval_s,where='post',color=palette[m],label=m)
        axes[1].step(g.timestamp,g.fast_used,where='post',color=palette[m]);axes[2].step(g.timestamp,np.arange(1,len(g)+1),color=palette[m])
    axes[0].legend(ncol=4);axes[0].set_ylabel('Next interval (s)');axes[1].set_ylabel('Actual fast samples /120s');axes[1].axhline(6,color='black',ls='--')
    axes[2].set(xlabel='Source time (s)',ylabel='Cumulative samples')
    save(fig,3,'High-noise acquisition timeline and actual rolling budget',f'Preselected seed{plan["representative_seed"]}; noisy_none; actual samples only')
    fig,axes=plt.subplots(4,1,figsize=(12,9),sharex=True)
    truth=events[(events.seed==plan['representative_seed'])&(events.scenario=='high_frequency')&(events.method=='A5')&(events.channel=='temperature')&(events.side=='sender')].sort_values('truth_start').iloc[0]
    for ax,m in zip(axes,MAIN):
        g=timelines[(timelines.scenario=='high_frequency')&(timelines.channel=='temperature')&(timelines.method==m)]
        ax.plot(g.timestamp,g.value,'o',ms=3,color=palette[m]);ax.axvspan(truth.truth_start,truth.truth_end,color='grey',alpha=.2)
        ax.set(ylabel=m+'\nTemperature (C)',xlim=(truth.truth_start-80,truth.truth_end+80))
    axes[-1].set_xlabel('Source time (s)');save(fig,4,'Before/after event observation opportunities',f'Preselected seed{plan["representative_seed"]}; first temperature event in high_frequency; grey=truth')
    fig,axes=plt.subplots(1,2,figsize=(12,5));boxes(axes[0],'precoverage',label='Pre-onset sample within20s (fraction)');boxes(axes[1],'finite_event_coverage',label='Event has >=1 finite acquired value (fraction)')
    save(fig,5,'Event observation coverage across whole seeds')
    fig,axes=plt.subplots(1,3,figsize=(15,5));boxes(axes[0],'fast_window_max',label='Maximum fast acquisitions /120s');axes[0].axhline(6,color='black',ls='--')
    boxes(axes[1],'fast_share',label='Fast share of actual intersample gaps');boxes(axes[2],'fast_outside',label='Fast acquired samples outside truth /seed')
    save(fig,6,'Actual high-frequency budget consumption; old methods have no cap')
    fig,axes=plt.subplots(1,2,figsize=(13,6));categories=['A_opportunity','B_detector','C_gate','C_exposure','D_reporting'];base=np.zeros(4)
    for i,c in enumerate(categories):
        values=[len(forensics[(forensics.method==m)&(forensics.miss_category==c)])/frame.seed.nunique() for m in MAIN]
        axes[0].bar(MAIN,values,bottom=base,label=c,color=plt.get_cmap('Set2')(i));base+=values
    axes[0].set_ylabel('Misses per seed (category is diagnostic, not causal proof)');axes[0].legend(fontsize=7)
    boxes(axes[1],'fn',label='All misses per seed');axes[0].tick_params(axis='x',rotation=35)
    save(fig,7,'Miss attribution with uncertainty: C_exposure remains unidentified')
    fig,axes=plt.subplots(1,2,figsize=(12,5));boxes(axes[1],'restricted_delay_s',label='Restricted loss over ALL events (s; miss=120)')
    means=[]
    for m in MAIN:
        means.append(events[(events.method==m)&(events.side=='sender')&events.matched].groupby('seed').delay_s.mean().to_numpy())
    axes[0].boxplot(means,tick_labels=MAIN);axes[0].set_ylabel('Successful-detection mean per seed (s)');axes[0].tick_params(axis='x',rotation=35)
    save(fig,8,'Successful delay and miss-inclusive restricted loss are different')
    fig,axes=plt.subplots(1,2,figsize=(12,5));sweep=frame[frame.cohort=='factor_sweep'].copy();sweep['noise_factor']=sweep.scenario.str.rsplit('_n',n=1).str[-1].astype(float)
    for m in MAIN:
        for ax,metric,label in [(axes[0],'f1','F1'),(axes[1],'samples','Samples per seed over6 conditions')]:
            xx=[];yy=[];lo=[];hi=[]
            for noise,g in sweep[sweep.method==m].groupby('noise_factor'):
                ss=seed_table(g);point,l,h=ci(ss[metric]);xx.append(noise);yy.append(point);lo.append(point-l);hi.append(h-point)
            ax.errorbar(xx,yy,yerr=[lo,hi],fmt='o-',label=m,color=palette[m],capsize=3);ax.set(xlabel='Noise sigma multiplier',ylabel=label,xticks=[1,3])
    axes[0].legend(fontsize=8);save(fig,9,'Balanced noise-level comparison (amplitude/duration crossed)',f'{frame.seed.nunique()} paired seeds; balanced12-case supplement only;95% whole-seed bootstrap')
    fig,axes=plt.subplots(1,2,figsize=(12,6));pairs=[('Fixed20 U','A5','A3'),('Native U','A7','A6'),('Robust U','Robust-T1-U1','Robust-T0-U1'),('Risk U','Risk-T1-U1','Risk-T0-U1')]
    for ax,metric,scale,label in [(axes[0],'f1',100,'Trust F1 difference (pp)'),(axes[1],'fault_induced_false',1,'Trust FI difference per seed')]:
        for i,(name,a,b) in enumerate(pairs):
            pivot=seeds.pivot(index='seed',columns='method',values=metric);d=(pivot[a]-pivot[b])*scale;point,lo,hi=ci(d)
            ax.scatter(d,np.full(len(d),i),s=10,alpha=.25,color='#4477aa');ax.errorbar(point,i,xerr=[[point-lo],[hi-point]],fmt='o',color='black',capsize=3)
        ax.axvline(0,color='black',lw=.8);ax.set(yticks=range(4),yticklabels=[p[0] for p in pairs],xlabel=label)
    save(fig,10,'SensorTrust × sampling interaction; intervals are descriptive')
    fig,ax=plt.subplots(figsize=(10,6))
    for m in order:
        g=seeds[seeds.method==m];ax.scatter(g.bytes/1e6,g.finite_age_mean_s,color=palette[m],s=6,alpha=.15)
        ax.scatter(g.bytes.mean()/1e6,g.finite_age_mean_s.mean(),color=palette[m],label=m)
    ax.set(xlabel='Application MB per seed',ylabel='Mean age of latest finite received value (s)');ax.legend(bbox_to_anchor=(1.01,1),loc='upper left',fontsize=7,frameon=False)
    save(fig,11,'Receiver freshness vs communication: all24 methods')
    fig,ax=plt.subplots(figsize=(12,10));bp=ax.boxplot([seeds.loc[seeds.method==m,'f1'] for m in order],orientation='horizontal',tick_labels=order,patch_artist=True)
    for patch,m in zip(bp['boxes'],order):patch.set_facecolor(palette[m]);patch.set_alpha(.6)
    ax.set(xlabel='Sender F1, each seed micro-aggregated across all66 cases',xlim=(0,1));save(fig,12,'Across-seed performance distributions; all modes retained')


def analyze(root,phase):
    source=root/phase;manifest=json.loads((source/'manifest.json').read_text());assert manifest['status']=='COMPLETE'
    for name,h in manifest['outputs'].items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==h,name
    plan=json.loads((root/'sources/configs/phase4.json').read_text()) if (root/'freeze.json').exists() else json.loads((ROOT/'configs/phase4.json').read_text())
    frame=pd.read_csv(source/'metrics.csv');events=pd.read_csv(source/'events.csv');forensics=pd.read_csv(source/'forensics.csv.gz');timelines=pd.read_csv(source/'timelines.csv')
    if phase=='engineering':
        # Engineering has no prespecified final representative seed. Use the
        # first engineering seed by regenerating its stored trace values only
        # in the runner; final selection remains seed920, never a favorable run.
        if timelines.empty:raise ValueError('Engineering timelines were not stored')
        plan={**plan,'representative_seed':int(timelines.seed.iloc[0])}
    out=source/'analysis';out.mkdir(exist_ok=True);seeds=seed_table(frame);seeds.to_csv(out/'seed_metrics.csv',index=False)
    effects=inference(seeds,plan);effects.to_csv(out/'paired_effects.csv',index=False)
    summary=[]
    for field in ['cohort','fault_kind','scenario']:
        for (group,m),g in frame.groupby([field,'method']):summary.append(dict(group_type=field,group=group,method=m,**aggregate(g)))
    for m,g in frame.groupby('method'):
        row=dict(group_type='overall',group='all',method=m,**aggregate(g));ee=events[(events.method==m)&(events.side=='sender')&events.matched]
        for q,fn in [('mean',np.mean),('median',np.median),('p95',lambda x:np.percentile(x,95))]:row['delay_'+q+'_s']=float(fn(ee.delay_s)) if len(ee) else np.nan
        summary.append(row)
    pd.DataFrame(summary).to_csv(out/'summary.csv',index=False)
    seeds.groupby('method')[ENDPOINTS+['finite_age_mean_s','fast_share','first_observation_delay_s']].agg(['mean','median','std','min','max']).to_csv(out/'distributions.csv')
    gates(frame,seeds,effects,plan).to_csv(out/'default_gates.csv',index=False)
    forensics.groupby(['method','miss_category']).size().rename('events').reset_index().to_csv(out/'miss_causes.csv',index=False)
    figures(frame,events,forensics,seeds,effects,timelines,out,plan)
    outputs={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    (out/'manifest.json').write_text(json.dumps(dict(status='COMPLETE',inputs=manifest['outputs'],analysis_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                                   inference='whole-seed paired bootstrap/sign-flip; Holm across136 prespecified tests; subgroup descriptive',outputs=outputs),indent=2)+'\n')
    print('Analysis complete:',len(frame),'runs;',len(events),'side-specific events;12 figures')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT/'results/phase4');p.add_argument('--phase',choices=['engineering','test'],default='test')
    a=p.parse_args();analyze(a.root,a.phase)
