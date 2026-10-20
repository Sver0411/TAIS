"""Engineering fixtures for independent sampled decisions, adapters and actual wire counts.

Used seeds exercise causality and recovery; they are not new held-out evidence."""
import sys
from pathlib import Path
from copy import deepcopy
import pytest
from tais.config import load,baseline
from tais.signals import generate
from tais.paper_baselines import IndependentSampler,run_independent,decorate
from tais.replay import run
from tais.wire_codec import encode,decode,envelope_from_record
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from paper_metrics import metrics
from benchmark_joint_optimization import metrics as old_metrics

@pytest.mark.parametrize('kind',['Delta','Variance','Rao-inspired'])
def test_bounds_recovery_and_timestamps(kind):
    p=IndependentSampler(kind,{'temperature':.15},40,4,{'temperature':24})
    assert p.update(0,{'temperature':24})==40
    assert p.update(40,{'temperature':28})==5
    for t in range(45,3600,5):p.update(t,{'temperature':24})
    assert p.interval==40
    assert len(p.history['temperature'])<=4
    with pytest.raises(ValueError):p.update(10,{'temperature':24})

@pytest.mark.parametrize('period',[5,10,20,30,40,60])
def test_reuse_fixed(period):
    cfg=load();tr=generate(cfg,20,'clean_short')
    r=run_independent(tr,cfg,dict(kind='Fixed',cap=period))
    assert r==run(tr,cfg,f'Fixed-{period}')
    assert [x['timestamp'] for x in r['records']]==list(range(0,1800,period))
    assert all(x['upload'] for x in r['records'])

@pytest.mark.parametrize('kind',['Delta','Variance','Rao-inspired'])
def test_causal_only_actual_samples(kind):
    cfg=load();tr=generate(cfg,20,'clean_short');spec=dict(kind=kind,cap=60,threshold=4)
    r=run_independent(tr,cfg,spec);ts={x['timestamp'] for x in r['records']}
    changed=deepcopy(tr)
    for row in changed.observed:
        if row['timestamp'] not in ts:
            row['temperature']=1e6;row['humidity']=-1e6
    assert run_independent(changed,cfg,spec)==r
    cut=deepcopy(tr);cut.observed=cut.observed[:700]
    assert run_independent(cut,cfg,spec)['records']==[x for x in r['records'] if x['timestamp']<700]

@pytest.mark.parametrize('case',['clean_none','range_same_long','missing_cross_long'])
def test_codec_health_receiver_and_adapters(case):
    cfg=load();tr=generate(cfg,20,case)
    r=run_independent(tr,cfg,dict(kind='Fixed',cap=20))
    h=decorate(r,cfg);u=decorate(r,cfg,upload=True);c=decorate(r,cfg,common=True)
    assert [x['timestamp'] for x in r['records']]==[x['timestamp'] for x in h['records']]
    assert [x['active'] for x in h['records']]==[x['active'] for x in u['records']]
    assert [x['active'] for x in r['records']]==[x['active'] for x in c['records']]
    for x in h['records']:
        env=envelope_from_record(x);assert decode(encode(env))==env
    _,ff=old_metrics(tr,h,cfg,h)
    m,frames,rx,ev,ages=metrics(tr,h,cfg,h,ff)
    assert m['rx_tp']==m['tp'] and m['important_edges_unreported']==0
    assert m['binary_v1_bytes']==sum(len(bytes.fromhex(f['frame_hex'])) for f in frames)
    if not tr.events:assert m['recall'] is None

def test_nonuniform_timestamps_change_rate():
    a=IndependentSampler('Delta',{'x':1},60,4)
    b=IndependentSampler('Delta',{'x':1},60,4)
    a.update(0,{'x':0});b.update(0,{'x':0})
    assert a.update(5,{'x':2})==5
    assert b.update(60,{'x':2})==60

@pytest.mark.parametrize('kind',['Delta','Variance','Rao-inspired'])
def test_budget_bound_does_not_change_native_default(kind):
    p=IndependentSampler(kind,{'temperature':.15},50,2,{'temperature':24},minimum=20)
    assert p.update(0,{'temperature':24})==50
    assert p.update(50,{'temperature':28})==20
    assert p.update(70,{'temperature':24})>=20
