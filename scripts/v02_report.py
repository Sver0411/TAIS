"""Build v0.2 report exclusively from completed split outputs."""
import sys,json
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src')]
from tais import ROOT
import pandas as pd

def fmt(v):
    if pd.isna(v):return 'N/A'
    if isinstance(v,str):return v
    return f'{v:.6g}'

def table(df,columns):
    return '| '+' | '.join(columns)+' |\n| '+' | '.join(['---']*len(columns))+' |\n'+''.join('| '+' | '.join(fmt(r[c]) for c in columns)+' |\n' for _,r in df.iterrows())

def main():
    chunks=['# TAIS v0.2 research report\n\nThis report is generated from actual completed outputs. The design was committed at8222873 before implementation1dbc102; v0.1 source/config/results remain intact. Seeds20–49 are diagnostic only; the new final split is50–99. Frozen selection rule: no parameter selection, all three inherited threshold multipliers retained.\n',
    '## Root causes and mechanism\n\n[Failure forensics](FAILURE_ANALYSIS_V0.1.md) proves400 observation-identical event/no-event pairs across old seeds. All18 extra old same-channel AS matches occur identically without the event in range scenarios. The old pooled recall gap therefore does not establish loss of18 observable events. Sampling/debounce, C offset/stuck blind spots and degraded confirmation churn are distinct causes.\n\nThe selected mechanism is one bounded persistent episode: pre-update EMA reference, signed displacement, >=3 sampled confirmations, >=10 s duration, <=120 s pending window, existing upstream debounce and unchanged hard FAULT exclusion. Candidate evidence survives a drop below scheduler ALERT entry. Full V02 adds5 s demand; V02-Passive retains evidence with ordinary scheduling. [Exact rules and frozen protocol](V02_DESIGN.md). This is observational persistence, not causal identification.\n']
    cols=['method','multiplier','n_events','tp','missed','recall','fault_induced_false','false_reports','samples','uploads','payload_bytes']
    for split in ['development','validation','test']:
        dest=ROOT/'results/v0.2'/split
        m=json.loads((dest/'manifest.json').read_text());summary=pd.read_csv(dest/'summary.csv')
        chunks.append(f'## {split}: {m["runs"]:,} scored runs\n\nSeeds{m["seeds"]}; actual source commit`{m["source_commit"]}`. [Raw metrics](../results/v0.2/{split}/metrics.csv), [event records](../results/v0.2/{split}/events.csv), [manifest and source/archive hashes](../results/v0.2/{split}/manifest.json).\n\n'+table(summary,cols))
    dest=ROOT/'results/v0.2/test';group=pd.read_csv(dest/'by_relationship.csv');info=pd.read_csv(dest/'by_information_class.csv');summary=pd.read_csv(dest/'summary.csv');ci=pd.read_csv(dest/'paired_bootstrap.csv')
    chunks.append('## New independent test: temporal relationships, original thresholds\n\n'+table(group[(group.multiplier==1)&group.method.isin(['AdaptiveSense','GateOnly','TAIS','V02','V02-Passive'])],['relationship']+cols))
    chunks.append('## Same-channel information classes (all declared points)\n\nMatched TP remains the unchanged temporal metric, including coincidental matches in observation-erased cases. It cannot demonstrate causal event sensitivity in those cases.\n\n'+table(info[(info.information_class!='other')&info.method.isin(['AdaptiveSense','GateOnly','TAIS','V02','V02-Passive'])],['information_class']+cols))
    select=ci[ci.group.isin(['all','relationship:same','relationship:cross','relationship:clean','information_class:same_additive']) & ci.metric.isin(['recall','fault_induced_false','samples','uploads','payload_bytes']) & ci.reference.isin(['TAIS','V02-Passive'])]
    chunks.append('## Paired differences: V02 minus reference, every threshold point\n\nCounts are per-seed batches of all scenarios in the stated group; recall is a fraction (x100 gives percentage points). Whole-seed2000-replicate percentile95% CIs, RNG731; descriptive and not multiplicity-adjusted. Delay comparisons condition on detection and are not a missed-event penalty. [Complete paired CIs, including AS/GateOnly and secondary metrics](../results/v0.2/test/paired_bootstrap.csv), [absolute CIs](../results/v0.2/test/confidence_intervals.csv).\n\n'+table(select,['group','multiplier','reference','metric','mean_difference','ci_low','ci_high','seeds']))
    chunks.append('## Secondary independent-test metrics at original thresholds\n\nMAE/RMSE are mean per-run causal-hold reconstruction errors, in separate channel units; finite faulty readings remain included. Delays exclude misses; counts above retain them.\n\n'+table(summary[summary.multiplier==1],['method','latency_mean_s','false_per_hour','fault_detection_rate','fault_latency_mean_s','confirmation_samples','diagnostic_only_samples','sample_mae_temperature','sample_rmse_temperature','sample_mae_humidity','sample_rmse_humidity','upload_mae_temperature','upload_rmse_temperature','upload_mae_humidity','upload_rmse_humidity']))
    chunks.append('## All-type and profile comparisons\n\n[Every scenario](../results/v0.2/test/by_scenario.csv), [fault type](../results/v0.2/test/by_fault_type.csv), [joint duration/intensity profile](../results/v0.2/test/by_profile.csv). Short/long vary event duration, fault duration and intensity together; these do not identify independent effects. Sequential spikes are separately labeled and remain included overall.\n\n![Recall versus uploads](../results/v0.2/test/recall_uploads.png)\n\n![Fault false reports versus recall](../results/v0.2/test/faultfalse_recall.png)\n')
    (ROOT/'docs/RESEARCH_REPORT_V0.2.md').write_text('\n\n'.join(chunks)+'\n')
    print('Generated actual-data tables; append interpretation after reviewing them.')
if __name__=='__main__':main()
