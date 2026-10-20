"""No silent cache reuse; exact business values whenever reconstruction succeeds."""
from copy import deepcopy
import math
import random
import struct
import sys
import zlib
import pytest
from tais import wire_codec as v1
from tais.wire_v2 import Sender, Receiver, WireError, parse, _pack, MIN_FRAME_BYTES, MAX_FRAME_BYTES


def env(t=0, layout=1):
    names=v1.LAYOUTS[layout]
    return dict(timestamp=t,values={n:float(i+24) for i,n in enumerate(names)},
                environment_active={n:False for n in names},
                health={n:dict(state='HEALTHY',score=100,flags=0) for n in names})


def exact(a,b):
    assert type(a)==type(b)
    if isinstance(a,float):assert struct.pack('>d',a)==struct.pack('>d',b)
    elif isinstance(a,dict):
        assert a.keys()==b.keys()
        for k in a:exact(a[k],b[k])
    else:assert a==b


def crc(body):return bytes(body)+struct.pack('>I',zlib.crc32(body))


@pytest.mark.parametrize('period',[1,8,16,32])
@pytest.mark.parametrize('layout',[1,2,3])
def test_lossless_stream_and_intact_v1_snapshots(period,layout):
    s=Sender(period=period,layout_id=layout);r=Receiver({1:layout})
    values=[None,0,-1,-(1<<63),(1<<63)-1,-0.0,5e-324,-5e-324,sys.float_info.max,0.1]
    for i in range(70):
        e=env(i,layout);name=v1.LAYOUTS[layout][0]
        e['values'][name]=values[i%len(values)]
        e['environment_active'][name]=bool(i%2)
        e['health'][name]=dict(state=v1.STATES[i%3],score=i%101,flags=(1<<32)-1 if i%4==0 else i)
        frame=s.encode(e);p=parse(frame)
        assert p.keyframe==(i%period==0)
        if p.keyframe:
            assert frame.endswith(v1.encode(e,layout)+frame[-4:])
        exact(e,r.receive(frame).envelope)


@pytest.mark.parametrize('field,value',[('state','DEGRADED'),('state','FAULT'),('score',99),('score',0),('flags',16),('flags',(1<<32)-1)])
def test_every_changed_health_field_is_sent_even_if_only_score_changes(field,value):
    s=Sender();r=Receiver();e=env();r.receive(s.encode(e))
    e=deepcopy(e);e['timestamp']=1;e['health']['temperature'][field]=value
    f=s.encode(e);p=parse(f)
    assert p.changes['temperature']=={field:value}
    assert p.changes['humidity']=={}
    exact(e,r.receive(f).envelope)


def test_presence_add_remove_and_no_internal_or_mutable_history():
    s=Sender();r=Receiver();e=env();saved=deepcopy(e);f=s.encode(e)
    e['health']['temperature']['score']=0  # Caller mutation must not mutate sender cache.
    exact(saved,r.receive(f).envelope)
    for t,names in enumerate([[],['temperature'],['humidity'],['temperature','humidity']],1):
        e=env(t);e['health']={n:e['health'][n] for n in names}
        exact(e,r.receive(s.encode(e)).envelope)


def stream(period=8,count=40):
    """Construct emitted envelopes and frames for loss/restart tests, without a live link."""
    s=Sender(period=period);es=[env(i) for i in range(count)]
    for i,e in enumerate(es):e['health']['temperature']['score']=100-i
    return es,[s.encode(e) for e in es]


@pytest.mark.parametrize('lost',[(0,),(1,),(1,2,3),(6,7,8,9),(0,1,2,3,4,5,6,7,8)])
def test_single_burst_and_missing_init_fail_closed_until_complete_snapshot(lost):
    es,fs=stream();r=Receiver();waiting=False;recovered=0
    for i,f in enumerate(fs):
        if i in lost:waiting=True;continue
        x=r.receive(f)
        if waiting and not parse(f).keyframe:
            assert x.envelope is None and x.status=='WAIT_KEYFRAME'
        else:
            exact(es[i],x.envelope)
            if waiting:assert x.recovered;recovered+=1;waiting=False
    assert recovered>=1


def test_receiver_restart_does_not_reuse_old_health():
    es,fs=stream();r=Receiver()
    for i in range(3):r.receive(fs[i])
    r.reset()
    for i in range(3,8):assert r.receive(fs[i]).envelope is None
    x=r.receive(fs[8]);assert x.recovered;exact(es[8],x.envelope)


