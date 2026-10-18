#!/usr/bin/env python3
"""IRB-1 paired whole-seed inference; thresholds and budgets never selected here."""
import argparse,csv,json,subprocess,sys
from collections import defaultdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from tais.budget_eval import sha,COUNT_FIELDS
from tais.reference_metrics import aggregate,groups,EXTRA
from run_independent_reference_budget import DEST,csv_write,fingerprints
META={'scenario','method','cohort','shape','reference','temporal','counterfactual_path'}
COUNTS=tuple(k for k in (*COUNT_FIELDS,*EXTRA) if k!='binary_v1_bytes')


def read_rows(path):
    return [{k:(v if k in META or k.endswith('_sha256') else None if v=='' else int(v) if k=='seed' else float(v)) for k,v in r.items()} for r in csv.DictReader(path.open())]


def read_phase(root,phase,plan):
    path=root/phase;m=json.loads((path/'manifest.json').read_text())
    if m['status']!='COMPLETE' or m['frozen_files']!=fingerprints():raise ValueError('Source changed or incomplete')
    for name,h in m['csv_sha256'].items():
        if sha(path/name)!=h:raise ValueError('Changed CSV')
    rows=read_rows(path/'metrics.csv')
    if phase!='calibrate':
        if sorted(float(x) for x in m['budgets'])!=sorted(plan['budget_levels']):raise ValueError('Missing budget point')
        expected={(s,c,method,float(b)) for s in m['seeds'] for c in m['cases'] for method in plan['methods'] for b in m['budgets']}
        if len(rows)!=len(expected) or {(r['seed'],r['scenario'],r['method'],r['budget']) for r in rows}!=expected:raise ValueError('Incomplete or duplicate matrix')
        if m['seeds']!=plan['seeds'][phase] or m['cases']!=[s['id'] for s in plan['scenarios']]:raise ValueError('Wrong population')
    return m,rows


def make_pairs(rows,level):
    index={method:{(r['seed'],r['scenario']):r for r in rows if r['method']==method and r['budget']==level} for method in ('GateOnly','ReferenceGate')}
    g,t=index['GateOnly'],index['ReferenceGate']
    if g.keys()!=t.keys():raise ValueError('Unpaired row keys')
    out=[]
    for key in sorted(g):
        a,b=g[key],t[key]
        for field in ('signals_sha256','latent_sha256','noisy_sha256','observed_sha256','events_sha256','faults_sha256','cap_reads','cap_uploads','cap_bytes'):
            if a[field]!=b[field]:raise ValueError('Unequal paired input/cap')
        out.append((a,b))
    return out


def bootstrap(pairs,plan):
    seeds=sorted({g['seed'] for g,t in pairs});rng=np.random.default_rng(plan['bootstrap_seed']);idx=rng.integers(0,len(seeds),size=(plan['bootstrap_replicates'],len(seeds)))
    by={s:(aggregate([g for g,t in pairs if g['seed']==s]),aggregate([t for g,t in pairs if g['seed']==s])) for s in seeds}
    def divide(a,b):
        with np.errstate(divide='ignore',invalid='ignore'):return np.where(b>0,a/b,np.nan)
    vectors={k:(np.array([by[s][0][k] for s in seeds]),np.array([by[s][1][k] for s in seeds])) for k in COUNTS}
    def calc(draw):
        a={k:x[idx].sum(axis=1) if draw else np.array([x.sum()]) for k,(x,y) in vectors.items()}
        b={k:y[idx].sum(axis=1) if draw else np.array([y.sum()]) for k,(x,y) in vectors.items()}
        out={k:b[k]-a[k] for k in ('tp','missed','false_reports','fault_induced_false','environment_false','environment_induced_false','samples','main_reads','reference_reads','uploads','payload_bytes','upload_denials','read_denials')}
        for label,n,d in [('recall','tp','n_events'),('environment_recall','environment_tp','n_events'),('local_candidate_recall','local_tp','n_events'),('latency_mean_s','latency_sum_s','latency_n')]:out[label]=divide(b[n],b[d])-divide(a[n],a[d])
        out['environment_induced_false_relative']=divide(b['environment_induced_false']-a['environment_induced_false'],a['environment_induced_false'])
        return out
    point,draws=calc(False),calc(True);out=[]
    for metric,values in draws.items():
        good=values[np.isfinite(values)];estimate=float(point[metric][0]);estimate=estimate if np.isfinite(estimate) else None
        q=np.quantile(good,[.025,.975,plan['alpha']/(2*plan['primary_family_size']),1-plan['alpha']/(2*plan['primary_family_size'])]) if len(good) else [None]*4
        out.append(dict(metric=metric,reference_minus_gate=estimate,ci95_low=q[0],ci95_high=q[1],adjusted_low=q[2],adjusted_high=q[3],seeds=len(seeds),valid_draws=len(good),replicates=plan['bootstrap_replicates']))
    return out


