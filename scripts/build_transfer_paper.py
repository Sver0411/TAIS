#!/usr/bin/env python3
"""Bind every G2 empirical table/paragraph to literal committed CSV cells."""
from pathlib import Path
import json,shutil
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/tais-transfer';PAPER=ROOT/'papers/tais';TABLES=PAPER/'tables';audit=[];frames={}

def source(name):
    p='results/tais-transfer/'+name
    if p not in frames:frames[p]=pd.read_csv(ROOT/p)
    return p,frames[p]
def value(name,filters,metric,fmt='pct'):
    p,d=source(name);mask=np.ones(len(d),dtype=bool)
    for k,v in filters.items():mask&=d[k]==v
    found=d[mask];assert len(found)==1,(p,filters);idx=int(found.index[0]);x=found.iloc[0][metric]
    audit.append(dict(source=p,row_index=idx,metric=metric,value=x,format=fmt))
    if pd.isna(x):return 'N/A'
    if fmt=='pct':return f'{100*x:.2f}'
    if fmt=='signed_pct':return f'{100*x:+.2f}'
    if fmt=='int':return f'{x:,.0f}'
    if fmt=='float_raw':return repr(float(x))
    return f'{x:.2f}'
def v(m,k,g='overall',fmt='pct'):return value('test/analysis/summary.csv',dict(method=m,group=g),k,fmt)
def ev(m,k,g,fmt='pct'):return value('test/analysis/events_grouped.csv',dict(method=m,group=g),k,fmt)
def interval(A,B,k='f1'):
    filt=dict(A=A,B=B,group='overall',metric=k)
    return '['+value('test/analysis/paired_intervals.csv',filt,'ci95_low','signed_pct')+', '+value('test/analysis/paired_intervals.csv',filt,'ci95_high','signed_pct')+']'
def label(m):return m.replace('AdaptiveSense+TrustLog','AS+C11').replace('JO-SU-','SU').replace('GateOnly','Gate').replace('Variance','Var').replace('-budget-SU40','-bS40')
def write(name,text):(TABLES/name).write_text(text.rstrip()+'\n')
def table(name,headers,rows):
    text=r'\setlength{\tabcolsep}{3pt}\begin{tabular}{l'+'r'*(len(headers)-1)+r'}\toprule'+'\n'+' & '.join(headers)+r' \\\midrule'+'\n'
    text+='\n'.join(' & '.join(row)+r' \\' for row in rows)+'\n'+r'\bottomrule\end{tabular}';write(name,text)
