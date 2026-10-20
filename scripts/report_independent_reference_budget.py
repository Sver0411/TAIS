#!/usr/bin/env python3
"""IRB-1 presentation and observable-input audit from completed frozen files only."""
import csv,gzip,hashlib,json,math,sys
from functools import lru_cache
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from tais.budget_eval import sha
from tais.config import load
from tais.reference_metrics import aggregate
from run_independent_reference_budget import DEST,csv_write
from analyze_independent_reference_budget import read_rows
from run_experiments import canonical


def main():
    root=DEST;analysis=root/'test/analysis';verification=json.loads((root/'test/verification.json').read_text())
    if not verification['all_metrics_recomputed']:raise ValueError('Wait for independent verification')
    out=root/'interpretation'
    if out.exists():raise FileExistsError('Never overwrite a report run')
    out.mkdir();plan=json.loads((ROOT/'configs/independent-reference-budget.json').read_text());rows=read_rows(root/'test/metrics.csv')
    summary=list(csv.DictReader((analysis/'summary.csv').open()));cis=list(csv.DictReader((analysis/'paired_intervals.csv').open()));decisions=list(csv.DictReader((analysis/'decisions.csv').open()))
    manifest=json.loads((root/'test/manifest.json').read_text());archive=Path(manifest['archive_root'])
    resource_fields=['seed','scenario','method','budget','cohort','alpha','shape','duration_scenario','offset_s','samples','main_reads','reference_reads','uploads','payload_bytes','cap_reads','cap_uploads','cap_bytes','proposed_uploads','upload_denials','read_denials','n_events','tp','environment_tp','fault_induced_false','environment_induced_false','unresolved_received','received_candidates','received_supported_candidates']
    csv_write(out/'budget_consumption.csv',[{k:r[k] for k in resource_fields} for r in rows])
    csv_write(out/'scenario_parameters.csv',plan['scenarios'])
    @lru_cache(maxsize=32)
    def raw(rel):return json.loads(gzip.decompress((archive/rel).read_bytes()))
    @lru_cache(maxsize=16)
    def signal(seed,case):return raw(f'{seed}/{case}/signals.json.gz')
    quality=[];transcripts={};timings={}
    for r in rows:
        if r['method']!='ReferenceGate':continue
        seed,case,level=r['seed'],r['scenario'],str(float(r['budget']));d=raw(f'{seed}/{case}/ReferenceGate-{level}.json.gz');bundle=signal(seed,case);meta=bundle['metadata']
        events=meta['events'];bevents=meta['reference_physical_labels'];timings[seed,case]=dict(seed=seed,scenario=case,**{k:v for k,v in meta.items() if k not in ('seed','spec','overlap','events','faults','reference_physical_labels')},**{'overlap_'+k:v for k,v in meta['overlap'].items()},A_truth_start=events[0]['start_s'] if events else None,A_truth_end=events[0]['end_s'] if events else None,B_truth_start=bevents[0]['start_s'] if bevents else None,B_truth_end=bevents[0]['end_s'] if bevents else None);reads=d['reference_reads'];finite=[x for x in reads if x['value'] is not None and math.isfinite(x['value'])]
        inside=lambda x,labels:any(e['start_s']<=x['timestamp']<=e['end_s'] for e in labels)
        reasons=[e['reason'] for e in d['episodes'] if e['status']=='undecided']
        quality.append(dict(seed=seed,scenario=case,budget=r['budget'],cohort=r['cohort'],alpha=r['alpha'],shape=r['shape'],duration_scenario=r['duration_scenario'],
             B_reads=len(reads),B_missing=len(reads)-len(finite),B_finite=len(finite),B_finite_in_A_truth=sum(inside(x,events) for x in finite),B_finite_in_B_physical_truth=sum(inside(x,bevents) for x in finite),
             only_baseline=int(len(reads)==1),candidate_episodes=len(d['episodes']),unresolved_missing=reasons.count('missing'),unresolved_read_budget=reasons.count('read_budget'),unresolved_baseline=reasons.count('baseline_unavailable'),unresolved_channel_only=reasons.count('channel_only_or_inconsistent'),unresolved_end=reasons.count('run_or_read_budget_end'),unresolved_busy=reasons.count('busy')))
        if r['cohort']=='drift_only' or r['cohort']=='event_only' and r['shape']=='matched_ramp':
            key=seed,case,float(level)
            inputs=([dict(timestamp=x['timestamp'],value=x['values']['temperature']) for x in d['records']], [dict(timestamp=x['timestamp'],value=x['value']) for x in reads])
            transcripts[key]=hashlib.sha256(canonical(inputs)).hexdigest()
    csv_write(out/'reference_availability.csv',quality)
    csv_write(out/'actual_scenario_timing.csv',list(timings.values()))
    index={(r['seed'],r['scenario'],r['method'],r['budget']):r for r in rows};pairs=[]
    for seed in plan['seeds']['test']:
        for duration in (240,600):
            fault=next(s['id'] for s in plan['scenarios'] if s['cohort']=='drift_only' and s['duration_s']==duration)
            a=signal(seed,fault)['trace']['observed'];a_hash=hashlib.sha256(canonical([(x['timestamp'],x['temperature']) for x in a])).hexdigest()
            for alpha in (0.,.5,1.):
                event=next(s['id'] for s in plan['scenarios'] if s['cohort']=='event_only' and s['shape']=='matched_ramp' and s['duration_s']==duration and s['alpha']==alpha)
                b=signal(seed,event)['trace']['observed'];b_hash=hashlib.sha256(canonical([(x['timestamp'],x['temperature']) for x in b])).hexdigest()
                for level in plan['budget_levels']:
                    x,y=index[seed,fault,'ReferenceGate',level],index[seed,event,'ReferenceGate',level]
                    pairs.append(dict(seed=seed,duration_scenario=duration,alpha=alpha,budget=level,fault_world=fault,event_world=event,A_full_equal=a_hash==b_hash,AB_full_equal=x['observed_sha256']==y['observed_sha256'],paid_input_transcripts_equal=transcripts[seed,fault,level]==transcripts[seed,event,level],complete_outputs_equal=x['result_sha256']==y['result_sha256']))
    csv_write(out/'observability_and_acquisition_pairs.csv',pairs)
    core=[r for r in rows if r['cohort'] in ('mixed','event_only','drift_only','clean')]
    by_core=[dict(method=method,budget=level,alpha=alpha,**aggregate([r for r in core if r['method']==method and r['budget']==level and r['alpha']==alpha])) for method in plan['methods'] for level in plan['budget_levels'] for alpha in (1.,.5,0.)]
    csv_write(out/'core_alpha_summary.csv',by_core)
    def f(x,scale=1,places=3):return 'N/A' if x is None or x=='' else f'{float(x)*scale:,.{places}f}'
    def n(r,k):return f(r[k],places=0)
    def table(headers,data):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in data])
    def select(group,method,level):return next(r for r in summary if r['group']==group and r['method']==method and float(r['budget'])==level)
    def bound(group,level,metric):
        r=next(r for r in cis if r['group']==group and float(r['budget'])==level and r['metric']==metric)
        scale=100 if metric in ('recall','environment_recall','environment_induced_false_relative') else 1
        return f"{f(r['reference_minus_gate'],scale)} [{f(r['ci95_low'],scale)}, {f(r['ci95_high'],scale)}]"
    decision=json.loads((analysis/'decision.json').read_text());caps=json.loads((root/'budget-lock.json').read_text())
    counts=[];phase_summary=[]
    for phase in ('calibrate','development','validation','test'):
        m=json.loads((root/phase/'manifest.json').read_text());counts.append([phase,f"{m['seeds'][0]}–{m['seeds'][-1]}",m['runs'],m['counterfactual_runs'],len(m['artifacts'])])
        if phase!='calibrate':phase_summary.extend(dict(phase=phase,**r) for r in csv.DictReader((root/phase/'analysis/summary.csv').open()) if r['group'] in ('core','responsive'))
    csv_write(out/'split_comparison.csv',phase_summary)
    lines=['# IRB-1: independent-reference value under shared hard budgets',f"\n**Decision: {decision['decision']} for this predefined reference rule.** Prior confirmation NO-GO is preserved. Synthetic same-unit model only; no real environment, natural-fault, radio delivery or energy validation.",
      '\n## Execution, model and fixed comparisons',
      '\n[Preregistration with pre-data P1 clarification](INDEPENDENT_REFERENCE_BUDGET_PREREGISTRATION.md) · [Full matrix](../configs/independent-reference-budget.json) · [Final source/cap lock](../results/independent-reference-budget/final-lock.json). Three strategies only: original one-main-channel GateOnly, original TAIS and conservative ReferenceGate; multiplier 1.0. No threshold search or final point replacement.',
      '\n'+table(['Phase','Seeds','Scored runs','Offline counterfactuals','Gzip artifacts'],counts),
      '\n[Development / validation / final core and responsive totals](../results/independent-reference-budget/interpretation/split_comparison.csv) retain every budget and method; only the held-out final split enters the stated inference. No threshold or policy selection was performed. Development sets budget ceilings only.',
      '\nA and B measure Celsius,σ=0.08 C independent noise, common 24±0.03 C background, original 240/600 s drift at 0.015/0.03 C/s. Reference responseα1/.5/0 and static bias 0.3 C are modeled assumptions.24 missing/3C-bias pressure cases are synthetic stress, not occurrence estimates. Plateau uses 4 C / 26 or 180 s; matched ramps inherit original drift waveforms, including reset, not inflated amplitudes. Profile jointly changes duration,intensity and event duration. [All 87 parameters](../results/independent-reference-budget/interpretation/scenario_parameters.csv). [Actual independently labeled timing and overlap for every final seed/case](../results/independent-reference-budget/interpretation/actual_scenario_timing.csv) records planned changes separately from physical event windows; scenario names are not used as truth.',
      '\nGateOnly/TAIS main scheduler and real C11 core are unchanged. ReferenceGate preserves main candidates; two paid B observations can add environmental support, otherwise cause remains unresolved. Same sign and>1.2 C displacement twice at ≥10 s directly reuse existing thresholds. Baselines are the first actual readings, no healthy-history orα oracle. One bounded pending job, no extra A polls, no B future interpolation. Unsupported does not mean faulty.',
      '\n## Common hard caps and actual costs',
      '\n'+table(['Budget','Shared A+B reads','Issued requests','Actual JSON bytes'],[[level,*[caps['budgets'][str(float(level))][k] for k in ('reads','uploads','bytes')]] for level in plan['budget_levels']]),
      '\nCaps are floor(multiplier×development mean uncapped GateOnly cost), globally common for all cases/methods. They are ceilings, **not equal actual consumption**. Denied proposals are not issued requests; exact complete JSON includes reference values,timestamps, evidence and full A health fields. Every missing B read costs one. Ledger/JSON recomputation checks every admitted operation. A can still be read locally within remaining read quota after upload denial; logical scheduler request history is not rolled back. Pending B data are not silently dropped to fit.',
      '\n'+table(['Budget','Method','A reads','B reads','Requests','JSON bytes','Candidates TP / truth','Committed TP','Candidate unmatched','Committed fault-induced'],[[level,m,n(select('core',m,level),'main_reads'),n(select('core',m,level),'reference_reads'),n(select('core',m,level),'uploads'),n(select('core',m,level),'payload_bytes'),f"{n(select('core',m,level),'tp')} / {n(select('core',m,level),'n_events')}",n(select('core',m,level),'environment_tp'),n(select('core',m,level),'false_reports'),n(select('core',m,level),'environment_induced_false')] for level in plan['budget_levels'] for m in plan['methods']]),
      '\n[Every strategy/case resource row](../results/independent-reference-budget/interpretation/budget_consumption.csv). Raw candidate induced/unmatched counts remain available even when status is unresolved; they are not relabeled committed physical errors. No application byte is called a measured wireless byte or joule.',
      '\n## Predeclared primary paired findings',
      '\nReferenceGate−GateOnly, 60 whole-seed clusters, 10,000 Bootstrap draws. Primary groups contain core event-bearing responsive α=.5/1, pure α=1, pure α=.5. Three groups × three budgets × three endpoints = 27 fixed comparisons.95% intervals below; [all 27 Bonferroni-adjusted intervals](../results/independent-reference-budget/test/analysis/primary_corrected_intervals.csv) and every deletion check are retained. No α0/stress post-hoc path to GO.',
      '\n'+table(['Budget/group','Candidate Recall Δ(pp),95%CI','Committed Recall Δ(pp),95%CI','Committed induced relative Δ(%),95%CI','NI candidate','NI environment','False benefit','Decision'],[[f"{r['budget']}/{r['group']}",bound(r['group'],float(r['budget']),'recall'),bound(r['group'],float(r['budget']),'environment_recall'),bound(r['group'],float(r['budget']),'environment_induced_false_relative'),r['candidate_noninferior'],r['environment_noninferior'],r['false_benefit'],r['go']] for r in decisions]),
      '\nBoth candidate and committed-event NI require lower bounds>−1pp in 95% and adjusted intervals; false reduction requires≥5% and directional intervals, plus deletion robustness and hard caps. Thus removing most true events into unresolved status cannot pass. A zero Gate false denominator is insufficient evidence. Common caps do not isolate information value from changed A allocation or earlier budget exhaustion.',
      '\n## Coverage, abstention and causal attribution',
      '\n'+table(['Budget/alpha','Candidate Recall','Supported Recall','Unresolved received','Decisive candidate coverage','Wrong support rate'],[[f"{r['budget']}/{r['alpha']}",f(r['recall'],100)+'%',f(r['environment_recall'],100)+'%',f(r['unresolved_received_rate'],100)+'%',f(r['decisive_candidate_coverage'],100)+'%',f(r['supported_false_rate'],100)+'%'] for r in by_core if r['method']=='ReferenceGate']),
      '\n**Receiver semantics are experimental:** the legacy JSON `environment_active` field still carries the raw GateOnly candidate state. `reference.evidence.status` is a separate annotation; only an evidence-aware consumer can apply the supported/committed interpretation used here. A legacy consumer would still see the candidate alarms. This is not a deployable backwards-compatible alarm-suppression protocol and does not prove that raw candidate notifications disappeared.',
      '\nUnresolved is neither credited correct nor counted as a committed environmental error. Candidate notifications remain and are fully scored separately. Supported environment evidence does **not** assert A is fault-free: event+drift can coexist. Unique physical-source attribution accuracy is N/A. Reference-only fault-attribution Precision is N/A and Recall 0: no fault cause is asserted from B nonresponse.',
      '\n'+table(['Budget','Method','C11 local fault-claim P/R','Received fault-claim P/R','Support scenario coverage','Post-denial candidate Recall'],[[level,m,f"{f(select('core',m,level)['fault_claim_precision'],100)} / {f(select('core',m,level)['fault_claim_recall'],100)}%",f"{f(select('core',m,level)['received_fault_claim_precision'],100)} / {f(select('core',m,level)['received_fault_claim_recall'],100)}%",f(select('core',m,level)['decisive_scenario_coverage'],100)+'%',f(select('core',m,level)['post_denial_recall'],100)+'%'] for level in plan['budget_levels'] for m in plan['methods']]),
      '\nC11 claims here are scenario-level any sampled flag versus known drift presence, not calibrated physical causation. Existing in-injection flag/type Recall/delay is separately retained. A late flag can be a scenario-positive claim without timely episode localization. Reference does not add a C11 fault detector; P/R changes can follow changed sampling. Post-denial strata are descriptive, not counterfactual proof about a missed event.',
      '\n## What information actually existed',
      '\n[Reference availability](../results/independent-reference-budget/interpretation/reference_availability.csv) separates charged attempts,finite/missing values and finite reads inside A/B independent physical-label windows. A nonzero modeledα does not mean the rule acquired a usable event sample. Baseline-only B reads or main-candidate gating can prevent information acquisition; missing B is never filled or treated as unchanged healthy evidence.',
      '\n[Full-versus-paid observation pairs](../results/independent-reference-budget/interpretation/observability_and_acquisition_pairs.csv) compare matched-ramp event worlds to drift-only worlds for allα/durations/budgets. Atα0, exact complete A/B streams are equal despite different physical truth; full policy outputs must be equal at the same caps. No deterministic observer on that information can guarantee correct per-case separation. Existing event-only/drift-only cases are reused, not counted as extra independent samples.',
      '\nAtα>0, complete B streams can differ while A remains exactly equal. If paid transcripts remain equal for a particular strategy/quota, that is **acquisition-limited evidence**, not an impossibility proof for every possible budgeted acquisition rule. When B supplies cochange, it supports environmental presence, not absence of simultaneous A drift. Current g,noise,bias/reliability and response assumptions limit deployment conclusions.',
      '\n## Validation and boundaries',
      '\nBefore new data: 609 full-suite tests passed, 2 unchanged strict xfails, 0 failed; 110 new tests passed. The initial 108-pass/2-fail parity run is retained: a missing internal debug field `t` was restored without changing algorithms or assertions. P1 label semantics were clarified before any 300–399 trajectory. Full 87-case old-seed-20 pipeline, independent ledger/JSON checks,exact twin streams/outputs,physical labels,future/hidden-data noninterference and unpaid-reference access are tested.',
      '\nAll scored metrics are independently recomputed offline from saved records; verification never calls the policy again. Old 657 tracked files, 236,199 ignored files, both pinned upstreams and external raw-file stat signatures are protected. Analysis manifests exclude themselves from their own hash list. Final source/caps and calibration hashes remain unchanged. [Final verification](../results/independent-reference-budget/test/verification.json) · [Execution notes](../results/independent-reference-budget/checks/execution_notes.json) · [Reproduction commands](../results/independent-reference-budget/README.md).',
      '\nThis study does not alter prior confirmation NO-GO,old generators, Wire v1/v2, OSP-1, main or upstream sources. Fresh noise under one synthetic model is not real external validation. A new mechanism needs a new task/protocol and fresh audited data; no retuning on these final seeds.']
    plot(by_core,summary,out,plan)
    plot_intervals(cis,out,plan)
    lines+=['\n![Paired intervals at every primary point](../results/independent-reference-budget/interpretation/primary_paired_intervals.png)','\n![All response and budget points](../results/independent-reference-budget/interpretation/core_response_tradeoff.png)','\n![Actual consumption under common caps](../results/independent-reference-budget/interpretation/budget_usage.png)']
    with (ROOT/'docs/INDEPENDENT_REFERENCE_BUDGET_REPORT.md').open('x') as f:f.write('\n'.join(lines)+'\n')
    outputs={p.name:sha(p) for p in out.iterdir() if p.is_file()}
    (out/'manifest.json').write_text(json.dumps(dict(report_script_sha256=sha(Path(__file__)),input_sha256={str(p.relative_to(ROOT)):sha(p) for p in (root/'test/metrics.csv',analysis/'summary.csv',analysis/'paired_intervals.csv',analysis/'decision.json',root/'test/verification.json')},outputs=outputs),indent=2)+'\n')
    print('Completed source-pinned report and observational-input audit without rerunning a policy.')