def test_sender_restart_and_late_old_session_cannot_roll_back():
    s=Sender(period=8);r=Receiver();old=s.encode(env());r.receive(old)
    s.restart(2);fresh=s.encode(env(10));assert parse(fresh).sequence==0 and parse(fresh).keyframe
    x=r.receive(fresh);assert x.new_session and x.recovered;exact(env(10),x.envelope)
    assert r.receive(old).status=='STALE_SESSION'
    for bad in [1,2,0,-1,True]:
        with pytest.raises(WireError):s.restart(bad)


def test_new_session_delta_seen_before_key_retires_old_session():
    s=Sender();r=Receiver();old=s.encode(env());r.receive(old)
    s.restart(2);s.encode(env(1));d=s.encode(env(2))
    assert r.receive(d).status=='WAIT_KEYFRAME'
    assert r.receive(old).status=='STALE_SESSION'


def test_duplicate_conflict_stale_and_reordering_do_not_emit_false_complete_values():
    es,fs=stream();r=Receiver();r.receive(fs[0]);assert r.receive(fs[0]).status=='DUPLICATE'
    assert r.receive(fs[2]).status=='WAIT_KEYFRAME'
    assert r.receive(fs[1]).status=='STALE'
    assert r.receive(fs[2]).status=='DUPLICATE'
    assert r.receive(fs[3]).envelope is None
    exact(es[8],r.receive(fs[8]).envelope)
    other=Sender();other_frame=other.encode(env(999))
    r=Receiver();r.receive(fs[0]);assert r.receive(other_frame).status=='CONFLICT'
    assert r.receive(fs[1]).envelope is None
    exact(es[8],r.receive(fs[8]).envelope)


def test_three_interleaved_devices_have_independent_state():
    senders={d:Sender(device_id=d,session_id=d+100,layout_id=(d if d<3 else 1),period=8) for d in (1,2,3)}
    receiver=Receiver({1:1,2:2,3:1})
    for i in range(20):
        for device in (3,1,2):
            e=env(i,2 if device==2 else 1);e['health'][next(iter(e['health']))]['score']=device+i
            frame=senders[device].encode(e)
            if device==2 and i==2:continue
            x=receiver.receive(frame)
            if device==2 and 3<=i<8:assert x.envelope is None
            else:exact(e,x.envelope)


def test_self_contained_empty_or_full_health_delta_can_recover_without_borrowing():
    s=Sender();e=env();e['health']={};s.encode(e);f=s.encode(e)
    p=parse(f);assert p.self_contained and not p.keyframe
    exact(e,Receiver().receive(f).envelope)
    s=Sender();s.encode(env());e=env(1)
    for h in e['health'].values():h.update(state='FAULT',score=0,flags=31)
    f=s.encode(e);assert parse(f).self_contained
    exact(e,Receiver().receive(f).envelope)


def test_bad_emission_never_commits_sender_history_and_sequence_never_wraps():
    s=Sender();bad=env();bad['health']['temperature']['score']=101
    with pytest.raises(WireError):s.encode(bad)
    assert parse(s.encode(env())).sequence==0
    s._seq=(1<<32)-1
    assert parse(s.encode(env())).sequence==(1<<32)-1
    with pytest.raises(WireError):s.encode(env())
    s.restart(2);assert parse(s.encode(env())).sequence==0


def test_maximum_identifiers_and_minimum_frame_sizes():
    s=Sender(device_id=(1<<32)-1,session_id=(1<<64)-1)
    s._seq=(1<<32)-1;e=env((1<<64)-1)
    for n in e['values']:e['values'][n]=-(1<<63);e['health'][n]['flags']=(1<<32)-1
    f=s.encode(e);assert len(f)==MAX_FRAME_BYTES
    exact(e,Receiver({(1<<32)-1:1}).receive(f).envelope)
    s=Sender();e=env();e['health']={};e['values']={n:None for n in e['values']}
    s.encode(e);f=s.encode(e);assert len(f)==MIN_FRAME_BYTES
    exact(e,Receiver().receive(f).envelope)


@pytest.mark.parametrize('key',[True,False])
def test_every_truncation_and_single_bit_corruption_rejected_without_state_poison(key):
    es,fs=stream();frame=fs[0 if key else 1]
    for n in range(len(frame)):
        with pytest.raises(WireError):parse(frame[:n])
    r=Receiver();r.receive(fs[0])
    for i in range(len(frame)):
        for bit in range(8):
            bad=bytearray(frame);bad[i]^=1<<bit
            with pytest.raises(WireError):r.receive(bad)
    exact(es[1],r.receive(fs[1]).envelope)


@pytest.mark.parametrize('offset,value',[(0,0),(2,1),(2,3),(3,99),(4,0x81),(5,0),(6,0)])
def test_structural_rejection_with_valid_checksum(offset,value):
    f=bytearray(Sender().encode(env())[:-4]);f[offset]=value
    with pytest.raises(WireError):parse(crc(f))


