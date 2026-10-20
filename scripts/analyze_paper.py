#!/usr/bin/env python3
"""All views/groups retained; paired seed clusters and literal operating points."""
import argparse,csv,json,sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from benchmark_paper import OUT,sha,dump
from analyze_su import aggregate as su_aggregate
from analyze_joint_optimization import groups

def write(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(path,index=False)
def read(root,phase):
    manifest=json.loads((root/phase/'manifest.json').read_text());assert manifest['status']=='COMPLETE'
    assert sha(root/phase/'metrics.csv')==manifest['metrics_sha256']
    d=pd.read_csv(root/phase/'metrics.csv');assert len(d)==manifest['runs']
    return d.replace({np.nan:None}).to_dict('records')
def aggregate(rows):
    a=su_aggregate(rows)
    health=all(r['health_available'] for r in rows)
    if not health:
        for k in ['fault_detection_rate','fault_detected','fault_type_detected','fault_latency_sum_s']:a[k]=None
    a.update(health_available=health,runs=len(rows),local_recall=a['local_tp']/a['n_events'] if a['n_events'] else None,average_upload_bytes=a['binary_v1_bytes']/a['uploads'] if a['uploads'] else None,rx_event_delay_s=a['rx_latency_sum_s']/a['rx_latency_n'] if a['rx_latency_n'] else None)
    return a

def paired(rows,contrasts,out):
    rng=np.random.default_rng(2026101917);seeds=sorted({r['seed'] for r in rows});draw=rng.integers(0,len(seeds),(5000,len(seeds)));result=[]
    gs=['overall','profile:short','profile:long','relation:same','relation:cross','fault:drift','fault:stable_offset','no_events']
    keys=['precision','recall','f1','rx_precision','rx_recall','rx_f1','samples','uploads','binary_v1_bytes','fault_induced_false','rx_fault_induced_false','fault_detection_rate','event_delay_s','rx_event_delay_s']
    for view,A,B in contrasts:
        for group in gs:
            aa=[r for r in rows if r['view']==view and r['method']==A and group in groups(r)];bb=[r for r in rows if r['view']==view and r['method']==B and group in groups(r)]
            if not aa or not bb:continue
            a,b=aggregate(aa),aggregate(bb);pa=[aggregate([r for r in aa if r['seed']==s]) for s in seeds];pb=[aggregate([r for r in bb if r['seed']==s]) for s in seeds]
            def boot(p,k):
                def summed(x):return np.array([r[x] or 0 for r in p])[draw].sum(axis=1)
                def ratio(x,y):return np.divide(x,y,out=np.full(5000,np.nan),where=y>0)
                rx=k.startswith('rx_');kk=k[3:] if rx else k;prefix='rx_' if rx else ''
                if kk in ['precision','recall','f1']:
                    tp=summed(prefix+'tp');fp=summed(prefix+'false_reports');n=summed('n_events');den={'precision':tp+fp,'recall':n,'f1':n+tp+fp}[kk]
                    return ratio(tp*(2 if kk=='f1' else 1),den)
                if k=='fault_detection_rate':return ratio(summed('fault_detected'),summed('fault_episodes'))
                if kk=='event_delay_s':return ratio(summed(prefix+'latency_sum_s'),summed(prefix+'latency_n'))
                return summed(k)
            for k in keys:
                if a[k] is None or b[k] is None:continue
                delta=boot(pa,k)-boot(pb,k);lo,hi=np.nanpercentile(delta,[2.5,97.5])
                result.append(dict(view=view,A=A,B=B,group=group,metric=k,difference=a[k]-b[k],ci95_low=lo,ci95_high=hi))
    write(out/'paired_intervals.csv',result)

def figures(summary,out):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    for view in ['native','common']:
        d={r['method']:r for r in summary if r['view']==view and r['group']=='overall'}
        fig,axs=plt.subplots(2,2,figsize=(12,9));pairs=[('samples','recall'),('samples','f1'),('binary_v1_bytes','f1'),('samples','fault_induced_false')]
        for ax,(x,y) in zip(axs.flat,pairs):
            for color,kind in zip(['#666666','#e69f00','#0072b2','#009e73'],['Fixed','Delta','Variance','Rao-inspired']):
                names=[f'Fixed-{c}' for c in [5,10,20,30,40,60]] if kind=='Fixed' else [f'{kind}-c{c}' for c in [20,40,60]]
                if view=='native':names=[n+'+C11' for n in names]
                rr=[d[n] for n in names]
                ax.scatter([r[x] for r in rr],[100*r[y] if y in ['recall','f1'] else r[y] for r in rr],c=color,label=kind+' + C11' if view=='native' else kind,s=40)
                for n,r in zip(names,rr):
                    label=n.split('+')[0].split('-')[-1].replace('c','')
                    ax.annotate(label,(r[x],100*r[y] if y in ['recall','f1'] else r[y]),fontsize=6,xytext=(3,3),textcoords='offset points')
            for marker,color,m in [('s','#cc79a7','GateOnly'),('x','#cc79a7','GateOnly+U'),('^','#d55e00','JO-SU-20'),('D','#d55e00','JO-SU-30'),('*','#d55e00','JO-SU-40'),('P','#000000','AdaptiveSense+TrustLog')]:
                r=d[m];ax.scatter(r[x],100*r[y] if y in ['recall','f1'] else r[y],label=m,marker=marker,c=color,s=75)
            ax.set_xlabel({'samples':'Actual sample cycles','binary_v1_bytes':'Actual Binary v1 bytes'}[x]);ax.set_ylabel({'f1':'F1 (%)','recall':'Recall (%)','fault_induced_false':'Operational fault-induced false reports'}[y]);ax.grid(alpha=.2)
        axs[0,0].legend(fontsize=6,ncol=2);fig.suptitle(view+': discrete operating points; no interpolation; all45 scenarios /20 seeds');fig.tight_layout();fig.savefig(out/f'{view}_tradeoffs.png',dpi=180)
        for ax,(x,y) in zip(axs.flat,pairs):
            extent=ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted()).expanded(1.22,1.35)
            fig.savefig(out/f'{view}_{y}_vs_{x}.png',bbox_inches=extent,dpi=180)
        plt.close(fig)

