"""Legacy gate engineering regression against pinned upstream behavior and synthetic fixtures."""
from copy import deepcopy
from dataclasses import asdict
import csv,inspect,math,random,subprocess
import pytest
from tais import ROOT
from tais.config import load,baseline
from tais.trust import SensorTrust
from tais.scheduler import Scheduler
from tais.signals import generate,scenarios
from tais.replay import run
from simulator.adaptive import AdaptiveScheduler
from simulator.replay import run_adaptive

@pytest.fixture
def cfg():return load()

def test_pinned_sources():
    for p,sha in [('AdaptiveSense','f7ec30fd4721aa1a7c308f879050a83936e60067'),('SensorTrust','2ce98dd043bb01ea99052eda218c68a172499a4c')]:
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT/'vendor'/p,text=True).strip()==sha

@pytest.mark.parametrize('case',scenarios())
def test_bounds_and_reproducibility(cfg,case):
    a=run(generate(cfg,0,case),cfg,'TAIS')
    b=run(generate(cfg,0,case),cfg,'TAIS')
    # NaN values are invalid; compare canonical serialisation via shared helper below.
    import json
    assert json.dumps(a,default=asdict,sort_keys=True)==json.dumps(b,default=asdict,sort_keys=True)
    assert all(5<=r['interval']<=60 for r in a['records'])

def test_cross_channel_fault_does_not_erase_event(cfg):
    a=Scheduler(cfg)
    out=[]
    for t in range(0,180,5):
        out.append(a.update(t,{'temperature':150 if t>=50 else 24+.03*math.sin(t),'humidity':45 if t<60 else 61}))
    assert any('humidity' in d.onsets for d in out)
    assert not any('temperature' in d.onsets for d in out if d.t>=50)

@pytest.mark.parametrize('confirm',[True,False])
def test_fault_cannot_trigger_and_recovery_resets(cfg,confirm):
    a=Scheduler(cfg,confirmation=confirm)
    for t in range(0,120,5):
        d=a.update(t,{'temperature':150 if 20<=t<80 else 24,'humidity':45+.1*math.sin(t)})
        assert 'temperature' not in d.onsets
        if t==80:assert 'temperature' in d.recovery_reset

def test_isolated_degraded_spike_never_confirmed(cfg):
    a=Scheduler(cfg);out=[]
    for t in range(0,150,5):out.append(a.update(t,{'temperature':36 if t==60 else 24,'humidity':45+.1*math.sin(t)}))
    assert out[12].health['temperature']['state']=='DEGRADED'
    assert out[12].confirmation
    assert not any('temperature' in d.onsets for d in out)

def test_sustained_healthy_event(cfg):
    a=Scheduler(cfg)
    out=[a.update(t,{'temperature':24 if t<60 else 28,'humidity':45+.1*math.sin(t)}) for t in range(0,150,5)]
    assert any('temperature' in d.onsets for d in out)

def test_confirmation_persistence_and_duration(cfg):
    a=Scheduler(cfg)
    out=[a.update(t,{'temperature':24 if t<60 else 36,'humidity':45+.1*math.sin(t)}) for t in range(0,100,5)]
    assert not any('temperature' in d.onsets for d in out if d.t<70)
    assert any('temperature' in d.onsets for d in out if d.t>=70)

def test_confirmation_is_bounded(cfg):
    a=Scheduler(cfg)
    # Monotonic changes keep DRIFT suspicious; confirmation cannot renew while score remains high.
    out=[a.update(t,{'temperature':24+t*.02,'humidity':45+.1*math.sin(t)}) for t in range(0,1800,5)]
    streak=0
    for d in out:
        streak=streak+5 if d.confirmation else 0
        assert streak<=cfg['trust']['max_confirmation_duration_s']+5

def test_future_and_truth_changes_do_not_change_prefix(cfg):
    a=generate(cfg,2,'range_cross_long');b=deepcopy(a)
    for r in b.observed[901:]:r['temperature']=1000;r['humidity']=-1000
    b.events=[];b.faults=[];b.latent=[];b.noisy=[]
    ra=run(a,cfg,'TAIS')['records'];rb=run(b,cfg,'TAIS')['records']
    assert [r for r in ra if r['timestamp']<=900]==[r for r in rb if r['timestamp']<=900]
    assert list(inspect.signature(Scheduler.update).parameters)==['self','t','values']

@pytest.mark.parametrize("method",["Fixed-60","TAIS"])
def test_unsampled_values_are_not_read(cfg,method):
    a=generate(cfg,0,'clean_event')
    allowed={r['timestamp'] for r in run(a,cfg,method)['records']}
    class Hidden(dict):
        def __getitem__(self,k):
            if k!='timestamp' and super().__getitem__('timestamp') not in allowed:
                raise AssertionError('unsampled observation accessed')
            return super().__getitem__(k)
    a.observed=[Hidden(r) for r in a.observed]
    run(a,cfg,method)

