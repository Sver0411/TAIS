#!/usr/bin/env python3
"""Generate every empirical manuscript cell and claim from real held-out outputs."""
from pathlib import Path
import csv,json,shutil,sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/tais-paper';PAPER=ROOT/'papers/tais';TABLES=PAPER/'tables';FIGS=PAPER/'figures'
TABLES.mkdir(exist_ok=True);FIGS.mkdir(exist_ok=True)
s=pd.read_csv(OUT/'test/analysis/summary.csv');ci=pd.read_csv(OUT/'test/analysis/paired_intervals.csv');budget=pd.read_csv(OUT/'test/analysis/budget_comparisons.csv');selection=json.loads((OUT/'operating-points.json').read_text());audit=[]

def row(m,group='overall',view='native'):
    r=s[(s.method==m)&(s.group==group)&(s['view']==view)];assert len(r)==1,(m,group,view);return r.iloc[0]
def val(m,k,g='overall',v='native',fmt='pct'):
    x=row(m,g,v)[k];audit.append(dict(method=m,view=v,group=g,metric=k,value=x,format=fmt))
    if pd.isna(x):return 'N/A'
    if fmt=='pct':return f'{x*100:.2f}'
    if fmt=='int':return f'{x:,.0f}'
    return f'{x:.2f}'
def esc(x):return str(x).replace('_',r'\_').replace('%',r'\%').replace('&',r'\&')
def label(m):
    m=m.replace('AdaptiveSense+TrustLog','AS+C11').replace('AdaptiveSense','AS').replace('JO-SU-','SU').replace('JO-S','S').replace('GateOnly','Gate').replace('Variance','Var').replace('-budget-SU40','-bS40').replace('-budget-Gate','-bGate').replace('-c','-')
    return esc(m)
def write(name,text):(TABLES/name).write_text(text.rstrip()+'\n')
def table(name,headers,rows,align=None):
    a=align or 'l'+'r'*(len(headers)-1)
    text=r'\setlength{\tabcolsep}{3pt}\begin{tabular}{'+a+r'}\toprule'+'\n'+' & '.join(headers)+r' \\\midrule'+'\n'
    text+='\n'.join(' & '.join(map(str,r))+r' \\' for r in rows)+'\n'+r'\bottomrule\end{tabular}'
    write(name,text)
def interval(A,B,k='f1',view='native',group='overall'):
    r=ci[(ci.A==A)&(ci.B==B)&(ci.metric==k)&(ci['view']==view)&(ci.group==group)];assert len(r)==1
    r=r.iloc[0];audit.append(dict(method=A+' minus '+B,view=view,group=group,metric=k+'_ci',value=f'{r.ci95_low},{r.ci95_high}',format='paired interval'))
    scale=100 if k in ['f1','recall','precision','rx_f1','rx_recall','rx_precision'] else 1
    return f'[{r.ci95_low*scale:+.2f}, {r.ci95_high*scale:+.2f}]'

macros=[]
for prefix,m in [('SU','JO-SU-40'),('Gate','GateOnly'),('Trust','AdaptiveSense+TrustLog')]:
    for suffix,k in [('Recall','recall'),('Fone','f1'),('Precision','precision'),('RxFone','rx_f1')]:macros.append(r'\newcommand{'+chr(92)+prefix+suffix+'}{'+val(m,k)+r'\%}')
    for suffix,k in [('Samples','samples'),('Bytes','binary_v1_bytes'),('False','fault_induced_false')]:macros.append(r'\newcommand{'+chr(92)+prefix+suffix+'}{'+val(m,k,fmt='int')+'}')
