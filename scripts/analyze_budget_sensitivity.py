#!/usr/bin/env python3
"""Post-hoc qualification only: read frozen totals, never replay/select a policy."""
import hashlib,json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/tais-paper-review'
INPUTS={'G1':'results/tais-paper/test/analysis/summary.csv','G2':'results/tais-transfer/test/analysis/summary.csv'}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def analyze():
    """Write post-hoc 2/5/10% eligibility for all existing control-target totals.

    Changing the displayed tolerance never selects new parameters or new data.
    The original frozen qualification band remains 5%; this is a writer."""
    rows=[]
    for generator,path in INPUTS.items():
        d=pd.read_csv(ROOT/path);d=d[d.group=='overall']
        if 'view' in d:d=d[d['view']=='native']
        d=d.set_index('method');controls=[m for m in d.index if m.endswith('+C11')]
        for m in controls:
            for target in ['GateOnly','JO-SU-40']:
                samples=int(d.loc[m,'samples']);target_samples=int(d.loc[target,'samples']);gap=samples/target_samples-1
                selected_pair=('-budget-Gate+' in m and target=='GateOnly') or ('-budget-SU40+' in m and target=='JO-SU-40')
                rows.append(dict(generator=generator,method=m,target=target,samples=samples,target_samples=target_samples,relative_gap=gap,gap_percent=gap*100,within_2pct=abs(gap)<=.02,within_5pct=abs(gap)<=.05,within_10pct=abs(gap)<=.10,original_budget_pair=selected_pair,discussion_focus=selected_pair or (m=='Fixed-20+C11' and target=='JO-SU-40'),source=path))
    OUT.mkdir(parents=True,exist_ok=True);pd.DataFrame(rows).to_csv(OUT/'budget_sensitivity.csv',index=False)
    meta=dict(status='PASS',analysis='Post-hoc tolerance sensitivity of existing operating points; no algorithm/parameter selection and no new observations',definition='gap=control samples/target samples-1; absolute gap <= tolerance',thresholds=[.02,.05,.10],historical_rule='5% reproduces the original frozen rule; the three-threshold comparison is post hoc, not a new preregistration',inputs={p:sha(ROOT/p) for p in INPUTS.values()},output_sha256=sha(OUT/'budget_sensitivity.csv'),rows=len(rows))
    (OUT/'budget_sensitivity_manifest.json').write_text(json.dumps(meta,indent=2)+'\n');return rows
if __name__=='__main__':
    rows=analyze();print(pd.DataFrame(rows).query('discussion_focus')[['generator','method','target','gap_percent','within_2pct','within_5pct','within_10pct']].to_string(index=False));print('All',len(rows),'actual control-target pairs retained')
