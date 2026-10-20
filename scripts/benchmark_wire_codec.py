#!/usr/bin/env python3
"""Audit immutable archived uploads, never run a scheduler or generate signals.

Default input is the original 20--49 test archive. New outputs are exclusive.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import platform
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from tais.config import load
from tais.wire_codec import (VERSION, LAYOUTS, encode, decode,
                             envelope_from_record, layout_descriptor, validate_layout)
from simulator.events import Event, match_events

BASE = 'f21bc2f0e1d01d0670ce1c1bd4ab5a2aab7e171d'
METHODS = ('AdaptiveSense', 'AdaptiveSense+TrustLog', 'GateOnly', 'TAIS')
SUM_FIELDS = ('n_events', 'tp', 'missed', 'local_tp', 'false_reports',
              'redundant_reports', 'fault_induced_false', 'fault_associated_false',
              'samples', 'uploads', 'payload_bytes', 'fault_episodes',
              'fault_detected', 'fault_type_detected', 'confirmation_samples',
              'diagnostic_samples', 'diagnostic_only_samples', 'duration_s',
              'latency_sum_s', 'latency_n', 'fault_latency_sum_s')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args, binary=False):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=not binary)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def exact(a, b):
    """Strict semantic identity, including numeric type and all float bits."""
    if type(a) is not type(b):
        return False
    if isinstance(a, float):
        return struct.pack('>d', a) == struct.pack('>d', b)
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(exact(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(exact(x, y) for x, y in zip(a, b))
    return a == b


def source_closure(source):
    """Every original policy/config source blob must still be identical."""
    listing = git('ls-tree', '-rz', source, '--', 'src/tais',
                  'configs/experiment.yaml', binary=True)
    result = {}
    for entry in listing.split(b'\0'):
        if not entry:
            continue
        metadata, name = entry.split(b'\t', 1)
        path = name.decode()
        blob = metadata.split()[2].decode()
        data = (ROOT / path).read_bytes()
        actual = sha(data)
        check(git('hash-object', path).strip() == blob, f'Policy source changed: {path}')
        result[path] = actual
    for path, expected in [('vendor/AdaptiveSense', 'f7ec30fd4721aa1a7c308f879050a83936e60067'),
                           ('vendor/SensorTrust', '2ce98dd043bb01ea99052eda218c68a172499a4c')]:
        actual = subprocess.check_output(['git', '-C', str(ROOT/path), 'rev-parse', 'HEAD'], text=True).strip()
        dirty = subprocess.check_output(['git', '-C', str(ROOT/path), 'status', '--porcelain'], text=True)
        check(actual == expected and not dirty, f'Upstream changed: {path}')
        result[path] = actual
    return result


def audit_result(result, truth, original, tolerance):
    """Substitute decoded envelopes on uploads; re-extract frozen sender events.

    Nonuploaded sample states remain internal inputs, not receiver knowledge.
    """
    names = LAYOUTS[1]
    opened = dict.fromkeys(names)
    sent = dict.fromkeys(names, False)
    last = dict.fromkeys(names, 0)
    reports, detections = [], []
    before_hash, after_hash = hashlib.sha256(), hashlib.sha256()
    binary_hash = hashlib.sha256()
    hist = {'JSON': Counter(), 'Binary': Counter()}
    samples = uploads = json_bytes = binary_bytes = health_entries = active_flags = 0
    all_health = hashlib.sha256()
    for record in result['records']:
        samples += 1
        # Full internal health output is immutable, including nonuploaded states.
        internal_health = canonical(record['health'])
        all_health.update(struct.pack('>I', len(internal_health)) + internal_health)
        t, active = record['timestamp'], record['active']
        if record['upload']:
            uploads += 1
            old = envelope_from_record(record)
            old_json = canonical(old)
            check(len(old_json) == record['payload_bytes'], 'Original per-frame JSON mismatch')
            wire = encode(old)
            restored = decode(wire)
            check(exact(old, restored), 'Lossy business-envelope round trip')
            restored_json = canonical(restored)
            check(old_json == restored_json, 'JSON rendering changed after decoding')
            before_hash.update(struct.pack('>I', len(old_json)) + old_json)
            after_hash.update(struct.pack('>I', len(restored_json)) + restored_json)
            binary_hash.update(struct.pack('>I', len(wire)) + wire)
            for encoding, size in [('JSON', len(old_json)), ('Binary', len(wire))]:
                hist[encoding][size] += 1
            json_bytes += len(old_json)
            binary_bytes += len(wire)
            health_entries += len(restored['health'])
            active_flags += sum(restored['environment_active'].values())
            t, active = restored['timestamp'], restored['environment_active']
        else:
            check(record['payload_bytes'] == 0, 'Nonupload counted as transmitted')
        for name in names:
            if active[name]:
                last[name] = t
                if opened[name] is None:
                    opened[name], sent[name] = t, False
                if record['upload'] and not sent[name]:
                    reports.append(Event(name, t, t))
                    sent[name] = True
            elif opened[name] is not None:
                detections.append(Event(name, opened[name], last[name]))
                opened[name] = None
    for name in names:
        if opened[name] is not None:
            detections.append(Event(name, opened[name], last[name]))
    check([asdict(e) for e in reports] == result['reports'], 'Sender reports changed')
    check([asdict(e) for e in detections] == result['detections'], 'Sender detections changed')
    events = [Event(**e) for e in truth['events']]
    matched = match_events(events, reports, tolerance)
    local = match_events(events, detections, tolerance)
    measured = dict(n_events=len(events), tp=matched.true_positives,
                    missed=matched.false_negatives, local_tp=local.true_positives,
                    false_reports=matched.false_positives,
                    redundant_reports=len(matched.redundant_detections),
                    latency_sum_s=sum(matched.latencies), latency_n=len(matched.latencies),
                    samples=samples, uploads=uploads, payload_bytes=json_bytes)
    for field, value in measured.items():
        check(math.isclose(value, float(original[field]), abs_tol=1e-10, rel_tol=0),
              f'Historical run metric mismatch: {field}: {value} != {original[field]}')
    check(before_hash.digest() == after_hash.digest(), 'Envelope stream changed')
    return dict(binary_bytes=binary_bytes, reports=len(reports), detections=len(detections),
                uploaded_health_entries=health_entries, uploaded_active_flags=active_flags,
                original_envelopes_sha256=before_hash.hexdigest(),
                decoded_envelopes_sha256=after_hash.hexdigest(),
                binary_frames_sha256=binary_hash.hexdigest(),
                internal_health_sha256=all_health.hexdigest(),
                roundtrip_verified=uploads, sender_events_identical=True,
                matching_identical=True), hist


def stats(hist):
    count, total = sum(hist.values()), sum(size*n for size, n in hist.items())
    def rank(r):
        cumulative = 0
        for size, n in sorted(hist.items()):
            cumulative += n
            if cumulative >= r:
                return size
    return dict(bytes=total, mean_bytes=total/count, median_bytes=(rank((count+1)//2)+rank((count+2)//2))/2,
                p95_bytes=rank(math.ceil(.95*count)), min_bytes=min(hist), max_bytes=max(hist))


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows, fields):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[k] for k in fields)].append(row)
    output = []
    for key, group in sorted(groups.items()):
        item = dict(zip(fields, key))
        for field in (*SUM_FIELDS, 'binary_bytes', 'reports', 'detections',
                      'uploaded_health_entries', 'uploaded_active_flags', 'roundtrip_verified'):
            item[field] = sum(float(r[field]) for r in group)
            if item[field].is_integer():
                item[field] = int(item[field])
        item['runs'] = len(group)
        output.append(item)
    return output


def compare(summaries):
    lookup = {(r['method'], r['multiplier'], r['encoding']): r for r in summaries}
    rows = []
    def pair(label, a, b):
        x, y = lookup[a], lookup[b]
        rows.append(dict(comparison=label, numerator_method=a[0], numerator_multiplier=a[1],
                         numerator_encoding=a[2], denominator_method=b[0], denominator_multiplier=b[1],
                         denominator_encoding=b[2], numerator_bytes=x['bytes'], denominator_bytes=y['bytes'],
                         difference_bytes=x['bytes']-y['bytes'], relative_difference=x['bytes']/y['bytes']-1,
                         saving=1-x['bytes']/y['bytes']))
    for method, multiplier in sorted({(r['method'],r['multiplier']) for r in summaries}):
        pair('encoding_only', (method,multiplier,'Binary'), (method,multiplier,'JSON'))
    for encoding in ('JSON', 'Binary'):
        pair('policy_same_encoding', ('TAIS',1.0,encoding), ('AdaptiveSense',1.0,encoding))
        pair('diagnostic_information', ('AdaptiveSense+TrustLog',1.0,encoding), ('AdaptiveSense',1.0,encoding))
        pair('policy_with_diagnostics', ('TAIS',1.0,encoding), ('AdaptiveSense+TrustLog',1.0,encoding))
    pair('mixed_encoding_not_policy_evidence', ('TAIS',1.0,'Binary'), ('AdaptiveSense',1.0,'JSON'))
    return rows


def plot(summaries, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    lookup = {(r['method'], r['encoding']): r for r in summaries if r['multiplier'] == 1}
    fig, ax = plt.subplots(figsize=(10, 5.8))
    for index, (encoding, color) in enumerate([('JSON','#627b95'),('Binary','#187d79')]):
        xs = [i+(index-.5)*.36 for i in range(4)]
        ys = [lookup[(method,encoding)]['bytes']/1e6 for method in METHODS]
        bars = ax.bar(xs,ys,width=.34,label=encoding,color=color)
        ax.bar_label(bars, labels=[f'{y:.3f}' for y in ys], padding=4, fontsize=10)
    ax.set_xticks(range(4), ['AdaptiveSense','AdaptiveSense\n+ TrustLog','GateOnly','TAIS'])
    ax.set_ylabel('Application bytes (decimal MB)')
    ax.set_title('Same historical uploads, lossless serialization\nNative multiplier 1.0 · seeds 20–49 · 45 scenarios')
    ax.legend(frameon=False)
    ax.spines[['top','right']].set_visible(False)
    ax.set_ylim(0,max(r['bytes']/1e6 for r in lookup.values())*1.17)
    ax.text(0, -.22, 'Application serialization only; no radio energy or packet-count inference.', transform=ax.transAxes, fontsize=10)
    fig.tight_layout()
    for suffix in ('png','svg'):
        fig.savefig(output/f'bytes_comparison.{suffix}', dpi=180, bbox_inches='tight')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=ROOT/'results/traces/test')
    parser.add_argument('--output', type=Path, default=ROOT/'results/wire-payload/test')
    parser.add_argument('--smoke', action='store_true', help='24 archived runs, not the complete comparison')
    args = parser.parse_args()
    check(not args.output.exists(), 'Output exists; choose a new directory, never overwrite')
    source = ROOT/'results/test'
    manifest = json.loads((source/'manifest.json').read_text())
    check(sha((source/'metrics.csv').read_bytes()) == manifest['metrics_sha256'], 'Historical metrics hash mismatch')
    check(sha((ROOT/'configs/experiment.yaml').read_bytes()) == manifest['config_sha256'], 'Configuration hash mismatch')
    closure = source_closure(manifest['source_commit'])
    cfg = load()
    validate_layout(tuple(cfg['channels']))
    old_summary = list(csv.DictReader((source/'summary.csv').open()))
    selected = [r for r in csv.DictReader((source/'metrics.csv').open()) if r['method'] in METHODS]
    if args.smoke:
        selected = [r for r in selected if r['seed'] == '20' and r['scenario'] in ('clean_none','range_same_long','spike_same_short')]
    check(len(selected) == (24 if args.smoke else 10800), 'Unexpected method/scenario/seed matrix')
    args.output.mkdir(parents=True)
    verified = {}
    def read_archive(relative):
        data = (args.archive/relative).read_bytes()
        digest = sha(data)
        check(digest == manifest['artifacts'][relative], f'Archive SHA mismatch: {relative}')
        verified[relative] = digest
        return json.loads(gzip.decompress(data))
    rows, histograms = [], defaultdict(lambda: {'JSON': Counter(), 'Binary': Counter()})
    previous, truth = None, None
    for i, original in enumerate(selected):
        seed, scenario = int(original['seed']), original['scenario']
        if (seed,scenario) != previous:
            truth = read_archive(f'{seed}/{scenario}/signals.json.gz')
            previous = seed,scenario
        method, multiplier = original['method'], float(original['multiplier'])
        relative = f'{seed}/{scenario}/{method}-{multiplier:g}.json.gz'
        result = read_archive(relative)
        audited, hist = audit_result(result, truth, original, cfg['evaluation']['event_match_tolerance_s'])
        row = {**original, **audited, 'archive_sha256':verified[relative],
               'signals_sha256':verified[f'{seed}/{scenario}/signals.json.gz']}
        rows.append(row)
        for encoding in hist:
            histograms[(method,multiplier)][encoding].update(hist[encoding])
        if (i+1) % 1000 == 0:
            print(f'Checked {i+1}/{len(selected)} archived runs', flush=True)
    totals = aggregate(rows, ('method','multiplier'))
    summaries = []
    for total in totals:
        method, multiplier = total['method'], float(total['multiplier'])
        old = next(r for r in old_summary if r['method'] == method and float(r['multiplier']) == multiplier)
        if not args.smoke:
            for field in SUM_FIELDS:
                check(math.isclose(total[field], float(old[field]), abs_tol=1e-8, rel_tol=0), f'Frozen summary mismatch: {method}/{multiplier}/{field}')
        for encoding in ('JSON','Binary'):
            h = histograms[(method,multiplier)][encoding]
            tp, fp, missed = total['tp'],total['false_reports'],total['missed']
            summaries.append({**total, 'multiplier':multiplier, 'encoding':encoding, **stats(h),
                              'compression_saving':0 if encoding == 'JSON' else 1-total['binary_bytes']/total['payload_bytes'],
                              'precision':tp/(tp+fp) if tp+fp else None,
                              'recall':tp/(tp+missed) if tp+missed else None,
                              'f1':2*tp/(2*tp+fp+missed) if 2*tp+fp+missed else None,
                              'latency_mean_s':total['latency_sum_s']/total['latency_n'] if total['latency_n'] else None,
                              'events_and_health_identical':True,
                              'binary_with_hypothetical_one_descriptor_per_run':total['binary_bytes']+total['runs']*len(layout_descriptor())})
    summary_path = args.output/'summary.csv'
    write_csv(summary_path, summaries)
    write_csv(args.output/'per_run.csv', rows)
    write_csv(args.output/'by_seed.csv', aggregate(rows, ('method','multiplier','seed')))
    write_csv(args.output/'by_scenario.csv', aggregate(rows, ('method','multiplier','scenario')))
    write_csv(args.output/'comparisons.csv', compare(summaries))
    hist_rows = [dict(method=method,multiplier=multiplier,encoding=encoding,frame_bytes=size,count=count)
                 for (method,multiplier), encodings in sorted(histograms.items())
                 for encoding,hist in encodings.items() for size,count in sorted(hist.items())]
    write_csv(args.output/'frame_size_histogram.csv', hist_rows)
    primary = next(r for r in summaries if r['method']=='TAIS' and r['multiplier']==1 and r['encoding']=='Binary')
    details = dict(status='PASS', scope='partial smoke' if args.smoke else 'complete historical format-layer engineering review',
                   runs=len(rows), verified_archive_files=len(verified), uploaded_frames=sum(r['roundtrip_verified'] for r in rows),
                   all_roundtrips_exact=True, all_original_json_bytes_match=True,
                   all_sender_reports_detections_and_matches_identical=True,
                   historical_group_totals_match=not args.smoke,
                   unchanged_metrics='Frozen original metrics retained, except application byte cost; matching recomputed. Fault attribution not rerun.',
                   layout_descriptor_bytes=len(layout_descriptor()),
                   version_layout_cost_per_frame=2, minimum_legal_frame=13, maximum_legal_frame=56,
                   goal_fraction=.4, primary_goal_met=primary['compression_saving']>=.4,
                   primary_tais_json_bytes=primary['payload_bytes'], primary_tais_binary_bytes=primary['binary_bytes'],
                   primary_tais_saving=primary['compression_saving'])
    (args.output/'verification.json').write_text(json.dumps(details, indent=2)+'\n')
    plot(summaries,args.output)
    check(source_closure(manifest['source_commit']) == closure, 'Policy source changed during audit')
    outputs = {p.name:sha(p.read_bytes()) for p in sorted(args.output.iterdir()) if p.is_file()}
    provenance = dict(created_utc=datetime.now(timezone.utc).isoformat(), command=sys.argv,
                      research_base=BASE, implementation_commit=git('rev-parse','HEAD').strip(),
                      original_experiment_source_commit=manifest['source_commit'],
                      original_config_sha256=manifest['config_sha256'], original_policy_sources=closure,
                      original_files={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in [source/'manifest.json',source/'metrics.csv',source/'summary.csv']},
                      implementation_files={p:sha((ROOT/p).read_bytes()) for p in ['src/tais/wire_codec.py','scripts/benchmark_wire_codec.py','tests/test_wire_codec.py']},
                      archive_root=str(args.archive.resolve()), archive_files_checked=len(verified),
                      verified_archive_index_sha256=sha(canonical(verified)),
                      original_manifest_contains_each_archive_sha256=True,
                      seeds=[20] if args.smoke else manifest['seeds'], scenarios=sorted({r['scenario'] for r in rows}),
                      python=sys.version, platform=platform.platform(), wire_version=VERSION, layout_id=1,
                      layout_channels=LAYOUTS[1], output_sha256=outputs)
    (args.output/'manifest.json').write_text(json.dumps(provenance, indent=2)+'\n')
    print(json.dumps(details,indent=2), flush=True)


if __name__ == '__main__':
    main()
