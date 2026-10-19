import json,sys
from pathlib import Path
from copy import deepcopy
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from benchmark_transfer import plan,specs,policy,inherited
from benchmark_paper import native
from benchmark_joint_optimization import canon,metrics as codec_metrics
from transfer_metrics import metrics,diagnostics
from tais.config import load
from tais.transfer_signals import generate,counterfactual
from tais.paper_baselines import decorate
from tais.wire_codec import decode,encode

@pytest.mark.parametrize('spec',specs(),ids=lambda x:x['id'])
def test_frozen_parity_sample_only_and_prefix_causality(spec):
    cfg=load();t=generate(plan(),690,'drift_humidity_cross');r=policy(t,cfg,spec)
    direct=native(t,cfg,spec);direct=direct if spec['kind']=='TAIS' else decorate(direct,cfg)
    assert canon(direct)==canon(r)
    actual={r['timestamp'] for r in r['records']};changed=deepcopy(t)
    for row in changed.observed:
        if row['timestamp'] not in actual:row['temperature']=1e6;row['humidity']=-1e6
    assert canon(policy(changed,cfg,spec))==canon(r)
    cut=deepcopy(t);cut.observed=cut.observed[:731]
    assert canon(policy(cut,cfg,spec)['records'])==canon([x for x in r['records'] if x['timestamp']<731])
    # Everything hidden can be removed/replaced without affecting any decision.
    changed.latent=[];changed.noisy=[];changed.events=[];changed.faults=[];changed.metadata={}
    changed.observed=t.observed
    assert canon(policy(changed,cfg,spec))==canon(r)
    assert cfg['synthetic']['baseline']=={'temperature':24.0,'humidity':45.0}

@pytest.mark.parametrize('case',['clean_none','missing_humidity_same','stable_offset_humidity_cross','range_temperature_same','clean_both'])
def test_generic_metrics_actual_codec_receiver_multiple_events(case):
    cfg=load();t=generate(plan(),691,case);cf=counterfactual(t);s=next(s for s in specs() if s['id']=='JO-SU-40');r=policy(t,cfg,s);cr=policy(cf,cfg,s);_,ff=codec_metrics(cf,cr,cfg,cr)
    m,frames,rx,events,diags,hist=metrics(t,r,cfg,cr,ff)
    assert hist.sum()==len(t.observed)==1800
    assert len(events)==len(t.events) and m['n_events']==len(t.events)
    assert m['binary_v1_bytes']==sum(len(bytes.fromhex(f['frame_hex'])) for f in frames)
    assert all(encode(decode(bytes.fromhex(f['frame_hex']))).hex()==f['frame_hex'] for f in frames)
    if not t.events:assert m['recall'] is None
    if t.faults and t.faults[0].kind=='stable_offset':assert m['fault_type_detected']==0 and all(not d['type_supported'] for d in diags)
    assert m['important_edges']==m['event_edges']+m['health_edges']
    assert len(rx)==m['uploads']

def test_old_freeze_is_unchanged():assert inherited()

def test_wrong_type_never_counts_as_correct_type():
    t=generate(plan(),690,'drift_humidity_same');f=t.faults[0]
    r={'records':[dict(timestamp=f.start_s+1,health={'humidity':{'flags':1}})]}
    d=diagnostics(t,r)[0]
    assert d['any_detected'] and not d['type_detected'] and d['any_delay_s']==1 and d['type_delay_s'] is None
