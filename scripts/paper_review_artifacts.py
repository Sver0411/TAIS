#!/usr/bin/env python3
"""Publication-only bindings/plots from immutable G1/G2 outputs."""
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze_budget_sensitivity import analyze
ROOT=Path(__file__).resolve().parents[1];TABLES=ROOT/'papers/tais/tables';FIGS=ROOT/'papers/tais/figures';OUT=ROOT/'results/tais-paper-review'
METHODS=['AdaptiveSense+TrustLog','GateOnly','GateOnly+U','JO-SU-20','JO-SU-40']+[f'Fixed-{p}+C11' for p in [5,10,20,30,40,60]]+[f'{k}-budget-SU40+C11' for k in ['Delta','Variance','Rao-inspired']]
SUMMARY={'G1':'results/tais-paper/test/analysis/summary.csv','G2':'results/tais-transfer/test/analysis/summary.csv'}
CIS={'G1':'results/tais-paper/test/analysis/paired_intervals.csv','G2':'results/tais-transfer/test/analysis/paired_intervals.csv'}
AUDIT=[];FRAMES={}
def frame(path):
    if path not in FRAMES:FRAMES[path]=pd.read_csv(ROOT/path)
    return FRAMES[path]
def get(path,filters,column):
    d=frame(path);mask=np.ones(len(d),dtype=bool)
    for k,v in filters.items():mask&=d[k]==v
    rows=d[mask];assert len(rows)==1,(path,filters);index=int(rows.index[0]);x=rows.iloc[0][column]
    AUDIT.append(dict(source=path,row_index=index,metric=column,value=x))
    return x
def value(g,m,k,group='overall',view='native'):
    f=dict(method=m,group=group)
    if g=='G1':f['view']=view
    return get(SUMMARY[g],f,k)
def event(m,k,group):return get('results/tais-transfer/test/analysis/events_grouped.csv',dict(method=m,group=group),k)
def interval(g,a,b,metric='f1'):
    f=dict(A=a,B=b,metric=metric,group='overall')
    if g=='G1':f['view']='native'
    return '['+f"{100*get(CIS[g],f,'ci95_low'):+.2f}, {100*get(CIS[g],f,'ci95_high'):+.2f}"+']'
def n(x):return 'N/A' if pd.isna(x) else f'{x:,.0f}'
def p(x):return 'N/A' if pd.isna(x) else f'{100*x:.2f}'
def label(m):
    if m=='AdaptiveSense+TrustLog':return 'AS+C11'
    return m.replace('AdaptiveSense+TrustLog','AS+C11').replace('GateOnly','Gate').replace('JO-SU-','SU').replace('-budget-SU40+C11','-B').replace('-budget-Gate+C11','-G').replace('Variance','Var').replace('+C11','').replace('-c','-')
def write(name,text):(TABLES/name).write_text(text.rstrip()+'\n')
def tab(name,headers,rows,align=None):
    a=align or 'l'+'r'*(len(headers)-1)
    write(name,r'\begingroup\small\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.1}\begin{tabular}{'+a+r'}\toprule'+'\n'+' & '.join(headers)+r' \\\midrule'+'\n'+'\n'.join(' & '.join(r)+r' \\' for r in rows)+'\n'+r'\bottomrule\end{tabular}\endgroup')