@pytest.mark.parametrize('control,payload',[(3,b'\0\0'),(0,b'\0\1'),(0,b'\0\x41\xff'),(0,b'\0\x42\x65'),(0,b'\0\x44\x80\0'),(0,b'\0\x44\xff\xff\xff\xff\x10')])
def test_invalid_delta_fields_rejected_with_valid_crc(control,payload):
    with pytest.raises(WireError):parse(_pack(1,control,1,1,1,payload))


def test_wrong_configuration_and_wire_version_rejected():
    f=Sender().encode(env())
    for r in [Receiver({1:2}),Receiver({2:1})]:
        with pytest.raises(WireError):r.receive(f)
    with pytest.raises(WireError):Receiver().receive(v1.encode(env()))
    with pytest.raises(WireError):v1.decode(f)
    for bad in [0,-1,True,1<<32]:
        with pytest.raises(WireError):Sender(device_id=bad)
    for bad in [0,-1,True,1<<64]:
        with pytest.raises(WireError):Sender(session_id=bad)


def test_float_time_negative_zero_and_deterministic_fuzz_stream():
    rng=random.Random(2026101808);s=Sender();r=Receiver()
    for i in range(500):
        e=env(-0.0 if i%7==0 else i+.125)
        for name in e['values']:
            v=struct.unpack('>d',rng.getrandbits(64).to_bytes(8,'big'))[0]
            e['values'][name]=v if math.isfinite(v) else None
            e['health'][name]=dict(state=rng.choice(v1.STATES),score=rng.randrange(101),flags=rng.getrandbits(32))
        exact(e,r.receive(s.encode(e)).envelope)


@pytest.mark.parametrize('period',[8,16,32])
@pytest.mark.parametrize('profile',['loss0','loss1','loss5','loss10','burst','sender_restart','receiver_restart'])
def test_link_accounting_exactness_and_recovery_censoring(period,profile):
    from tais.wire_link import encode_stream,simulate,discarded,EVENT_COLUMNS
    es=[env(i*10) for i in range(70)];old=[v1.encode(e) for e in es]
    packets=encode_stream(es,period,restart=profile=='sender_restart')
    stats,episodes,events=simulate(es,packets,old,profile,20,'software_fixture',['validated']*len(es))
    assert len(events)==len(es) and all(len(e)==len(EVENT_COLUMNS) for e in events)
    assert stats['v2_bytes']==sum(len(p.wire) for p in packets)
    assert stats['received_unrestored']+stats['dropped']+stats['v2_decoded']==len(es)
    assert stats['permanently_missing_v2']==stats['received_unrestored']+stats['dropped']
    assert stats['dropped']==sum(discarded(profile,20,'software_fixture',i,e['timestamp']) for i,e in enumerate(es))
    if profile in ('loss0','sender_restart'):assert stats['v2_decoded']==len(es)
    for episode in episodes:
        if not episode['censored']:
            assert episode['wait_frames']>0 and episode['wait_s']==episode['wait_frames']*10
    if profile=='receiver_restart':assert stats['receiver_restarts']==1 and stats['received_unrestored']>0
    if profile=='sender_restart':assert stats['sender_restarts']==1


def test_nested_common_link_masks_and_unrecovered_tail_not_zero_latency():
    from tais.wire_link import discarded,encode_stream,simulate
    for i in range(500):
        loss=[discarded(p,20,'case',i,i*10) for p in ('loss1','loss5','loss10')]
        assert loss==sorted(loss)
    es=[env(i) for i in range(8)];packets=encode_stream(es,16)
    stats,episodes,_=simulate(es,packets,[v1.encode(e) for e in es],'burst',20,'tail',['hash']*len(es))
    assert stats['permanently_missing_v2']==3
    assert all(e['censored'] and e['end_s'] is None for e in episodes)
    assert all(e['wait_s']==2 for e in episodes)  # Lower bound, not a completed recovery.


@pytest.mark.parametrize('method',['AdaptiveSense','AdaptiveSense+TrustLog','GateOnly','TAIS'])
def test_real_c_replay_to_v2_preserves_source_records(method):
    from dataclasses import asdict
    import json
    from tais.config import load
    from tais.signals import generate
    from tais.replay import run
    cfg=load();result=run(generate(cfg,20,'spike_same_short'),cfg,method)
    before=json.dumps(result,default=asdict,sort_keys=True,allow_nan=True)
    s=Sender();r=Receiver()
    for record in result['records']:
        if record['upload']:
            e=v1.envelope_from_record(record);exact(e,r.receive(s.encode(e)).envelope)
    assert before==json.dumps(result,default=asdict,sort_keys=True,allow_nan=True)
