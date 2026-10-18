"""BM-1 bookkeeping, no-outcome selection, clustered uncertainty and strict gates."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import pytest
from tais.budget_eval import (aggregate,choose_pairs,paired_rows,paired_bootstrap,robustness,decision,groups,absolute_bootstrap)

ROOT=Path(__file__).resolve().parents[1]
PLAN=json.loads((ROOT/'configs/budget-matched.json').read_text())


def row(method='GateOnly',m=1.,seed=0,scenario='a',fault=10,tp=1,samples=100,uploads=50):
    return dict(method=method,multiplier=m,seed=seed,scenario=scenario,fault_kind='drift' if scenario=='a' else 'spike',
                profile='short',relationship='same',n_events=1,tp=tp,missed=1-tp,local_tp=tp,
                false_reports=fault,fault_induced_false=fault,samples=samples,uploads=uploads,payload_bytes=uploads*200,
                binary_v1_bytes=uploads*36,latency_sum_s=tp*10,latency_n=tp,duration_s=1800,
                signals_sha256='signal',observed_sha256='observed',events_sha256='events',faults_sha256='faults')


def matrix():
    return [row(method,m,s,case,samples=100+20*(2-m)+(.5 if method=='TAIS' else 0),uploads=50+10*(2-m)+(.2 if method=='TAIS' else 0))
            for method in ('GateOnly','TAIS') for m in PLAN['grid'] for s in (0,1) for case in ('a','b')]


def test_resource_selection_is_blind_to_all_detection_outcomes():
    data=matrix();choices,candidates=choose_pairs(data,data,PLAN)
    corrupted=deepcopy(data)
    for i,r in enumerate(corrupted):r.update(tp=i*100,missed=-i,false_reports=99999-i,fault_induced_false=i*50,latency_sum_s=12345-i,payload_bytes=999999)
    other,_=choose_pairs(corrupted,corrupted,PLAN)
    assert choices==other
    assert len(candidates)==3*9*9
    assert all(c['calibration_matched'] and not c['fallback'] and c['gate_multiplier']==c['tais_multiplier']==c['anchor'] for c in choices)


def test_no_feasible_pair_is_marked_unmatched_not_interpolated():
    data=matrix()
    for r in data:
        if r['method']=='TAIS':r['samples']*=2;r['uploads']*=2
    choices,_=choose_pairs(data,data,PLAN)
    assert all(not c['calibration_matched'] and c['fallback'] for c in choices)
    assert all(c['gate_multiplier']==c['tais_multiplier']==c['anchor'] for c in choices)


def test_validation_can_reject_a_development_match_and_matrix_must_be_complete():
    dev=matrix();val=matrix()
    for r in val:
        if r['method']=='TAIS':r['uploads']*=1.5
    assert all(c['fallback'] for c in choose_pairs(dev,val,PLAN)[0])
    with pytest.raises(ValueError):choose_pairs([r for r in dev if r['multiplier']!=2],val,PLAN)


def test_exact_one_percent_boundary_and_no_rounding():
    plan={**PLAN,'grid':[1.],'anchors':[1.]};data=[row(),row('TAIS',samples=101,uploads=50.5)]
    assert choose_pairs(data,data,plan)[0][0]['calibration_matched']
    data[1]['samples']+=1e-8
    assert not choose_pairs(data,data,plan)[0][0]['calibration_matched']


def test_truth_and_full_pair_keys_must_match():
    data=[row(),row('TAIS')];assert len(paired_rows(data,1,1))==1
    data[1]['observed_sha256']='different'
    with pytest.raises(ValueError):paired_rows(data,1,1)
    with pytest.raises(ValueError):paired_rows([row()],1,1)


def test_no_event_recall_and_conditional_latency_are_not_zero_filled():
    r=row(tp=0);r.update(n_events=0,missed=0)
    a=aggregate([r]);assert a['recall'] is None and a['latency_mean_s'] is None
    ci=paired_bootstrap([(r,deepcopy(r))],200,731)
    recall=next(x for x in ci if x['metric']=='recall');assert recall['tais_minus_gate'] is None and recall['valid_draws']==0
    assert 'no_event' in groups(r) and 'fault_no_event' in groups(r)


def test_whole_seed_cluster_not_individual_observations():
    pairs=[]
    for seed,delta in [(0,1),(1,-1)]:
        for i in range(100):pairs.append((row(seed=seed,scenario=str(i),fault=10),row('TAIS',seed=seed,scenario=str(i),fault=10+delta)))
    c=next(c for c in paired_bootstrap(pairs,2000,731) if c['metric']=='fault_induced_false')
    assert c['seeds']==2 and c['tais_minus_gate']==0
    assert c['ci95_low']==-200 and c['ci95_high']==200
    assert c['familywise_low']<=c['ci95_low']<=c['ci95_high']<=c['familywise_high']


def positive_pairs():return [(row(seed=s,scenario=c,fault=10),row('TAIS',seed=s,scenario=c,fault=5)) for s in (0,1,2) for c in ('a','b')]


def test_go_requires_every_preregistered_gate_and_unmatched_is_ineligible():
    p=positive_pairs();choice=dict(budget='B1.00',gate_multiplier=1.,tais_multiplier=1.,calibration_matched=True)
    ci=paired_bootstrap(p,500,731);rob=robustness(p)
    # Two fault classes; deleting one still retains a benefit.
    assert all(r['passes'] for r in rob)
    assert decision(choice,p,ci,rob,PLAN)['go']
    assert not decision({**choice,'calibration_matched':False},p,ci,rob,PLAN)['go']
    worse=deepcopy(p)
    for g,t in worse:t['samples']=g['samples']*1.02
    assert not decision(choice,worse,ci,rob,PLAN)['go']
    margin=deepcopy(ci);next(c for c in margin if c['metric']=='recall')['ci95_low']=-.01
    assert not decision(choice,p,margin,rob,PLAN)['go']


def test_favorable_recall_does_not_override_extra_fault_false_reports():
    p=positive_pairs()
    for g,t in p:t['fault_induced_false']=g['fault_induced_false']+1
    choice=dict(budget='B1.00',gate_multiplier=1.,tais_multiplier=1.,calibration_matched=True)
    d=decision(choice,p,paired_bootstrap(p,300,731),robustness(p),PLAN)
    assert not d['fault_improvement'] and not d['go']


def test_single_fault_class_only_improvement_fails_deletion_guard():
    p=positive_pairs()
    for g,t in p:
        if g['fault_kind']=='spike':t['fault_induced_false']=g['fault_induced_false']
    removed=next(r for r in robustness(p) if r['deleted_field']=='fault_kind' and r['deleted_value']=='drift')
    assert not removed['passes'] and removed['fault_induced_difference']==0


def test_reconstruction_rmse_pools_squared_errors_with_coverage():
    a=row();b=row();a.update(sample_rmse_temperature=2,sample_mae_temperature=2,sample_coverage_temperature=1)
    b.update(sample_rmse_temperature=4,sample_mae_temperature=4,sample_coverage_temperature=.5)
    result=aggregate([a,b]);assert result['sample_mae_temperature']==pytest.approx(8/3)
    assert result['sample_rmse_temperature']==pytest.approx((8)**.5)


def test_absolute_bootstrap_retains_undefined_denominators():
    r=row(tp=0);r.update(n_events=0,missed=0)
    cis=absolute_bootstrap([r],100,731)
    recall=next(c for c in cis if c['metric']=='recall');assert recall['estimate'] is None and recall['ci95_low'] is None


def test_runner_uses_actual_unmodified_replay_and_independent_truth(tmp_path):
    import sys
    sys.path.insert(0,str(ROOT/'scripts'))
    from run_budget_matched_experiment import worker
    from tais.signals import generate
    from tais.config import load
    from tais.replay import run
    from run_experiments import canonical
    import gzip,csv
    result=worker(20,['clean_none','spike_same_short','range_cross_long'],[(m,1.) for m in ('AdaptiveSense','AdaptiveSense+TrustLog','GateOnly','TAIS')],str(tmp_path))
    assert result['runs']==12
    recorded=list(csv.DictReader(open(result['metrics'])))
    for method in ('GateOnly','TAIS'):
        actual=gzip.decompress((tmp_path/f'20/spike_same_short/{method}-1.json.gz').read_bytes())
        expected=run(generate(load(),20,'spike_same_short'),load(),method)
        assert actual==canonical(expected)
    for case in ('clean_none','spike_same_short','range_cross_long'):
        selected=[r for r in recorded if r['scenario']==case]
        assert len({r['signals_sha256'] for r in selected})==1
        assert len({r['events_sha256'] for r in selected})==1
        assert len({r['faults_sha256'] for r in selected})==1


def test_complete_analysis_pipeline_on_old_seed20_only(tmp_path):
    import csv,sys
    sys.path.insert(0,str(ROOT/'scripts'))
    from run_budget_matched_experiment import worker,fingerprints
    from analyze_budget_matched_results import analyze
    from tais.signals import scenarios
    from tais.budget_eval import sha
    points=[(m,1.) for m in ('AdaptiveSense','AdaptiveSense+TrustLog','GateOnly','TAIS')]
    result=worker(20,scenarios(),points,str(tmp_path/'raw'))
    out=tmp_path/'test';out.mkdir()
    import shutil
    shutil.copyfile(result['metrics'],out/'metrics.csv');shutil.copyfile(result['events'],out/'event_matches.csv')
    choice=dict(budget='B1.00',gate_multiplier=1.,tais_multiplier=1.,calibration_matched=True)
    lock=dict(budgets=[choice],final_points=[dict(method=m,multiplier=x) for m,x in points])
    (tmp_path/'selection.json').write_text(json.dumps(lock))
    manifest=dict(status='COMPLETE',phase='test',runs=180,seeds=[20],cases=scenarios(),points=points,
                  metrics_sha256=sha(out/'metrics.csv'),event_matches_sha256=sha(out/'event_matches.csv'),
                  selection_sha256=sha(tmp_path/'selection.json'),frozen_files=fingerprints())
    (out/'manifest.json').write_text(json.dumps(manifest))
    fixture_plan={**PLAN,'seeds':{'test':[20]},'bootstrap_replicates':100}
    analyze(tmp_path,'test',fixture_plan)
    actual=json.loads((out/'analysis/decision.json').read_text())
    assert actual['decision']=='NO-GO' and actual['seeds']==[20]
    assert (out/'analysis/budget_tradeoff.png').exists()
    with pytest.raises(FileExistsError):analyze(tmp_path,'test',fixture_plan)