def main():
    analyze();TABLES.mkdir(exist_ok=True);FIGS.mkdir(exist_ok=True)
    rows=[[label(m)]+[p(value(g,m,k)) for g in ['G1','G2'] for k in ['precision','recall','f1']] for m in METHODS]
    tab('review_quality.tex',['Mode','G1 P','G1 R','G1 F1','G2 P','G2 R','G2 F1'],rows)
    rr=[]
    for g in ['G1','G2']:
        rr.append([r'\multicolumn{7}{l}{\textit{'+g+r': separate task totals}}'])
        for m in METHODS:
            gap=value(g,m,'samples')/value(g,'JO-SU-40','samples')-1
            rr.append([label(m),n(value(g,m,'samples')),n(value(g,m,'binary_v1_bytes')),n(value(g,m,'fault_induced_false')),n(value(g,m,'pooled_age_p95_s')),f'{gap*100:+.2f}',('yes' if abs(gap)<=.05 else 'no')])
    tab('review_resources.tex',['Mode','Samples','Bytes','FI','Age P95(s)','Gap(\\%)','5\\%'],rr)
    su='JO-SU-40';var='Variance-budget-SU40+C11';fix='Fixed-20+C11'
    abstract=f'''Single-node IoT monitoring must distinguish environmental events from sensor faults while limiting acquisition and transmission. We evaluate TAIS, an executable integration of heuristic sensor-health diagnostics, event-aware sampling, upload suppression, stateless binary snapshots, and an independently decoded receiver. Fixed-period, delta-driven, variance-driven, and explicitly Rao-inspired schedules provide independent controls. Evaluation uses two separately specified synthetic tasks: G1 supports development and held-out comparison, whereas G2 applies frozen policies without retuning and changes signal dynamics, fault processes, event timing, and ground-truth interval definitions. SU40's F1 difference from the variance-budget control changes from {100*(value('G1',su,'f1')-value('G1',var,'f1')):+.2f} percentage points in G1 to {100*(value('G2',su,'f1')-value('G2',var,'f1')):+.2f} in G2; the G2 descriptive seed-paired 95\\% interval, {interval('G2',su,var)}, includes zero. Thus its near-budget quality advantage is not established across these tasks. Lower application-byte counts and fewer operationally attributed fault-induced reports coexist with missed short events and older receiver data. All communication counts come from actual encoding and independent receiver reconstruction. The study contributes reproducible system integration, independent resource comparisons, and explicit failure boundaries, rather than a new trust theory or universally superior policy. Two project-defined synthetic tasks and ideal local delivery do not establish field robustness or measured battery savings.'''
    write('review_abstract.tex',abstract)
    words=len(abstract.replace('\\%','%').split());assert 150<=words<=220,words
    (OUT/'abstract.json').write_text(json.dumps(dict(words=words,source='papers/tais/tables/review_abstract.tex',method='Whitespace-delimited rendered prose; percentage escapes counted as words within surrounding text'),indent=2)+'\n')
    text=f'''In G1, SU40-minus-Variance F1 is {100*(value('G1',su,'f1')-value('G1',var,'f1')):+.2f} percentage points (pp), with pointwise interval {interval('G1',su,var)}. In G2, the corresponding difference is {100*(value('G2',su,'f1')-value('G2',var,'f1')):+.2f} pp, interval {interval('G2',su,var)}. This interval includes zero: it does not establish either an F1 advantage for SU40 or an overall F1 disadvantage. The G2 Recall difference is {100*(value('G2',su,'recall')-value('G2',var,'recall')):+.2f} pp, interval {interval('G2',su,var,'recall')}, which lies below zero descriptively. These are unadjusted, endpoint-specific intervals, not a multiple-comparison-controlled superiority test.'''
    write('review_contrasts.tex',text)
    text=f'''SU40's near-budget detection-quality advantage observed in G1 was not retained under the independently specified G2 synthetic task, which differs in signal dynamics, fault processes, event timing, and ground-truth interval definitions. The experiment cannot separately identify the contributions of distributional changes, pulse shapes, or label geometry. In particular, comparing absolute G1/G2 Recall as if only the input distribution changed would be misleading. The G2 F1 point estimate favors Variance ({p(value('G2',var,'f1'))}\\% versus {p(value('G2',su,'f1'))}\\%), but its interval includes zero; the narrower defensible conclusion is absence of support for SU40's nearby-budget F1 advantage in this task.'''
    write('review_task_interpretation.tex',text)
    text=f'''Fixed20+C11 makes the objective conflict concrete. On G2 its F1 is {p(value('G2',fix,'f1'))}\\%, compared with SU40's {p(value('G2',su,'f1'))}\\%, while sample totals are {n(value('G2',fix,'samples'))} and {n(value('G2',su,'samples'))}, respectively. The control's relative sample gap is {(value('G2',fix,'samples')/value('G2',su,'samples')-1)*100:+.2f}\\%, within the original qualification band. These are descriptive point comparisons, not evidence of a stable global Fixed20 advantage. SU40 emits {n(value('G2',su,'binary_v1_bytes'))} rather than {n(value('G2',fix,'binary_v1_bytes'))} application bytes and has {n(value('G2',su,'fault_induced_false'))} rather than {n(value('G2',fix,'fault_induced_false'))} operationally attributed fault-induced reports. Its pooled P95 age is {n(value('G2',su,'pooled_age_p95_s'))} rather than {n(value('G2',fix,'pooled_age_p95_s'))}s. Thus better quality at similar acquisition counts coexists with more communication and more attributed reports, while suppression coexists with substantially older ordinary data. Neither mode dominates these dimensions.'''
    write('review_fixed_tradeoff.tex',text)
    text=f'''SU20 reaches G2 Recall {p(value('G2','JO-SU-20','recall'))}\\% and F1 {p(value('G2','JO-SU-20','f1'))}\\%; SU40 reaches {p(value('G2',su,'recall'))}\\% and {p(value('G2',su,'f1'))}\\%. This difference comes with {(value('G2','JO-SU-20','samples')/value('G2',su,'samples')-1)*100:.2f}\\% more sample cycles and FI counts {n(value('G2','JO-SU-20','fault_induced_false'))} versus {n(value('G2',su,'fault_induced_false'))}. It is a different operating tradeoff, not a universally improved setting. Independent controls remain competitive: G2's higher-quality Delta and Rao-inspired budget points have sample gaps {(value('G2','Delta-budget-SU40+C11','samples')/value('G2',su,'samples')-1)*100:+.2f}\\% and {(value('G2','Rao-inspired-budget-SU40+C11','samples')/value('G2',su,'samples')-1)*100:+.2f}\\%, so they do not qualify as nearby-budget comparisons at any displayed tolerance.'''
    write('review_modes.tex',text)
    text=f'''In G2, SU20 covers {p(event('JO-SU-20','coverage','duration:short'))}\\% of short events but reports only {p(event('JO-SU-20','recall','duration:short'))}\\%; SU40 reports {p(event(su,'recall','duration:short'))}\\%, versus GateOnly's {p(event('GateOnly','recall','duration:short'))}\\%. Coverage therefore does not guarantee that confirmation, gating and event shape permit a report. GateOnly, SU20 and SU40 each miss all {n(event(su,'events','fully_overwritten'))} full-support replacement events. Some independent-method reports can coincide with these labels; such coincidences do not establish reconstruction of erased physical information. SU40 stable-offset any-flag detection is {p(value('G2',su,'fault_detection_rate','fault:stable_offset'))}\\%; a correct offset type is unsupported because C11 has no dedicated offset bit. Humidity-fault Recall is {p(value('G2',su,'recall','fault_channel:humidity'))}\\%, so adding the second faulty channel does not remove missed-event limitations.'''
    write('review_failures.tex',text)
    text=f'''On G2, GateOnly and Gate+U have identical sender quality and {n(value('G2','GateOnly','samples'))} sample cycles, but bytes change from {n(value('G2','GateOnly','binary_v1_bytes'))} to {n(value('G2','GateOnly+U','binary_v1_bytes'))}, and pooled P95 age from {n(value('G2','GateOnly','pooled_age_p95_s'))} to {n(value('G2','GateOnly+U','pooled_age_p95_s'))}s. The G1 independent-schedule +U ablations likewise retain schedules and sender reports (Appendix~\\ref{{app:diagnostics}}). Consequently, communication savings are partly attributable to a reusable upload rule; they cannot all be credited to the originality of SU40 sampling. The G1 common-detector view isolates sample schedules, whereas native comparisons also include gating, reset and emission behavior.'''
    write('review_upload.tex',text)
    text=f'''The receiver is evaluated from decoded frames, not copied sender state. In G2, SU40 receiver TP/FP/FN are {n(value('G2',su,'rx_tp'))}/{n(value('G2',su,'rx_false_reports'))}/{n(value('G2',su,'rx_missed'))}, with {n(value('G2',su,'important_edges_unreported'))} missed sampled event/health edges. GateOnly misses {n(value('G2','GateOnly','important_edges_unreported'))} sampled edges; Gate+U misses {n(value('G2','GateOnly+U','important_edges_unreported'))}. Restoring edges can also expose a false onset, so exact delivery is not synonymous with higher event F1. Detailed local/sender/receiver counts and conditional delays remain in the appendix and artifact.'''
    write('review_receiver.tex',text)
    # Complete post-hoc sensitivity with repeated headers and comfortable type.
    b=frame('results/tais-paper-review/budget_sensitivity.csv');headers=['Task','Control','Target','Gap(\\%)','2\\%','5\\%','10\\%'];rows=[]
    for _,r in b.iterrows():
        idx=dict(generator=r.generator,method=r.method,target=r.target)
        gap=get('results/tais-paper-review/budget_sensitivity.csv',idx,'gap_percent')
        rows.append([r.generator,label(r.method),label(r.target),f'{gap:+.2f}']+['yes' if r[c] else 'no' for c in ['within_2pct','within_5pct','within_10pct']])
    long=r'\begingroup\small\setlength{\tabcolsep}{5pt}\begin{longtable}{lllrrrr}\caption{Post-hoc budget qualification of all existing independent +C11 native control--target pairs. No operating point is selected or changed.}\label{tab:sensitivity}\\\toprule '+' & '.join(headers)+r' \\\midrule\endfirsthead\multicolumn{7}{l}{\textit{Budget qualification (continued)}}\\\toprule '+' & '.join(headers)+r' \\\midrule\endhead'+'\n'+'\n'.join(' & '.join(r)+r' \\' for r in rows)+'\n'+r'\bottomrule\end{longtable}\endgroup'
    write('review_sensitivity.tex',long)
    # Focused contrasts are descriptive existing intervals; no new p-values.
    tab('review_intervals.tex',['Task','SU40 minus','Endpoint','Difference(pp)','Pointwise 95\\% CI'],[[g,label(b),k,f'{100*(value(g,su,k)-value(g,b,k)):+.2f}',interval(g,su,b,k)] for g in ['G1','G2'] for b in [var,'Rao-inspired-budget-SU40+C11','GateOnly','AdaptiveSense+TrustLog'] for k in ['f1','recall']])
    figures()
    pd.DataFrame(AUDIT).to_csv(TABLES/'review_data_audit.csv',index=False)
    sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FRAMES}
    (TABLES/'review_source_fingerprints.json').write_text(json.dumps(sources,indent=2)+'\n')
    manifest=dict(inputs=sources,abstract_words=words,generated_tex={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(TABLES.glob('review_*.tex'))},figures={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(FIGS.glob('review_*.png'))})
    (OUT/'build_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('Review bindings',len(AUDIT),'abstract words',words)

def figures():
    plt.rcParams.update({'font.size':11,'axes.labelsize':11,'axes.titlesize':12,'legend.fontsize':10,'savefig.dpi':220,'pdf.fonttype':42})
    fig,axs=plt.subplots(1,2,figsize=(8.5,6.2),sharey=True)
    for ax,g in zip(axs,['G1','G2']):
        y=np.arange(len(METHODS));ax.scatter([100*value(g,m,'recall') for m in METHODS],y-.08,facecolors='white',edgecolors='black',marker='o',s=36,label='Recall');ax.scatter([100*value(g,m,'f1') for m in METHODS],y+.08,c='black',marker='x',s=28,label='F1')
        ax.set_yticks(y,[label(m) for m in METHODS]);ax.set_xlim(0,100);ax.set_xlabel('Sender metric (%)');ax.set_title(g+' synthetic task');ax.grid(axis='x',color='.85');ax.set_axisbelow(True)
    axs[0].invert_yaxis();fig.legend(*axs[0].get_legend_handles_labels(),loc='upper center',ncol=2,frameon=False);fig.tight_layout(rect=(0,0,1,.95));fig.savefig(FIGS/'review_task_quality.png');plt.close(fig)
    su='JO-SU-40';fix='Fixed-20+C11';fig,axs=plt.subplots(2,3,figsize=(8.5,5.6))
    for ax,(metric,title,scale) in zip(axs.flat,[('f1','F1 (%)',100),('samples','Sample cycles',1),('binary_v1_bytes','Binary v1 bytes',1),('fault_induced_false','Attributed false reports',1),('pooled_age_p95_s','P95 receiver age (s)',1),('uploads','Uploads',1)]):
        vals=[scale*value('G2',m,metric) for m in [su,fix]];bars=ax.bar([0,1],vals,color=['.25','white'],edgecolor='black',hatch=None,width=.55);bars[1].set_hatch('//')
        ax.set_xticks([0,1],['SU40','Fixed20+C11'],fontsize=9);ax.set_title(title,fontsize=10);ax.set_ylim(0,max(vals)*1.28);ax.tick_params(axis='y',labelsize=9)
        if max(vals)>9999:ax.ticklabel_format(axis='y',style='sci',scilimits=(0,0));ax.yaxis.get_offset_text().set_size(9)
        for i,v in enumerate(vals):ax.annotate(f'{v:.2f}' if metric=='f1' else f'{v:,.0f}',(i,v),xytext=(0,4),textcoords='offset points',ha='center',fontsize=9)
        ax.grid(axis='y',color='.88');ax.set_axisbelow(True)
    fig.tight_layout(h_pad=2,w_pad=1.5);fig.savefig(FIGS/'review_fixed20_tradeoff.png');plt.close(fig)
if __name__=='__main__':main()
