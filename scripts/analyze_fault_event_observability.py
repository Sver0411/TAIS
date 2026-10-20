#!/usr/bin/env python3
"""FO-1 predeclared whole-seed comparisons; no policy or parameter selection."""
import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from tais.budget_eval import sha,paired_bootstrap
from tais.observability_eval import aggregate,groups
from run_fault_event_observability import RESULTS,fingerprints,csv_write

META={'scenario','relationship','profile','fault_kind','cohort','temporal','event_start_order','method','counterfactual_path'}


def read_rows(path):
    result=[]
    for r in csv.DictReader(path.open()):
        result.append({k:(v if k in META or k.endswith('_sha256') else None if v=='' else int(v) if k=='seed' else float(v)) for k,v in r.items()})
    return result


def read_phase(root,phase,plan):
    path=root/phase;m=json.loads((path/'manifest.json').read_text())
    if m['status']!='COMPLETE' or m['frozen_files']!=fingerprints():raise ValueError('Phase incomplete or sources changed')
    for name,digest in m['csv_sha256'].items():
        if sha(path/name)!=digest:raise ValueError('CSV changed')
    rows=read_rows(path/'metrics.csv')
    expected={(s,c,method) for s in m['seeds'] for c in m['cases'] for method in plan['methods']}
    actual={(r['seed'],r['scenario'],r['method']) for r in rows}
    if actual!=expected or len(rows)!=len(expected):raise ValueError('Incomplete/duplicate matrix')
    if phase!='smoke' and (m['seeds']!=plan['seeds'][phase] or m['cases']!=plan['scenarios']):raise ValueError('Unexpected population')
    return m,rows


def pairs(rows):
    g={(r['seed'],r['scenario']):r for r in rows if r['method']=='GateOnly'}
    t={(r['seed'],r['scenario']):r for r in rows if r['method']=='TAIS'}
    if g.keys()!=t.keys():raise ValueError('Missing paired run')
    output=[]
    for key in sorted(g):
        a,b=g[key],t[key]
        for field in ('signals_sha256','latent_sha256','noisy_sha256','observed_sha256','events_sha256','faults_sha256'):
            if a[field]!=b[field]:raise ValueError('Unequal paired inputs')
        output.append((a,b))
    return output


def contrast_values(paired,spec,omit_field=None,omit_value=None):
    """Average per-seed difference of policy effects, normalize by actual cells."""
    buckets=defaultdict(lambda: [[],[]])
    for g,t in paired:
        if g['fault_kind']!=spec['kind'] or not g['n_events']:continue
        if omit_field and g[omit_field]==omit_value:continue
        field='relationship' if isinstance(spec['left'],str) else 'offset_s'
        if g[field]==spec['left']:buckets[g['seed']][0].append((g,t))
        if g[field]==spec['right']:buckets[g['seed']][1].append((g,t))
    out={metric:[] for metric in ('recall','fault_induced_false_per_run')}
    for seed,(left,right) in sorted(buckets.items()):
        if not left or not right:continue
        def effect(p,metric):
            if metric=='recall':return sum(t['tp']-g['tp'] for g,t in p)/sum(g['n_events'] for g,t in p)
            return sum(t['fault_induced_false']-g['fault_induced_false'] for g,t in p)/len(p)
        for metric in out:out[metric].append(effect(left,metric)-effect(right,metric))
    return out


def interactions(paired,plan):
    rows=[];deletions=[]
    for spec in plan['primary_contrasts']:
        values=contrast_values(paired,spec)
        selected=[g for g,t in paired if g['fault_kind']==spec['kind'] and g['n_events'] and g['relationship'] in ('same','cross')]
        field='relationship' if isinstance(spec['left'],str) else 'offset_s'
        selected=[g for g in selected if g[field] in (spec['left'],spec['right'])]
        omissions=[('seed',s) for s in sorted({g['seed'] for g in selected})]+[('scenario',s) for s in sorted({g['scenario'] for g in selected})]
        for metric,data in values.items():
            a=np.array(data);estimate=float(a.mean());idx=np.random.default_rng(plan['bootstrap_seed']).integers(0,len(a),size=(plan['bootstrap_replicates'],len(a)))
            draws=a[idx].mean(axis=1);alpha=plan['alpha'];family=plan['primary_family_size']
            lo,hi,adjlo,adjhi=np.quantile(draws,[alpha/2,1-alpha/2,alpha/(2*family),1-alpha/(2*family)])
            signs=[]
            for f,v in omissions:
                remaining=contrast_values(paired,spec,f,v)[metric]
                delta=float(np.mean(remaining)) if remaining else None
                consistent=delta is not None and estimate*delta>0
                signs.append(consistent)
                deletions.append(dict(contrast=spec['name'],metric=metric,deleted_field=f,deleted_value=v,difference=delta,same_direction=consistent))
            rows.append(dict(contrast=spec['name'],metric=metric,estimate=estimate,ci95_low=lo,ci95_high=hi,
                             familywise_low=adjlo,familywise_high=adjhi,family_size=family,confidence_adjusted=1-alpha/family,
                             seeds=len(a),valid_draws=len(draws),replicates=len(draws),adjusted_excludes_zero=bool(adjlo>0 or adjhi<0),
                             all_deletions_same_direction=all(signs),deletion_checks=len(signs),deletion_checks_passed=sum(signs)))
    return rows,deletions


