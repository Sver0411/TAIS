#!/usr/bin/env python3
"""Read-only MA-1 integrity, pairing and metric consistency checks."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from benchmark_ablation import DEFAULT, sources


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root, archives=False, replay=False):
    lock = json.loads((root/'freeze.json').read_text())
    assert lock['sources'] == sources(), 'Current frozen code/config differs'
    for name, expected in lock['sources'].items():
        assert digest(root/'sources'/name) == expected, name
    manifest = json.loads((root/'test/manifest.json').read_text())
    assert manifest['status'] == 'COMPLETE' and manifest['sources'] == lock['sources']
    assert manifest['freeze_sha256'] == digest(root/'freeze.json')
    for name, expected in manifest['outputs'].items():
        assert digest(root/'test'/name) == expected, name
    analysis = json.loads((root/'test/analysis/analysis_manifest.json').read_text())
    for name, expected in analysis['outputs'].items():
        assert digest(root/'test/analysis'/name) == expected, name
    frame = pd.read_csv(root/'test/metrics.csv')
    events = pd.read_csv(root/'test/events.csv')
    keys = ['seed', 'scenario', 'method']
    assert len(frame) == manifest['runs'] == len(manifest['seeds'])*len(manifest['cases'])*len(manifest['methods'])
    assert not frame.duplicated(keys).any()
    assert frame.groupby(['seed', 'scenario']).observed_sha256.nunique().eq(1).all()
    for a, b in [('A0', 'A1'), ('A0', 'A3'), ('A0', 'A5'), ('A2', 'A6'), ('A4', 'A7')]:
        paired = frame[frame.method == a].merge(frame[frame.method == b], on=['seed', 'scenario'], suffixes=('_a', '_b'))
        assert paired.sample_schedule_sha256_a.eq(paired.sample_schedule_sha256_b).all()
        if (a, b) in [('A0', 'A3'), ('A2', 'A6'), ('A4', 'A7')]:
            for metric in ('sender_tp', 'sender_fp', 'sender_fn', 'receiver_tp', 'receiver_fp'):
                assert paired[metric+'_a'].eq(paired[metric+'_b']).all()
    for side in ('sender', 'receiver'):
        e = events[events.side == side]
        counts = e.groupby(keys).agg(event_count=('matched', 'size'), matched_count=('matched', 'sum'), capped_sum=('restricted_delay_s', 'sum'))
        joined = frame.set_index(keys).join(counts)
        assert joined.event_count.fillna(0).eq(joined.n_events).all()
        assert joined.matched_count.fillna(0).eq(joined[side+'_tp']).all()
        assert np.allclose(joined.capped_sum.fillna(0), joined[side+'_restricted_delay_sum_s'])
        assert (frame[side+'_tp']+frame[side+'_fn']).eq(frame.n_events).all()
    checked = 0
    if archives:
        for name, expected in json.loads((root/'test/archives.json').read_text()).items():
            assert digest(Path(manifest['archive_root'])/name) == expected, name
            checked += 1
    replayed = 0
    if replay:
        from ablation_support import make_trace, replay as run_policy, supplement_metrics
        from tais.config import load
        from tais.transfer_signals import counterfactual
        from benchmark_joint_optimization import metrics as codec_metrics, canon
        from paper_metrics import metrics as score
        import gzip
        plan = json.loads((root/'sources/configs/module-ablation.json').read_text())
        for seed, case, method in [(900, 'clean_both', 'A0'), (910, 'multi_range', 'A7'),
                                   (919, 'drift_humidity_same', 'JO-SU-40')]:
            cfg = load()
            tr = make_trace(plan, seed, case)
            cf = counterfactual(tr)
            cr = run_policy(cf, cfg, method, plan)
            _, ff = codec_metrics(cf, cr, cfg, cr)
            result = run_policy(tr, cfg, method, plan)
            original, frames, _, _, _ = score(tr, result, cfg, cr, ff)
            extras, _ = supplement_metrics(tr, result, frames, cfg, plan, cr, ff)
            row = frame[(frame.seed == seed) & (frame.scenario == case) & (frame.method == method)].iloc[0]
            actual = hashlib.sha256(gzip.compress(canon(dict(result=result, frames=frames)), mtime=0)).hexdigest()
            assert actual == row.result_sha256
            for key, value in extras.items():
                assert pd.isna(row[key]) if value is None else np.isclose(row[key], value), key
            replayed += 1
    print(json.dumps(dict(status='PASS', runs=len(frame), seed_clusters=frame.seed.nunique(),
                          scenarios=frame.scenario.nunique(), events_per_side=int(frame[frame.method == 'A0'].n_events.sum()),
                          raw_archives_checked=checked, deterministic_replays=replayed,
                          frozen_sources_unchanged=True), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT)
    parser.add_argument('--archives', action='store_true')
    parser.add_argument('--replay', action='store_true')
    args = parser.parse_args()
    verify(args.root, args.archives, args.replay)
