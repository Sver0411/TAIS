"""FO-1 fixture tests use only already-used seed20; no final-noise peeking."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from tais.config import load
from tais.observability_signals import generate,scenarios,specification,metadata,overlap,OFFSETS
from tais.signals import generate as original,scenarios as original_cases,Fault
from simulator.events import Event
from run_experiments import canonical


def test_matrix_has_exactly93_unique_and_default_only_once():
    assert len(scenarios())==len(set(scenarios()))==93
    assert scenarios()[:45]==original_cases()
    for kind in OFFSETS:
        assert sum(x.startswith(kind+'_') and '_dt_' in x for x in scenarios())==24
    with pytest.raises(ValueError):specification('spike_same_short_dt_p60')
    with pytest.raises(ValueError):specification('drift_cross_long_dt_p61')


@pytest.mark.parametrize('case',original_cases())
def test_every_original_case_keeps_exact_history(case):
    assert canonical(generate(load(),20,case))==canonical(original(load(),20,case))


@pytest.mark.parametrize('kind',('spike','drift'))
@pytest.mark.parametrize('relation',('same','cross'))
@pytest.mark.parametrize('profile',('short','long'))
def test_all_registered_offsets_truth_noise_and_fault_boundaries(kind,relation,profile):
    cfg=load();saved=deepcopy(cfg);reference=original(cfg,20,f'{kind}_{relation}_{profile}')
    old_no_event=original(cfg,20,f'{kind}_none_{profile}')
    for dt in OFFSETS[kind]:
        name=f'{kind}_{relation}_{profile}' if dt==60 else f'{kind}_{relation}_{profile}_dt_{"m"+str(-dt) if dt<0 else "p"+str(dt)}'
        trace=generate(cfg,20,name);meta=metadata(trace,cfg);f=trace.faults[0]
        assert cfg==saved and trace.faults==reference.faults
        assert len(trace.events)==1 and meta['offset_s']==dt
        assert trace.events[0].channel==('humidity' if relation=='cross' else 'temperature')
        assert meta['event_plan_start_s']==f.start_s+dt
        assert meta['overlap']['observation_points']==sum(trace.events[0].start_s<=i<=trace.events[0].end_s and f.start_s<=i<f.end_s for i in range(1800))
        assert meta['overlap']['duration_s']==max(0,min(trace.events[0].end_s,f.end_s)-max(trace.events[0].start_s,f.start_s))
        if kind=='spike':assert f.end_s-f.start_s==1
        else:assert f.end_s-f.start_s==cfg['synthetic']['profiles'][profile]['fault_duration_s']
        # Noise draws preserved despite different driven means (floating subtraction roundoff).
        for a,b,c,d in zip(trace.noisy,trace.latent,reference.noisy,reference.latent):
            for channel in cfg['channels']:assert a[channel]-b[channel]==pytest.approx(c[channel]-d[channel],abs=1e-14)
        assert all(canonical(a)==canonical(b) for i,(a,b) in enumerate(zip(trace.observed,trace.noisy)) if not f.start_s<=i<f.end_s)


def test_overlap_half_open_injection_and_inclusive_label_endpoint():
    f=Fault('temperature',10,11,'spike')
    assert overlap(Event('temperature',11,20),f)['observation_points']==0
    x=overlap(Event('temperature',0,10),f)
    assert x['observation_points']==1 and x['duration_s']==0
    assert overlap(Event('temperature',0,9),f)['observation_points']==0


def test_truth_does_not_call_scorer_or_scheduler(monkeypatch):
    import tais.scheduler
    import simulator.scoring
    def forbidden(*a,**k):raise AssertionError('Truth leaked from algorithm')
    monkeypatch.setattr(tais.scheduler.Scheduler,'update',forbidden)
    monkeypatch.setattr(simulator.scoring.ChangeAnalyzer,'update',forbidden)
    a=generate(load(),20,'drift_same_short_dt_p0');b=generate(load(),20,'spike_same_short_dt_m10')
    assert len(a.events)==len(b.events)==1


@pytest.mark.parametrize('method',('AdaptiveSense','GateOnly','TAIS'))
def test_online_replay_cannot_use_hidden_truth_or_future_values(method):
    from tais.replay import run
    cfg=load();a=generate(cfg,20,'spike_same_long_dt_m10');b=deepcopy(a)
    # Destroy labels, hidden latent/noise and future suffix; prefix must remain identical.
    b.events=[];b.faults=[];b.latent=[];b.noisy=[]
    for row in b.observed[900:]:row['temperature']=70;row['humidity']=90
    ra=run(a,cfg,method);rb=run(b,cfg,method)
    assert canonical([r for r in ra['records'] if r['timestamp']<900])==canonical([r for r in rb['records'] if r['timestamp']<900])
    assert all(5<=r['interval']<=60 for r in ra['records'])


def test_runner_cache_uses_exact_clean_stream_not_only_relation_profile(tmp_path):
    from run_fault_event_observability import worker
    import csv,gzip
    cases=['spike_same_short','drift_same_short','spike_same_short_dt_m10']
    chunk=worker(20,cases,tmp_path,'fixture')
    rows=list(csv.DictReader(open(chunk['paths']['metrics'])))
    assert chunk['runs']==9 and chunk['counterfactuals']==6
    for method in ('AdaptiveSense','GateOnly','TAIS'):
        selected=[r for r in rows if r['method']==method]
        assert selected[0]['counterfactual_path']==selected[1]['counterfactual_path']
        assert selected[0]['counterfactual_path']!=selected[2]['counterfactual_path']
    for case in cases:assert len({r['observed_sha256'] for r in rows if r['scenario']==case})==1


def test_physical_label_overlap_not_inferred_from_offset_sign():
    for relation in ('same','cross'):
        for dt in ('m1','p0','p1'):
            t=generate(load(),20,f'spike_{relation}_short_dt_{dt}')
            assert metadata(t,load())['temporal']=='fault_before_event'
        assert metadata(generate(load(),20,f'spike_{relation}_short_dt_m10'),load())['temporal']=='overlap'


def test_equal_observations_can_have_different_event_truth():
    for kind in ('range','missing','invalid','stuck'):
        for profile in ('short','long'):
            a=generate(load(),20,f'{kind}_same_{profile}');b=generate(load(),20,f'{kind}_none_{profile}')
            assert a.events and not b.events
            assert canonical(a.observed)==canonical(b.observed)


def test_primary_interaction_is_normalized_per_seed_and_family_fixed():
    from analyze_fault_event_observability import interactions
    plan=json.loads((ROOT/'configs/fault-event-observability.json').read_text())
    assert len(plan['primary_contrasts'])*len(plan['primary_metrics'])==12
    paired=[]
    for s in (0,1,2):
        for dt in (-10,60):
            for relation in ('same','cross'):
                g=dict(seed=s,scenario=f'{dt}-{relation}',fault_kind='spike',n_events=1,relationship=relation,offset_s=dt,tp=0,fault_induced_false=2)
                t={**g,'tp':int(dt==-10),'fault_induced_false':1 if dt==-10 else 2}
                paired.append((g,t))
    small={**plan,'primary_contrasts':plan['primary_contrasts'][:1],'bootstrap_replicates':100}
    out,deletions=interactions(paired,small)
    assert len(out)==2
    assert out[0]['estimate']==1 and out[1]['estimate']==-1
    assert all(r['adjusted_excludes_zero'] and r['all_deletions_same_direction'] for r in out)


def test_partial_smoke_cannot_claim_unavailable_equivalence_pair():
    from analyze_fault_event_observability import equivalences
    assert equivalences([dict(seed=20,scenario='range_same_long',method='GateOnly')])==[]


def test_complete_execution_analysis_and_verification_on_old_seed20(tmp_path):
    from run_fault_event_observability import worker,fingerprints
    from analyze_fault_event_observability import analyze
    from verify_fault_event_observability import verify
    from tais.budget_eval import sha
    import shutil
    plan=json.loads((ROOT/'configs/fault-event-observability.json').read_text())
    fixture={**plan,'seeds':{'test':[20]},'bootstrap_replicates':100}
    archive=tmp_path/'raw';chunk=worker(20,scenarios(),archive,sha(ROOT/'configs/fault-event-observability.json'))
    assert chunk['runs']==279
    path=tmp_path/'test';path.mkdir()
    for name in ('metrics','event_matches','reports'):shutil.copyfile(chunk['paths'][name],path/(name+'.csv'))
    (tmp_path/'final-lock.json').write_text('{}')
    manifest=dict(status='COMPLETE',phase='test',seeds=[20],cases=scenarios(),runs=279,methods=plan['methods'],
       frozen_files=fingerprints(),csv_sha256={p.name:sha(p) for p in path.glob('*.csv')},archive_root=str(archive),
       artifacts=chunk['artifacts'],plan_sha256=sha(ROOT/'configs/fault-event-observability.json'),final_lock_sha256=sha(tmp_path/'final-lock.json'))
    (path/'manifest.json').write_text(json.dumps(manifest))
    analyze(tmp_path,'test',fixture)
    assert verify(tmp_path,'test',fixture)['verified_rows']==279
    output=json.loads((path/'analysis/manifest.json').read_text())
    assert 'manifest.json' not in output['outputs']
    for name,digest in output['outputs'].items():assert sha(path/'analysis'/name)==digest
    with pytest.raises(FileExistsError):analyze(tmp_path,'test',fixture)
