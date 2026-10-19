"""Integration checks on old software seed20; no new research validation data."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tais.config import load
from tais.core_stream import CoreSender, CoreReceiver, LocalLink, render
from tais.signals import generate, scenarios
from tais.wire_codec import encode, decode, WireError
from tais.replay import run as frozen_run

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('core_example', ROOT/'examples/tais-core/run.py')
example = importlib.util.module_from_spec(spec);spec.loader.exec_module(example)


@pytest.mark.parametrize('scenario', scenarios())
def test_all45_scenarios_match_frozen_gateonly_and_actual_wire(scenario):
    cfg = load();trace = generate(cfg,20,scenario);sender = CoreSender(cfg)
    receiver = CoreReceiver();entries=[];link = LocalLink(receiver,entries.append)
    records=[];reports=[];frames=[]
    for row in trace.observed:
        result=sender.push(row)
        if result is None:continue
        records.append(result['record']);reports.extend(result['reports'])
        if result['frame'] is not None:
            frames.append(result['frame']);link.send(result['frame'])
            assert encode(receiver.latest)==result['frame']
    sender.close();link.flush();expected=frozen_run(trace,cfg,'GateOnly')
    assert example.canonical(records)==example.canonical(expected['records'])
    assert example.canonical(reports)==example.canonical([vars(e) for e in expected['reports']])
    assert sender.counts['binary_bytes']==sum(map(len,frames))==link.counts['sent_bytes']
    assert receiver.counts['updates']==sender.counts['uploads']
    assert all(5<=r['interval']<=60 and not r['confirmation'] for r in records)


@pytest.mark.parametrize('layout', [1,2,3])
def test_actual_receiver_independent_loss_corruption_reorder_duplicate_restart(layout):
    from tais.wire_codec import LAYOUTS
    names=LAYOUTS[layout]
    def envelope(t):
        return dict(timestamp=t,values={n:(-0.0 if i==0 else None) for i,n in enumerate(names)},
                    environment_active={n:bool(t%2) for n in names},
                    health={n:dict(state=['HEALTHY','DEGRADED','FAULT'][t%3],score=100-t,flags=t) for n in names})
    frames=[encode(envelope(t),layout) for t in range(1,5)]
    rx=CoreReceiver(layout)
    assert rx.receive(frames[0])['status']=='updated'
    # Frame 2 is independently lost; frame 3 still restores full health.
    assert rx.receive(frames[2])['envelope']==envelope(3)
    assert rx.receive(frames[1])['status']=='out_of_order' and rx.latest==envelope(3)
    assert rx.receive(frames[2])['status']=='duplicate'
    invalid=bytes([frames[3][0]^1])+frames[3][1:]
    assert rx.receive(invalid)['status']=='invalid' and rx.latest==envelope(3)
    assert rx.receive(frames[3])['status']=='updated'
    assert CoreReceiver(layout).receive(frames[3])['envelope']==envelope(4)
    conflict=envelope(4);conflict['health'][names[0]]['score']=0
    assert rx.receive(encode(conflict,layout))['status']=='conflict'
    assert rx.latest==envelope(4)
    wrong=CoreReceiver(2 if layout==1 else 1)
    assert wrong.receive(frames[0])['status']=='invalid'


def test_due_gate_does_not_access_unsampled_values_or_future_truth():
    cfg=load();sender=CoreSender(cfg)
    sender.push(dict(timestamp=0,temperature=24.,humidity=45.))
    class Hidden(dict):
        def __getitem__(self,k):
            if k!='timestamp':raise AssertionError('Unsampled value accessed')
            return super().__getitem__(k)
    assert sender.push(Hidden(timestamp=1)) is None
    with pytest.raises(ValueError):sender.push(dict(timestamp=1,temperature=24.,humidity=45.))
    with pytest.raises(ValueError):sender.push(dict(timestamp=float('nan')))
    sender.close()


def test_link_faults_are_not_sender_feedback_and_receiver_never_fills_gaps():
    trace=generate(load(),20,'missing_cross_long');a=CoreSender(load());b=CoreSender(load())
    rx=CoreReceiver();events=[];link=LocalLink(rx,events.append,3,4,True)
    for row in trace.observed:
        x,y=a.push(row),b.push(row)
        assert example.canonical(x['record'] if x else None)==example.canonical(y['record'] if y else None)
        if y and y['frame'] is not None:link.send(y['frame'])
    link.flush();a.close();b.close()
    assert a.counts==b.counts and link.counts['dropped']>0 and rx.counts['corrupt']>0
    assert rx.counts['out_of_order']>0 and rx.counts['decoded']<b.counts['uploads']
    assert 'age=' in render(b,rx,'synthetic') and len(rx.timeline)<=12


@pytest.mark.parametrize('mode',['csv','stdin'])
def test_user_inputs_complete_pipeline_without_invented_truth(tmp_path,mode):
    out=tmp_path/'run';args=[sys.executable,str(ROOT/'examples/tais-core/run.py'),
                           '--out',str(out),'--ui','quiet','--pace','0']
    if mode=='csv':
        source=tmp_path/'input.csv';source.write_text('timestamp,temperature,humidity\n0,24,45\n20,,46\n40,25,47\n')
        args+=['--csv',str(source)];data=None
    else:
        args+=['--stdin'];data=''.join(json.dumps(dict(timestamp=t,temperature=24.,humidity=45.))+'\n' for t in [0,20,40])
    result=subprocess.run(args,input=data,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    summary=json.loads((out/'summary.json').read_text())
    assert summary['status']=='COMPLETE' and summary['truth_metrics'] is None
    assert summary['sender']['uploads']==summary['receiver']['updates']>0
    assert subprocess.run(args,input=data,text=True,capture_output=True).returncode!=0


def test_invalid_input_retains_failed_partial_run(tmp_path):
    out=tmp_path/'bad';source=tmp_path/'bad.csv'
    source.write_text('timestamp,temperature,humidity\n0,24,45\n0,25,45\n')
    r=subprocess.run([sys.executable,str(ROOT/'examples/tais-core/run.py'),'--csv',str(source),
                      '--out',str(out),'--ui','quiet','--pace','0'],capture_output=True,text=True)
    s=json.loads((out/'summary.json').read_text())
    assert r.returncode==1 and s['status']=='FAILED' and s['sender']['samples']==1
    assert s['truth_metrics'] is None and 'strictly increase' in s['error']


def test_environment_recovery_timeline_is_from_received_frames_only():
    rx=CoreReceiver()
    def f(t,state,flags,active):
        return encode(dict(timestamp=t,values=dict(temperature=24.,humidity=None),
                           health=dict(temperature=dict(state=state,score=100 if not flags else 45,flags=flags)),
                           environment_active=dict(temperature=active,humidity=False)))
    rx.receive(f(0,'HEALTHY',0,False));rx.receive(f(10,'FAULT',16,False))
    rx.receive(f(20,'HEALTHY',0,True))
    assert rx.timeline[-1]['recovery'] and rx.timeline[-1]['event_active']


def test_standalone_receiver_only_consumes_actual_bytes(tmp_path):
    cfg=load();sender=CoreSender(cfg)
    step=sender.push(dict(timestamp=0,temperature=-0.0,humidity=None));sender.close()
    frame=step['frame'];bad=bytes([frame[0]^1])+frame[1:]
    data=bad.hex()+'\n'+frame.hex()+'\n'+frame.hex()+'\nnot hex\n'
    out=tmp_path/'receiver'
    result=subprocess.run([sys.executable,str(ROOT/'examples/tais-core/receiver.py'),'--out',str(out)],
                          input=data,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    summary=json.loads((out/'summary.json').read_text())
    assert summary['receiver']['corrupt']==1 and summary['receiver']['updates']==1
    assert summary['receiver']['duplicate']==1 and summary['invalid_text_lines']==1
    assert encode(summary['latest'])==frame