def common_delays(path,plan):
    rows=list(csv.DictReader(path.open()));index={(int(r['seed']),r['scenario'],r['method']):r for r in rows};by=defaultdict(list)
    for (s,c,m),r in index.items():
        if m!='GateOnly':continue
        t=index[s,c,'TAIS']
        if r['matched']=='True' and t['matched']=='True':by[s].append(float(t['latency_s'])-float(r['latency_s']))
    seeds=sorted({s for s,c,m in index});sums=np.array([sum(by[s]) for s in seeds]);counts=np.array([len(by[s]) for s in seeds])
    idx=np.random.default_rng(plan['bootstrap_seed']).integers(0,len(seeds),size=(plan['bootstrap_replicates'],len(seeds)))
    denom=counts[idx].sum(axis=1)
    with np.errstate(divide='ignore',invalid='ignore'):draws=sums[idx].sum(axis=1)/denom
    finite=draws[np.isfinite(draws)];lo,hi=np.quantile(finite,[.025,.975]) if len(finite) else (None,None)
    return dict(common_matched_events=int(counts.sum()),tais_minus_gate_delay_s=float(sums.sum()/counts.sum()) if counts.sum() else None,ci95_low=lo,ci95_high=hi,valid_draws=len(finite))


def equivalences(rows):
    index={(r['seed'],r['scenario'],r['method']):r for r in rows};out=[]
    for seed in sorted({r['seed'] for r in rows}):
        for kind in ('range','missing','invalid','stuck'):
            for profile in ('short','long'):
                cases=(f'{kind}_same_{profile}',f'{kind}_none_{profile}')
                if any((seed,c,'GateOnly') not in index for c in cases):continue
                a,b=index[seed,cases[0],'GateOnly'],index[seed,cases[1],'GateOnly']
                out.append(dict(seed=seed,kind=kind,profile=profile,event_case=cases[0],no_event_case=cases[1],
                    observed_full_stream_equal=a['observed_sha256']==b['observed_sha256'],latent_different=a['latent_sha256']!=b['latent_sha256'],
                    truth_different=a['events_sha256']!=b['events_sha256'],
                    all_three_policy_outputs_equal=all(index[seed,cases[0],m]['result_sha256']==index[seed,cases[1],m]['result_sha256'] for m in ('AdaptiveSense','GateOnly','TAIS'))))
    return out


def plot(summary,intervals,out,plan):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for kind in ('spike','drift'):
        fig,axes=plt.subplots(2,2,figsize=(12,8),sharex='col')
        for col,relation in enumerate(('same','cross')):
            for profile,style in [('short','-'),('long','--')]:
                for method,color in [('AdaptiveSense','#909090'),('GateOnly','#496c94'),('TAIS','#128575')]:
                    data=[next(r for r in summary if r['method']==method and r['group']==f'{kind}:{relation}:{profile}:dt:{dt}') for dt in plan['offsets'][kind]]
                    x=plan['offsets'][kind]
                    axes[0,col].plot(x,[100*r['recall'] for r in data],style,marker='o',color=color,label=f'{method} {profile}')
                    axes[1,col].plot(x,[r['fault_induced_false']/r['runs'] for r in data],style,marker='o',color=color)
            axes[0,col].set_title(f'{kind}: {relation} channel placement');axes[1,col].set_xlabel('Event plan start − fault start (s)')
        axes[0,0].set_ylabel('Event recall (%)');axes[1,0].set_ylabel('Fault-induced reports / run')
        axes[0,1].legend(fontsize=8);fig.suptitle('All registered offsets; lines guide the eye, not interpolation or synchronization evidence')
        fig.tight_layout();fig.savefig(out/f'{kind}_timing.png',dpi=160);plt.close(fig)
    family=list(dict.fromkeys(r['contrast'] for r in intervals));fig,axes=plt.subplots(2,1,figsize=(12,7))
    for ax,metric,scale,label in zip(axes,('recall','fault_induced_false_per_run'),(100,1),('Interaction in recall (pp)','Interaction in fault-induced reports / run')):
        for i,name in enumerate(family):
            r=next(r for r in intervals if r['contrast']==name and r['metric']==metric)
            ax.vlines(i,scale*r['familywise_low'],scale*r['familywise_high'],color='#128575');ax.plot(i,scale*r['estimate'],'o',color='#128575')
        ax.axhline(0,color='#777',linewidth=1);ax.set_ylabel(label);ax.set_xticks(range(len(family)),family,rotation=13,fontsize=8)
    fig.suptitle('All12 primary contrasts; Bonferroni familywise intervals');fig.tight_layout();fig.savefig(out/'primary_interactions.png',dpi=160);plt.close(fig)


