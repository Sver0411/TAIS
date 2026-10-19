#!/usr/bin/env python3
"""Actual local streaming sender -> byte link -> independent v1 receiver."""
import argparse
from copy import deepcopy
import csv
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from tais.config import load
from tais.core_stream import CoreSender, CoreReceiver, LocalLink, render, timestamp
from tais.signals import generate, scenarios
from tais.wire_codec import LAYOUTS, encode, layout_descriptor


def clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def canonical(value):
    return json.dumps(clean(value), sort_keys=True, separators=(',', ':'), allow_nan=False)


def file_sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def number(text):
    if text is None or text.strip().lower() in ('', 'null', 'none'):
        return None
    try:
        value = json.loads(text)
    except ValueError:
        value = float(text)
    if type(value) not in (int, float):
        raise ValueError('CSV cells must be numeric or empty/null')
    return value


def csv_rows(path, names):
    with path.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if not set(('timestamp', *names)) <= set(reader.fieldnames or ()):
            raise ValueError('CSV requires timestamp and every configured channel column')
        for line, raw in enumerate(reader, 2):
            try:
                yield dict(timestamp=number(raw['timestamp']),
                           **{n: number(raw[n]) for n in names}), dict(line=line, raw=raw)
            except (ValueError, TypeError, OverflowError) as error:
                raise ValueError(f'CSV line {line}: {error}') from error


def stdin_rows(stream, names):
    for line, text in enumerate(stream, 1):
        if not text.strip():
            continue
        def invalid(_):
            raise ValueError('JSON nonfinite constants are invalid; use null')
        row = json.loads(text, parse_constant=invalid)
        if not isinstance(row, dict) or not set(('timestamp', *names)) <= row.keys():
            raise ValueError(f'JSONL line {line}: timestamp and all channel fields required')
        yield {n: row[n] for n in ('timestamp', *names)}, dict(line=line)


def evaluation(trace, records, reports, cfg):
    # Offline only, after EOF. Unlabeled user inputs never enter this function.
    from simulator.events import Event, match_events
    result = match_events(trace.events, [Event(**x) for x in reports],
                          cfg['evaluation']['event_match_tolerance_s'])
    tp, fp, fn = result.true_positives, result.false_positives, result.false_negatives
    detected = sum(any(f.start_s <= r['timestamp'] < f.end_s and
                       r['health'][f.channel]['flags'] for r in records) for f in trace.faults)
    return dict(source='synthetic independent intervention labels; offline only',
                truth=[asdict(e) for e in trace.events], faults=[asdict(f) for f in trace.faults],
                tp=tp, unmatched=fp, missed=fn,
                precision=tp/(tp+fp) if tp+fp else None,
                recall=tp/(tp+fn) if tp+fn else None,
                f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
                fault_episodes=len(trace.faults), flagged_during_fault=detected)


