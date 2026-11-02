#!/usr/bin/env python3
"""Phase4.1: read-only MA-1 per-event forensics; never parameter selection."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from tais.config import load
from tais.scheduler import Scheduler
from ablation_support import FACTORS, NeutralHealth
from benchmark_joint_optimization import canon

MA = ROOT/'results/module-ablation/test'
FOCUS = ['high_frequency', 'low_frequency', 'slow_change', 'noisy_none',
         'noisy_events', 'multi_range', 'multi_stuck', 'multi_drift']


def annotated(rows, cfg, method):
    """Recover actual hidden debounce for factor groups on EXACT saved samples."""
    if method not in FACTORS:
        return [dict(r, candidate={n: r.get('su', {}).get('candidate_starts', {}).get(n)
                                  for n in cfg['channels']},
                     raw_candidate={n: r['active'][n] for n in cfg['channels']},
                     candidate_evidence='recorded state; unrecorded debounce unknown') for r in rows]
    base = Scheduler(cfg, confirmation=False)
    if not FACTORS[method][0]:
        for engine in base.trust.values():
            engine.close()
        base.trust = {n: NeutralHealth() for n in cfg['channels']}
    out = []
    try:
        for r in rows:
            d = base.update(r['timestamp'], r['values'])
            assert d.active == r['active'] and d.health == r['health']
            out.append(dict(r, candidate={n: a._potential_start for n, a in base.analyzers.items()},
                            raw_candidate={n: a.event_active and r['values'][n] is not None and
                                           r['health'][n]['state'] != 'FAULT'
                                           for n, a in base.analyzers.items()},
                            candidate_evidence='exact frozen Scheduler replay on saved samples'))
    finally:
        for engine in base.trust.values():
            engine.close()
    return out


def event_rows(records, truth_rows, cfg):
    times = np.array([r['timestamp'] for r in records])
    out = []
    for e in truth_rows:
        c = e['channel'];a = e['truth_start'];b = e['truth_end']
        deadline = min(b+5, a+120)
        during = [r for r in records if a <= r['timestamp'] <= b]
        window = [r for r in records if a-5 <= r['timestamp'] <= deadline]
        finite = [r for r in window if r['values'][c] is not None and np.isfinite(r['values'][c])]
        before = times[times < a];after = times[times >= a]
        cand = [r['candidate'][c] for r in window if r['candidate'][c] is not None]
        raw = [r for r in window if r['raw_candidate'][c]]
        suppressed = [r for r in raw if not r['active'][c] and r['health'][c]['state'] != 'HEALTHY']
        health = [r for r in window if r['health'][c]['state'] != 'HEALTHY' or c in r.get('recovery_reset', [])]
        if e['matched']:
            category, reason = 'detected', 'deadline_sender_match'
        elif suppressed:
            category, reason = 'C_gate', 'confirmed_sampled_candidate_suppressed'
        elif not finite:
            category, reason = 'A_opportunity', 'no_finite_sample_in_evaluation_window'
        elif len(finite) < 2:
            category, reason = 'A_opportunity', 'fewer_than_two_finite_observations'
        elif health:
            category, reason = 'C_exposure', 'health_or_rewarm_exposure; causality_not_identified'
        elif any(r['active'][c] for r in window):
            category, reason = 'D_reporting', 'active_without_new_matched_report; onset_or_assignment'
        else:
            category, reason = 'B_detector', 'finite_coverage_but_no_confirmed_report'
        gaps = np.diff([r['timestamp'] for r in during])
        out.append(dict(**e, last_sample_before_s=float(before[-1]) if len(before) else None,
                        first_sample_after_s=float(after[0]) if len(after) else None,
                        first_observation_delay_s=float(after[0]-a) if len(after) else None,
                        pre_event_coverage_20s=bool(len(before) and a-before[-1] <= 20),
                        samples_during=len(during), finite_samples_in_window=len(finite),
                        interval_min_s=float(gaps.min()) if len(gaps) else None,
                        interval_median_s=float(np.median(gaps)) if len(gaps) else None,
                        interval_max_s=float(gaps.max()) if len(gaps) else None,
                        interval_distribution=json.dumps([float(x) for x in gaps]),
                        candidate_start_s=min(cand) if cand else None,
                        first_confirmed_candidate_s=raw[0]['timestamp'] if raw else None,
                        first_gate_suppression_s=suppressed[0]['timestamp'] if suppressed else None,
                        health_exposure_samples=len(health), recovery_resets=sum(c in r.get('recovery_reset', []) for r in window),
                        health_states='|'.join(sorted({r['health'][c]['state'] for r in window})),
                        miss_category=category, suppression_reason=reason,
                        candidate_evidence=records[0]['candidate_evidence']))
    return out


def worker(seed, archive):
    cfg = load()
    ev = pd.read_csv(MA/'events.csv')
    ev = ev[(ev.seed == seed) & (ev.side == 'sender')]
    rx = pd.read_csv(MA/'events.csv')
    rx = rx[(rx.seed == seed) & (rx.side == 'receiver')].set_index(['scenario','method','channel','truth_start'])
    out, timeline = [], []
    for (case, method), g in ev.groupby(['scenario','method']):
        p = archive/str(seed)/case/(method+'.json.gz')
        saved = json.loads(gzip.decompress(p.read_bytes()))
        rows = annotated(saved['result']['records'], cfg, method)
        truth = []
        for e in g.to_dict('records'):
            e['receiver_matched'] = bool(rx.loc[(case,method,e['channel'],e['truth_start']), 'matched'])
            truth.append(e)
        out += event_rows(rows, truth, cfg)
        if seed == 900 and case in FOCUS and method in ['A0','A5','A7']:
            for r in rows:
                for c in cfg['channels']:
                    timeline.append(dict(seed=seed,scenario=case,method=method,channel=c,
                                         timestamp=r['timestamp'],value=r['values'][c],interval_s=r['interval'],
                                         active=r['active'][c],candidate_start_s=r['candidate'][c],
                                         health_state=r['health'][c]['state'],flags=r['health'][c]['flags'],
                                         upload=r['upload']))
    # No-event/noisy_none contributes zero event rows but still needs timelines.
    if seed == 900:
        case = 'noisy_none'
        for method in ['A0','A5','A7']:
            saved=json.loads(gzip.decompress((archive/str(seed)/case/(method+'.json.gz')).read_bytes()))
            for r in saved['result']['records']:
                for c in cfg['channels']:
                    timeline.append(dict(seed=seed,scenario=case,method=method,channel=c,timestamp=r['timestamp'],
                                         value=r['values'][c],interval_s=r['interval'],active=r['active'][c],
                                         candidate_start_s=None,health_state=r['health'][c]['state'],
                                         flags=r['health'][c]['flags'],upload=r['upload']))
    return out, timeline


def main(out, workers):
    manifest=json.loads((MA/'manifest.json').read_text())
    for name, expected in manifest['outputs'].items():
        assert hashlib.sha256((MA/name).read_bytes()).hexdigest()==expected
    out.mkdir(parents=True,exist_ok=False)
    (out/'manifest.json').write_text(json.dumps(dict(status='STARTED',purpose='historical diagnosis only; no parameter selection',
        source_manifest_sha256=hashlib.sha256((MA/'manifest.json').read_bytes()).hexdigest(),seeds=manifest['seeds']),indent=2)+'\n')
    rows=[];timeline=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for seed,(r,t) in zip(manifest['seeds'],pool.map(worker,manifest['seeds'],[Path(manifest['archive_root'])]*len(manifest['seeds']))):
            rows+=r;timeline+=t;print('diagnosed',seed,len(r),'events',flush=True)
    frame=pd.DataFrame(rows).sort_values(['seed','scenario','method','channel','truth_start'])
    frame.to_csv(out/'events.csv',index=False)
    frame[~frame.matched].groupby(['method','miss_category']).size().rename('events').reset_index().to_csv(out/'miss_causes.csv',index=False)
    pd.DataFrame(timeline).to_csv(out/'timelines.csv',index=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(4,2,figsize=(14,11))
    tf=pd.DataFrame(timeline)
    for ax,case in zip(axes.flat,FOCUS):
        for method,color in [('A0','#777777'),('A5','#4477aa'),('A7','#cc3311')]:
            g=tf[(tf.scenario==case)&(tf.method==method)&(tf.channel=='temperature')]
            ax.step(g.timestamp,g.interval_s,where='post',label=method,color=color,lw=1)
        truths=frame[(frame.seed==900)&(frame.scenario==case)&(frame.method=='A7')]
        for a,b in truths[['truth_start','truth_end']].drop_duplicates().itertuples(index=False,name=None):
            ax.axvspan(a,b,color='grey',alpha=.12)
        ax.set(title=case,xlabel='Source time (s)',ylabel='Next interval (s)')
    axes.flat[0].legend();fig.suptitle('MA-1 diagnostic timelines; seed900 exposed; shaded truth supports (offline only)')
    fig.tight_layout();fig.savefig(out/'timelines.png',dpi=180);fig.savefig(out/'timelines.pdf');plt.close(fig)
    (out/'manifest.json').write_text(json.dumps(dict(status='COMPLETE',purpose='historical diagnosis only; no parameter selection',
        event_rows=len(frame),misses=int((~frame.matched).sum()),outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.name!='manifest.json'}),indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'results/phase4/diagnosis')
    parser.add_argument('--workers',type=int,default=4)
    a=parser.parse_args();main(a.out,a.workers)
