#!/usr/bin/env python3
"""Static research figures from actual G1/G2 outputs and declared example seeds."""
import gzip,json,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from benchmark_transfer import OUT,RAW,plan
from tais.config import load
from tais.signals import generate as g1_generate
from tais.transfer_signals import generate as g2_generate
from benchmark_joint_optimization import sha
SHORT={'AdaptiveSense+TrustLog':'AS+Trust','GateOnly':'Gate','GateOnly+U':'Gate+U','JO-SU-20':'SU20','JO-SU-40':'SU40','Delta-budget-SU40+C11':'Delta-B','Variance-budget-SU40+C11':'Var-B','Rao-inspired-budget-SU40+C11':'Rao-B'}
def label(m):return SHORT.get(m,m.replace('+C11',''))
def main():
    out=OUT/'figures';out.mkdir(exist_ok=True);p=plan();d=pd.read_csv(OUT/'summary.csv').set_index('method');old=pd.read_csv(ROOT/'results/tais-paper/summary.csv');old=old[old['view']=='native'].set_index('method');methods=list(d.index)
    plt.rcParams.update({'font.size':9,'axes.titlesize':11,'axes.labelsize':10,'legend.fontsize':8,'savefig.dpi':200})
    fig,axes=plt.subplots(1,2,figsize=(11,6.4),sharey=True)
    for ax,src,title in zip(axes,[old,d],['G1: original mechanism','G2: frozen transfer test']):
        y=np.arange(len(methods));ax.scatter(src.loc[methods,'recall']*100,y,marker='o',label='Recall');ax.scatter(src.loc[methods,'f1']*100,y,marker='s',label='F1');ax.set_yticks(y,[label(m) for m in methods]);ax.set_xlim(0,100);ax.set_xlabel('Sender (%)');ax.set_title(title);ax.grid(axis='x',alpha=.2);ax.legend(loc='lower right')
    axes[0].invert_yaxis();fig.tight_layout();fig.savefig(out/'quality_comparison.png');plt.close(fig)
    fixed=[m for m in methods if m.startswith('Fixed-')];selected=[m for m in methods if m not in fixed]
    fig,axes=plt.subplots(2,2,figsize=(11,8));pairs=[('samples','recall'),('samples','f1'),('binary_v1_bytes','f1'),('samples','fault_induced_false')]
    colors=plt.cm.tab10(np.linspace(0,1,len(selected)))
    for ax,(x,y) in zip(axes.flat,pairs):
        for method,color in zip(selected,colors):
            r=d.loc[method];scale=100 if y in ('recall','f1') else 1;ax.scatter(r[x],r[y]*scale,label=label(method),c=[color],s=55,marker='*' if method=='JO-SU-40' else 'o')
        for method in fixed:
            r=d.loc[method];ax.scatter(r[x],r[y]*(100 if y in ('recall','f1') else 1),c='#666666',s=24,marker='x');ax.annotate(method.split('-')[1].split('+')[0],(r[x],r[y]*(100 if y in ('recall','f1') else 1)),fontsize=7,xytext=(3,3),textcoords='offset points')
        ax.set_xlabel('Total actual '+('sample cycles' if x=='samples' else 'Binary v1 bytes'));ax.set_ylabel({'recall':'Recall (%)','f1':'F1 (%)','fault_induced_false':'Fault-induced false reports'}[y]);ax.grid(alpha=.2);ax.ticklabel_format(axis='x',style='sci',scilimits=(0,0))
    axes[0,0].legend(ncol=2,fontsize=7);fig.suptitle('G2: discrete frozen operating points; fixed periods labeled in seconds');fig.tight_layout();fig.savefig(out/'tradeoffs.png');plt.close(fig)
    # Separate publication panels, preserving every point and label.
    for x,y,name in [('samples','recall','samples_recall'),('samples','f1','samples_f1'),('binary_v1_bytes','f1','bytes_f1')]:
        fig,ax=plt.subplots(figsize=(8,5))
        for method,color in zip(selected,colors):
            r=d.loc[method];ax.scatter(r[x],100*r[y],label=label(method),c=[color],s=65,marker='*' if method=='JO-SU-40' else 'o')
        for method in fixed:
            r=d.loc[method];ax.scatter(r[x],100*r[y],c='#777777',marker='x');ax.annotate(label(method),(r[x],100*r[y]),fontsize=7,xytext=(3,3),textcoords='offset points')
        ax.set_xlabel('Total actual '+('sample cycles' if x=='samples' else 'Binary v1 bytes'));ax.set_ylabel(y.title()+' (%)');ax.legend(ncol=2);ax.grid(alpha=.2);ax.ticklabel_format(axis='x',style='sci',scilimits=(0,0));fig.tight_layout();fig.savefig(out/(name+'.png'));plt.close(fig)
    summary=pd.read_csv(OUT/'test/analysis/summary.csv');faults=['range','spike','stuck','drift','missing','invalid','stable_offset'];sel=['AdaptiveSense+TrustLog','GateOnly','JO-SU-20','JO-SU-40','Variance-budget-SU40+C11','Rao-inspired-budget-SU40+C11']
    fig,axes=plt.subplots(1,2,figsize=(11,4.8),sharey=True)
    oldgroups=pd.read_csv(ROOT/'results/tais-paper/test/analysis/summary.csv');oldgroups=oldgroups[oldgroups['view']=='native']
    for ax,src,title in zip(axes,[oldgroups,summary],['G1','G2']):
        for i,m in enumerate(sel):
            sub=src[(src.method==m)&src.group.isin(['fault:'+f for f in faults])].set_index('group');vals=[sub.loc['fault:'+f,'fault_induced_false']/sub.loc['fault:'+f,'runs'] for f in faults]
            ax.bar(np.arange(7)+(i-2.5)*.13,vals,width=.13,label=label(m))
        ax.set_xticks(range(7),['range','spike','stuck','drift','missing','invalid','offset'],rotation=35);ax.set_title(title);ax.set_ylabel('Fault-induced reports / run');ax.grid(axis='y',alpha=.2)
    axes[1].legend(fontsize=7,ncol=2);fig.tight_layout();fig.savefig(out/'fault_false_reports.png');plt.close(fig)
    ev=pd.read_csv(OUT/'test/analysis/events_grouped.csv');bins=['12-20','21-40','41-60','61-100','101-160','161-240'];fig,axes=plt.subplots(1,2,figsize=(11,4.7),gridspec_kw={'width_ratios':[1,2]})
    for i,m in enumerate(sel):
        orig=oldgroups[(oldgroups.method==m)&oldgroups.group.isin(['profile:short','profile:long'])].set_index('group');axes[0].scatter([26,180],[orig.loc['profile:short','recall']*100,orig.loc['profile:long','recall']*100],label=label(m),marker=['o','s','^','*','D','v'][i])
        sub=ev[(ev.method==m)&ev.group.str.startswith('actual_duration:')].set_index('group');vals=[sub.loc['actual_duration:'+b,'recall']*100 for b in bins];axes[1].scatter(np.arange(6)+(i-2.5)*.09,vals,label=label(m),marker=['o','s','^','*','D','v'][i])
    axes[0].set_xticks([26,180]);axes[0].set_xlabel('G1 injected support (s)');axes[1].set_xticks(range(6),bins,rotation=20);axes[1].set_xlabel('G2 actual injected duration (s), discrete bins')
    for ax in axes:ax.set_ylabel('Sender Recall (%)');ax.set_ylim(0,100);ax.grid(alpha=.2)
    axes[1].legend(fontsize=7,ncol=2);fig.tight_layout();fig.savefig(out/'duration_recall.png');plt.close(fig)
    example=p['example'];traces=[g1_generate(load(),example['g1_seed'],example['g1_scenario']),g2_generate(p,example['g2_seed'],example['g2_scenario'])]
    fig,axes=plt.subplots(2,2,figsize=(12,6.4),sharex=True)
    for col,(trace,title) in enumerate(zip(traces,['G1: seed610, drift_same_long','G2: seed700, drift_temperature_same'])):
        for i,c in enumerate(['temperature','humidity']):
            ax=axes[i,col];ax.plot([r['timestamp'] for r in trace.latent],[r[c] for r in trace.latent],label='latent',lw=1.2);ax.plot([r['timestamp'] for r in trace.observed],[r[c] if r[c] is not None else np.nan for r in trace.observed],label='observed',alpha=.6,lw=.7)
            for e in trace.events:
                if e.channel==c:ax.axvspan(e.start_s,e.end_s,color='#009e73',alpha=.15)
            for f in trace.faults:
                if f.channel==c:ax.axvspan(f.start_s,f.end_s,color='#d55e00',alpha=.12)
            ax.set_ylabel('Temperature (C)' if i==0 else 'Humidity (%RH)');ax.grid(alpha=.15)
            if i==0:ax.set_title(title)
            else:ax.set_xlabel('Source time (s)')
    axes[0,0].legend();fig.suptitle('Predeclared illustrative inputs: green=event scoring window; red=fault support');fig.tight_layout();fig.savefig(out/'generator_traces.png');plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(11,4.8),sharex=True)
    for ax,tr,title in zip(axes,traces,['G1 example','G2 example']):
        for j,c in enumerate(['temperature','humidity']):
            ax.broken_barh([(e.start_s,e.end_s-e.start_s+1) for e in tr.events if e.channel==c],(j-.15,.3),facecolors='#009e73',label='event' if j==0 else None)
            ax.broken_barh([(f.start_s,f.end_s-f.start_s) for f in tr.faults if f.channel==c],(j+.2,.2),facecolors='#d55e00',label='fault' if j==0 else None)
        ax.set_yticks([0,1],['temperature','humidity']);ax.set_title(title);ax.set_xlim(0,1800);ax.grid(axis='x',alpha=.2)
    axes[0].legend(ncol=2,loc='upper right');axes[1].set_xlabel('Source time (s); event and fault positions independently drawn in G2');fig.tight_layout();fig.savefig(out/'fault_timelines.png');plt.close(fig)
    sources=['results/tais-transfer/summary.csv','results/tais-transfer/test/analysis/summary.csv','results/tais-transfer/test/analysis/events_grouped.csv','results/tais-paper/summary.csv','results/tais-paper/test/analysis/summary.csv','configs/tais-transfer.json','src/tais/transfer_signals.py','src/tais/signals.py']
    (out/'manifest.json').write_text(json.dumps(dict(inputs={p:sha(ROOT/p) for p in sources},figures={p.name:sha(p) for p in sorted(out.glob('*.png'))}),indent=2)+'\n')
if __name__=='__main__':main()