for k,n in [('Delta','DeltaThreshold'),('Variance','VarianceThreshold'),('Rao-inspired','RaoThreshold')]:macros.append(r'\newcommand{'+chr(92)+n+'}{'+str(selection['thresholds'][k])+'}')
write('macros.tex','\n'.join(macros))
main=['AdaptiveSense','AdaptiveSense+TrustLog','GateOnly','GateOnly+U','JO-S','JO-SU-20','JO-SU-30','JO-SU-40']+[f'Fixed-{c}+C11' for c in [5,10,20,30,40,60]]+[f'{k}-c40+C11' for k in ['Delta','Variance','Rao-inspired']]
table('native_main.tex',['Method','P','R','F1','Samples','Bytes','FI'],[[label(m)]+[val(m,k,fmt=f) for k,f in [('precision','pct'),('recall','pct'),('f1','pct'),('samples','int'),('binary_v1_bytes','int'),('fault_induced_false','int')]] for m in main])
# Complete data, including health-free payloads, duplicate matches, and diagnostics.
for view in ['native','common']:
    rr=s[(s['view']==view)&(s.group=='overall')]
    text=r'\begin{small}\setlength{\tabcolsep}{3pt}\begin{longtable}{lrrrrrrr}'+('\n'+r'\caption{Complete G1 '+view+r' operating points; all source scenarios and final seeds.}\label{tab:'+view+r'complete}\\')+'\n'+r'\toprule Method & P & R & F1 & RxF1 & Samples & Bytes & FI \\\midrule\endfirsthead\multicolumn{8}{l}{\textit{Table \thetable{} (continued)}}\\\toprule Method & P & R & F1 & RxF1 & Samples & Bytes & FI \\\midrule\endhead'+'\n'
    for _,r in rr.iterrows():
        m=r.method;family=m.split('-')[0];next_m=rr.loc[rr.index[rr.index.get_loc(r.name)+1],'method'] if rr.index.get_loc(r.name)+1<len(rr) else None
        continuation=next_m is not None and next_m.split('-')[0]==family
        text+=' & '.join([label(m)]+[val(m,k,v=view,fmt=f) for k,f in [('precision','pct'),('recall','pct'),('f1','pct'),('rx_f1','pct'),('samples','int'),('binary_v1_bytes','int'),('fault_induced_false','int')]])+(r' \\*' if continuation else r' \\')+'\n'
    text+=r'\bottomrule\end{longtable}\end{small}';write(view+'_complete.tex',text)

brows=[]
for _,b in budget[budget['view']=='native'].iterrows():
    dR=(b.target_recall-b.recall)*100;dF=(b.target_f1-b.f1)*100
    brows.append([label(b.target),label(b.method).replace('+C11',''),f'{b.minimum:.0f}/{b.cap:.0f}',f'{b.test_gap*100:+.2f}'+r'\%',f'{dR:+.2f}',f'{dF:+.2f}',interval(b.target,b.method),('yes' if b.within_5pct else 'no')])
table('budgets.tex',['Target','Independent+C11','Min/cap','Gap',r'$\Delta$R',r'$\Delta$F1','F1 CI',r'Within 5\%'],brows)

groups=['clean','range','spike','stuck','drift','missing','invalid','stable_offset']
rows=[]
for g in groups:
    group='fault:'+g;rows.append([esc(g)]+[val(m,'recall',group) for m in ['GateOnly','JO-SU-40','Fixed-30+C11']]+[val(m,'fault_induced_false',group,fmt='int') for m in ['GateOnly','JO-SU-40','Fixed-30+C11']])
table('faults.tex',['Fault','Gate R','SU40 R','Fixed30 R','Gate FI','SU40 FI','Fixed30 FI'],rows)
boundary=['GateOnly','GateOnly+U','JO-SU-20','JO-SU-40','Fixed-20+C11','Fixed-30+C11']+[f'{k}-budget-SU40+C11' for k in ['Delta','Variance','Rao-inspired']]
table('boundaries.tex',['Mode','Short','Long','Same','Cross','FD','Delay(s)','Age(s)'],[[label(m)]+[val(m,'recall',g) for g in ['profile:short','profile:long','relation:same','relation:cross']]+[val(m,'fault_detection_rate'),val(m,'event_delay_s',fmt='float'),val(m,'pooled_age_p95_s',fmt='int')+'/'+val(m,'pooled_age_max_s',fmt='int')] for m in boundary])

communication=['AdaptiveSense+TrustLog','GateOnly','GateOnly+U','JO-S','JO-SU-20','JO-SU-30','JO-SU-40']+[k+'-c40+C11+U' for k in ['Delta','Variance','Rao-inspired']]
table('communication.tex',['Mode','Tx','B/Tx','Age P95/max(s)','Missed','Lag E/H(s)'],[[label(m),val(m,'uploads',fmt='int'),val(m,'average_upload_bytes',fmt='float'),val(m,'pooled_age_p95_s',fmt='int')+'/'+val(m,'pooled_age_max_s',fmt='int'),val(m,'important_edges_unreported',fmt='int'),val(m,'event_edge_delay_max_s',fmt='int')+'/'+val(m,'health_edge_delay_max_s',fmt='int')] for m in communication])
a=row('JO-SU-40');g=row('GateOnly');t=row('AdaptiveSense+TrustLog');f=row('Fixed-30+C11')
nb=budget[budget['view']=='native'];qualified=nb[nb.within_5pct];su_b=nb[nb.target=='JO-SU-40'];wins=int((su_b.target_f1>su_b.f1).sum());losses=int((su_b.target_f1<su_b.f1).sum())
abstract_controls=[]
for _,r in su_b.iterrows():
    abstract_controls.append(f"{r.method.split('-budget-')[0]} F1 {r.f1*100:.2f}\\% (sample gap {r.test_gap*100:+.2f}\\%)")
