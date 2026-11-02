"""Phase4 causal, budget, persistence, health, wire and historical contracts."""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import random
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from tais.adaptive import RobustSampler,RiskAwareSampler
from tais.adaptive.policy import Phase4Sender
from tais.config import load
from tais.scheduler import Scheduler
from tais.wire_codec import encode,decode
from phase4_support import replay,make_trace,cases,methods
from benchmark_joint_optimization import canon

PLAN=json.loads((ROOT/'configs/phase4.json').read_text())


def build(kind='Robust',noise=None,**overrides):
    options={**PLAN['common'],**PLAN['robust' if kind=='Robust' else 'risk'],**overrides}
    return (RobustSampler if kind=='Robust' else RiskAwareSampler)(noise or {'x':1.},options)


def health(names):
    return {n:dict(state='HEALTHY',score=100,flags=0) for n in names}


@pytest.mark.parametrize('kind',['Robust','Risk'])
def test_noise_is_bounded_in_every_actual_rolling_window(kind):
    rng=random.Random(940);s=build(kind);t=0;times=[];intervals=[]
    while t<3600:
        interval,d=s.update(t,{'x':rng.gauss(0,30)},health(['x']))
        times.append(t);intervals.append(interval);t+=interval
        assert 5<=interval<=60
    fast=[b for a,b in zip(times,times[1:]) if b-a<=5]
    assert all(sum(t-120<x<=t for x in fast)<=6 for t in times)
    assert intervals[-50:].count(5)<50


@pytest.mark.parametrize('kind',['Robust','Risk'])
def test_delayed_input_does_not_consume_requested_fast_slots(kind):
    s=build(kind);t=0
    for value in [0.]*9+[30.,30.,30.]:
        interval,d=s.update(t,{'x':value},health(['x']))
        t+=max(40,interval)
        assert d['fast_used']==0


def test_real_step_has_probe_persistence_hysteresis_and_cooldown():
    s=build();t=0
    for _ in range(7):
        i,_=s.update(t,{'x':0.},health(['x']));t+=i
    i,d=s.update(t,{'x':8.},health(['x']));assert i==5 and d['state']=='PROBE';t+=i
    i,d=s.update(t,{'x':8.},health(['x']));assert i==5 and d['state']=='TRACK';t+=i
    i,d=s.update(t,{'x':0.},health(['x']));assert d['state']=='COOLDOWN' and i==20
    end=d['cool_until'];t+=i
    i,d=s.update(t,{'x':100.},health(['x']));assert t<end and d['state']=='COOLDOWN' and i==20


@pytest.mark.parametrize('kind',['Robust','Risk'])
def test_custom_intervals_multichannel_invalids_and_missing_keep_running(kind):
    s=build(kind,noise={'a':1.,'b':2.,'c':3.},min_interval_s=2,watch_interval_s=8,
            cooldown_interval_s=10,diagnostic_interval_s=10,idle_interval_s=20,max_interval_s=45)
    t=0
    for value in [None,float('nan'),float('inf'),-float('inf'),1.,2.,3.]:
        i,d=s.update(t,dict(a=value,b=2.,c=3.),health(['a','b','c']))
        assert 2<=i<=45;t+=i
    assert len(s.history)==3
    with pytest.raises(ValueError):s.update(t-100,dict(a=1,b=2,c=3),health(['a','b','c']))


@pytest.mark.parametrize('kind',['Robust','Risk'])
def test_invalid_configuration_raises(kind):
    with pytest.raises(ValueError):build(kind,fast_limit=0)
    with pytest.raises(ValueError):build(kind,enter_z=float('nan'))
    with pytest.raises(ValueError):build(kind,min_interval_s=80)


def test_risk_forecast_is_fitted_before_current_observation():
    a=build('Risk');b=build('Risk');t=0
    for x in [0.,.1,.2,.3]:
        ia,_=a.update(t,{'x':x},health(['x']));ib,_=b.update(t,{'x':x},health(['x']));assert ia==ib;t+=ia
    _,da=a.update(t,{'x':20.},health(['x']));_,db=b.update(t,{'x':-20.},health(['x']))
    assert da['features']['x']['prediction']==db['features']['x']['prediction']
    assert da['features']['x']['slope']==db['features']['x']['slope']


