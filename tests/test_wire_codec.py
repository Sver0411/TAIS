"""Exact business semantics and strict, stateless binary decoding."""
from copy import deepcopy
from dataclasses import asdict
import json
import math
import random
import struct
import sys
import zlib

import pytest

from tais.config import load
from tais.replay import run
from tais.signals import generate
from tais.wire_codec import (VERSION, LAYOUTS, WireError, encode, decode,
                             envelope_from_record, validate_layout, layout_descriptor)


def envelope(layout_id=1):
    names = LAYOUTS[layout_id]
    return {"timestamp": 0, "values": {n: float(i+24) for i,n in enumerate(names)},
            "environment_active": {n: False for n in names},
            "health": {n: {"score":100,"state":"HEALTHY","flags":0} for n in names}}


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


def exact(original, recovered):
    assert recovered == original
    assert type(recovered["timestamp"]) is type(original["timestamp"])
    for n,v in original["values"].items():
        assert type(recovered["values"][n]) is type(v)
        if type(v) is float:
            assert struct.pack(">d",v) == struct.pack(">d",recovered["values"][n])
    if type(original["timestamp"]) is float:
        assert struct.pack(">d",original["timestamp"]) == struct.pack(">d",recovered["timestamp"])
    assert canonical(original) == canonical(recovered)


def crc(body):
    return bytes(body)+struct.pack(">I",zlib.crc32(body))


@pytest.mark.parametrize("layout",[1,2,3])
@pytest.mark.parametrize("state",["HEALTHY","DEGRADED","FAULT"])
@pytest.mark.parametrize("flags",[0,1,2|4,1|2|4|8|16,(1<<32)-1])
def test_states_flags_and_layouts(layout,state,flags):
    e=envelope(layout)
    for n,h in e["health"].items():h.update(state=state,flags=flags,score=45 if state=="FAULT" else 75)
    for n in e["environment_active"]:e["environment_active"][n]=True
    before=deepcopy(e)
    exact(e,decode(encode(e,layout),layout));assert before==e


@pytest.mark.parametrize("value",[None,0,1,-1,-(1<<63),(1<<63)-1,0.0,-0.0,
                                  sys.float_info.max,-sys.float_info.max,
                                  sys.float_info.min,5e-324,-5e-324,0.1,math.nextafter(1.0,2.0)])
def test_numeric_types_and_exact_float_boundaries(value):
    e=envelope();e["values"]["temperature"]=value
    exact(e,decode(encode(e)))


@pytest.mark.parametrize("time",[0,127,128,1799,(1<<64)-1,0.0,-0.0,0.1,5e-324,sys.float_info.max])
def test_timestamp_full_information(time):
    e=envelope();e["timestamp"]=time
    exact(e,decode(encode(e)))


def test_health_absence_and_partial_health_are_preserved():
    e=envelope()
    for names in [[],["humidity"],["temperature"],["temperature","humidity"]]:
        e["health"]={n:{"score":0,"state":"FAULT","flags":16} for n in names}
        exact(e,decode(encode(e)))


def test_minimum_maximum_sizes_and_layout_cost():
    e=envelope();e["values"]={n:None for n in LAYOUTS[1]};e["health"]={}
    assert len(encode(e))==13
    e["timestamp"]=(1<<64)-1;e["values"]={n:-(1<<63) for n in LAYOUTS[1]}
    e["health"]={n:{"score":100,"state":"FAULT","flags":(1<<32)-1} for n in LAYOUTS[1]}
    assert len(encode(e))==56
    exact(e,decode(encode(e)))
    assert json.loads(layout_descriptor())["channels"]==["temperature","humidity"]
    assert validate_layout(load()["channels"])==LAYOUTS[1]


def test_stateless_frames_can_be_reordered_repeated_or_omitted():
    a=envelope();b=envelope();b["timestamp"]=1;b["health"]["temperature"]["flags"]=8
    for e in [b,a,b,a]:exact(e,decode(encode(e)))