def main():
    methods=pd.read_csv(OUT/'summary.csv').method.tolist();sel=['AdaptiveSense+TrustLog','GateOnly','GateOnly+U','JO-SU-20','JO-SU-40','Delta-budget-SU40+C11','Variance-budget-SU40+C11','Rao-inspired-budget-SU40+C11']
    table('transfer_main.tex',['Mode','P','R','F1','RxF1','FI','Samples','Bytes'],[[label(m)]+[v(m,k,fmt=fmt) for k,fmt in [('precision','pct'),('recall','pct'),('f1','pct'),('rx_f1','pct'),('fault_induced_false','int'),('samples','int'),('binary_v1_bytes','int')]] for m in methods])
    table('transfer_communication.tex',['Mode','Tx','B/Tx','Mean age','P95/max(s)','Miss E/H'],[[label(m),v(m,'uploads',fmt='int'),v(m,'average_upload_bytes',fmt='float'),v(m,'age_mean_s',fmt='float'),v(m,'pooled_age_p95_s',fmt='int')+'/'+v(m,'pooled_age_max_s',fmt='int'),v(m,'event_edges_unreported',fmt='int')+'/'+v(m,'health_edges_unreported',fmt='int')] for m in methods])
    table('transfer_boundaries.tex',['Mode','Short R','Medium R','Long R','Coverage','Hit/covered','Masked R'],[[label(m),ev(m,'recall','duration:short'),ev(m,'recall','duration:medium'),ev(m,'recall','duration:long'),ev(m,'coverage','overall'),ev(m,'covered_success','overall'),ev(m,'recall','fully_overwritten')] for m in sel])
    budget=pd.read_csv(OUT/'test/analysis/budget_comparisons.csv');rows=[]
    for _,r in budget.iterrows():
        filt=dict(method=r.method);gap=value('test/analysis/budget_comparisons.csv',filt,'relative_gap','signed_pct')
        delta=value('test/analysis/paired_intervals.csv',dict(A='JO-SU-40',B=r.method,metric='f1',group='overall'),'difference','signed_pct')
        rows.append([label(r.method),gap,('yes' if r.within_5pct else 'no'),delta,interval('JO-SU-40',r.method)])
    # All frozen fixed periods also get literal G2 gaps; no post-test point selection.
    for period in [5,10,20,30,40,60]:
        m=f'Fixed-{period}+C11';gap=float(v(m,'samples',fmt='float'))/float(v('JO-SU-40','samples',fmt='float'))-1
        delta=float(v('JO-SU-40','f1',fmt='float_raw'))-float(v(m,'f1',fmt='float_raw'))
        rows.append([label(m),f'{100*gap:+.2f}',('yes' if abs(gap)<=.05 else 'no'),f'{100*delta:+.2f}','not estimated'])
    table('transfer_budgets.tex',['Independent+C11','Actual sample gap(\\%)','Within5\\%',r'$\Delta$F1(pp)','95\\% CI(pp)'],rows)
    write('transfer_counts.tex',r'\begin{small}\setlength{\tabcolsep}{4pt}\begin{longtable}{lrrrrrrr}\caption{G2 local, sender and independently decoded receiver event counts.}\label{tab:transfercounts}\\\toprule Mode & Local TP & Sender TP & FP & FN & Rx TP & FP & FN \\\midrule\endhead'+'\n'+'\n'.join(' & '.join([label(m)]+[v(m,k,fmt='int') for k in ['local_tp','tp','false_reports','missed','rx_tp','rx_false_reports','rx_missed']])+r' \\' for m in methods)+'\n'+r'\bottomrule\end{longtable}\end{small}')
    # All prose numbers below use the same cell binding as tables.
    text=f'On G2, SU40 achieved Precision {v("JO-SU-40","precision")}\\%, Recall {v("JO-SU-40","recall")}\\%, and F1 {v("JO-SU-40","f1")}\\%; GateOnly F1 was {v("GateOnly","f1")}\\%, with a paired SU40-minus-Gate F1 interval of {interval("JO-SU-40","GateOnly")} percentage points. Against AS+C11, the F1 interval was {interval("JO-SU-40","AdaptiveSense+TrustLog")}. SU20 Recall/F1 were {v("JO-SU-20","recall")}\\%/{v("JO-SU-20","f1")}\\%, versus SU40 {v("JO-SU-40","recall")}\\%/{v("JO-SU-40","f1")}\\%; their F1 interval was {interval("JO-SU-20","JO-SU-40")}. '
    text+='For independent SU40-targeted controls, Table~\\ref{tab:transferbudget} reports actual gaps rather than importing G1 matching status. '
    for m in ['Delta-budget-SU40+C11','Variance-budget-SU40+C11','Rao-inspired-budget-SU40+C11']:
        text+=f'{label(m)} yielded F1 {v(m,"f1")}\\% and Recall {v(m,"recall")}\\%; SU40-minus-control F1 interval {interval("JO-SU-40",m)}. '
    write('transfer_results.tex',text)
    short=f'SU20 short-event Recall was {ev("JO-SU-20","recall","duration:short")}\\% and sampled coverage {ev("JO-SU-20","coverage","duration:short")}\\%, compared with SU40 {ev("JO-SU-40","recall","duration:short")}\\% and {ev("JO-SU-40","coverage","duration:short")}\\%. Overall sampled coverage and covered-event success are distinct in Table~\\ref{{tab:transferboundary}}. Fully overwritten-support Recall was {ev("JO-SU-40","recall","fully_overwritten")}\\% for SU40; matching tolerance and onset ambiguity mean this group is a descriptive stress label, not proof that erased information has been reconstructed. '
    short+=f'For humidity-fault scenarios SU40 Recall/F1 were {v("JO-SU-40","recall","fault_channel:humidity")}\\%/{v("JO-SU-40","f1","fault_channel:humidity")}\\%, and temperature-fault scenarios {v("JO-SU-40","recall","fault_channel:temperature")}\\%/{v("JO-SU-40","f1","fault_channel:temperature")}\\%. Stable-offset any-flag detection was {v("JO-SU-40","fault_detection_rate","fault:stable_offset")}\\%; correct offset-type detection is unsupported (N/A). '
    write('transfer_failures.tex',short)
    comm=f'GateOnly and Gate+U used {v("GateOnly","samples",fmt="int")} and {v("GateOnly+U","samples",fmt="int")} sample cycles, respectively; their bytes were {v("GateOnly","binary_v1_bytes",fmt="int")} and {v("GateOnly+U","binary_v1_bytes",fmt="int")}, with pooled P95 age {v("GateOnly","pooled_age_p95_s",fmt="int")} and {v("GateOnly+U","pooled_age_p95_s",fmt="int")}s. SU40 receiver TP/FP/FN were {v("JO-SU-40","rx_tp",fmt="int")}/{v("JO-SU-40","rx_false_reports",fmt="int")}/{v("JO-SU-40","rx_missed",fmt="int")}; its event/health edge misses were {v("JO-SU-40","event_edges_unreported",fmt="int")}/{v("JO-SU-40","health_edges_unreported",fmt="int")}, and reported event/health edge maximum delay {v("JO-SU-40","event_edge_delay_max_s",fmt="int")}/{v("JO-SU-40","health_edge_delay_max_s",fmt="int")}s. These sampled-edge lags are distinct from physical-event-to-report delays.'
    write('transfer_receiver.tex',comm)
    abstract=f'Performance differed across synthetic tasks with different signal, fault, timing and label definitions. In a second independently specified stochastic generator, with all policies transferred without retuning over twenty new seeds and 46 scenarios, SU40 F1 was {v("JO-SU-40","f1")}\\% versus {v("GateOnly","f1")}\\% for GateOnly and {v("Variance-budget-SU40+C11","f1")}\\% for the frozen variance-budget control. The G1 near-budget quality advantage is not supported in the independently specified G2 task; this is not an isolated distribution-shift effect. '
    write('transfer_abstract.tex',abstract)
    conclusion=f'The zero-retuning G2 test gave SU40 Recall/F1 {v("JO-SU-40","recall")}\\%/{v("JO-SU-40","f1")}\\% and SU20 {v("JO-SU-20","recall")}\\%/{v("JO-SU-20","f1")}\\%. Independent controls and actual budget shifts qualify the interpretation; two synthetic mechanisms broaden the stress test without establishing natural-fault or field generalization.'
    write('transfer_conclusion.tex',conclusion)
    # Typed flags and delays for the representative modes, all seven kinds and both channels.
    diag=pd.read_csv(OUT/'test/analysis/fault_diagnostics.csv');rows=[]
    for m in ['GateOnly','JO-SU-20','JO-SU-40','Variance-budget-SU40+C11']:
        for k in ['range','spike','stuck','drift','missing','invalid','stable_offset']:
            for c in ['temperature','humidity']:
                fil=dict(method=m,kind=k,channel=c)
                rows.append([label(m),k.replace('_',r'\_'),'T' if c=='temperature' else 'H']+[value('test/analysis/fault_diagnostics.csv',fil,x,fmt) for x,fmt in [('any_detection_rate','pct'),('type_detection_rate','pct'),('any_delay_s','float'),('type_delay_s','float')]])
    write('transfer_health.tex',r'\begin{small}\setlength{\tabcolsep}{4pt}\begin{longtable}{lllrrrr}\caption{Raw G2 C11 diagnostics for representative modes; T/H denote fault channel.}\label{tab:transferhealth}\\\toprule Mode & Fault & Ch & Any(\%) & Type(\%) & Any delay(s) & Type delay(s) \\\midrule\endfirsthead\multicolumn{7}{l}{\textit{Table \thetable{} (continued)}}\\\toprule Mode & Fault & Ch & Any(\%) & Type(\%) & Any delay(s) & Type delay(s) \\\midrule\endhead'+'\n'+'\n'.join(' & '.join(r)+(r' \\*' if (i+1)%14 else r' \\') for i,r in enumerate(rows))+'\n'+r'\bottomrule\end{longtable}\end{small}')
    def ratio(a,b,k):
        return (float(v(a,k,fmt='float_raw'))/float(v(b,k,fmt='float_raw'))-1)*100
    text='The G1 near-budget F1 advantage over Variance was not retained under the differently defined G2 synthetic task: in G2 the point estimate favors Variance, while the SU40-minus-Variance F1 interval spans zero, and its unadjusted pointwise Recall interval is '+interval('JO-SU-40','Variance-budget-SU40+C11','recall')+' percentage points. '
    text+=f"Fixed20+C11 also has higher point F1 ({v('Fixed-20+C11','f1')}\\%) at an actual sample gap of {ratio('Fixed-20+C11','JO-SU-40','samples'):+.2f}\\%; no predeclared fixed-point interval was estimated. Thus the data do not support SU40 quality superiority at approximately matched acquisition totals. All fixed points remain visible, including Fixed10's F1 {v('Fixed-10+C11','f1')}\\%. "
    text+=f"SU40 instead uses {ratio('JO-SU-40','Variance-budget-SU40+C11','binary_v1_bytes'):+.2f}\\% bytes and {ratio('JO-SU-40','Variance-budget-SU40+C11','fault_induced_false'):+.2f}\\% operational fault-induced reports relative to Variance, with a larger ordinary-data age. The U diagnostic on G1 and Gate+U on G2 show that part of this advantage is reusable communication behavior, not unique sampling novelty. "
    text+=f"SU20 improves G2 Recall over SU40, but sample cycles change by {ratio('JO-SU-20','JO-SU-40','samples'):+.2f}\\% and FI counts are {v('JO-SU-20','fault_induced_false',fmt='int')} versus {v('JO-SU-40','fault_induced_false',fmt='int')}. Its short-event Recall remains only {ev('JO-SU-20','recall','duration:short')}\\%, despite {ev('JO-SU-20','coverage','duration:short')}\\% sampled coverage. SU40 short Recall ({ev('JO-SU-40','recall','duration:short')}\\%) is below GateOnly ({ev('GateOnly','recall','duration:short')}\\%), another reversal of the G1 short-event pattern. Sampling coverage alone does not guarantee debounce, gating or shape-specific detection success. "
    text+='Rao-inspired remains competitive on quality despite fixed-center mismatch, but its actual sample budget grows well beyond SU40; this is neither matched-budget evidence nor a faithful Rao reproduction. The contrast also combines changed signal shapes, correlated noise, amplitudes, timing and label geometry, so these data cannot uniquely attribute a reversal to one causal factor. The revised contribution is a reproducible conditional systems tradeoff and a boundary on a broad cross-task superiority claim, not evidence of a universally preferable balanced mode.'
    write('transfer_discussion.tex',text)

    pd.DataFrame(audit).to_csv(TABLES/'transfer_data_audit.csv',index=False)
    from benchmark_joint_optimization import sha
    (TABLES/'transfer_source_fingerprints.json').write_text(json.dumps({p:sha(ROOT/p) for p in frames},indent=2)+'\n')
    for file in (OUT/'figures').glob('*.png'):shutil.copyfile(file,PAPER/'figures'/('transfer_'+file.name))
    print('G2 manuscript cells bound:',len(audit))
if __name__=='__main__':main()
