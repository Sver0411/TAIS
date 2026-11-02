"""Experimental adapters only: unchanged Scheduler, C11, Upload and generators.

Disabled trust is an explicitly neutral health input to the existing Scheduler;
it is not a claim that an unexamined sensor is healthy. Frames retain constant
health fields to hold serialization layout fixed across the factorial design.
"""
from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace
import math

import numpy as np

from tais.config import baseline
from tais.scheduler import Scheduler
from tais.trust import Health
from tais.joint_upload import Upload
from tais.paper_baselines import episodes, decorate
from tais.transfer_signals import generate, scenarios, TransferTrace
from tais.replay import finite
from simulator.events import Event, match_events

FACTORS = {
    'A0': (0, 0, 0), 'A1': (1, 0, 0), 'A2': (0, 1, 0),
    'A3': (0, 0, 1), 'A4': (1, 1, 0), 'A5': (1, 0, 1),
    'A6': (0, 1, 1), 'A7': (1, 1, 1),
}


class NeutralHealth:
    def update(self, t, value):
        return Health(100, 'HEALTHY', 0)

    def close(self):
        pass


def factorial_replay(observed, cfg, method, period=20):
    """Only due observed rows enter Scheduler; no trace/truth access."""
    trust, adaptive, selective = FACTORS[method]
    scheduler = Scheduler(cfg, confirmation=False)
    if not trust:
        for engine in scheduler.trust.values():
            engine.close()
        scheduler.trust = {n: NeutralHealth() for n in cfg['channels']}
    b = baseline(cfg)
    upload = Upload({n: b['adaptive']['channels'][n]['noise_floor']
                     for n in cfg['channels']}, heartbeat=120)
    rows = []
    due = 0
    previous = -1
    try:
        for source in observed:
            t = source['timestamp']
            if not math.isfinite(t) or t <= previous:
                raise ValueError('Source timestamps must increase')
            previous = t
            if t < due:
                continue
            values = {n: source[n] for n in cfg['channels']}
            d = scheduler.update(t, values)
            interval = d.interval if adaptive else period
            reasons = (upload.decide(t, values, d.active, d.health)
                       if selective else ['every_sample'])
            detail = asdict(d)
            detail.pop('t')
            detail.update(timestamp=t, values=values, interval=interval,
                          upload=bool(reasons), reasons=reasons, payload_bytes=0)
            rows.append(detail)
            due = t + interval
    finally:
        for engine in scheduler.trust.values():
            engine.close()
    return episodes(rows, tuple(cfg['channels']))


def cases(plan):
    return scenarios() + plan['supplements']


def make_trace(plan, seed, case):
    """Reuse G2 with declared overrides/composition; no new signal equations."""
    spec = deepcopy(plan['generator'])
    if case in scenarios():
        return generate(spec, seed, case)
    if case.startswith('multi_'):
        kind = case[6:]
        parts = [generate(spec, seed, f'{kind}_{c}_same')
                 for c in ('temperature', 'humidity')]
        arrays = []
        for field in ('latent', 'noisy', 'observed'):
            arrays.append([dict(timestamp=t, **{
                c: getattr(part, field)[t][c]
                for c, part in zip(('temperature', 'humidity'), parts)})
                for t in range(spec['duration_s'])])
        metadata = deepcopy(parts[0].metadata)
        for field in ('event_schedule', 'fault_schedule'):
            metadata[field] = sum((p.metadata[field] for p in parts), [])
        metadata['composition'] = 'two independently generated channel histories'
        return TransferTrace(case, 'both', 'mixed', seed, *arrays,
                             sorted(sum((p.events for p in parts), []),
                                    key=lambda e: (e.start_s, e.channel)),
                             sum((p.faults for p in parts), []), metadata)
    if case == 'low_frequency':
        spec['events']['onset_ranges'] = [[660, 780]]
    elif case == 'high_frequency':
        spec['events']['onset_ranges'] = [[100+260*i, 120+260*i] for i in range(6)]
        spec['events']['duration_ranges'] = {f'bin{i}': [41, 100] for i in range(6)}
        spec['events']['shapes'] *= 2
    elif case == 'slow_change':
        spec['events']['onset_ranges'] = [[300, 360]]
        spec['events']['duration_ranges'] = {'slow': [900, 1000]}
        spec['events']['shapes'] = ['smooth_pulse']
    elif case in ('noisy_none', 'noisy_events'):
        spec['noise']['sigma'] = [x*7 for x in spec['noise']['sigma']]
    else:
        raise ValueError(case)
    tr = generate(spec, seed, 'clean_none' if case == 'noisy_none' else 'clean_both')
    tr.scenario = case
    return tr


def replay(trace, cfg, method, plan):
    if method in FACTORS:
        return factorial_replay(trace.observed, cfg, method, plan['fixed_interval_s'])
    # Reuse exactly the frozen G1 operating point, including independent bounds.
    from benchmark_paper import native
    from pathlib import Path
    import json
    from tais import ROOT
    specs = json.loads((ROOT/'results/tais-paper/operating-points.json').read_text())['schedules']
    spec = next(s for s in specs if s['id'] == method)
    result = native(SimpleNamespace(observed=trace.observed), cfg, spec)
    return result if spec['kind'] == 'TAIS' else decorate(result, cfg)


def deadline_truth(events, deadline, tolerance):
    return [Event(e.channel, e.start_s, min(e.end_s, e.start_s+deadline-tolerance))
            for e in events]