def freeze(root,plan):
    calibration={}
    for phase in ('development','validation'):
        read_phase(root,phase,plan)
        verification=root/phase/'verification.json';v=json.loads(verification.read_text())
        if not v['all_metrics_recomputed'] or not v['no_policy_rerun']:raise ValueError('Calibration not verified')
        for p in [root/phase/'manifest.json',root/phase/'metrics.csv',verification,root/phase/'analysis/manifest.json']:
            calibration[str(p.resolve().relative_to(ROOT))]=sha(p)
    lock=dict(status='FROZEN_BEFORE_TEST',no_parameter_search=True,frozen_files=fingerprints(),plan_sha256=sha(ROOT/'configs/fault-event-observability.json'),calibration_files=calibration,
              source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),final_seeds=plan['seeds']['test'])
    with (root/'final-lock.json').open('x') as f:json.dump(lock,f,indent=2);f.write('\n')
    print('Final source/population lock written; commit before final access.')


def analyze(root,phase,plan):
    m,rows=read_phase(root,phase,plan);out=root/phase/'analysis'
    if out.exists():raise FileExistsError('Never overwrite/repeat analysis')
    out.mkdir();by=defaultdict(list)
    for r in rows:
        for group in groups(r):by[r['method'],group].append(r)
    summary=[dict(method=method,group=group,**aggregate(values)) for (method,group),values in sorted(by.items())]
    csv_write(out/'summary.csv',summary);eq=equivalences(rows)
    if eq:csv_write(out/'observational_equivalence.csv',eq)
    if phase=='test':
        lock=root/'final-lock.json'
        if m['final_lock_sha256']!=sha(lock):raise ValueError('Final lock changed')
        paired=pairs(rows);grouped=defaultdict(list);intervals=[]
        for g,t in paired:
            for group in groups(g):grouped[group].append((g,t))
        for group,p in sorted(grouped.items()):
            for r in paired_bootstrap(p,plan['bootstrap_replicates'],plan['bootstrap_seed'],family=plan['primary_family_size']):
                if r['metric'].startswith('binary_v1'):continue
                intervals.append(dict(group=group,**r))
        csv_write(out/'paired_intervals.csv',intervals)
        primary,deletions=interactions(paired,plan)
        csv_write(out/'timing_interactions.csv',primary);csv_write(out/'interaction_deletions.csv',deletions)
        (out/'common_matched_delay.json').write_text(json.dumps(common_delays(root/phase/'event_matches.csv',plan),indent=2)+'\n')
        plot(summary,primary,out,plan)
    # Enumerate completed outputs BEFORE opening manifest: no self-hash defect.
    outputs={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}
    with (out/'manifest.json').open('x') as f:json.dump(dict(phase=phase,runs=len(rows),seeds=m['seeds'],source_manifest_sha256=sha(root/phase/'manifest.json'),frozen_files=fingerprints(),outputs=outputs),f,indent=2);f.write('\n')
    print(f'{phase} analysis complete: {len(rows)} runs, {len(summary)} grouped summaries',flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--phase',choices=['smoke','development','validation','test']);g.add_argument('--freeze',action='store_true');p.add_argument('--root',type=Path,default=RESULTS);args=p.parse_args()
    plan=json.loads((ROOT/'configs/fault-event-observability.json').read_text())
    if args.freeze:freeze(args.root,plan)
    else:analyze(args.root,args.phase,plan)
if __name__=='__main__':main()