def robustness(pairs):
    omissions=[('seed',s) for s in sorted({g['seed'] for g,t in pairs})]+[('scenario',s) for s in sorted({g['scenario'] for g,t in pairs})]
    out=[]
    for field,value in omissions:
        p=[(g,t) for g,t in pairs if g[field]!=value];g=aggregate([a for a,b in p]);r=aggregate([b for a,b in p]);delta=r['environment_induced_false']-g['environment_induced_false']
        out.append(dict(deleted_field=field,deleted_value=value,environment_induced_difference=delta,direction_retained=delta<0 and g['environment_induced_false']>0))
    return out


def decision(level,group,pairs,cis,deleted,plan):
    ci={r['metric']:r for r in cis};g=aggregate([g for g,t in pairs]);r=aggregate([t for g,t in pairs])
    def ni(metric):return all(ci[metric][k] is not None and ci[metric][k]>plan['recall_margin'] for k in ('ci95_low','adjusted_low'))
    false=ci['environment_induced_false_relative'];benefit=false['reference_minus_gate'] is not None and false['reference_minus_gate']<=-plan['minimum_false_reduction'] and all(false[k] is not None and false[k]<0 for k in ('ci95_high','adjusted_high'))
    hard=all(x['samples']<=x['cap_reads'] and x['uploads']<=x['cap_uploads'] and x['payload_bytes']<=x['cap_bytes'] for p in pairs for x in p)
    return dict(budget=level,group=group,hard_caps_respected=hard,candidate_noninferior=ni('recall'),environment_noninferior=ni('environment_recall'),false_benefit=benefit,robust=all(x['direction_retained'] for x in deleted),
                go=hard and ni('recall') and ni('environment_recall') and benefit and all(x['direction_retained'] for x in deleted),gate_environment_false=g['environment_induced_false'],reference_environment_false=r['environment_induced_false'])


def equivalences(rows,plan):
    index={(r['seed'],r['scenario'],r['method'],r['budget']):r for r in rows};out=[]
    for seed in sorted({r['seed'] for r in rows}):
        for a,b in plan['equivalence_pairs']:
            if (seed,a,'GateOnly',plan['budget_levels'][0]) not in index or (seed,b,'GateOnly',plan['budget_levels'][0]) not in index:continue
            for level in plan['budget_levels']:
                for method in plan['methods']:
                    x,y=index[seed,a,method,level],index[seed,b,method,level]
                    out.append(dict(seed=seed,budget=level,method=method,fault_world=a,event_world=b,observations_equal=x['observed_sha256']==y['observed_sha256'],truth_different=x['events_sha256']!=y['events_sha256'],latent_different=x['latent_sha256']!=y['latent_sha256'],complete_outputs_equal=x['result_sha256']==y['result_sha256']))
    return out