write('abstract_results.tex',f'JO-SU-40 achieved {val("JO-SU-40","recall")}\\% Recall and {val("JO-SU-40","f1")}\\% F1 with {val("JO-SU-40","samples",fmt="int")} samples and {val("JO-SU-40","binary_v1_bytes",fmt="int")} application bytes. Development-selected SU40-budget controls yielded '+ '; '.join(abstract_controls)+'. Individual paired intervals and budget qualification are reported.')
unmatched=su_b[~su_b.within_5pct]
if len(unmatched):
    with (TABLES/'abstract_results.tex').open('a') as fh:fh.write(' '+', '.join(r.method.split('-budget-')[0] for _,r in unmatched.iterrows())+' failed the 5\\% matching tolerance.\n')
write('abstract_boundary.tex',f'Against GateOnly, SU40 used {(a.samples/g.samples-1)*100:+.2f}\\% samples and produced {a.fault_induced_false-g.fault_induced_false:+.0f} additional operational fault-induced false reports.')
write('results_overview.tex',f'The final evaluation contains {int(json.loads((OUT/"test/manifest.json").read_text())["runs"]):,} scored method/view runs on {int(a.runs)} seed--scenario streams, with {int(a.n_events)} labeled events per operating point. Table~\\ref{{tab:native}} separates the costs of native behavior. Compared with AS+C11, SU40 changed Recall from {val("AdaptiveSense+TrustLog","recall")}\\% to {val("JO-SU-40","recall")}\\%, F1 from {val("AdaptiveSense+TrustLog","f1")}\\% to {val("JO-SU-40","f1")}\\%, samples by {(a.samples/t.samples-1)*100:+.2f}\\%, and bytes by {(a.binary_v1_bytes/t.binary_v1_bytes-1)*100:+.2f}\\%. This comparison alone is insufficient: against GateOnly the F1 difference is {(a.f1-g.f1)*100:+.2f} points, 95\\% CI {interval("JO-SU-40","GateOnly")}, accompanied by {(a.samples/g.samples-1)*100:+.2f}\\% samples and {a.fault_induced_false-g.fault_induced_false:+.0f} fault-induced reports. Fixed competitors and all adverse modes remain visible.')
parts=[f'{len(qualified)}/{len(nb)} native independent budget points remained within 5\\% in the held-out split. No parameters were adjusted.']
for _,b in nb.iterrows():parts.append(f'{label(b.target)} versus {label(b.method)}: final sample gap {b.test_gap*100:+.2f}\\%, target-minus-independent F1 {(b.target_f1-b.f1)*100:+.2f} points, 95\\% CI {interval(b.target,b.method)}; '+('qualifies as approximately matched.' if b.within_5pct else 'does not qualify as matched.'))
write('budget_text.tex',' '.join(parts))
write('fault_text.tex',f'Table~\\ref{{tab:faults}} includes every fault class. For drift, GateOnly/SU40 Recall is {val("GateOnly","recall","fault:drift")}\\%/{val("JO-SU-40","recall","fault:drift")}\\%, and operational induced counts are {val("GateOnly","fault_induced_false","fault:drift",fmt="int")}/{val("JO-SU-40","fault_induced_false","fault:drift",fmt="int")}. Stable-offset groups yield Recall {val("GateOnly","recall","fault:stable_offset")}\\%/{val("JO-SU-40","recall","fault:stable_offset")}\\%. These failures are not removed from overall totals. Short-event Recall is {val("GateOnly","recall","profile:short")}\\% for GateOnly and {val("JO-SU-40","recall","profile:short")}\\% for SU40; long-event rates are separately tabulated.')
parts=[]
for m in ['GateOnly','GateOnly+U','JO-SU-20','JO-SU-40']:
    r=row(m);parts.append(f'{label(m)}: sender TP/FP/FN {int(r.tp)}/{int(r.false_reports)}/{int(r.missed)}, receiver {int(r.rx_tp)}/{int(r.rx_false_reports)}/{int(r.rx_missed)}; receiver F1 {r.rx_f1*100:.2f}\\%; sampled important edges unreported {int(r.important_edges_unreported)}, maximum reported edge delay {r.important_edge_delay_max_s:.0f}s.')