def test_labels_independent_of_policy_and_fault_values(cfg):
    a=generate(cfg,5,'range_same_long');b=deepcopy(cfg)
    b['synthetic']['range_value']=900
    z=generate(b,5,'range_same_long')
    assert a.events==z.events and a.faults==z.faults and a.latent==z.latent and a.noisy==z.noisy
    before=(list(a.events),list(a.faults))
    for m in ['TAIS','GateOnly','AdaptiveSense','Fixed-5']:run(a,cfg,m)
    assert before==(a.events,a.faults)

def test_adaptive_baseline_matches_actual_upstream(cfg):
    trace=generate(cfg,3,'clean_event');b=baseline(cfg)
    ref=run_adaptive([r['timestamp'] for r in trace.observed],trace.observed,b)
    ours=run(trace,cfg,'AdaptiveSense')
    assert [r['timestamp'] for r in ours['records']]==ref.sample_timestamps
    assert [r['upload'] for r in ours['records']]==[d.upload_requested for d in ref.decisions]
    assert [(r['state'],r['interval']) for r in ours['records']]==[(d.state,d.interval_s) for d in ref.decisions]
    assert ours['detections']==ref.detected

def test_diagnostic_logging_never_affects_sampling(cfg):
    trace=generate(cfg,7,'drift_same_long')
    a=run(trace,cfg,'AdaptiveSense')['records'];b=run(trace,cfg,'AdaptiveSense+TrustLog')['records']
    assert [(r['timestamp'],r['upload'],r['active']) for r in a]==[(r['timestamp'],r['upload'],r['active']) for r in b]

def test_missing_is_never_scored_even_before_c_limit(cfg):
    a=Scheduler(cfg);a.update(0,{'temperature':24,'humidity':45})
    d=a.update(5,{'temperature':None,'humidity':46})
    assert d.health['temperature']['state']=='HEALTHY'
    assert not d.active['temperature'] and d.scores['temperature']==0

def test_invalid_configuration_and_clock(cfg):
    c=deepcopy(cfg);c['sampling']['min_interval_s']=100
    a=Scheduler(cfg);a.update(0,{'temperature':24,'humidity':45})
    with pytest.raises(ValueError):a.update(0,{'temperature':24,'humidity':45})
    bad=dict(cfg['channels']['temperature']['trust']);bad['stuck_window']=1000
    with pytest.raises(ValueError):SensorTrust(bad)

def test_c_adapter_matches_unmodified_upstream_cli(tmp_path):
    root=ROOT/'vendor/SensorTrust';exe=tmp_path/'replay'
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-O2','-I',str(root/'core'),str(root/'core/sensor_trust.c'),str(root/'simulator/replay_main.c'),'-lm','-o',str(exe)],check=True)
    for path in sorted((root/'results/dataset').glob('*.csv')):
        lines=path.read_text().splitlines();c={}
        for line in lines:
            if line.startswith('#config:'):
                c={k:float(v) if any(s in v.lower() for s in ['.','e']) else int(v) for k,v in [x.split('=') for x in line[8:].split()]}
        detector=SensorTrust(c)
        raw=list(csv.DictReader(x for x in lines if not x.startswith('#')))
        expected=list(csv.DictReader(subprocess.check_output([str(exe),str(path)],text=True).splitlines()))
        assert len(raw)==len(expected)>0
        for r,e in zip(raw,expected):
            h=detector.update(int(r['timestamp_ms'])/1000,float(r['value']) if int(r['valid']) else None)
            assert (h.score,h.state,h.flags)==(int(e['health_score']),e['state'],int(e['fault_flags']))

def test_no_event_recall_is_not_zero(cfg):
    from tais.metrics import evaluate
    trace=generate(cfg,0,'clean_none');r=run(trace,cfg,'TAIS')
    m=evaluate(trace,r,cfg)
    assert m['n_events']==0 and m['recall'] is None

def test_metric_report_matching_and_fault_attribution(cfg):
    from tais.metrics import evaluate
    from simulator.events import Event
    trace=generate(cfg,0,'range_same_long')
    result=run(trace,cfg,'TAIS');result['reports']=[Event('temperature',trace.faults[0].start_s+5,trace.faults[0].start_s+5)]
    m=evaluate(trace,result,cfg,{'reports':[]})
    assert m['fault_induced_false']==1 and m['tp']==0
    m=evaluate(trace,result,cfg,{'reports':result['reports']})
    assert m['fault_induced_false']==0

def test_zero_order_hold_reconstruction_uses_only_past(cfg):
    from tais.metrics import evaluate
    trace=generate(cfg,0,'clean_event');r=run(trace,cfg,'Fixed-60');m=evaluate(trace,r,cfg)
    # Two channels have different units and must stay separate.
    assert m['sample_mae_temperature']>=0 and m['sample_rmse_temperature']>=m['sample_mae_temperature']
    assert m['sample_coverage_temperature']==1