def test_deterministic_generated_ieee_and_uint32_roundtrips():
    rng=random.Random(2026101803)  # Codec test generator, not an algorithm-validation seed.
    for _ in range(500):
        e=envelope();e["timestamp"]=rng.getrandbits(64)
        for n in LAYOUTS[1]:
            v=struct.unpack(">d",rng.getrandbits(64).to_bytes(8,"big"))[0]
            e["values"][n]=v if math.isfinite(v) else None
            e["environment_active"][n]=bool(rng.getrandbits(1))
            e["health"][n]={"score":rng.randrange(101),"state":rng.choice(["HEALTHY","DEGRADED","FAULT"]),"flags":rng.getrandbits(32)}
        exact(e,decode(encode(e)))


def test_every_truncation_and_every_single_bit_corruption_rejected():
    frame=encode(envelope())
    for n in range(len(frame)):
        with pytest.raises(WireError):decode(frame[:n])
    for i in range(len(frame)):
        for bit in range(8):
            bad=bytearray(frame);bad[i]^=1<<bit
            with pytest.raises(WireError):decode(bad)


@pytest.mark.parametrize("offset,value",[(0,0),(2,2),(3,250),(4,2),(6,0x80),(6,3),(7,4),(8,4)])
def test_invalid_structure_even_with_valid_crc(offset,value):
    e=envelope();e["values"]={n:None for n in LAYOUTS[1]};e["health"]={}
    body=bytearray(encode(e)[:-4]);body[offset]=value
    with pytest.raises(WireError):decode(crc(body))


@pytest.mark.parametrize("suffix",[b"\xff\x64\x00",b"\x00\x65\x00",b"\x00\x64",
                                    b"\x00\x64\x80\x00",b"\x00\x64\xff\xff\xff\xff\x10",
                                    b"\x00\x64\x80\x80\x80\x80\x80\x00"])
def test_bad_health_entry_not_hidden_by_checksum(suffix):
    body=b"TW"+bytes([1,1,0,0,0,0,1])+suffix
    with pytest.raises(WireError):decode(crc(body))


@pytest.mark.parametrize("value",[math.nan,math.inf,-math.inf])
def test_nonfinite_requires_null_semantics(value):
    e=envelope();e["values"]["temperature"]=value
    with pytest.raises(WireError):encode(e)
    record={"timestamp":0,"values":e["values"],"active":e["environment_active"],"health":e["health"],"scores":{"temperature":99},"interval":60}
    clean=envelope_from_record(record)
    assert clean["values"]["temperature"] is None
    assert set(clean)=={"timestamp","values","environment_active","health"}
    exact(clean,decode(encode(clean)))
    body=b"TW"+bytes([1,1,0,0,1,0,0])+struct.pack(">d",value)
    with pytest.raises(WireError):decode(crc(body))


def test_noncanonical_timestamp_and_trailing_data_rejected():
    body=b"TW"+bytes([1,1,0,0x80,0,0,0,0])
    with pytest.raises(WireError):decode(crc(body))
    frame=encode(envelope())
    with pytest.raises(WireError):decode(crc(frame[:-4]+b"\x00"))


@pytest.mark.parametrize("field,value",[("timestamp",True),("timestamp",-1),("timestamp",1<<64),
                                        ("timestamp",float("nan")),("timestamp",-1.0),
                                        ("measurement",True),("measurement",1<<63),
                                        ("measurement",-(1<<63)-1),("measurement","24")])
def test_bad_numeric_inputs_are_rejected(field,value):
    e=envelope()
    if field=="timestamp":e[field]=value
    else:e["values"]["temperature"]=value
    with pytest.raises(WireError):encode(e)


@pytest.mark.parametrize("key,value",[("score",True),("score",101),("score",-1),("score",1.0),
                                     ("flags",-1),("flags",1<<32),("flags",1.0),("state","UNKNOWN")])
def test_bad_health_inputs_are_rejected(key,value):
    e=envelope();e["health"]["temperature"][key]=value
    with pytest.raises(WireError):encode(e)


