"""All points plotted separately by suite, plus a sampled-state regression figure."""
import sys,argparse,json,gzip
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
from tais import ROOT
from summarize_results import aggregate
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def tradeoffs(df,dest,suite):
 relations=['all','cross','same'] if suite=='main' else ['all','cross_sequential','same_sequential']
 for kind in ['recall_uploads','faultfalse_recall']:
  fig,axes=plt.subplots(1,3,figsize=(15,4.5),constrained_layout=True)
  for ax,relation in zip(axes,relations):
   sub=df if relation=='all' else df[df.relationship==relation]
   if sub.empty:ax.set_axis_off();continue
   summary=aggregate(sub,['method','multiplier'])
   for i,(method,g) in enumerate(summary.groupby('method')):
    g=g.sort_values('multiplier');x=g.uploads_per_run if kind=='recall_uploads' else g.recall*100
    y=g.recall*100 if kind=='recall_uploads' else g.fault_induced_false/(g.duration_s/1800)
    ax.plot(x,y,marker=['s','o','^','v','d'][i],label=method,linestyle='-' if len(g)>1 else '')
    for xx,yy,m in zip(x,y,g.multiplier):
     if len(g)>1:ax.annotate(f'{m:g}',(xx,yy),xytext=(3,3),textcoords='offset points',fontsize=7)
   ax.set(title=suite+' / '+relation,xlabel='Uploads / 30-min run' if kind=='recall_uploads' else 'Reported recall (%)',ylabel='Reported recall (%)' if kind=='recall_uploads' else 'Fault false reports / run');ax.grid(alpha=.2)
  fig.legend(*axes[0].get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.5,-.08),ncol=5,fontsize=9)
  fig.savefig(dest/(kind+'.png'),dpi=160,bbox_inches='tight');plt.close(fig)

def regression():
 dest=ROOT/'results/blocked-rearm/diagnosis';fig,axes=plt.subplots(5,1,figsize=(12,12),sharex=True,constrained_layout=True)
 for i,method in enumerate(['TAIS','V02','V02-Rearm']):
  o=json.loads(gzip.decompress((dest/(method+'.json.gz')).read_bytes()));tr=o['trace'];r=o['result'];records=r['records'];tt=[x['timestamp'] for x in records];color=f'C{i}'
  if i==0:
   axes[0].plot([x['timestamp'] for x in tr['latent']],[x['temperature'] for x in tr['latent']],label='Latent (offline)',color='black')
   axes[0].plot([x['timestamp'] for x in tr['observed']],[x['temperature'] for x in tr['observed']],label='Observed (offline)',alpha=.35)
  axes[0].scatter(tt,[x['values']['temperature'] for x in records],s=14,color=color,label=method+' actual samples')
  axes[1].step(tt,[x['health']['temperature']['score'] for x in records],where='post',label=method,color=color)
  axes[2].plot(tt,[x.get('evidence',{}).get('temperature',{}).get('raw_score',x['scores'].get('temperature',0)) for x in records],color=color,label=method)
  phases=[x.get('evidence',{}).get('temperature',{}).get('phase','LEGACY') for x in records]
  if method!='TAIS':axes[3].step(tt,[dict(IDLE=0,PENDING=1,CONFIRMED=2,BLOCKED=3)[x] for x in phases],where='post',color=color,label=method)
  for x in records:
   for a in x.get('evidence',{}).get('temperature',{}).get('actions',[]):
    if a['action']=='rearmed':axes[3].scatter(x['timestamp'],0,marker='*',s=100,color=color)
  axes[4].scatter([x['timestamp'] for x in records if x['upload']],[i]*sum(x['upload'] for x in records),marker='|',color=color,label=method+' upload')
  reports=[e['start_s'] for e in r['reports'] if e['channel']=='temperature'];axes[4].scatter(reports,[i+.35]*len(reports),marker='^',color=color)
 for ax in axes:
  for e in tr['events']:ax.axvspan(e['start_s'],e['end_s'],alpha=.1,color='green')
  for f in tr['faults']:ax.axvspan(f['start_s'],f['end_s'],alpha=.2,color='red')
  ax.legend(fontsize=8,loc='upper right');ax.grid(alpha=.2)
 axes[0].set_title('Seed91 regression only: red fault, green truth; no truth online')
 for ax,label in zip(axes,['Temperature C','Real C health score','Change score (legacy gated)','Phase: 0 idle / 1 pending\n2 confirmed / 3 blocked','Upload | / report onset ^']):ax.set_ylabel(label)
 axes[3].set_yticks([0,1,2,3]);axes[-1].set(xlim=(560,900),xlabel='Seconds')
 fig.savefig(dest/'before-after.png',dpi=150);plt.close(fig)
if __name__=='__main__':regression()