def resource(summary,out):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    d={r['method']:r for r in summary if r['view']=='native' and r['group']=='overall'}
    a=np.logspace(-2,4,41);b=np.logspace(-2,4,41);aa,bb=np.meshgrid(a,b);s=d['JO-SU-40'];rows=[]
    names=['GateOnly','Fixed-30+C11','Variance-budget-SU40+C11'];fig,axes=plt.subplots(1,3,figsize=(13,4))
    for ax,name in zip(axes,names):
        r=d[name];base=aa*r['samples']+bb*r['uploads']+r['binary_v1_bytes'];cost=aa*s['samples']+bb*s['uploads']+s['binary_v1_bytes'];ratio=cost/base
        im=ax.pcolormesh(a,b,ratio,shading='auto',cmap='RdBu_r',vmin=.5,vmax=1.5)
        if ratio.min()<1<ratio.max():ax.contour(a,b,ratio,levels=[1],colors='k',linewidths=1)
        ax.set(xscale='log',yscale='log',xlabel='sample cost / byte cost',ylabel='fixed tx cost / byte cost',title='SU40 / '+name);fig.colorbar(im,ax=ax)
        for i,y in enumerate(b):
            for j,x in enumerate(a):rows.append(dict(comparator=name,sample_per_byte=x,tx_fixed_per_byte=y,su40_cost_ratio=ratio[i,j],extra_processing_break_even=base[i,j]-cost[i,j]))
    fig.suptitle('Conditional additive cost, equal processing assumed; dimensionless, NOT measured energy');fig.tight_layout();fig.savefig(out/'resource_sensitivity.png',dpi=180);plt.close(fig);write(out/'resource_sensitivity.csv',rows)