def verify(out, trace, cfg, layout):
    """Compare actual sender journal to frozen replay and decode actual frames."""
    from tais.replay import run as frozen_run
    entries = [json.loads(line) for line in (out/'journal.jsonl').open()]
    samples = [e['record'] for e in entries if e['kind'] == 'sample']
    tx = {e['harness_tx_id']: e for e in entries if e['kind'] == 'tx'}
    expected = frozen_run(trace, cfg, 'GateOnly', multiplier=1.0)
    parity = None
    if trace is not None:
        assert canonical(samples) == canonical(expected['records']), 'Frozen sender records differ'
        reports = [r for e in entries if e['kind'] == 'sample' for r in e['reports']]
        assert canonical(reports) == canonical([asdict(r) for r in expected['reports']])
        parity = True
    sizes = 0
    for e in tx.values():
        frame = bytes.fromhex(e['frame_hex']);sizes += len(frame)
        assert e['frame_bytes'] == len(frame) and encode(e['envelope'], layout) == frame
    exact = 0
    for e in entries:
        if e['kind'] == 'rx' and e['envelope'] is not None:
            assert encode(e['envelope'], layout) == bytes.fromhex(tx[e['harness_tx_id']]['frame_hex'])
            exact += 1
    return dict(frozen_gateonly_records_and_reports_identical=parity,
                tx_frames=len(tx), actual_binary_bytes_recomputed=sizes,
                received_valid_frames_exact=exact,
                all_valid_received_envelopes_match_sender=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    inputs = p.add_mutually_exclusive_group()
    inputs.add_argument('--scenario', choices=scenarios())
    inputs.add_argument('--csv', type=Path)
    inputs.add_argument('--stdin', action='store_true', help='one current JSON object per line until EOF')
    p.add_argument('--seed', type=int, default=20, help='used demonstration seed, not new validation')
    p.add_argument('--layout', type=int, choices=LAYOUTS, default=1)
    p.add_argument('--pace', type=float, default=.01, help='wall seconds per input second; 0=fast, 1=recorded speed')
    p.add_argument('--ui', choices=['live', 'log', 'quiet'], default='live')
    p.add_argument('--out', type=Path, required=True, help='new run directory; existing paths refused')
    p.add_argument('--drop-every', type=int, default=0)
    p.add_argument('--corrupt-every', type=int, default=0)
    p.add_argument('--reorder-pairs', action='store_true')
    p.add_argument('--verify', action='store_true', help='after finite synthetic EOF compare frozen replay')
    a = p.parse_args()
    if not math.isfinite(a.pace) or a.pace < 0:
        p.error('pace must be finite and nonnegative')
    if min(a.drop_every, a.corrupt_every) < 0:
        p.error('link periods must be nonnegative')
    if a.verify and (a.csv or a.stdin):
        p.error('--verify uses synthetic truth; user streams have no verified labels')
    cfg = deepcopy(load());cfg['channels'] = {n: cfg['channels'][n] for n in LAYOUTS[a.layout]}
    if not (a.csv or a.stdin) and a.layout != 1:
        p.error('existing synthetic demonstrations use the frozen two-channel layout 1')
    trace = None
    if a.csv:
        source = csv_rows(a.csv, tuple(cfg['channels']));label = 'USER CSV | provenance unverified | no truth metrics'
    elif a.stdin:
        source = stdin_rows(sys.stdin, tuple(cfg['channels']));label = 'USER JSONL | provenance unverified | no truth metrics'
    else:
        trace = generate(cfg, a.seed, a.scenario or 'clean_none')
        source = ((r, {}) for r in trace.observed)
        label = f'SYNTHETIC DEMO {trace.scenario} seed={a.seed} | not device measurements'
    a.out.mkdir(parents=True, exist_ok=False)
    manifest = dict(policy='GateOnly', multiplier=1.0, wire_version=1,
                    input_label=label, source_commit=subprocess.check_output(
                        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    command=sys.argv, layout=json.loads(layout_descriptor(a.layout)),
                    mapping_preprovisioned=True, descriptor_bytes_not_transmitted=len(layout_descriptor(a.layout)),
                    source_csv_sha256=file_sha(a.csv) if a.csv else None,
                    config_sha256=hashlib.sha256((ROOT/'configs/experiment.yaml').read_bytes()).hexdigest(),
                    transport='local bounded Python frame link; no ACK, radio or network headers',
                    failures=dict(drop_every=a.drop_every, corrupt_every=a.corrupt_every, reorder_pairs=a.reorder_pairs))
    manifest['source_sha256'] = {name: file_sha(ROOT/name) for name in (
        'src/tais/core_stream.py', 'examples/tais-core/run.py', 'src/tais/scheduler.py',
        'src/tais/replay.py', 'src/tais/trust.py', 'src/tais/trust_bridge.c',
        'src/tais/wire_codec.py', 'configs/experiment.yaml',
        'vendor/SensorTrust/core/sensor_trust.c', 'vendor/SensorTrust/core/sensor_trust.h',
        'vendor/AdaptiveSense/simulator/scoring.py', 'vendor/AdaptiveSense/simulator/adaptive.py')}
    (a.out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    sender, receiver = CoreSender(cfg, a.layout), CoreReceiver(a.layout)
    status, error = 'COMPLETE', None
    with (a.out/'journal.jsonl').open('x') as journal:
        def emit(entry):
            journal.write(canonical(entry)+'\n');journal.flush()
        link = LocalLink(receiver, emit, a.drop_every, a.corrupt_every, a.reorder_pairs)
        last_tick = None
        last_render = 0
        try:
            for row, metadata in source:
                t = timestamp(row['timestamp'])
                if last_tick is not None and t <= last_tick:
                    raise ValueError('source timestamps must strictly increase')
                if last_tick is not None and a.pace:
                    time.sleep((t-last_tick)*a.pace)
                last_tick = t
                emit(dict(kind='source', row=row, provenance=metadata))
                step = sender.push(row)
                if step is None:
                    if a.ui == 'live' and time.monotonic()-last_render >= .1:
                        print('\x1b[2J\x1b[H'+render(sender, receiver, label), flush=True)
                        last_render = time.monotonic()
                    continue
                emit(dict(kind='sample', record=step['record'], reports=step['reports']))
                if step['frame'] is not None:
                    frame = step['frame']
                    emit(dict(kind='tx', harness_tx_id=sender.counts['uploads'],
                              frame_hex=frame.hex(), frame_bytes=len(frame), envelope=step['envelope']))
                    link.send(frame)
                if a.ui != 'quiet':
                    print(('\x1b[2J\x1b[H' if a.ui == 'live' else '\n')
                          + render(sender, receiver, label), flush=True)
                    last_render = time.monotonic()
        except KeyboardInterrupt:
            status = 'STOPPED'
        except Exception as exc:
            status, error = 'FAILED', f'{type(exc).__name__}: {exc}'
            emit(dict(kind='error', error=error))
        finally:
            link.flush()
            sender.close()
    summary = dict(status=status, error=error, input_label=label, sender=dict(sender.counts),
                   health_sample_counts=dict(sender.health_counts), link=dict(link.counts),
                   receiver=dict(receiver.counts), truth_metrics=None,
                   truth_metrics_reason='user data has no verified event/fault labels')
    if trace is not None and status == 'COMPLETE':
        entries = [json.loads(line) for line in (a.out/'journal.jsonl').open()]
        summary['truth_metrics'] = evaluation(trace, [e['record'] for e in entries if e['kind']=='sample'],
                                            [r for e in entries if e['kind']=='sample' for r in e['reports']], cfg)
        summary['truth_metrics_reason'] = 'offline synthetic truth; not available to sender or receiver'
    if a.verify and status == 'COMPLETE':
        summary['verification'] = verify(a.out, trace, cfg, a.layout)
        assert summary['verification']['actual_binary_bytes_recomputed'] == summary['sender']['binary_bytes']
    summary['journal_sha256'] = file_sha(a.out/'journal.jsonl')
    (a.out/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    print(render(sender, receiver, label), flush=True)
    print(json.dumps(summary, indent=2, allow_nan=False), flush=True)
    if status == 'FAILED':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
