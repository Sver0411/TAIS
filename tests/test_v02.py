"""Mechanism, causality, real C integration and immutable legacy regression."""
from copy import deepcopy
from dataclasses import asdict
import gzip,json,math,hashlib
import pytest
from tais import ROOT
from tais.signals import generate,scenarios
from tais.replay import run as legacy_run
from tais_v02.config import load
from tais_v02.replay import run
from tais_v02.scheduler import Scheduler
from tais_v02.evidence import Evidence

@pytest.fixture
def cfg():return load()[0]

def canon(x):return json.dumps(x,default=asdict,sort_keys=True)

@pytest.mark.parametrize('case',scenarios())
def test_matrix_deterministic_and_bounded(cfg,case):
    a=run(generate(cfg,0,case),cfg,'V02');b=run(generate(cfg,0,case),cfg,'V02')
    assert canon(a)==canon(b)
    assert all(cfg['sampling']['min_interval_s']<=r['interval']<=cfg['sampling']['max_interval_s'] for r in a['records'])

def test_real_c_healthy_isolation(cfg):
    s=Scheduler(cfg)
    rows=[s.update(t,dict(temperature=150 if t>=50 else 24+.03*math.sin(t),humidity=45 if t<60 else 61)) for t in range(0,150,5)]
    assert any(d.active['humidity'] for d in rows)
    assert not any(d.active['temperature'] for d in rows if d.t>=50)

def test_real_c_single_spike_and_stale_recovery(cfg):
    for mode in ['spike','range','missing']:
        s=Scheduler(cfg);out=[]
        for t in range(0,150,5):
            value=36 if mode=='spike' and t==60 else (150 if mode=='range' and 20<=t<80 else (None if mode=='missing' and 20<=t<80 else 24))
            out.append(s.update(t,dict(temperature=value,humidity=45+.1*math.sin(t))))
        assert not any(d.active['temperature'] for d in out),mode
        if mode=='spike':assert out[12].health['temperature']['state']=='DEGRADED' and out[12].confirmation
        else:assert 'temperature' in out[16].recovery_reset

def test_real_c_degraded_sustained_event_has_opportunity(cfg):
    # Fast real-C windows create a known DEGRADED integration fixture, not labels.
    cfg=deepcopy(cfg);tr=cfg['channels']['temperature']['trust']
    tr.update(drift_window=2,drift_threshold=.00001,stuck_epsilon=0,spike_threshold=1000)
    s=Scheduler(cfg);out=[]
    for t in range(0,120,5):out.append(s.update(t,dict(temperature=24+t*.001+(4 if t>=60 else 0),humidity=45+.1*math.sin(t))))
    assert all(d.health['temperature']['state']=='DEGRADED' for d in out if 60<=d.t<=75)
    assert not any(d.active['temperature'] for d in out if d.t<70)
    assert any(d.active['temperature'] for d in out if 70<=d.t<=90)
    assert any(a['action']=='confirmed' for d in out for a in d.evidence['temperature']['actions'])

def test_deadline_rearm_and_passive_ablation(cfg):
    p=deepcopy(cfg['v02']);p['confirmation_samples']=1000;e=Evidence(p)
    for t in range(0,150,5):
        event,pending,actions=e.step(t,30,'DEGRADED',20,True,24,8,.15)
        assert not event
        if t>=120:assert not pending
    assert e.blocked
    e.step(150,24,'DEGRADED',0,False,24,8,.15)
    assert not e.blocked
    a=Scheduler(cfg,confirmation=True);b=Scheduler(cfg,confirmation=False)
    a.update(0,dict(temperature=24,humidity=45));b.update(0,dict(temperature=24,humidity=45))
    da=a.update(60,dict(temperature=36,humidity=45));db=b.update(60,dict(temperature=36,humidity=45))
    assert da.confirmation and not db.confirmation
    assert da.evidence==db.evidence
    assert da.interval<=db.interval

def test_pending_uses_event_threshold_across_alert_and_health(cfg):
    e=Evidence(cfg['v02'])
    e.step(0,28,'DEGRADED',20,False,24,8,.15)
    event,pending,_=e.step(5,28,'DEGRADED',9,False,25,8,.15)
    assert pending and not event  # legacy >=12 re-entry would cancel here
    event,pending,actions=e.step(10,28,'HEALTHY',9,True,26,8,.15)
    assert event and not pending
    assert any(a['action']=='confirmed' for a in actions)

@pytest.mark.parametrize('method',['V02','V02-Passive'])
def test_causality_truth_and_unsampled_guard(cfg,method):
    a=generate(cfg,2,'drift_same_long');b=deepcopy(a)
    for r in b.observed[901:]:r.update(temperature=1000,humidity=-1000)
    b.events=[];b.faults=[];b.latent=[];b.noisy=[]
    ra=run(a,cfg,method)['records'];rb=run(b,cfg,method)['records']
    assert [r for r in ra if r['timestamp']<=900]==[r for r in rb if r['timestamp']<=900]
    allowed={r['timestamp'] for r in ra}
    class Hidden(dict):
        def __getitem__(self,k):
            if k!='timestamp' and super().__getitem__('timestamp') not in allowed:raise AssertionError('unsampled value')
            return super().__getitem__(k)
    a.observed=[Hidden(r) for r in a.observed]
    # Compare entire replay to a fresh ordinary trace; guard raises on any hidden read.
    assert canon(run(a,cfg,method))==canon(run(generate(cfg,2,'drift_same_long'),cfg,method))

def test_disabled_exact_legacy_and_frozen_sources(cfg):
    cfg['v02']['enabled']=False
    for case in ['clean_short','drift_same_long','range_cross_short','spike_same_short']:
        tr=generate(cfg,0,case)
        assert canon(run(tr,cfg,'V02'))==canon(legacy_run(tr,cfg,'TAIS'))
    # Committed immutable hashes also work in GitHub's depth-1 checkout.
    frozen=json.loads((ROOT/'results/v0.2/legacy_source_hashes.json').read_text())
    for name,digest in frozen.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest

def test_legacy_archive_fresh_reproduction(cfg):
    import sys
    sys.path.insert(0,str(ROOT/'scripts'))
    from run_experiments import canonical
    for method in ['AdaptiveSense','GateOnly','TAIS']:
        original=ROOT/f'results/traces/test/20/drift_same_long/{method}-1.json.gz'
        if original.exists():
            assert canonical(legacy_run(generate(cfg,20,'drift_same_long'),cfg,method))==gzip.decompress(original.read_bytes())
        else:
            # Portable committed forensic record contains the identical result.
            committed=ROOT/f'results/v0.2/forensics/drift_same_long-{method}.json.gz'
            archived=json.loads(gzip.decompress(committed.read_bytes()))['result']
            assert json.loads(canonical(legacy_run(generate(cfg,20,'drift_same_long'),cfg,method)))==archived

@pytest.mark.parametrize('kind',['range','missing','invalid','stuck'])
def test_nonidentifiable_pairs_are_boundary_not_success(cfg,kind):
    a=generate(cfg,0,kind+'_same_long');b=generate(cfg,0,kind+'_none_long')
    assert canon(a.observed)==canon(b.observed) and len(a.events)==1 and not b.events
    assert canon(run(a,cfg,'V02'))==canon(run(b,cfg,'V02'))

def test_known_blocked_rearm_failure_after_spike(cfg):
    from simulator.events import match_events
    trace=generate(cfg,91,'spike_same_long')
    from tais_rearm.replay import run as repaired_run
    result=repaired_run(trace,cfg,'V02-Rearm')
    assert match_events(trace.events,result['reports'],5).true_positives==1