@pytest.mark.parametrize('kind',['Robust','Risk'])
@pytest.mark.parametrize('trust',[False,True])
@pytest.mark.parametrize('case',['clean_both','missing_temperature_cross','multi_range','noisy_events'])
def test_upload_does_not_change_sample_health_detector_or_budget(kind,trust,case):
    cfg=load();trace=make_trace(PLAN,940,case)
    a=Phase4Sender(cfg,PLAN,kind,trust,False);b=Phase4Sender(cfg,PLAN,kind,trust,True)
    try:
        for row in trace.observed:
            x,y=a.push(row),b.push(row);assert (x is None)==(y is None)
            if x:
                for k in ('timestamp','interval','active','scores','health','adaptive','candidate_starts'):
                    assert canon(x['record'][k])==canon(y['record'][k])
                if y['frame']:assert encode(decode(y['frame']))==y['frame']
    finally:a.close();b.close()


@pytest.mark.parametrize('kind',['Robust','Risk'])
def test_actual_c11_and_gate_are_exact_original_on_same_acquisitions(kind):
    cfg=load();sender=Phase4Sender(cfg,PLAN,kind,True,True);original=Scheduler(cfg,confirmation=False)
    try:
        for row in make_trace(PLAN,940,'range_temperature_same').observed:
            x=sender.push(row)
            if x:
                r=x['record'];d=original.update(r['timestamp'],r['values'])
                assert r['health']==d.health and r['active']==d.active and r['scores']==d.scores
    finally:
        sender.close()
        for engine in original.trust.values():engine.close()


@pytest.mark.parametrize('kind',['Robust','Risk'])
def test_disabled_trust_neutral_and_nonfinite_contract(kind):
    s=Phase4Sender(load(),PLAN,kind,False,True)
    try:
        for t,v in [(0,24.),(40,None),(80,float('inf')),(120,100.)]:
            x=s.push(dict(timestamp=t,temperature=v,humidity=45.))
            if x:assert all(h==dict(state='HEALTHY',score=100,flags=0) for h in x['record']['health'].values())
    finally:s.close()


@pytest.mark.parametrize('kind',['Robust','Risk'])
def test_stream_never_reads_unsampled_values_future_or_hidden_truth(kind):
    class Row(dict):
        def __getitem__(self,k):
            if k not in ('timestamp','temperature','humidity'):raise AssertionError('Hidden metadata read')
            return super().__getitem__(k)
    class Unsampled(dict):
        def __getitem__(self,k):
            if k!='timestamp':raise AssertionError('Unsampled value read')
            return super().__getitem__(k)
    class Trace:
        observed=[Row(timestamp=0,temperature=24.,humidity=45.),Unsampled(timestamp=1),Row(timestamp=60,temperature=25.,humidity=45.)]
        def __getattr__(self,k):raise AssertionError('Hidden truth/fault/future read: '+k)
    result=replay(Trace(),load(),kind+'-T1-U1',PLAN)
    assert [r['timestamp'] for r in result['records']]==[0,60]


@pytest.mark.parametrize('kind',['Robust','Risk'])
def test_repeated_input_is_deterministic_and_future_does_not_change_prefix(kind):
    cfg=load();tr=make_trace(PLAN,941,'noisy_events')
    a=replay(tr,cfg,kind+'-T1-U1',PLAN);b=replay(tr,cfg,kind+'-T1-U1',PLAN)
    assert canon(a)==canon(b)
    prefix=deepcopy(tr);prefix.observed=prefix.observed[:500]
    c=replay(prefix,cfg,kind+'-T1-U1',PLAN)
    assert canon(c['records'])==canon([r for r in a['records'] if r['timestamp']<500])


def test_matrix_and_historical_code_configs_results_remain_unchanged():
    assert len(cases(PLAN))==66 and len(methods(PLAN))==24
    protection=json.loads((ROOT/'results/phase4/historical-protection.json').read_text())
    for name,expected in protection['files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
    from benchmark_ablation import sources
    lock=json.loads((ROOT/'results/module-ablation/freeze.json').read_text())
    assert sources()==lock['sources']