def analyze(root,phase,plan):
    m,rows=read_phase(root,phase,plan);out=root/phase/'analysis'
    if out.exists():raise FileExistsError('Analysis exists')
    out.mkdir();by=defaultdict(list)
    for r in rows:
        for group in groups(r):by[r['method'],r['budget'],group].append(r)
    summary=[dict(method=k[0],budget=k[1],group=k[2],**aggregate(v)) for k,v in sorted(by.items())];csv_write(out/'summary.csv',summary)
    eq=equivalences(rows,plan)
    if eq:csv_write(out/'observational_equivalence.csv',eq)
    if phase=='test':
        if m['final_lock_sha256']!=sha(root/'final-lock.json'):raise ValueError('Final lock changed')
        cis=[];deletes=[];decisions=[]
        for level in plan['budget_levels']:
            gp=defaultdict(list)
            for g,r in make_pairs(rows,level):
                for group in groups(g):gp[group].append((g,r))
            for group,pairs in sorted(gp.items()):
                bounds=bootstrap(pairs,plan);cis.extend(dict(budget=level,group=group,**r) for r in bounds)
                if group in plan['primary_groups']:
                    d=robustness(pairs);deletes.extend(dict(budget=level,group=group,**x) for x in d);decisions.append(decision(level,group,pairs,bounds,d,plan))
        csv_write(out/'paired_intervals.csv',cis);csv_write(out/'deletion_checks.csv',deletes);csv_write(out/'decisions.csv',decisions)
        primary=[r for r in cis if r['group'] in plan['primary_groups'] and r['metric'] in ('recall','environment_recall','environment_induced_false_relative')];assert len(primary)==3*len(plan['primary_groups'])*len(plan['budget_levels'])
        csv_write(out/'primary_corrected_intervals.csv',primary)
        result=dict(decision='GO' if any(x['go'] and x['group']=='responsive' for x in decisions) else 'CONDITIONAL_GO' if any(x['go'] for x in decisions) else 'NO-GO',budgets=decisions,family=27,prior_confirmation_nogo_preserved=True)
        (out/'decision.json').write_text(json.dumps(result,indent=2)+'\n');plot(summary,out,plan)
    outputs={p.name:sha(p) for p in out.iterdir() if p.is_file()}
    (out/'manifest.json').write_text(json.dumps(dict(phase=phase,frozen_files=fingerprints(),source_manifest_sha256=sha(root/phase/'manifest.json'),outputs=outputs),indent=2)+'\n')
    print(f'{phase}: {len(rows)} rows, {len(summary)} summaries, all scenarios retained',flush=True)


def plot(summary,out,plan):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(14,8))
    for col,alpha in enumerate((1.,.5,0.)):
        for method,color in [('GateOnly','#516f91'),('TAIS','#999999'),('ReferenceGate','#157f79')]:
            data=[next(r for r in summary if r['method']==method and r['budget']==level and r['group']==f'alpha:{alpha}') for level in plan['budget_levels']]
            axes[0,col].plot(plan['budget_levels'],[100*r['recall'] for r in data],'-o',label=method+' candidate',color=color)
            if method=='ReferenceGate':axes[0,col].plot(plan['budget_levels'],[100*r['environment_recall'] for r in data],'--s',color=color,label='Reference supported')
            axes[1,col].plot(plan['budget_levels'],[r['environment_induced_false'] for r in data],'-o',color=color,label=method)
        axes[0,col].set_title(f'alpha={alpha} (core + declared stress, descriptive)');axes[1,col].set_xlabel('Shared hard-budget multiplier')
        axes[0,col].set_ylabel('Event recall (%)');axes[1,col].set_ylabel('Committed fault-induced reports')
    axes[0,0].legend(fontsize=8);axes[1,0].legend(fontsize=8);fig.tight_layout();fig.savefig(out/'reference_tradeoff.png',dpi=170);plt.close(fig)


def freeze(root,plan):
    files={}
    for phase in ('calibrate','development','validation'):
        read_phase(root,phase,plan)
        v=root/phase/'verification.json';d=json.loads(v.read_text())
        if not d['all_metrics_recomputed'] or not d['no_policy_rerun']:raise ValueError('Unverified calibration')
        for p in [root/phase/'metrics.csv',root/phase/'manifest.json',v]:files[str(p.resolve().relative_to(ROOT))]=sha(p)
    lock=dict(status='FROZEN_BEFORE_TEST',frozen_files=fingerprints(),budget_lock_sha256=sha(root/'budget-lock.json'),calibration_files=files,final_seeds=plan['seeds']['test'],source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    with (root/'final-lock.json').open('x') as f:json.dump(lock,f,indent=2);f.write('\n')
    print('Final lock written; commit before test.')


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--phase',choices=['development','validation','test']);g.add_argument('--freeze',action='store_true');p.add_argument('--root',type=Path,default=DEST);a=p.parse_args();plan=json.loads((ROOT/'configs/independent-reference-budget.json').read_text())
    if a.freeze:freeze(a.root,plan)
    else:analyze(a.root,a.phase,plan)
if __name__=='__main__':main()
