"""MA-1 engineering contracts on exposed seed20; no final seed tuning."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from ablation_support import (FACTORS, cases, make_trace, factorial_replay,
                              supplement_metrics, deadline_truth)
from tais.config import load
from tais.transfer_signals import generate, counterfactual
from tais.wire_codec import encode, decode, envelope_from_record
from simulator.events import Event, match_events
from benchmark_su import replay as frozen_replay
from benchmark_joint_optimization import canon

PLAN = json.loads((ROOT/'configs/module-ablation.json').read_text())


@pytest.mark.parametrize('case', ['clean_both', 'range_temperature_same',
                                  'missing_humidity_cross', 'drift_temperature_same'])
def test_factorial_u_preserves_actual_samples_and_every_local_state(case):
    tr = make_trace(PLAN, 20, case)
    cfg = load()
    for no_u, u in [('A0', 'A3'), ('A1', 'A5'), ('A2', 'A6'), ('A4', 'A7')]:
        a = factorial_replay(tr.observed, cfg, no_u)
        b = factorial_replay(tr.observed, cfg, u)
        assert len(a['records']) == len(b['records'])
        for x, y in zip(a['records'], b['records']):
            for field in ('timestamp', 'interval', 'scores', 'active', 'health', 'recovery_reset'):
                assert x[field] == y[field]
            if x['upload']:
                frame = encode(envelope_from_record(y))
                assert encode(decode(frame)) == frame
        for old, new in zip(b['records'], b['records'][1:]):
            if any((old['active'][n], old['health'][n]['state'], old['health'][n]['flags']) !=
                   (new['active'][n], new['health'][n]['state'], new['health'][n]['flags']) for n in cfg['channels']):
                assert new['upload']


@pytest.mark.parametrize('case', ['clean_both', 'stuck_temperature_same',
                                  'missing_temperature_cross', 'invalid_humidity_same'])
def test_a7_is_exact_existing_gateonly_plus_u(case):
    tr = make_trace(PLAN, 20, case)
    new = factorial_replay(tr.observed, load(), 'A7')
    old = frozen_replay(tr, load(), 'GateOnly+U')
    for field in ('reports', 'detections'):
        assert canon(new[field]) == canon(old[field])
    for a, b in zip(new['records'], old['records']):
        for field in ('timestamp', 'interval', 'active', 'scores', 'health', 'upload', 'reasons'):
            assert canon(a[field]) == canon(b[field])
    assert len(new['records']) == len(old['records'])


def test_fixed_budget_and_disabled_trust_semantics():
    tr = make_trace(PLAN, 20, 'range_temperature_same')
    for method in ('A0', 'A1', 'A3', 'A5'):
        rows = factorial_replay(tr.observed, load(), method)['records']
        assert [r['timestamp'] for r in rows] == list(range(0, 1800, 20))
        if not FACTORS[method][0]:
            assert all(h == dict(state='HEALTHY', score=100, flags=0)
                       for r in rows for h in r['health'].values())


def test_no_unsampled_values_or_truth_are_read():
    class Hidden(dict):
        def __getitem__(self, key):
            if key != 'timestamp':
                raise AssertionError('Read an unsampled channel')
            return super().__getitem__(key)
    source = [dict(timestamp=0, temperature=24., humidity=45.), Hidden(timestamp=1),
              dict(timestamp=20, temperature=24., humidity=45.)]
    assert len(factorial_replay(source, load(), 'A0')['records']) == 2
    with pytest.raises(ValueError, match='timestamps'):
        factorial_replay([source[0], source[0]], load(), 'A0')


def test_all_supplements_use_independent_truth_and_valid_schedules():
    assert len(cases(PLAN)) == 54
    for case in PLAN['supplements']:
        tr = make_trace(PLAN, 20, case)
        assert len(tr.observed) == 1800
        assert all(0 <= e.start_s <= e.end_s < 1800 for e in tr.events)
        assert len(tr.events) == len(tr.metadata['event_schedule'])
        cf = counterfactual(tr)
        assert cf.observed == tr.noisy
        if case.startswith('multi_'):
            assert {f.channel for f in tr.faults} == {'temperature', 'humidity'}
    assert len(make_trace(PLAN, 20, 'high_frequency').events) == 12
    assert len(make_trace(PLAN, 20, 'low_frequency').events) == 2


def test_common_deadline_rejects_late_match_and_keeps_misses_in_delay():
    tr = make_trace(PLAN, 20, 'clean_both')
    tr.events = [Event('temperature', 10, 500), Event('humidity', 100, 500)]
    r = factorial_replay(tr.observed, load(), 'A0')
    r['reports'] = [Event('temperature', 20, 20), Event('humidity', 230, 230)]
    frames = [dict(timestamp=x['timestamp'], frame_hex=encode(envelope_from_record(x)).hex())
              for x in r['records'] if x['upload']]
    out, events = supplement_metrics(tr, r, frames, load(), PLAN)
    assert out['sender_tp'] == 1 and out['sender_fn'] == 1 and out['sender_fp'] == 1
    assert out['sender_delay_mean_s'] == 10
    assert out['sender_restricted_delay_sum_s'] == 130
    assert sum(e['matched'] for e in events if e['side'] == 'sender') == 1


def test_finite_value_age_does_not_reset_on_null_frame():
    tr = make_trace(PLAN, 20, 'clean_none')
    for t in range(200, 600):
        tr.observed[t]['temperature'] = None
    r = factorial_replay(tr.observed, load(), 'A0')
    frames = [dict(timestamp=x['timestamp'], frame_hex=encode(envelope_from_record(x)).hex())
              for x in r['records']]
    out, events = supplement_metrics(tr, r, frames, load(), PLAN)
    assert out['finite_value_age_mean_s'] > out['frame_age_mean_s']
    assert out['finite_value_coverage'] == 1
    assert out['sender_recall'] is None and out['sender_delay_mean_s'] is None


def test_factorial_contrasts_and_holm_have_known_answers():
    from analyze_ablation import contrasts, holm
    # y=T+2S+3U+4S*U; only the S:U interaction is nonzero.
    y = np.array([t+2*s+3*u+4*s*u for t, s, u in FACTORS.values()])
    assert contrasts()['T'] @ y == 1
    assert contrasts()['S:U'] @ y == 4
    assert contrasts()['T:S'] @ y == 0
    assert np.allclose(holm([.01, .04, .02]), [.03, .04, .04])
