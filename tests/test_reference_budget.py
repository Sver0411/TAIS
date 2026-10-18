"""IRB-1 software checks use old seed20 only, not new research seeds."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from tais.config import load
from tais.reference_signals import generate,scenario_specs,equivalence_pairs,main_config,A,B
from tais.reference_policy import Budget,run,json_bytes
from run_experiments import canonical


def test87_unique_cases_and_nonapplicable_factors_not_duplicated():
    specs=scenario_specs();assert len(specs)==len({s['id'] for s in specs})==87
    assert {c:sum(s['cohort']==c for s in specs) for c in ('mixed','event_only','drift_only','clean','missing','bias_stress')}==dict(mixed=48,event_only=12,drift_only=2,clean=1,missing=12,bias_stress=12)
    assert len(equivalence_pairs())==2
    assert all(s['alpha'] is None for s in specs if s['cohort'] in ('drift_only','clean'))


@pytest.mark.parametrize('spec',scenario_specs(),ids=lambda x:x['id'])
def test_same_quantity_model_and_independent_physical_labels(spec):
    cfg=load();old=deepcopy(cfg);trace,meta=generate(cfg,20,spec['id']);assert cfg==old
    assert meta['unit']=='degree_C' and meta['noise_sigma_C']==.08
    assert len(trace.events)==int(spec['event']) and len(trace.faults)==int(spec['drift'])
    assert (len(meta['reference_physical_labels'])>0)==(spec['event'] and spec['alpha']>0)
    if trace.faults:assert trace.faults[0].end_s-trace.faults[0].start_s==spec['duration_s']
    if trace.events and trace.faults:
        e,f=trace.events[0],trace.faults[0]
        assert meta['overlap']['observation_points']==sum(e.start_s<=t<=e.end_s and f.start_s<=t<f.end_s for t in range(1800))
    assert any(trace.noisy[t][A]-trace.latent[t][A]!=trace.noisy[t][B]-trace.latent[t][B]-.3 for t in range(10))
    if spec['reference']=='missing':assert any(r[B] is None for r in trace.observed)
    else:assert all(r[B] is not None for r in trace.observed)


@pytest.mark.parametrize('method',('GateOnly','TAIS','ReferenceGate'))
@pytest.mark.parametrize('level',(.75,1.,1.5))
def test_exact_twin_full_stream_and_every_policy_output(method,level):
    for fault,event in equivalence_pairs():
        a,ma=generate(load(),20,fault);b,mb=generate(load(),20,event)
        assert canonical(a.observed)==canonical(b.observed)
        assert canonical(a.latent)!=canonical(b.latent) and not a.events and b.events
        caps=dict(reads=int(100*level),uploads=int(80*level),bytes=int(25000*level))
        assert canonical(run(a,load(),method,caps))==canonical(run(b,load(),method,caps))


@pytest.mark.parametrize('method',('GateOnly','TAIS'))
def test_unbounded_wrapper_preserves_original_one_channel_replay(method):
    from tais.replay import run as original
    spec=next(s for s in scenario_specs() if s['cohort']=='mixed' and s['shape']=='plateau' and s['alpha']==1 and s['duration_s']==600 and s['offset_s']==60)
    trace,_=generate(load(),20,spec['id']);a=original(trace,main_config(load()),method);b=run(trace,load(),method,dict(reads=100000,uploads=100000,bytes=100000000))
    for ra,rb in zip(a['records'],b['records']):
        for k,v in ra.items():assert canonical(v)==canonical(rb[k]),k
    assert canonical(a['reports'])==canonical(b['reports']) and canonical(a['detections'])==canonical(b['detections'])


def test_truth_never_calls_scheduler_or_scorer(monkeypatch):
    from tais.scheduler import Scheduler
    from simulator.scoring import ChangeAnalyzer
    def fail(*a,**k):raise AssertionError('Algorithm used for truth')
    monkeypatch.setattr(Scheduler,'update',fail);monkeypatch.setattr(ChangeAnalyzer,'update',fail)
    for x,y in equivalence_pairs():assert not generate(load(),20,x)[0].events and generate(load(),20,y)[0].events


def test_budget_limits_exact_read_request_byte_boundaries():
    frame=dict(timestamp=0,value=24.25);size=len(json_bytes(frame));b=Budget(dict(reads=1,uploads=1,bytes=size))
    assert b.read(0,'A') and not b.read(0,'B')
    assert b.upload(0,frame)==(True,size) and not b.upload(1,frame)[0]
    c=Budget(dict(reads=0,uploads=2,bytes=size-1));assert not c.upload(0,frame)[0] and c.used['bytes']==0
    with pytest.raises(ValueError):Budget(dict(reads=1.5,uploads=1,bytes=1))


@pytest.mark.parametrize('method',('GateOnly','TAIS','ReferenceGate'))
def test_no_hidden_truth_future_or_overbudget_access(method):
    cfg=load();case=next(s['id'] for s in scenario_specs() if s['cohort']=='mixed' and s['offset_s']==0)
    trace,_=generate(cfg,20,case);other=deepcopy(trace);other.latent=[];other.noisy=[];other.events=[];other.faults=[]
    for r in other.observed[900:]:r[A]=80;r[B]=60
    caps=dict(reads=200,uploads=100,bytes=40000)
    a=run(trace,cfg,method,caps);b=run(other,cfg,method,caps)
    assert canonical([r for r in a['records'] if r['timestamp']<900])==canonical([r for r in b['records'] if r['timestamp']<900])
    class Guard(dict):
        def __getitem__(self,key):
            if key==B:raise AssertionError('Unpaid reference access')
            return super().__getitem__(key)
    x=SimpleNamespace(observed=[Guard(timestamp=0,temperature=24.)])
    assert not run(x,cfg,method,dict(reads=0,uploads=1,bytes=1000))['records']
    assert len(run(x,cfg,method,dict(reads=1,uploads=1,bytes=1000))['records'])==1


def fake_scheduler(*args,**kwargs):
    from tais.scheduler import Decision
    class Fake:
        def update(self,t,values):
            active=t in (10,20)
            return Decision(t,10,'ALERT' if active else 'STABLE',{A:20 if active else 0},{A:dict(score=100,state='HEALTHY',flags=0)},{A:active},[A] if t==10 else [],True,['fixture'],False,False,[])
    return Fake()


@pytest.mark.parametrize('b_change,expected',[(0,'undecided'),(2,'supported'),(4,'supported'),(None,'undecided')])
def test_reference_rule_preserves_candidate_when_flat_or_missing(monkeypatch,b_change,expected):
    import tais.reference_policy as policy
    monkeypatch.setattr(policy,'Scheduler',fake_scheduler)
    rows=[dict(timestamp=t,temperature=24.+(4 if t>=10 else 0),reference_temperature=(24.3+(b_change or 0) if t>=10 else 24.3)) for t in (0,10,20,30)]
    if b_change is None:
        rows[1][B]=None;rows[2][B]=None
    result=run(SimpleNamespace(observed=rows),load(),'ReferenceGate',dict(reads=100,uploads=100,bytes=100000))
    assert len(result['reports'])==1 and result['reports'][0].start_s==10
    assert result['episodes'][0]['status']==expected
    assert len(result['supported_reports'])==int(expected=='supported')
    assert len(result['reference_reads']) in (2,3)
    assert all(e['health'][A]['flags']==0 for e in result['envelopes'])


def test_unresolved_is_neither_correct_cause_nor_committed_environment_error(monkeypatch):
    import tais.reference_policy as policy
    from tais.reference_metrics import evaluate_reference
    from tais.signals import Trace
    monkeypatch.setattr(policy,'Scheduler',fake_scheduler)
    rows=[dict(timestamp=t,temperature=24.+(4 if 10<=t else 0),reference_temperature=24.3) for t in range(40)]
    trace=Trace('fixture','same','short',20,rows,rows,rows,[],[])
    result=run(trace,load(),'ReferenceGate',dict(reads=100,uploads=100,bytes=100000))
    m=evaluate_reference(trace,result,load(),dict(reports=[],supported_reports=[]))
    assert m['unresolved_received']==1 and m['false_reports']==1 and m['environment_false']==0
    assert m['fault_claim_tp']==m['fault_claim_fp']==0


def test_worker_full_matrix_analysis_and_offline_verification_old_seed20(tmp_path):
    from run_independent_reference_budget import worker,fingerprints
    from analyze_independent_reference_budget import analyze
    from verify_independent_reference_budget import verify
    from tais.budget_eval import sha
    import shutil
    plan=json.loads((ROOT/'configs/independent-reference-budget.json').read_text())
    caps={'1.0':dict(reads=75,uploads=60,bytes=14000)};archive=tmp_path/'raw'
    chunk=worker(20,scenario_specs(),archive,sha(ROOT/'configs/independent-reference-budget.json'),caps)
    assert chunk['runs']==261
    out=tmp_path/'test';out.mkdir()
    for src,name in [(chunk['rows'],'metrics.csv'),(chunk['events'],'event_matches.csv')]:shutil.copyfile(src,out/name)
    (tmp_path/'final-lock.json').write_text('{}')
    m=dict(status='COMPLETE',phase='test',seeds=[20],cases=[s['id'] for s in scenario_specs()],methods=plan['methods'],budgets=caps,runs=261,archive_root=str(archive),artifacts=chunk['artifacts'],frozen_files=fingerprints(),final_lock_sha256=sha(tmp_path/'final-lock.json'),csv_sha256={p.name:sha(p) for p in out.glob('*.csv')})
    (out/'manifest.json').write_text(json.dumps(m))
    fixture={**plan,'budget_levels':[1.],'seeds':{'test':[20]},'bootstrap_replicates':100}
    analyze(tmp_path,'test',fixture)
    assert verify(tmp_path,'test',fixture)['verified_rows']==261
    assert 'manifest.json' not in json.loads((out/'analysis/manifest.json').read_text())['outputs']
    with pytest.raises(FileExistsError):analyze(tmp_path,'test',fixture)