def supplement_metrics(trace, result, frames, cfg, plan, cf=None, cf_frames=None):
    """Common 120s deadline, explicit misses, per-channel finite AoI/coverage."""
    from benchmark_su import receiver_result
    receiver, _ = receiver_result(result, frames)
    cf_receiver = receiver_result(cf, cf_frames)[0] if cf is not None else None
    tol = cfg['evaluation']['event_match_tolerance_s']
    truth = deadline_truth(trace.events, plan['deadline_s'], tol)
    rows = result['records']
    out = {}
    events = []
    tx = np.array([f['timestamp'] for f in frames])
    for side, reports in [('sender', result['reports']), ('receiver', receiver['reports'])]:
        matched = match_events(truth, reports, tol)
        by = {(p.ground_truth.channel, p.ground_truth.start_s): p.detected.start_s
              for p in matched.matches}
        tp, fp, fn = matched.true_positives, matched.false_positives, matched.false_negatives
        latencies = matched.latencies
        prefix = side+'_'
        fault_false = [d for d in matched.unmatched_detections if any(
            f.channel == d.channel and f.start_s <= d.start_s < f.end_s+cfg['evaluation']['fault_recovery_attribution_s']
            for f in trace.faults)]
        clean_reports = (cf['reports'] if side == 'sender' else cf_receiver['reports']) if cf is not None else []
        induced = [d for d in fault_false if not any(
            c.channel == d.channel and abs(c.start_s-d.start_s) <= tol for c in clean_reports)]
        out.update({prefix+'tp': tp, prefix+'fp': fp, prefix+'fn': fn,
                    prefix+'fault_associated_false': len(fault_false),
                    prefix+'fault_induced_false': len(induced) if cf is not None else None,
                    prefix+'precision': tp/(tp+fp) if tp+fp else None,
                    prefix+'recall': tp/len(truth) if truth else None,
                    prefix+'f1': 2*tp/(len(truth)+tp+fp) if len(truth)+tp+fp else None,
                    prefix+'miss_rate': fn/len(truth) if truth else None,
                    prefix+'restricted_delay_sum_s': sum(latencies)+fn*plan['deadline_s']})
        for q, fun in [('mean', np.mean), ('median', np.median), ('p95', lambda x: np.percentile(x, 95))]:
            out[prefix+'delay_'+q+'_s'] = float(fun(latencies)) if latencies else None
        for e in trace.events:
            report = by.get((e.channel, e.start_s))
            overlap = any(f.channel == e.channel and f.start_s <= e.end_s and f.end_s > e.start_s
                          for f in trace.faults)
            finite_times = [r['timestamp'] for r in rows if finite(r['values'][e.channel])]
            received_finite_times = [r['timestamp'] for r in rows
                                     if r['upload'] and finite(r['values'][e.channel])]
            age_index = np.searchsorted(finite_times, e.start_s, side='right')-1
            received_age_index = np.searchsorted(received_finite_times, e.start_s, side='right')-1
            tx_index = np.searchsorted(tx, e.start_s, side='right')-1
            events.append(dict(side=side, channel=e.channel, truth_start=e.start_s,
                               truth_end=e.end_s, matched=report is not None, report_time=report,
                               delay_s=max(0, report-e.start_s) if report is not None else None,
                               restricted_delay_s=max(0, report-e.start_s) if report is not None else plan['deadline_s'],
                               same_fault_overlap=overlap,
                               finite_sample_coverage=any(e.start_s <= t <= e.end_s for t in finite_times),
                               sample_age_at_onset_s=e.start_s-finite_times[age_index] if age_index >= 0 else None,
                               finite_value_age_at_onset_s=e.start_s-received_finite_times[received_age_index] if received_age_index >= 0 else None,
                               frame_age_at_onset_s=e.start_s-tx[tx_index] if tx_index >= 0 else None))
        out[prefix+'same_fault_fn'] = sum(not r['matched'] and r['same_fault_overlap'] for r in events if r['side'] == side)
    grid = np.arange(len(trace.observed))
    age = grid-tx[np.searchsorted(tx, grid, side='right')-1]
    out.update(frame_age_mean_s=float(age.mean()), frame_age_p95_s=float(np.percentile(age, 95)))
    # Time since latest FINITE delivered value, unlike mere frame age. Null does
    # not count as a new measurement; stale age continues, coverage is separate.
    value_ages = []
    for n in cfg['channels']:
        times = np.array([r['timestamp'] for r in rows if r['upload'] and finite(r['values'][n])])
        ix = np.searchsorted(times, grid, side='right')-1
        mask = ix >= 0
        value_ages.extend((grid[mask]-times[ix[mask]]).tolist())
    out['finite_value_coverage'] = len(value_ages)/(len(grid)*len(cfg['channels']))
    out['finite_value_age_mean_s'] = float(np.mean(value_ages)) if value_ages else None
    out['finite_value_age_p95_s'] = float(np.percentile(value_ages, 95)) if value_ages else None
    event_mask = np.array([any(e.start_s <= t <= e.end_s for e in trace.events) for t in grid])
    times = [r['timestamp'] for r in rows]
    event_samples = sum(event_mask[int(t)] for t in times)
    out.update(event_seconds=int(event_mask.sum()), nonevent_seconds=int((~event_mask).sum()),
               event_samples=int(event_samples), nonevent_samples=len(rows)-int(event_samples),
               mean_sampling_interval_s=float(np.mean(np.diff(times))) if len(times) > 1 else None)
    return out, events
