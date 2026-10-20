#!/usr/bin/env python3
"""Render FO-1 evidence tables from already-frozen analysis, never run a policy."""
import csv
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from tais.budget_eval import sha
from run_fault_event_observability import RESULTS,csv_write
from analyze_fault_event_observability import read_rows


def main():
    analysis=RESULTS/'test/analysis'
    if not (RESULTS/'test/verification.json').exists():raise ValueError('Wait for complete independent metric verification')
    summary=list(csv.DictReader((analysis/'summary.csv').open()))
    cis=list(csv.DictReader((analysis/'paired_intervals.csv').open()))
    primary=list(csv.DictReader((analysis/'timing_interactions.csv').open()))
    rows=read_rows(RESULTS/'test/metrics.csv');out=RESULTS/'interpretation'
    if out.exists():raise FileExistsError('Never overwrite interpretation')
    out.mkdir()
    def selected(group,method):return next(r for r in summary if r['group']==group and r['method']==method)
    def number(r,k):return float(r[k]) if r[k] else None
    def fmt(v,scale=1,digits=3):return 'N/A' if v is None or v=='' else f'{float(v)*scale:,.{digits}f}'
    def count(r,k):return fmt(number(r,k),digits=0)
    def paired(group,metric):return next(r for r in cis if r['group']==group and r['metric']==metric)
    def ci(group,metric,scale=1):
        r=paired(group,metric);return f"{fmt(r['tais_minus_gate'],scale)} [{fmt(r['ci95_low'],scale)}, {fmt(r['ci95_high'],scale)}]"
    def table(header,body):return '\n'.join(['| '+' | '.join(header)+' |','| '+' | '.join(['---']*len(header))+' |']+['| '+' | '.join(map(str,r))+' |' for r in body])
    timing=[]
    plan=json.loads((ROOT/'configs/fault-event-observability.json').read_text())
    for kind in ('spike','drift'):
        for relation in ('same','cross'):
            for profile in ('short','long'):
                for dt in plan['offsets'][kind]:
                    group=f'{kind}:{relation}:{profile}:dt:{dt}';g=selected(group,'GateOnly');t=selected(group,'TAIS')
                    timing.append(dict(kind=kind,relationship=relation,profile=profile,offset_s=dt,group=group,
                        truth=g['n_events'],gate_tp=g['tp'],tais_tp=t['tp'],gate_induced=g['fault_induced_false'],tais_induced=t['fault_induced_false'],
                        gate_samples=g['samples'],tais_samples=t['samples'],gate_uploads=g['uploads'],tais_uploads=t['uploads'],
                        recall_difference_pp=ci(group,'recall',100),fault_induced_difference_ci95=ci(group,'fault_induced_false')))
    csv_write(out/'all56_timing_cells.csv',timing)
    evidence=[]
    for method in plan['methods']:
        for group in ('overall','kind:spike','kind:drift','same','cross','spike:temporal:overlap','drift:temporal:overlap'):
            if group in ('same','cross'):used=[r for r in rows if r['method']==method and r['relationship']==group and r['n_events']]
            elif group=='overall':used=[r for r in rows if r['method']==method]
            elif group.startswith('kind:'):used=[r for r in rows if r['method']==method and r['fault_kind']==group[5:]]
            else:
                k,_,v=group.split(':');used=[r for r in rows if r['method']==method and r['fault_kind']==k and r['temporal']==v]
            faulty=[r for r in used if r['fault_episodes']];events=[r for r in used if r['n_events']]
            evidence.append(dict(method=method,group=group,runs=len(used),fault_runs=len(faulty),fault_completely_unsampled=sum(r['sampled_fault_points']==0 for r in faulty),
                event_runs=len(events),event_completely_unsampled=sum(r['sampled_event_points']==0 for r in events),
                fault_flagged_event_missed=sum(r['fault_flagged_event_missed'] for r in used),
                event_detected_no_fault_flag=sum(r['event_detected_no_fault_flag'] for r in used),
                event_detected_wrong_fault_type=sum(r['event_detected_wrong_fault_type'] for r in used),
                event_and_fault_detected=sum(r['event_and_fault_detected'] for r in used)))
    csv_write(out/'evidence_opportunities.csv',evidence)
    boundaries=[]
    for method in plan['methods']:
        for kind in ('range','missing','invalid','stuck'):
            for profile in ('short','long'):
                a=[r for r in rows if r['method']==method and r['scenario']==f'{kind}_same_{profile}']
                b=[r for r in rows if r['method']==method and r['scenario']==f'{kind}_none_{profile}']
                boundaries.append(dict(method=method,kind=kind,profile=profile,paired_worlds=len(a),event_truth=sum(r['n_events'] for r in a),
                    event_world_tp=sum(r['tp'] for r in a),no_event_world_tp=sum(r['tp'] for r in b),
                    event_world_unmatched=sum(r['false_reports'] for r in a),no_event_world_unmatched=sum(r['false_reports'] for r in b),
                    event_world_report_count=sum(r['tp']+r['false_reports'] for r in a),no_event_world_report_count=sum(r['tp']+r['false_reports'] for r in b)))
    csv_write(out/'equivalence_matching_boundary.csv',boundaries)
    counts=[]
    for phase in ('development','validation','test'):
        m=json.loads((RESULTS/phase/'manifest.json').read_text())
        counts.append(dict(phase=phase,seeds=len(m['seeds']),first_seed=m['seeds'][0],last_seed=m['seeds'][-1],scored_runs=m['runs'],counterfactual_runs=m['counterfactual_runs'],artifacts=len(m['artifacts']),manifest_sha256=sha(RESULTS/phase/'manifest.json')))
    csv_write(out/'phase_counts.csv',counts)
    overall=[selected('overall',m) for m in plan['methods']]
    lines=['# FO-1: timing dependence and limits of observed evidence',
      '\n**Completed synthetic benchmark; unchanged policies, no tuning. BM-1 confirmation NO-GO is preserved.**',
      '\n## Scope, freezing and actual execution',
      '\nBase `5b06d2feae44db2b3503697d246f51c43e5d8f2e`. Protocol commit `02c67a7293be1480cb99cd7f6dd19a6c82898235`; implementation `4b85e94ca9d266c8031ca55c1b5165e878635337`; completed software log `b7551fb87934f31048861264d7a8e71e3f45ee55`; **pre-final lock `1030868705e0ca004392ad1a5d3c597f66478a23`**. The protocol and code were frozen before new-noise generation; development/validation did not select parameters. [Protocol](FAULT_EVENT_OBSERVABILITY_PREREGISTRATION.md) and [final lock](../results/fault-event-observability/final-lock.json) remain unchanged.',
      '\n'+table(['Phase','Seeds','Scored runs','Offline clean counterfactuals','Gzip artifacts'],[[r['phase'],f"{r['first_seed']}–{r['last_seed']}",r['scored_runs'],r['counterfactual_runs'],r['artifacts']] for r in counts]),
      '\nAll93 scenarios ×three methods at multiplier1.0. Original45 delegated byte-identically to historical generation;48 added timing cases exclude already-counted default+60. Final240–299 ran once per method/case; metric verification reads saved artifacts without invoking policy. Seeds0–299 are now used/reserved. These are new random seeds under the same controlled model, **not external real-environment validation**.',
      '\nSampling/uploads differ naturally; this is **not a budget-matched causal policy comparison**. Short/long jointly change fault duration/intensity and event duration. Temperature/humidity have different amplitudes, noise floors and trust settings. Cross/same results do not isolate topology alone or establish a new fusion algorithm.',
      '\n## Full final outcomes',
      '\n'+table(['Method','TP / truth','Recall','Precision','F1','Misses','Strict unmatched','Fault-induced'],[[r['method'],f"{count(r,'tp')} / {count(r,'n_events')}",fmt(r['recall'],100)+'%',fmt(r['precision'],100)+'%',fmt(r['f1'],100)+'%',count(r,'missed'),count(r,'false_reports'),count(r,'fault_induced_false')] for r in overall]),
      '\n'+table(['Method','Samples','Uploads','Exact JSON bytes','Event delay(s)','Fault flags / episodes','Flag delay(s)'],[[r['method'],count(r,'samples'),count(r,'uploads'),count(r,'payload_bytes'),fmt(r['latency_mean_s']),('N/A (not implemented)' if r['method']=='AdaptiveSense' else f"{count(r,'fault_detected')} / {count(r,'fault_episodes')}"),('N/A' if r['method']=='AdaptiveSense' else fmt(r['fault_latency_mean_s']))] for r in overall]),
      '\nOverall TAIS−GateOnly paired differences (whole-seed95%CIs): Recall '+ci('overall','recall',100)+'pp; fault-induced '+ci('overall','fault_induced_false')+'; strict unmatched '+ci('overall','false_reports')+'; samples '+ci('overall','samples')+'; uploads '+ci('overall','uploads')+'; JSON bytes '+ci('overall','payload_bytes')+'. The overall mixture is a benchmark weighting, not natural occurrence prevalence.',
      '\nDelay is conditional on matched truth; [common-matched delay](../results/fault-event-observability/test/analysis/common_matched_delay.json) supplies the paired intersection and misses remain explicit. Diagnostic/confirmation counts overlap and do not automatically represent extra samples. Counterfactual incremental samples/uploads/JSON are preserved separately; intervention-induced schedule changes prevent a unique diagnostic-only causal interpretation.',
      '\n## All spike and drift timing points',
      '\nOffsets refer to **waveform plan start**. Physical truth starts2–3seconds later because of the unchanged threshold/ramp label. Spike offsets−1,0,+1 are sequential with respect to labeled truth, even when part of the physical ramp may already exist. Spike−10 overlaps truth in both profiles;−60 overlaps only long events. All temporal groups use actual interval/shared-point labels, not offset sign. [All56 geometry rows](../results/fault-event-observability/timing_geometry.csv) report inclusive-label versus half-open injection boundaries, geometric duration and sampled-grid overlap separately.']
    for kind in ('spike','drift'):
        lines+=['\n### '+kind,'\n'+table(['Offset(s)','Truth','TP Gate / TAIS','Recall difference(pp),95%CI','Induced Gate / TAIS','Induced difference,95%CI'],[[dt,count(selected(f'{kind}:dt:{dt}','GateOnly'),'n_events'),f"{count(selected(f'{kind}:dt:{dt}','GateOnly'),'tp')} / {count(selected(f'{kind}:dt:{dt}','TAIS'),'tp')}",ci(f'{kind}:dt:{dt}','recall',100),f"{count(selected(f'{kind}:dt:{dt}','GateOnly'),'fault_induced_false')} / {count(selected(f'{kind}:dt:{dt}','TAIS'),'fault_induced_false')}",ci(f'{kind}:dt:{dt}','fault_induced_false')] for dt in plan['offsets'][kind]]),f'\n![All {kind} conditions](../results/fault-event-observability/test/analysis/{kind}_timing.png)']
    lines+=['\nFull profiles/topologies are retained in [all56 timing cells](../results/fault-event-observability/interpretation/all56_timing_cells.csv) and the original per-run CSVs. No interpolation, budget point selection or scenario trimming was performed.',
      '\n## Primary timing interactions and multiplicity',
      '\nLet Δ be TAIS−GateOnly. The table reports Δ(left)−Δ(right). False-report interactions are **per run**, not cohort totals; Recall is percentage points.10,000 Bootstrap draws resample60whole seeds. Twelve fixed tests use Bonferroni99.583333% intervals;95% descriptive intervals and every deletion check remain in CSV. A robust interaction requires adjusted exclusion of0 and direction retained after each seed/scenario deletion.',
      '\n'+table(['Contrast','Outcome','Estimate','Adjusted interval','Excludes0','Deletion direction'],[[r['contrast'],r['metric'],fmt(r['estimate'],100 if r['metric']=='recall' else 1),f"[{fmt(r['familywise_low'],100 if r['metric']=='recall' else 1)}, {fmt(r['familywise_high'],100 if r['metric']=='recall' else 1)}]",r['adjusted_excludes_zero'],f"{r['deletion_checks_passed']} / {r['deletion_checks']}"] for r in primary]),
      '\n![All primary interactions](../results/fault-event-observability/test/analysis/primary_interactions.png)',
      '\n## Actual overlap and channel placement',
      '\n'+table(['Group','Truth','TP Gate / TAIS','Induced Gate / TAIS','Recall Δ(pp),95%CI'],[[group,count(selected(group,'GateOnly'),'n_events'),f"{count(selected(group,'GateOnly'),'tp')} / {count(selected(group,'TAIS'),'tp')}",f"{count(selected(group,'GateOnly'),'fault_induced_false')} / {count(selected(group,'TAIS'),'fault_induced_false')}",ci(group,'recall',100)] for group in ('spike:temporal:overlap','spike:temporal:event_before_fault','spike:temporal:fault_before_event','drift:temporal:overlap','drift:temporal:event_before_fault','drift:temporal:fault_before_event','spike:same','spike:cross','drift:same','drift:cross')]),
      '\nThese group intervals are descriptive and overlap. Cross means an event on healthy **humidity** while temperature is faulty, not an independent reference measuring the same physical temperature. An event on the unaffected channel supplies independent event evidence when sampled, but this does not identify the cause of temperature change. Healthy-channel isolation and failure to acquire a short event are separate properties.',
      '\n## Observations versus physical identification',
      '\n'+table(['Method/group','Fault runs','Entire fault unsampled','Event runs','Entire event unsampled','Flagged but event missed','Event found, no fault flag'],[[r['method']+'/'+r['group'],r['fault_runs'],r['fault_completely_unsampled'],r['event_runs'],r['event_completely_unsampled'],fmt(r['fault_flagged_event_missed'],digits=0),fmt(r['event_detected_no_fault_flag'],digits=0)] for r in evidence if r['method'] in ('GateOnly','TAIS') and r['group'] in ('kind:spike','kind:drift','same','cross')]),
      '\nA1-second spike can fall entirely between samples despite a5-second minimum requested interval; its absence from sampled observations is not successful spike diagnosis. A missed event with no in-truth sample lacks evidence, while misses despite samples can involve debounce, trust suppression or baseline recovery; sample presence alone does not prove sufficient duration evidence. Per-report preceding intervals and event/flag timestamps are in the committed CSVs; full health/score/state traces are archived with hashes.',
      '\nFault Recall here means **any nonzero C flag during the injected interval**, with type-specific counts separate. Pre-existing event-induced flags can count; it is not calibrated causal diagnosis. Plain AdaptiveSense has no diagnostic output, so no causal comparison of its structural zeros is made. Event-found/no-flag and wrong-type counters are joint detection descriptors, not source-attribution accuracy. No physical source classifier was implemented; that accuracy is **N/A**.',
      '\nThe original replacement/stuck cases provide an exact within-model boundary: range,missing,invalid and stuck each have short/long same-channel-event versus no-event pairs with different latent truth. The scheduled event is contained inside the replacement interval, and shared noise/background resumes identically outside it. [Equivalence results](../results/fault-event-observability/test/analysis/observational_equivalence.csv) compare the **entire two-channel1-Hz post-injection stream**, not only missing windows, and all three complete policy outputs. If observations match, any deterministic causal policy with the same initial state receives identical sampled histories by induction, even if it changes its sampling schedule. Different truth cannot then be guaranteed uniquely distinguished without new information or assumptions. Numerical matching to a coincident report is not physical recognition.',
      '\nFor additive drift and spikes, these registered timing cases do not themselves establish full-stream equivalence. Bias plus unknown real change can admit multiple physical decompositions without constraints, but poor success rates alone do not prove an information-theoretic impossibility. The dataset does not provide calibrated same-quantity spatial redundancy, extra references or a unique physical dynamics model. Type flags can add sampled evidence but do not resolve every decomposition.',
      '\n## Validation, failures and reproducibility',
      '\n**65new tests passed;499full software tests passed,2unchanged strict expected failures,0failed**, before new development generation. Original45 cases have bytewise old-seed20 generation regression; all offsets/boundaries, physical-label independence, policy input equality, future/hidden-data noninterference and full93-case old-seed20 execution/analysis/recomputation are tested. Existing high-threshold rearm pulse xfails and every old test remain unchanged.',
      '\nA partial old-seed20 CLI smoke analysis initially raised a missing-partner KeyError in equivalence reporting. The failed partial output and notes were retained. Requiring both members fixed that helper before any200–299 trajectory; corrected smoke and the complete-matrix test passed. A first ad-hoc import lacked PYTHONPATH and was corrected before data generation. No generator/label/protocol change was made after new seeds opened. See [execution notes](../results/fault-event-observability/checks/execution_notes.json).',
      '\nAll scored metrics and event matches were independently recomputed from saved records, with no policy rerun. Raw/checksum/paired source inputs and analysis outputs were checked; analysis manifests exclude themselves from their output hashes. Final history protection checks576baseline files,185,135old ignored files, both pinned submodules and external raw-file stat signatures. [Final verification](../results/fault-event-observability/test/verification.json). Raw archive data remain outside Git with reproducible commands and manifests. [Results README](../results/fault-event-observability/README.md).',
      '\nThe original research, BM-1 NO-GO, Wire v1/v2, OSP-1 and raw workbooks were not changed. No new thresholds, confirmation states, attribution classifier or scheduler were introduced. No physical energy, over-air delivery, natural-fault validity, universal identifiability or budget-matched superiority claim is supported. A future mechanism requires a new protocol and unused audited seeds.']
    # Categorical heatmaps make every registered offset individually readable.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    fig,axes=plt.subplots(2,2,figsize=(13,7))
    labels=[(r,p) for r in ('same','cross') for p in ('short','long')]
    for row,metric in enumerate(('recall','fault_induced_false')):
        arrays=[]
        for kind in ('spike','drift'):
            arr=[]
            for relation,profile in labels:
                line=[]
                for dt in plan['offsets'][kind]:
                    group=f'{kind}:{relation}:{profile}:dt:{dt}';g=selected(group,'GateOnly');t=selected(group,'TAIS')
                    line.append((number(t,metric)-number(g,metric))*(100 if metric=='recall' else 1/number(g,'runs')))
                arr.append(line)
            arrays.append(np.array(arr))
        bound=max(max(float(np.abs(a).max()) for a in arrays),.001)
        for col,(kind,a) in enumerate(zip(('spike','drift'),arrays)):
            ax=axes[row,col];im=ax.imshow(a,vmin=-bound,vmax=bound,cmap='RdBu_r',aspect='auto')
            ax.set_xticks(range(7),plan['offsets'][kind]);ax.set_yticks(range(4),[r+'/'+p for r,p in labels]);ax.set_xlabel('Event plan start − fault start (s)')
            ax.set_title(kind+(': recall difference (pp)' if metric=='recall' else ': induced difference / run'))
            for iy in range(4):
                for ix in range(7):ax.text(ix,iy,f'{a[iy,ix]:.2f}',ha='center',va='center',fontsize=8,color='white' if abs(a[iy,ix])>.6*bound else 'black')
            fig.colorbar(im,ax=ax,shrink=.8)
    fig.suptitle('TAIS − GateOnly, all56 timing cells; descriptive point estimates, no selection')
    fig.tight_layout();fig.savefig(out/'all_timing_cells.png',dpi=170);plt.close(fig)
    lines+=['\n![Every timing cell](../results/fault-event-observability/interpretation/all_timing_cells.png)']
    # Scientific conclusion is written separately after inspecting ALL completed tables.
    target=ROOT/'docs/FAULT_EVENT_OBSERVABILITY_REPORT.md'
    with target.open('x') as f:f.write('\n'.join(lines)+'\n')
    outputs={p.name:sha(p) for p in out.iterdir() if p.is_file()}
    (out/'manifest.json').write_text(json.dumps(dict(report_script_sha256=sha(Path(__file__)),input_checksums={str(p.relative_to(ROOT)):sha(p) for p in (analysis/'summary.csv',analysis/'paired_intervals.csv',analysis/'timing_interactions.csv',RESULTS/'test/metrics.csv',RESULTS/'test/verification.json')},outputs=outputs),indent=2)+'\n')
    print('Report tables rendered without executing or selecting a policy.')
if __name__=='__main__':main()