def plot_intervals(cis,out,plan):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,6.5));labels=[]
    points=[(b,g) for b in plan['budget_levels'] for g in plan['primary_groups']]
    for i,(b,g) in enumerate(points):
        labels.append(f'{b} / {g}')
        for metric,offset,color in [('recall',-.12,'#526f91'),('environment_recall',.12,'#147f79')]:
            r=next(x for x in cis if float(x['budget'])==b and x['group']==g and x['metric']==metric)
            y=i+offset
            axes[0].hlines(y,100*float(r['adjusted_low']),100*float(r['adjusted_high']),color=color,linewidth=1,alpha=.5)
            axes[0].hlines(y,100*float(r['ci95_low']),100*float(r['ci95_high']),color=color,linewidth=3)
            axes[0].plot(100*float(r['reference_minus_gate']),y,'o',color=color,markersize=4)
        r=next(x for x in cis if float(x['budget'])==b and x['group']==g and x['metric']=='environment_induced_false_relative')
        if r['reference_minus_gate']:
            axes[1].hlines(i,100*float(r['adjusted_low']),100*float(r['adjusted_high']),color='#b66740',linewidth=1,alpha=.5)
            axes[1].hlines(i,100*float(r['ci95_low']),100*float(r['ci95_high']),color='#b66740',linewidth=3)
            axes[1].plot(100*float(r['reference_minus_gate']),i,'o',color='#b66740',markersize=4)
    axes[0].axvline(-1,color='#9b3c40',linestyle='--',label='NI margin -1 pp');axes[0].axvline(0,color='#888',linewidth=.7)
    axes[0].plot([],[],'o',color='#526f91',label='Candidate Recall');axes[0].plot([],[],'o',color='#147f79',label='Committed Recall')
    axes[1].axvline(-5,color='#9b3c40',linestyle='--',label='Practical target -5%');axes[1].axvline(0,color='#888',linewidth=.7)
    for ax in axes:
        ax.set_yticks(range(len(points)),labels);ax.invert_yaxis();ax.grid(axis='x',alpha=.15);ax.legend(fontsize=8)
    axes[0].set_xlabel('ReferenceGate - GateOnly (percentage points)');axes[1].set_xlabel('Committed fault-induced count relative difference (%)')
    axes[0].set_title('Both Recall gates required');axes[1].set_title('Abstention disclosed separately')
    fig.suptitle('All primary points: thick 95% CI; thin Bonferroni-adjusted CI (27 endpoints)')
    fig.tight_layout();fig.savefig(out/'primary_paired_intervals.png',dpi=170);plt.close(fig)


