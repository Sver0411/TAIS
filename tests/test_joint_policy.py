"""Causal/state/wire engineering tests on already used seed20, not new evidence."""
from copy import deepcopy
from dataclasses import asdict
import importlib.util
from pathlib import Path
import pytest
from tais.config import load
from tais.joint_policy import JointSender,JointPolicy,Trend,APP_SUSPECT_DRIFT
from tais.joint_upload import Upload
from tais.joint_sampling import Rechecks
from tais.core_stream import CoreReceiver,CoreSender
from tais.trust import SensorTrust
from tais.wire_codec import encode,decode
from tais.signals import generate

OPT=dict(idle_interval_s=20,trend_slope=.005,heartbeat_s=120)
@pytest.mark.parametrize('variant',['JO-S','JO-HS','JO-Full'])
@pytest.mark.parametrize('case',['clean_none','clean_short','clean_event','drift_none_long','drift_same_long','drift_cross_long','missing_cross_long','range_same_long','spike_same_long'])
def test_real_c11_bits_bounds_and_wire(variant,case):
 cfg=load();s=JointSender(cfg,OPT,variant=variant);rx=CoreReceiver();independent={n:SensorTrust(c['trust']) for n,c in cfg['channels'].items()};sizes=0;records=[]
 try:
  for row in generate(cfg,20,case).observed:
   x=s.push(row)
   if x is None:continue
   r=x['record'];records.append(r);assert 5<=r['interval']<=60
   for n in cfg['channels']:
    raw=asdict(independent[n].update(row['timestamp'],row[n]))
    assert r['joint'][n]['raw_c11']==raw
    assert r['health'][n]['state']==raw['state'] and r['health'][n]['score']==raw['score']
    assert r['health'][n]['flags']&31==raw['flags']
    if raw['state']=='FAULT':assert not r['active'][n]
   if x['frame']:
    y=rx.receive(x['frame']);assert y['envelope']==x['envelope'];assert encode(y['envelope'])==x['frame'];sizes+=len(x['frame'])
   if variant=='JO-Full' and len(records)>1:
    old=records[-2]
    if any((r['active'][n],r['health'][n]['state'],r['health'][n]['flags'])!=(old['active'][n],old['health'][n]['state'],old['health'][n]['flags']) for n in cfg['channels']):assert r['upload']
  assert sizes==s.counts['binary_bytes']
 finally:
  s.close()
  for c in independent.values():c.close()

def test_unobserved_rows_and_future_suffix_do_not_change_prefix():
 a=JointSender(load(),OPT);b=JointSender(load(),OPT)
 class Hidden(dict):
  def __getitem__(self,k):
   if k!='timestamp':raise AssertionError('unsampled read')
   return super().__getitem__(k)
 try:
  assert a.push(dict(timestamp=0,temperature=24.,humidity=45.))==b.push(dict(timestamp=0,temperature=24.,humidity=45.))
  assert a.push(Hidden(timestamp=1)) is None
  assert b.push(Hidden(timestamp=1)) is None
  for t in range(20,400,20):assert a.push(dict(timestamp=t,temperature=24.,humidity=45.))==b.push(dict(timestamp=t,temperature=24.,humidity=45.))
  with pytest.raises(ValueError):a.push(dict(timestamp=300,temperature=1,humidity=2))
 finally:a.close();b.close()

def test_trend_prediction_is_strictly_past_and_memory_bounded():
 a=Trend(.15,.005);b=Trend(.15,.005)
 for t in range(0,180,20):a.update(t,24+t*.03);b.update(t,24+t*.03)
 x=a.update(180,100.);y=b.update(180,29.4)
 assert x[2]==y[2] and x[1] and y[1]
 for t in range(200,2000,20):a.update(t,24.)
 assert len(a.history)<=9 and not a.suspect

def test_finite_rechecks_do_not_create_an_infinite_sentinel():
 r=Rechecks();calls=[r.interval(t,True,5) for t in range(0,120,5)]
 assert sum(x is not None for x in calls)==3
 assert r.interval(120,True,5)==5

def test_full_upload_last_sent_deadband_and_mandatory_health_event_null_edges():
 u=Upload({'temperature':.15});h={'temperature':dict(state='HEALTHY',score=100,flags=0)};v={'temperature':24.};active={'temperature':False}
 assert u.decide(0,v,active,h)==['first']
 assert not u.decide(20,{'temperature':24.1},active,h)
 h['temperature']['score']=99;assert not u.decide(40,v,active,h)
 active['temperature']=True;assert 'event_edge:temperature' in u.decide(45,v,active,h)
 h['temperature']['flags']=32;assert 'health_edge:temperature' in u.decide(50,v,active,h)
 assert 'validity:temperature' in u.decide(55,{'temperature':None},active,h)
 assert u.last['health']['temperature']['score']==99

def test_cross_channel_healthy_event_is_not_masked_by_faulty_temperature():
 s=JointSender(load(),OPT);reports=[]
 try:
  for row in generate(load(),20,'missing_cross_long').observed:
   x=s.push(row)
   if x:reports+=x['reports']
 finally:s.close()
 assert any(r['channel']=='humidity' and 635<=r['start_s']<=814 for r in reports)

def test_single_spike_does_not_immediately_confirm_auxiliary_event():
 p=JointPolicy(load(),OPT)
 try:
  for t in range(0,200,20):p.update(t,{'temperature':24.+t*.03,'humidity':45.})
  d=p.update(200,{'temperature':60.,'humidity':45.})
  assert not d.active['temperature']
 finally:
  for c in p.trust.values():c.close()

@pytest.mark.parametrize('layout,names',[(1,['temperature','humidity']),(2,['temperature']),(3,['humidity'])])
def test_core_cli_joint_csv_all_layouts_has_no_invented_truth(tmp_path,layout,names):
 import subprocess,sys,json,csv
 root=Path(__file__).resolve().parents[1];source=tmp_path/'input.csv';out=tmp_path/'run'
 with source.open('w') as f:
  w=csv.DictWriter(f,fieldnames=['timestamp',*names]);w.writeheader()
  for t in (0,20,40):w.writerow(dict(timestamp=t,**{n:24. if n=='temperature' else 45. for n in names}))
 subprocess.run([sys.executable,str(root/'examples/tais-core/run.py'),'--policy','tais-jo','--layout',str(layout),'--csv',str(source),'--out',str(out),'--pace','0','--ui','quiet'],check=True,capture_output=True)
 summary=__import__('json').loads((out/'summary.json').read_text())
 assert summary['status']=='COMPLETE' and summary['truth_metrics'] is None
 entries=[json.loads(line) for line in (out/'journal.jsonl').read_text().splitlines()]
 tx=[e for e in entries if e['kind']=='tx'];rx=[e for e in entries if e['kind']=='rx']
 assert len(tx)==len(rx) and sum(e['frame_bytes'] for e in tx)==summary['sender']['binary_bytes']
 for e in tx:assert set(decode(bytes.fromhex(e['frame_hex']),expected_layout_id=layout)['health'])==set(names)
