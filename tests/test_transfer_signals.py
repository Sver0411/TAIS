"""G2 fixture checks separating reproducible process streams, injection and truth support."""
import json,math
from copy import deepcopy
from pathlib import Path
import pytest
from tais.transfer_signals import generate,scenarios,counterfactual,CHANNELS
ROOT=Path(__file__).resolve().parents[1]
SPEC=json.loads((ROOT/'configs/tais-transfer.json').read_text())

def test_matrix_and_independent_reproducible_streams():
    assert len(scenarios())==46
    a=generate(SPEC,690,'drift_temperature_same');b=generate(SPEC,690,'missing_temperature_same')
    assert a.latent==b.latent and a.noisy==b.noisy and a.events==b.events
    assert a.noisy==generate(SPEC,690,'drift_temperature_same').noisy
    assert a.noisy!=generate(SPEC,691,'drift_temperature_same').noisy
    # Changing ONLY the fault process cannot alter event placement or noise.
    changed=deepcopy(SPEC);changed['faults']['onset_s']=[40,50]
    c=generate(changed,690,'drift_temperature_same')
    assert c.noisy==a.noisy and c.events==a.events and c.faults!=a.faults
    assert generate(SPEC,690,'range_humidity_cross').noisy==a.noisy

@pytest.mark.parametrize('case',scenarios())
def test_grid_truth_injections_and_counterfactual(case):
    t=generate(SPEC,690,case);cf=counterfactual(t)
    assert [r['timestamp'] for r in t.observed]==list(range(1800))
    assert cf.observed==t.noisy and cf.latent==t.latent and cf.events==t.events and cf.faults==[]
    assert cf.observed is not t.noisy
    for series in [t.latent,t.noisy]:assert all(math.isfinite(r[c]) for r in series for c in CHANNELS)
    for e,s in zip(t.events,sorted(t.metadata['event_schedule'],key=lambda s:(s['start_s'],s['channel']))):
        assert (e.start_s,e.end_s)==(s['start_s'],s['end_exclusive_s']-1)
        assert s['physical_duration_s']==e.end_s-e.start_s+1
        assert SPEC['events']['duration_ranges'][s['duration_bin']][0]<=s['physical_duration_s']<=SPEC['events']['duration_ranges'][s['duration_bin']][1]
    for c in CHANNELS:
        for r,o in zip(t.noisy,t.observed):
            inside=any(f.channel==c and f.start_s<=r['timestamp']<f.end_s for f in t.faults)
            if not inside:assert o[c]==r[c]
    for f,s in zip(t.faults,t.metadata['fault_schedule']):
        values=[t.observed[i][f.channel] for i in range(int(f.start_s),int(f.end_s))]
        assert 0<=f.start_s<f.end_s<=1800
        if f.kind=='missing':assert all(v is None for v in values)
        elif f.kind=='invalid':assert all(math.isnan(v) for v in values)
        elif f.kind=='stuck':assert all(v==t.noisy[int(f.start_s)][f.channel] for v in values)
        elif f.kind=='range':assert all(v==s['value'] for v in values) and (s['value']<(-40 if f.channel=='temperature' else 0) or s['value']>(85 if f.channel=='temperature' else 100))
        else:assert any(t.observed[i][f.channel]!=t.noisy[i][f.channel] for i in range(int(f.start_s),int(f.end_s)))

def test_multiple_events_and_both_channel_controls():
    t=generate(SPEC,691,'clean_both');assert len(t.events)==6
    assert {e.channel for e in t.events}==set(CHANNELS)
    assert not generate(SPEC,691,'clean_none').events