def plot(core,summary,out,plan):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(14,8))
    for col,alpha in enumerate((1.,.5,0.)):
        for method,color in [('GateOnly','#526f91'),('TAIS','#999999'),('ReferenceGate','#147f79')]:
            r=[next(x for x in core if x['method']==method and x['alpha']==alpha and x['budget']==b) for b in plan['budget_levels']]
            axes[0,col].plot(plan['budget_levels'],[100*x['recall'] for x in r],'-o',color=color,label=method+' candidate')
            if method=='ReferenceGate':axes[0,col].plot(plan['budget_levels'],[100*x['environment_recall'] for x in r],'--s',color=color,label='Reference supported')
            axes[1,col].plot(plan['budget_levels'],[x['environment_induced_false'] for x in r],'-o',color=color,label=method)
        axes[0,col].set_title(f'Core alpha={alpha}');axes[1,col].set_xlabel('Shared hard-budget multiplier')
    axes[0,0].set_ylabel('Recall (%)');axes[1,0].set_ylabel('Committed fault-induced reports');axes[0,0].legend(fontsize=8);axes[1,0].legend(fontsize=8)
    fig.suptitle('All declared responses and budgets; candidate and committed reports separated');fig.tight_layout();fig.savefig(out/'core_response_tradeoff.png',dpi=170);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(14,4.5));labels=[];data=[]
    for b in plan['budget_levels']:
        for m in plan['methods']:
            r=next(x for x in summary if x['method']==m and float(x['budget'])==b and x['group']=='core');labels.append(f'{b}\n{m}');data.append(r)
    caps=json.loads((DEST/'budget-lock.json').read_text())['budgets']
    for ax,field,cap in zip(axes,('samples','uploads','payload_bytes'),('reads','uploads','bytes')):
        ax.bar(range(9),[100*float(r[field])/(float(r['runs'])*caps[str(float(r['budget']))][cap]) for r in data],color=['#526f91','#999999','#147f79']*3)
        ax.axhline(100,color='#555',linestyle='--');ax.set_ylim(0,110);ax.set_xticks(range(9),labels,rotation=55,ha='right',fontsize=7);ax.set_ylabel('Used / shared ceiling (%)');ax.set_title(field)
    fig.suptitle('Same hard ceilings, differing actual use; no free B operations');fig.tight_layout();fig.savefig(out/'budget_usage.png',dpi=170);plt.close(fig)
if __name__=='__main__':main()