parts.append('All corresponding local detections, separate event/health edge delays, uploads, mean bytes, receiver age and reconstruction coverage remain in the complete machine-readable summaries.')
write('receiver_text.tex',' '.join(parts))
parts=[]
for k in ['Delta','Variance','Rao-inspired']:
    m=k+'-c40+C11';u=m+'+U';r=row(m);z=row(u)
    assert r.samples==z.samples and r.tp==z.tp and r.false_reports==z.false_reports
    parts.append(f'Adding U to {label(m)} preserved sender TP/FP and sample counts while changing bytes by {(z.binary_v1_bytes/r.binary_v1_bytes-1)*100:+.2f}\\% and pooled age P95 from {r.pooled_age_p95_s:.0f}s to {z.pooled_age_p95_s:.0f}s; important missed edges were {int(z.important_edges_unreported)}.')
parts.append(f'In the common-detector view SU40 F1 was {val("JO-SU-40","f1",v="common")}\\%, compared with its native {val("JO-SU-40","f1")}\\%. The difference is a detector/gating comparison under the same sample times, not a new schedule.')
gate_rao=budget[(budget['view']=='native')&(budget.target=='GateOnly')&(budget.method=='Rao-inspired-budget-Gate+C11')].iloc[0]
parts.append(f'At the lower Gate budget, Rao-inspired F1 was {gate_rao.f1*100:.2f}\\% versus GateOnly {gate_rao.target_f1*100:.2f}\\%; Gate-minus-Rao F1 CI {interval("GateOnly",gate_rao.method)}. This adverse quality comparison remains despite higher independent-method fault-induced reporting. GateOnly is not universally optimal. ')
grx=row('GateOnly');urx=row('GateOnly+U')
parts.append(f'Gate+U also restored a received false edge: receiver false reports changed from {int(grx.rx_false_reports)} to {int(urx.rx_false_reports)}, although sender reports were unchanged. Complete edge delivery does not necessarily improve receiver F1. ')
write('discussion_results.tex',' '.join(parts))
qsu=su_b[su_b.within_5pct]
conclusion=f'The held-out results show a conditional operating tradeoff: SU40 F1 was {val("JO-SU-40","f1")}\\%, with {val("JO-SU-40","samples",fmt="int")} samples and {val("JO-SU-40","binary_v1_bytes",fmt="int")} bytes, while GateOnly F1 was {val("GateOnly","f1")}\\%. Of the three SU40-targeted independent controls, {len(qsu)} qualified within 5\\% on final samples. '
for _,r in qsu.iterrows():
    conclusion+=f'Against {r.method.split("-budget-")[0]}, the F1 difference was {(r.target_f1-r.f1)*100:+.2f} points, 95\\% CI {interval(r.target,r.method)}. '
for _,r in su_b[~su_b.within_5pct].iterrows():
    conclusion+=f'{r.method.split("-budget-")[0]} had a {r.test_gap*100:+.2f}\\% sample gap and cannot support a matched-budget superiority claim. '
conclusion+='Full native and common-view comparisons, adverse lower-budget results and interval uncertainty prevent a universal-superiority conclusion.'
write('conclusion_results.tex',conclusion)

for name in ['native_tradeoffs.png','common_tradeoffs.png','resource_sensitivity.png']:shutil.copyfile(OUT/'test/analysis'/name,FIGS/name)
pd.DataFrame(audit).to_csv(TABLES/'data_audit.csv',index=False)
budget.to_csv(TABLES/'budget_data_audit.csv',index=False)
# Keep exact source hashes in the paper artifact.
import hashlib
files=[OUT/'test/analysis/resource_sensitivity.csv',OUT/'test/metrics.csv',OUT/'test/analysis/summary.csv',OUT/'test/analysis/paired_intervals.csv',OUT/'test/analysis/budget_comparisons.csv']
(PAPER/'tables/source_fingerprints.json').write_text(json.dumps({str(p.resolve().relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2)+'\n')
from paper_publication_figures import render
render(FIGS,OUT/'test/analysis')
print('generated',len(audit),'audited numeric cells and all empirical paragraphs')
# The original G1 bindings above remain literal and unchanged. Append a separate
# G2 binding only after its independent final analysis is complete.
if (ROOT/'results/tais-transfer/test/analysis/manifest.json').exists():
    from build_transfer_paper import main as build_transfer
    build_transfer()

# Major revision: regenerate presentation and post-hoc qualification from frozen CSVs.
from paper_review_artifacts import main as build_review
build_review()