def main(root,phase):
    rows=read(root,phase);out=root/phase/'analysis';out.mkdir(parents=True,exist_ok=True);by={}
    for r in rows:
        for group in groups(r):by.setdefault((r['view'],r['method'],group),[]).append(r)
    ages={(r['view'],r['method']):r for r in pd.read_csv(root/phase/'pooled_age.csv').to_dict('records')}
    summary=[dict(view=v,method=m,group=g,**aggregate(rr),pooled_age_p95_s=ages[v,m]['p95_age_s'] if g=='overall' else None,pooled_age_max_s=ages[v,m]['max_age_s'] if g=='overall' else None) for (v,m,g),rr in sorted(by.items())]
    write(out/'summary.csv',summary);write(root/'summary.csv',[r for r in summary if r['group']=='overall'])
    selection=json.loads((OUT/'operating-points.json').read_text());budgets=[];contrasts=[]
    overall={(r['view'],r['method']):r for r in summary if r['group']=='overall'}
    for s in selection['budget_selection']:
        name=f"{s['kind']}-budget-{'Gate' if s['target']=='GateOnly' else 'SU40'}"
        for view in ['native','common']:
            m=name+'+C11' if view=='native' else name;a=overall[view,m];b=overall[view,s['target']];gap=a['samples']/b['samples']-1
            budgets.append(dict(view=view,method=m,target=s['target'],cap=s['cap'],minimum=s.get('minimum',5),threshold=s['threshold'],development_gap=s['relative_gap'],test_gap=gap,within_5pct=abs(gap)<=.05,samples=a['samples'],target_samples=b['samples'],recall=a['recall'],target_recall=b['recall'],f1=a['f1'],target_f1=b['f1'],rx_f1=a['rx_f1'],target_rx_f1=b['rx_f1'],binary_v1_bytes=a['binary_v1_bytes'],target_binary_v1_bytes=b['binary_v1_bytes'],fault_induced_false=a['fault_induced_false'],target_fault_induced_false=b['fault_induced_false']))
            for t in ['GateOnly','JO-SU-40']:contrasts.append((view,t,m))
    for view in ['native','common']:
        for f in [5,10,20,30,40,60]:
            m=f'Fixed-{f}'+('+C11' if view=='native' else '')
            for t in ['GateOnly','JO-SU-40']:contrasts.append((view,t,m))
    contrasts += [('native','JO-SU-40','GateOnly'),('native','JO-SU-40','AdaptiveSense+TrustLog'),('native','JO-SU-20','JO-S'),('native','GateOnly+U','GateOnly')]
    contrasts += [('native',f'{k}-c40+C11+U',f'{k}-c40+C11') for k in ['Delta','Variance','Rao-inspired']]
    write(out/'budget_comparisons.csv',budgets);paired(rows,contrasts,out)
    # Common-event delay comparison avoids comparing different hit subsets.
    events=pd.read_csv(root/phase/'events.csv');common=[]
    for view,A,B in contrasts:
        cols=['seed','scenario','channel','truth_start','truth_end'];a=events[(events['view']==view)&(events['method']==A)];b=events[(events['view']==view)&(events['method']==B)]
        x=a.merge(b,on=cols,suffixes=('_a','_b'));x=x[x.matched_a&x.matched_b]
        common.append(dict(view=view,A=A,B=B,matched_in_both=len(x),mean_delay_difference_s=float((x.report_time_a-x.report_time_b).mean()) if len(x) else None))
    write(out/'common_event_delays.csv',common)
    figures(summary,out);resource(summary,out)
    print('analyzed',phase,len(rows),'runs',len(summary),'group summaries',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['smoke','development','test'],required=True);p.add_argument('--root',type=Path,default=OUT);a=p.parse_args();main(a.root,a.phase)
