#!/usr/bin/env python3
"""BM-1: resource-only calibration selection and frozen paired analysis."""
from collections import defaultdict
from datetime import datetime,timezone
import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from tais.signals import scenarios
from tais.budget_eval import (sha,numeric_rows,aggregate,groups,choose_pairs,paired_rows,
                             paired_bootstrap,absolute_bootstrap,robustness,decision)
from run_budget_matched_experiment import fingerprints,csv_write


def read_phase(root,phase):
    path=root/phase;m=json.loads((path/'manifest.json').read_text())
    if m['status']!='COMPLETE' or sha(path/'metrics.csv')!=m['metrics_sha256'] or sha(path/'event_matches.csv')!=m['event_matches_sha256']:
        raise ValueError('Incomplete/changed phase '+phase)
    rows=numeric_rows(list(csv.DictReader((path/'metrics.csv').open())))
    if len(rows)!=m['runs']:raise ValueError('Phase row count mismatch')
    return m,rows


def select(root,plan):
    """Freeze pairs using development/validation resource fields only, never test outcomes.

    Preserve fallback and calibration-qualified status when no pair meets the
    declared bands. This writes an exclusive selection, not a validation report."""
    dm,dev=read_phase(root,'development');vm,val=read_phase(root,'validation')
    for phase,m in [('development',dm),('validation',vm)]:
        if m['seeds']!=plan['seeds'][phase] or m['frozen_files']!=fingerprints():raise ValueError('Calibration/code/split changed')
    choices,candidates=choose_pairs(dev,val,plan)
    final={('AdaptiveSense',1.),('AdaptiveSense+TrustLog',1.)}
    for m in plan['anchors']:final.update((method,m) for method in ('GateOnly','TAIS'))
    for c in choices:final.update([('GateOnly',c['gate_multiplier']),('TAIS',c['tais_multiplier'])])
    lock=dict(status='FROZEN_BEFORE_TEST',created_utc=datetime.now(timezone.utc).isoformat(),
              selected_at_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              selection_uses_only_resource_fields=True,plan_sha256=sha(ROOT/'configs/budget-matched.json'),
              frozen_files=fingerprints(),calibration_files={str(p.resolve().relative_to(ROOT)):sha(p) for phase in ('development','validation') for p in [root/phase/'metrics.csv',root/phase/'manifest.json']},
              budgets=choices,final_points=[dict(method=method,multiplier=m) for method,m in sorted(final)],
              final_seeds=plan['seeds']['test'],predeclared_family_size=3)
    csv_write(root/'selection_candidates.csv',candidates)
    with (root/'selection.json').open('x') as f:json.dump(lock,f,indent=2);f.write('\n')
    print(json.dumps(lock['budgets'],indent=2))


def common_delays(event_rows,gm,tm,seed):
    """Compare delay only for events matched by both methods, resampling whole seeds.

    Conditional delay omits events missed by either method; report those misses
    separately rather than interpreting this as unconditional detection speed."""
    def index(method,m):return {(int(r['seed']),r['scenario'],r['channel'],r['truth_start'],r['truth_end']):r for r in event_rows if r['method']==method and float(r['multiplier'])==m}
    g,t=index('GateOnly',gm),index('TAIS',tm)
    if g.keys()!=t.keys():raise ValueError('Event truths differ between selected methods')
    pairs=[]
    for k in sorted(g):
        a,b=g[k],t[k]
        if a['matched']=='True' and b['matched']=='True':pairs.append(dict(seed=k[0],scenario=k[1],channel=k[2],truth_start=k[3],truth_end=k[4],gate_latency_s=float(a['latency_s']),tais_latency_s=float(b['latency_s']),difference_s=float(b['latency_s'])-float(a['latency_s'])))
    seeds=sorted({int(r['seed']) for r in event_rows});stats={s:[r['difference_s'] for r in pairs if r['seed']==s] for s in seeds}
    sums=np.array([sum(stats[s]) for s in seeds]);counts=np.array([len(stats[s]) for s in seeds])
    idx=np.random.default_rng(seed).integers(0,len(seeds),size=(10000,len(seeds)))
    d=counts[idx].sum(axis=1)
    with np.errstate(divide='ignore',invalid='ignore'):v=sums[idx].sum(axis=1)/d
    valid=v[np.isfinite(v)];lo,hi=np.quantile(valid,[.025,.975]) if len(valid) else (None,None)
    return pairs,dict(common_matched_events=len(pairs),tais_minus_gate_latency_s=float(sums.sum()/counts.sum()) if counts.sum() else None,ci95_low=lo,ci95_high=hi,valid_draws=len(valid),replicates=10000)


