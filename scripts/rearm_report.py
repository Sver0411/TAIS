"""Render completed matrices into a new report, preserving every older report."""
import sys,json
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src')]
from tais import ROOT
import pandas as pd

def fmt(v):
 if pd.isna(v):return 'N/A'
 if isinstance(v,str):return v
 return f'{v:.6g}'
def table(df,cols):return '| '+' | '.join(cols)+' |\n| '+' | '.join(['---']*len(cols))+' |\n'+''.join('| '+' | '.join(fmt(r[c]) for c in cols)+' |\n' for _,r in df.iterrows())
def main():
 chunks=['# BLOCKED reference-return repair: independent report\n\n[Committed design](BLOCKED_REARM_FIX.md). The repair synchronizes one unconfirmed reference-return cancellation with the existing scorer reset. It suppresses that sample itself, never clears on health change alone, and retains all numerical parameters and hard FAULT exclusion. Original v0.1/v0.2 modules and experimental artifacts remain unchanged. Seed91 is regression evidence only.\n',
 '## Verified small gate\n\nOriginal regression forced with --runxfail actually failed. After repair its unchanged TP==1 assertion passes normally: report675, samples78 unchanged, uploads39→40. Initial new suite66 passed/2 failed; those two all-points detection assertions remain strict expected failures at1.5 because original TAIS also cannot satisfy the unchanged debounce. Their assertions/logs are retained; no scoring threshold was changed. Full test and baseline-replay logs are under results/blocked-rearm/diagnosis.\n\n![Known regression](../results/blocked-rearm/diagnosis/before-after.png)\n']
 cols=['method','multiplier','tp','n_events','recall','fault_induced_false','false_reports','latency_mean_s','samples','uploads','payload_bytes']
 for split in ['development','validation','test']:
  dest=ROOT/f'results/blocked-rearm/{split}';m=json.loads((dest/'manifest.json').read_text())
  chunks.append(f'## {split}: {m["runs"]} scored runs\n\nSeeds{m["seeds"]}; actual source`{m["source_commit"]}`. [Manifest](../results/blocked-rearm/{split}/manifest.json), [all raw metrics](../results/blocked-rearm/{split}/metrics.csv), [all event rows](../results/blocked-rearm/{split}/events.csv), [every changed event](../results/blocked-rearm/{split}/changed_events.csv).\n')
  for suite in ['main','aligned_recovery']:
   s=pd.read_csv(dest/suite/'summary.csv');chunks.append('### '+suite+'\n\n'+table(s,cols))
 dest=ROOT/'results/blocked-rearm/test'
 chunks.append('## Independent paired comparisons, repair minus unfixed V02\n\nAll three declared points are retained. Counts are mean differences per paired seed batch in the indicated suite/group; recall fractions x100 give percentage points.2000 whole-seed bootstrap draws, RNG731, descriptive95% percentile CIs without multiplicity adjustment. Delays condition on detected events; misses are reported separately. Main random-jitter distribution and aligned exposure challenge are never pooled.\n')
 for suite in ['main','aligned_recovery']:
  ci=pd.read_csv(dest/suite/'paired_bootstrap.csv');selected=ci[(ci.reference=='V02')&ci.group.isin(['all','relationship:clean','relationship:same','relationship:cross','relationship:same_sequential','relationship:cross_sequential'])&ci.metric.isin(['recall','samples','uploads','payload_bytes','fault_induced_false','false_reports','latency_mean_s'])]
  chunks.append('### '+suite+'\n\n'+table(selected,['group','multiplier','metric','mean_difference','ci_low','ci_high','seeds']))
  g=pd.read_csv(dest/suite/'by_relationship.csv');chunks.append(table(g[(g.multiplier==1)&g.method.isin(['TAIS','V02','V02-Rearm'])],['relationship']+cols))
  chunks.append(f'![Recall/uploads: {suite}](../results/blocked-rearm/test/{suite}/recall_uploads.png)\n\n![False reports/recall: {suite}](../results/blocked-rearm/test/{suite}/faultfalse_recall.png)\n')
 chunks.append('## Interpretation boundaries\n\nThe aligned suite intentionally exposes a sampled impulse at600 followed by a separate event60 s later. It is not natural fault prevalence or concurrent fault/event evidence. A repair may help only this stratum. Main same/cross denote actual overlap; spike same/cross are sequential and remain separately reported. Persistent offset, information-erasing faults and high-threshold debounce remain unresolved. No greenhouse or RF-energy evidence is added. See the final interpretation and limits accompanying these generated tables.\n')
 (ROOT/'docs/BLOCKED_REARM_REPORT.md').write_text('\n\n'.join(chunks)+'\n');print('Generated complete report from actual outputs')
if __name__=='__main__':main()