def test_mapping_and_business_field_contracts():
    for channels in [("humidity","temperature"),("temperature","pressure"),("temperature",)]:
        with pytest.raises(WireError):validate_layout(channels)
    with pytest.raises(TypeError):LAYOUTS[1]=("humidity","temperature")
    with pytest.raises(WireError):decode(encode(envelope(2),2))
    for e in [dict(envelope(),debug="not sent"), {k:v for k,v in envelope().items() if k!="health"}]:
        with pytest.raises(WireError):encode(e)
    e=envelope();e["environment_active"]["temperature"]=1
    with pytest.raises(WireError):encode(e)
    e=envelope();e["health"]["temperature"]["extra"]=0
    with pytest.raises(WireError):encode(e)
    with pytest.raises(WireError):decode("not bytes")
    with pytest.raises(WireError):decode(memoryview(bytes(100)).cast("I"))
    exact(envelope(),decode(memoryview(encode(envelope()))))


@pytest.mark.parametrize("method",["AdaptiveSense","AdaptiveSense+TrustLog","GateOnly","TAIS"])
@pytest.mark.parametrize("case",["clean_event","spike_same_short","missing_same_long"])
def test_real_c_replay_envelopes_keep_original_json_cost_and_every_field(method,case):
    result=run(generate(load(),20,case),load(),method)
    before=json.dumps(result,default=asdict,sort_keys=True,allow_nan=True)
    for record in result["records"]:
        if record["upload"]:
            e=envelope_from_record(record)
            assert len(canonical(e))==record["payload_bytes"]
            exact(e,decode(encode(e)))
    assert json.dumps(result,default=asdict,sort_keys=True,allow_nan=True)==before


def benchmark_module():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('wire_benchmark', Path(__file__).resolve().parents[1]/'scripts/benchmark_wire_codec.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit_fixture():
    from simulator.events import Event
    records=[]
    for t,active,upload in [(0,False,True),(1,True,True),(2,True,False),(3,False,True)]:
        e=envelope();e['timestamp']=t;e['environment_active']['temperature']=active
        r={'timestamp':t,'values':e['values'],'active':e['environment_active'],
           'health':e['health'],'upload':upload,'payload_bytes':len(canonical(e)) if upload else 0}
        records.append(r)
    result={'records':records,'reports':[asdict(Event('temperature',1,1))],
            'detections':[asdict(Event('temperature',1,2))]}
    truth={'events':[asdict(Event('temperature',1,2,'sustained_change'))]}
    original=dict(n_events=1,tp=1,missed=0,local_tp=1,false_reports=0,redundant_reports=0,
                  latency_sum_s=0,latency_n=1,samples=4,uploads=3,
                  payload_bytes=sum(r['payload_bytes'] for r in records))
    return result,truth,original


def test_archival_audit_preserves_sender_and_never_counts_nonuploads():
    bench=benchmark_module();result,truth,original=audit_fixture();before=deepcopy(result)
    measured,hist=bench.audit_result(result,truth,original,5)
    assert result==before
    assert measured['reports']==1 and measured['detections']==1
    assert measured['roundtrip_verified']==3
    assert measured['original_envelopes_sha256']==measured['decoded_envelopes_sha256']
    assert sum(hist['Binary'].values())==3
    assert sum(size*count for size,count in hist['JSON'].items())==original['payload_bytes']


@pytest.mark.parametrize('corruption',['frame_bytes','nonupload_bytes','reports','detections','metric'])
def test_archival_audit_fails_on_historical_inconsistency(corruption):
    bench=benchmark_module();result,truth,original=audit_fixture()
    if corruption=='frame_bytes':result['records'][0]['payload_bytes']+=1
    elif corruption=='nonupload_bytes':result['records'][2]['payload_bytes']=1
    elif corruption=='reports':result['reports']=[]
    elif corruption=='detections':result['detections']=[]
    else:original['tp']=0
    with pytest.raises(AssertionError):bench.audit_result(result,truth,original,5)


def test_frame_distribution_statistics_and_strict_numeric_identity():
    from collections import Counter
    bench=benchmark_module()
    assert bench.stats(Counter({10:2,20:2}))==dict(bytes=60,mean_bytes=15,median_bytes=15,p95_bytes=20,min_bytes=10,max_bytes=20)
    assert bench.stats(Counter({10:3,20:2}))['median_bytes']==10
    assert not bench.exact(0,0.0)
    assert not bench.exact(0.0,-0.0)
    assert bench.exact({'x':[-0.0,None,1]}, {'x':[-0.0,None,1]})