def plot(summary,intervals,decisions,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4.8))
    for method,marker,color in [('GateOnly','o','#627b95'),('TAIS','s','#187d79')]:
        r=[x for x in summary if x['method']==method and x['group']=='overall']
        r.sort(key=lambda x:x['uploads'])
        axes[0].plot([x['uploads'] for x in r],[100*x['recall'] for x in r],marker=marker,label=method,color=color)
    axes[0].set_xlabel('Application upload requests');axes[0].set_ylabel('Micro event recall (%)');axes[0].legend(frameon=False)
    axes[0].set_title('All frozen test configurations; no interpolation used for matching')
    for i,c in enumerate(decisions):
        r=next(x for x in intervals if x['budget']==c['budget'] and x['group']=='overall' and x['metric']=='fault_induced_false_relative_difference')
        if r['tais_minus_gate'] is not None:
            y=100*r['tais_minus_gate'];lo=100*r['ci95_low'];hi=100*r['ci95_high']
            axes[1].vlines(i,lo,hi,color='#187d79');axes[1].hlines([lo,hi],i-.06,i+.06,color='#187d79');axes[1].plot(i,y,'o',color='#187d79')
    axes[1].axhline(0,color='#777',linewidth=1);axes[1].axhline(-5,color='#a87824',linestyle='--',label='Practical target −5%')
    axes[1].set_xticks(range(len(decisions)),[c['budget']+(' matched' if c['test_matched'] else ' unmatched') for c in decisions],rotation=15)
    axes[1].set_ylabel('TAIS − GateOnly fault-induced reports (%)');axes[1].set_title('Paired seed-bootstrap95% intervals; all budgets');axes[1].legend(frameon=False)
    for ax in axes:ax.spines[['top','right']].set_visible(False)
    fig.tight_layout();fig.savefig(out/'budget_tradeoff.png',dpi=180);plt.close(fig)


