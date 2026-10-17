"""Populate report tables solely from completed, verified CSV outputs."""
import hashlib,json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]


def table(frame,columns):
    # Avoid an additional tabulate dependency.
    head='| '+' | '.join(columns.values())+' |\n| '+' | '.join('---' for _ in columns)+' |\n'
    rows=[]
    for _,r in frame.iterrows():
        cells=[]
        for name in columns:
            value=r[name]
            if pd.isna(value):text='N/A'
            elif name in ['recall','fault_detection_rate']:text=f'{value*100:.2f}%'
            elif isinstance(value,float) and value.is_integer():text=str(int(value))
            elif isinstance(value,float):text=f'{value:.3f}'
            else:text=str(value)
            cells.append(text)
        rows.append('| '+' | '.join(cells)+' |')
    return head+'\n'.join(rows)+'\n'


def main():
    sections=[];total=0
    for split in ['development','validation','test']:
        dest=ROOT/'results'/split;manifest=json.loads((dest/'manifest.json').read_text())
        assert hashlib.sha256((dest/'metrics.csv').read_bytes()).hexdigest()==manifest['metrics_sha256']
        total+=manifest['runs'];summary=pd.read_csv(dest/'summary.csv')
        sections.append(f'### {split.capitalize()}: {manifest["runs"]:,} scored runs\n\n'+table(summary,{'method':'Method','multiplier':'Threshold multiplier','recall':'Recall','tp':'TP','missed':'Missed','false_reports':'Strict false reports','fault_induced_false':'Counterfactual-new fault false','samples':'Samples','uploads':'Upload requests','payload_bytes':'Application bytes'})+f'\n[Per-scenario results](../results/{split}/by_scenario.csv), [manifest](../results/{split}/manifest.json), [paired CIs](../results/{split}/paired_bootstrap.csv).\n')
    test=ROOT/'results/test';summary=pd.read_csv(test/'summary.csv');relationship=pd.read_csv(test/'by_relationship.csv');paired=pd.read_csv(test/'paired_bootstrap.csv')
    sections.append('### Independent test: actual temporal relationships\n\nClean controls and sequential spike cases are explicitly separate. `cross` / `same` refer only to true fault/event overlap. The 1-second spike precedes the later event in v0.1; no concurrent-spike claim.\n\n'+table(relationship[(relationship.multiplier==1)&relationship.method.isin(['AdaptiveSense','GateOnly','TAIS'])],{'relationship':'Group','method':'Method','n_events':'Events','recall':'Recall','fault_induced_false':'Fault false','false_reports':'Strict false','uploads':'Requests','samples':'Samples','fault_detection_rate':'Fault diagnosis recall','latency_mean_s':'Event delay s'}))
    focus=paired[(paired.multiplier==1)&paired.relationship.isin(['all','cross','same'])&paired.method.isin(['TAIS','TAIS-minus-GateOnly'])]
    sections.append('### Paired independent-test differences at original thresholds\n\nTAIS rows compare to AdaptiveSense; TAIS-minus-GateOnly rows isolate confirmation. Recall differences are fractions (x100 gives percentage points). Count differences are mean **per seed batch of all scenarios in the stated group**, not per individual 30-minute trace. Intervals are descriptive 95% whole-seed bootstrap CIs, not adjusted hypothesis tests.\n\n'+table(focus,{'relationship':'Group','method':'Difference','metric':'Metric','paired_mean_difference':'Mean difference','ci_low':'CI lower','ci_high':'CI upper'}))
    # Fixed, explicitly disclosed failure probes, retaining all seeds.
    scenario=pd.read_csv(test/'by_scenario.csv')
    probes=['range_same_long','missing_same_long','range_cross_short','stable_offset_none_long','stuck_none_long','spike_same_short']
    selected=scenario[(scenario.multiplier==1)&scenario.scenario.isin(probes)&scenario.method.isin(['AdaptiveSense','GateOnly','TAIS'])]
    sections.append('### Disclosed failure probes\n\nThese fixed probes expose hard replacement/missingness, short healthy-channel events, offset/stuck blind spots and sequential spike history. The complete 45-scenario table remains available, including every unfavorable point.\n\n'+table(selected,{'scenario':'Scenario','method':'Method','n_events':'Events','tp':'TP','fault_induced_false':'Fault false','fault_detection_rate':'Fault diagnosis recall','samples':'Samples','uploads':'Requests'}))
    sections.append('### Cost comparison at original thresholds\n')
    ref=summary[(summary.method=='AdaptiveSense')&(summary.multiplier==1)].iloc[0]
    log=summary[(summary.method=='AdaptiveSense+TrustLog')&(summary.multiplier==1)].iloc[0]
    tais=summary[(summary.method=='TAIS')&(summary.multiplier==1)].iloc[0]
    gate=summary[(summary.method=='GateOnly')&(summary.multiplier==1)].iloc[0]
    sections.append(f'Full TAIS vs plain AdaptiveSense: uploads {(tais.uploads/ref.uploads-1)*100:+.2f}%, samples {(tais.samples/ref.samples-1)*100:+.2f}%, serialized application bytes {(tais.payload_bytes/ref.payload_bytes-1)*100:+.2f}%. Compared with diagnostic-only logging (same health metadata), TAIS bytes change {(tais.payload_bytes/log.payload_bytes-1)*100:+.2f}%. Metadata therefore matters; upload reductions do not establish lower total payload versus plain AdaptiveSense, much less lower radio energy.\n')
    sections.append(f'At this fixed point, TAIS recall is {tais.recall*100:.2f}% vs GateOnly {gate.recall*100:.2f}%; it uses {int(tais.samples-gate.samples):+,} samples and {int(tais.uploads-gate.uploads):+,} requests, with {int(tais.fault_induced_false-gate.fault_induced_false):+,} operational fault false reports. The ablation does not justify assuming confirmation helps. All other multipliers remain reported above.\n')
    secondary=summary[(summary.multiplier==1)&summary.method.isin(['AdaptiveSense','AdaptiveSense+TrustLog','GateOnly','TAIS','Fixed-5','Fixed-60'])]
    sections.append('### Secondary metrics at original thresholds\n\nDelays are conditional on matched events or detected fault episodes; misses are separately counted. Reconstruction uses the same naive causal hold from all finite observations, including annotated faulty values. MAE/RMSE retain C and %RH units, so they must not be pooled into one physical error.\n\n'+table(secondary,{'method':'Method','latency_mean_s':'Event delay s','false_per_hour':'False reports/h','sample_mae_temperature':'Sample MAE C','sample_rmse_temperature':'Sample RMSE C','sample_mae_humidity':'Sample MAE %RH','sample_rmse_humidity':'Sample RMSE %RH'})+'\n'+table(secondary,{'method':'Method','upload_mae_temperature':'Upload MAE C','upload_rmse_temperature':'Upload RMSE C','upload_mae_humidity':'Upload MAE %RH','upload_rmse_humidity':'Upload RMSE %RH'}))
    sections.append('Diagnostic demand is not automatically extra sampling. The paired total sample difference above measures actual incremental cost. Plain/fixed methods have no health detector (zero detected episodes by construction). Stable-offset has no dedicated C flag; type-specific counts expose this distinction.\n\n'+table(secondary,{'method':'Method','fault_episodes':'Fault episodes','fault_detected':'Any-flag detected','fault_type_detected':'Matching-type detected','fault_detection_rate':'Diagnosis recall','fault_latency_mean_s':'Fault delay s','diagnostic_samples':'Diagnostic demand','confirmation_samples':'Confirmation demand','diagnostic_only_samples':'Diagnostic-only cycles'}))
    sections.append('### Trade-off curves\n\n![All operating points and policy zoom](../results/test/tradeoff.png)\n\nThe full axes include every fixed baseline. The zoom retains all policy operating points. [Nearest actual budget comparisons](../results/test/budget_comparison.csv) include the budget gap; no interpolated or hand-picked matched-cost claim is made.\n')
    sections.insert(0,f'Completed scored runs: **{total:,}**. Raw archived replay hashes and exact metric checks are recorded per split.\n')
    path=ROOT/'docs/RESEARCH_REPORT.md';text=path.read_text()
    prefix=text.split('<!-- RESULTS_START -->')[0]
    suffix=text.split('<!-- RESULTS_END -->')[-1] if '<!-- RESULTS_END -->' in text else ''
    path.write_text(prefix+'<!-- RESULTS_START -->\n\n'+'\n'.join(sections)+'\n<!-- RESULTS_END -->'+suffix)
    print('Report built from',total,'scored runs')
if __name__=='__main__':main()
