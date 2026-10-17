"""State-boundary, real-C, causality and immutable-comparator regressions."""
from copy import deepcopy
from dataclasses import asdict
import gzip,hashlib,json,math
import pytest
from tais import ROOT
from tais.signals import generate,scenarios
from tais_v02.config import load
from tais_v02.replay import run as frozen_run
from tais_rearm.evidence import ReturnedReferenceEvidence
from tais_rearm.scheduler import Scheduler
from tais_rearm.replay import run
from simulator.events import match_events

@pytest.fixture
def cfg():return load()[0]
def canon(v):return json.dumps(v,default=asdict,sort_keys=True)
def seed_episode(cfg):
 e=ReturnedReferenceEvidence(cfg['v02']);e.step(0,36,'DEGRADED',80,False,24,8,.15);return e

def test_reference_return_rearms_but_does_not_emit_stale_event(cfg):
 e=seed_episode(cfg);event,pending,actions=e.step(5,24,'DEGRADED',70,True,26,8,.15)
 assert not event and not pending and not e.blocked
 assert [a['reason'] for a in actions]==['displacement_returned','reference_return_reset']

@pytest.mark.parametrize('reason',['opposite_overshoot','deadline','health_transition','confirmed_release','unusable'])
def test_rearm_is_not_unconditional(cfg,reason):
 e=seed_episode(cfg)
 if reason=='opposite_overshoot':e.step(5,10,'HEALTHY',90,True,26,8,.15);assert e.blocked
 elif reason=='deadline':e.step(120,36,'HEALTHY',80,True,30,8,.15);assert e.blocked
 elif reason=='health_transition':
  e.step(120,36,'DEGRADED',80,True,30,8,.15)
  _,_,a=e.step(125,36,'HEALTHY',80,True,30,8,.15);assert e.blocked and not a
 elif reason=='confirmed_release':
  e.step(5,36,'DEGRADED',80,False,25,8,.15);e.step(10,36,'DEGRADED',80,True,26,8,.15)
  e.step(15,24,'HEALTHY',90,True,27,8,.15);assert e.blocked
 else:
  event,pending,a=e.step(5,None,'FAULT',0,False,None,8,.15)
  assert not event and not pending and not any(x['reason']=='reference_return_reset' for x in a)

@pytest.mark.parametrize('profile',['short','long'])
@pytest.mark.parametrize('multiplier',[.75,1,pytest.param(1.5,marks=pytest.mark.xfail(strict=True,reason='Unchanged high-threshold debounce misses this pulse even in v0.1; assertion retained, rearm itself is IDLE'))])
def test_known_spike_then_event_all_points(cfg,profile,multiplier):
 tr=generate(cfg,91,'spike_same_'+profile);r=run(tr,cfg,'V02-Rearm',multiplier)
 assert match_events(tr.events,r['reports'],5).true_positives==1
 assert not any(e.start_s<660 for e in r['reports'])

@pytest.mark.parametrize('mode',['single','train','range','persistent'])
def test_real_c_no_duplicate_or_spike_only_reports(cfg,mode):
 s=Scheduler(cfg);out=[]
 for t in range(0,1800,5):
  if mode=='single':v=36 if t==60 else 24
  elif mode=='train':v=36 if t in [60,120,180] else 24
  elif mode=='range':v=150 if t>=60 else 24
  else:v=36 if t>=60 else 24
  out.append(s.update(t,dict(temperature=v,humidity=45+.1*math.sin(t))))
 onsets=[d.t for d in out if 'temperature' in d.onsets]
 if mode=='persistent':assert len(onsets)<=1
 else:assert not onsets
 assert out[-1].interval==60
 assert all(5<=d.interval<=60 for d in out)

@pytest.mark.parametrize('fault',['range','missing','spike'])
def test_recovery_and_cross_channel_isolation(cfg,fault):
 s=Scheduler(cfg);out=[]
 for t in range(0,180,5):
  v=(150 if fault=='range' else None) if 20<=t<80 and fault!='spike' else (36 if fault=='spike' and t==20 else 24)
  out.append(s.update(t,dict(temperature=v,humidity=45 if t<90 else 61)))
 assert any(d.active['humidity'] for d in out if d.t>=100)
 assert not any(d.active['temperature'] for d in out)
 if fault!='spike':assert 'temperature' in out[16].recovery_reset

def test_healthy_sustained_event_and_confirmed_episode_no_duplicates(cfg):
 s=Scheduler(cfg);out=[s.update(t,dict(temperature=24 if t<60 else 28,humidity=45+.1*math.sin(t))) for t in range(0,180,5)]
 assert sum('temperature' in d.onsets for d in out)==1
 e=seed_episode(cfg);count=0;was=False
 for t in range(5,180,5):
  event,_,_=e.step(t,36,'DEGRADED' if t%10 else 'HEALTHY',20,t>=10,26,8,.15)
  count+=event and not was;was=event
 assert count==1

def test_confirmation_deadline_stays_bounded(cfg):
 p=deepcopy(cfg);p['v02']['confirmation_samples']=1000;s=Scheduler(p)
 out=[s.update(t,dict(temperature=24 if t<60 else 36,humidity=45+.1*math.sin(t))) for t in range(0,240,5)]
 assert not any(d.confirmation for d in out if d.t>=180)

def test_frozen_v02_failure_and_archive_still_exact(cfg):
 tr=generate(cfg,91,'spike_same_long');r=frozen_run(tr,cfg,'V02')
 assert match_events(tr.events,r['reports'],5).true_positives==0
 archived=json.loads(gzip.decompress((ROOT/'results/v0.2/cases/91-spike_same_long-1.json.gz').read_bytes()))['runs']['V02'][0]
 assert json.loads(canon(r))==archived
 cfg['rearm']={'enabled':False}
 assert canon(run(tr,cfg,'V02-Rearm'))==canon(r)

@pytest.mark.parametrize('case',scenarios())
def test_new_variant_determinism_and_bounds(cfg,case):
 tr=generate(cfg,0,case);a=run(tr,cfg,'V02-Rearm');b=run(tr,cfg,'V02-Rearm')
 assert canon(a)==canon(b)
 assert all(5<=r['interval']<=60 for r in a['records'])

def test_causality_and_unsampled_read_guard(cfg):
 a=generate(cfg,2,'spike_same_long');b=deepcopy(a)
 for r in b.observed[901:]:r.update(temperature=1000,humidity=-1000)
 b.events=[];b.faults=[];b.latent=[];b.noisy=[]
 ra=run(a,cfg,'V02-Rearm');rb=run(b,cfg,'V02-Rearm')
 assert [r for r in ra['records'] if r['timestamp']<=900]==[r for r in rb['records'] if r['timestamp']<=900]
 allowed={r['timestamp'] for r in ra['records']}
 class Hidden(dict):
  def __getitem__(self,k):
   if k!='timestamp' and super().__getitem__('timestamp') not in allowed:raise AssertionError('unsampled read')
   return super().__getitem__(k)
 a.observed=[Hidden(r) for r in a.observed]
 assert canon(run(a,cfg,'V02-Rearm'))==canon(ra)
