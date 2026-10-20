"""Engineering invariants on used seed20, never final-data selection."""
from copy import deepcopy
from pathlib import Path
import importlib.util,json,subprocess,sys
import pytest
from tais.config import load
from tais.core_stream import CoreSender,CoreReceiver,LocalLink
from tais.joint_policy import JointSender
from tais.su_policy import SUSender
from tais.signals import generate,scenarios
from tais.wire_codec import encode

OPT=dict(idle_interval_s=20,trend_slope=.005,heartbeat_s=120)

def local_record(r):
    return {k:v for k,v in r.items() if k not in ['upload','reasons','payload_bytes','su']}

def canonical(x):
    if isinstance(x,float) and x!=x:return None
    if isinstance(x,dict):return {k:canonical(v) for k,v in x.items()}
    if isinstance(x,list):return [canonical(v) for v in x]
    return x

@pytest.mark.parametrize('case',scenarios())
@pytest.mark.parametrize('sampling',['jo-s','gateonly'])
def test_upload_cannot_change_any_local_candidate_sample_or_c11(case,sampling):
    cfg=load();a=JointSender(cfg,OPT,variant='JO-S') if sampling=='jo-s' else CoreSender(cfg)
    b=SUSender(cfg,sampling=sampling);rx=CoreReceiver();pairs=0;previous=None;changed=0
    if sampling=='jo-s':
        assert b.scheduler.base.health_layer is False
        assert b.scheduler.base.upload_layer is False
    try:
        for row in generate(cfg,20,case).observed:
            x,y=a.push(row),b.push(row)
            assert (x is None)==(y is None)
            if x is None:continue
            assert canonical(local_record(x['record']))==canonical(local_record(y['record']))
            assert canonical(y['record']['su']['original_upload'])==canonical(dict(upload=x['record']['upload'],reasons=x['record']['reasons']))
            raw_a=a.scheduler.base if sampling=='jo-s' else a.scheduler
            assert y['record']['su']['candidate_starts']=={n:z._potential_start for n,z in raw_a.analyzers.items()}
            assert all(h['flags']&~31==0 for h in y['record']['health'].values())
            changed+=x['record']['upload']!=y['record']['upload'];pairs+=1
            r=y['record']
            if previous and any((r['active'][n],r['health'][n]['state'],r['health'][n]['flags'])!=(previous['active'][n],previous['health'][n]['state'],previous['health'][n]['flags']) for n in cfg['channels']):assert y['frame'] is not None
            if y['frame']:
                e=rx.receive(y['frame']);assert encode(e['envelope'])==y['frame'] and e['envelope']==y['envelope']
            previous=r
        assert pairs>0 and changed>0
    finally:a.close();b.close()

@pytest.mark.parametrize('cap',[20,30,40])
def test_candidate_caps_are_exact_frozen_jo_s_sampling(cap):
    a=JointSender(load(),dict(OPT,idle_interval_s=cap),variant='JO-S');b=SUSender(load(),cap=cap)
    try:
        for row in generate(load(),20,'drift_same_long').observed:
            x,y=a.push(row),b.push(row)
            assert (x is None)==(y is None)
            if x:assert canonical(local_record(x['record']))==canonical(local_record(y['record']))
    finally:a.close();b.close()

def test_no_unsampled_or_future_read_and_no_link_feedback():
    a=SUSender(load());b=SUSender(load());rx=CoreReceiver();events=[];link=LocalLink(rx,events.append,3,4,True)
    class Hidden(dict):
        def __getitem__(self,k):
            if k!='timestamp':raise AssertionError('Unsampled read')
            return super().__getitem__(k)
    try:
        first=dict(timestamp=0,temperature=24.,humidity=45.)
        assert a.push(first)['record']==b.push(first)['record']
        assert a.push(Hidden(timestamp=1)) is None
        assert b.push(Hidden(timestamp=1)) is None
        for row in generate(load(),20,'missing_cross_long').observed[2:]:
            x,y=a.push(row),b.push(row)
            assert canonical(x['record'] if x else None)==canonical(y['record'] if y else None)
            if y and y['frame']:link.send(y['frame'])
        link.flush();assert rx.counts['decoded']<b.counts['uploads']
    finally:a.close();b.close()

@pytest.mark.parametrize('policy',['tais-su','gateonly-u'])
@pytest.mark.parametrize('layout,names',[(1,['temperature','humidity']),(2,['temperature']),(3,['humidity'])])
def test_new_core_policies_really_encode_decode_user_csv_without_truth(tmp_path,policy,layout,names):
    import csv
    root=Path(__file__).resolve().parents[1];source=tmp_path/'input.csv';out=tmp_path/'run'
    with source.open('w') as f:
        w=csv.DictWriter(f,fieldnames=['timestamp',*names]);w.writeheader()
        for t in (0,20,40,60,120,180):w.writerow(dict(timestamp=t,**{n:(24. if n=='temperature' else 45.) for n in names}))
    subprocess.run([sys.executable,str(root/'examples/tais-core/run.py'),'--policy',policy,'--layout',str(layout),'--csv',str(source),'--out',str(out),'--ui','quiet','--pace','0'],check=True,capture_output=True)
    summary=json.loads((out/'summary.json').read_text());assert summary['status']=='COMPLETE' and summary['truth_metrics'] is None
    entries=[json.loads(line) for line in (out/'journal.jsonl').read_text().splitlines()];tx=[x for x in entries if x['kind']=='tx'];rx=[x for x in entries if x['kind']=='rx'];assert len(tx)==len(rx)
    assert sum(x['frame_bytes'] for x in tx)==summary['sender']['binary_bytes']
    assert all(not h['flags']&32 for x in rx for h in x['envelope']['health'].values())

@pytest.mark.parametrize('send_clear',[False,True])
def test_receiver_only_counts_edges_actually_present_on_wire(send_clear):
    from tais.wire_codec import encode
    root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'scripts'))
    from benchmark_su import receiver_result
    def frame(t,active):
        e=dict(timestamp=t,values=dict(temperature=24.,humidity=45.),environment_active=dict(temperature=active,humidity=False),health={n:dict(state='HEALTHY',score=100,flags=0) for n in ['temperature','humidity']})
        return dict(timestamp=t,frame_hex=encode(e).hex())
    frames=[frame(0,False),frame(10,True)]+([frame(20,False)] if send_clear else [])+[frame(30,True),frame(40,False)]
    # Hidden local episode boundaries/reports must not create receiver knowledge.
    r,log=receiver_result(dict(records=[],reports=['hidden episode at30'],detections=[]),frames)
    assert [e.start_s for e in r['reports']]==([10,30] if send_clear else [10])
    assert len(log)==len(frames)