def analyze(root,phase,plan):
    manifest,rows=read_phase(root,phase)
    if manifest['phase']!=phase:raise ValueError('Wrong phase label')
    if phase!='smoke':
        if manifest['seeds']!=plan['seeds'][phase] or manifest['cases']!=scenarios():raise ValueError('Partial/wrong seed-scenario population')
    keys={(r['seed'],r['scenario'],r['method'],r['multiplier']) for r in rows}
    expected={(seed,case,method,float(m)) for seed in manifest['seeds'] for case in manifest['cases'] for method,m in manifest['points']}
    if len(keys)!=len(rows) or keys!=expected:raise ValueError('Incomplete or duplicate actual run matrix')
    out=root/phase/'analysis'
    if out.exists():raise FileExistsError('Never overwrite an analysis')
    out.mkdir();by=defaultdict(list)
    for row in rows:
        for group in groups(row):by[row['method'],row['multiplier'],group].append(row)
    summary=[dict(method=k[0],multiplier=k[1],group=k[2],**aggregate(v)) for k,v in sorted(by.items())]
    csv_write(out/'summary.csv',summary)
    counts={k:len({r['seed'] for r in v}) for k,v in by.items()}
    verification=dict(phase=phase,rows=len(rows),seeds=manifest['seeds'],scenarios=manifest['cases'],points=manifest['points'],all_groups_seed_clustered=True)
    if phase!='test':
        with (out/'verification.json').open('x') as f:json.dump(verification,f,indent=2);f.write('\n')
        print(f'{phase}: all-grid summaries produced; selection does not use outcomes');return
    selection=json.loads((root/'selection.json').read_text())
    if manifest['selection_sha256']!=sha(root/'selection.json'):raise ValueError('Test lock mismatch')
    if manifest['frozen_files']!=fingerprints():raise ValueError('Analysis or source changed since test freeze')
    intervals=[];absolute=[];deletions=[];decisions=[];common=[];event_pairs=[]
    event_rows=list(csv.DictReader((root/phase/'event_matches.csv').open()))
    for choice in selection['budgets']:
        gm,tm=choice['gate_multiplier'],choice['tais_multiplier'];pairs=paired_rows(rows,gm,tm)
        group_pairs=defaultdict(list)
        for g,t in pairs:
            for group in groups(g):group_pairs[group].append((g,t))
        overall=[]
        for group,p in sorted(group_pairs.items()):
            cis=paired_bootstrap(p,plan['bootstrap_replicates'],plan['bootstrap_seed'],family=plan['comparison_family_size'])
            intervals.extend(dict(budget=choice['budget'],group=group,**c) for c in cis)
            if group=='overall':overall=cis
        robust=robustness(pairs);deletions.extend(dict(budget=choice['budget'],**d) for d in robust)
        decisions.append(decision(choice,pairs,overall,robust,plan))
        ep,cm=common_delays(event_rows,gm,tm,plan['bootstrap_seed']);common.append(dict(budget=choice['budget'],**cm));event_pairs.extend(dict(budget=choice['budget'],**p) for p in ep)
    # Absolute outcomes, every actual method/point at overall and predeclared subgroup levels.
    for key,values in sorted(by.items()):
        for c in absolute_bootstrap(values,plan['bootstrap_replicates'],plan['bootstrap_seed']):absolute.append(dict(method=key[0],multiplier=key[1],group=key[2],**c))
    csv_write(out/'paired_intervals.csv',intervals);csv_write(out/'absolute_intervals.csv',absolute)
    csv_write(out/'robustness_deletions.csv',deletions);csv_write(out/'decisions.csv',decisions)
    csv_write(out/'common_matched_delay.csv',common)
    if event_pairs:csv_write(out/'common_matched_event_pairs.csv',event_pairs)
    plot(summary,intervals,decisions,out)
    final=dict(decision='GO' if any(c['go'] for c in decisions) else 'NO-GO',budgets=decisions,
               rule='All predeclared matching,noninferiority,practical false-reduction,multiplicity and deletion-robustness gates',
               counts=dict(paired_intervals=len(intervals),absolute_intervals=len(absolute),deletion_checks=len(deletions)),
               selection_sha256=sha(root/'selection.json'),source_manifest_sha256=sha(root/phase/'manifest.json'),
               frozen_plan_sha256=sha(ROOT/'configs/budget-matched.json'),**verification)
    with (out/'decision.json').open('x') as f:json.dump(final,f,indent=2);f.write('\n')
    with (out/'manifest.json').open('x') as f:json.dump(dict(frozen_files=fingerprints(),outputs={p.name:sha(p) for p in sorted(out.iterdir())}),f,indent=2);f.write('\n')
    print(json.dumps(final,indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__);a=p.add_mutually_exclusive_group(required=True)
    a.add_argument('--select',action='store_true');a.add_argument('--phase',choices=['smoke','development','validation','test'])
    p.add_argument('--root',type=Path,default=ROOT/'results/budget-matched');args=p.parse_args()
    plan=json.loads((ROOT/'configs/budget-matched.json').read_text())
    if args.select:select(args.root,plan)
    else:analyze(args.root,args.phase,plan)

if __name__=='__main__':main()
