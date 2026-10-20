#!/usr/bin/env python3
"""BM-1 historical engineering review, no policy replay or new algorithm test."""
import argparse
from collections import defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from tais.budget_eval import numeric_rows, aggregate, groups, paired_bootstrap, sha
from tais.wire_codec import encode, decode, envelope_from_record
from benchmark_wire_codec import exact


def csv_write(path, rows):
    with path.open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args();source = ROOT/'results/budget-matched/test'
    manifest = json.loads((source/'manifest.json').read_text())
    if sha(source/'metrics.csv') != manifest['metrics_sha256']:
        raise ValueError('Frozen BM-1 metrics checksum differs')
    archive = a.archive or Path(manifest['archive_root'])
    rows = numeric_rows(csv.DictReader((source/'metrics.csv').open()))
    rows = [r for r in rows if r['method']=='GateOnly' or r['method']=='AdaptiveSense+TrustLog']
    assert len(rows)==5400 and {r['seed'] for r in rows}==set(range(170,200))
    assert len({r['scenario'] for r in rows})==45
    a.out.mkdir(parents=True, exist_ok=False)
    audited = []
    for r in rows:
        rel = f"{r['seed']}/{r['scenario']}/{r['method']}-{r['multiplier']:g}.json.gz"
        if sha(archive/rel) != manifest['artifacts'][rel] or sha(archive/rel) != r['result_sha256']:
            raise ValueError('Frozen archive mismatch '+rel)
        result = json.loads(gzip.decompress((archive/rel).read_bytes()))
        total = uploads = json_total = 0
        for record in result['records']:
            if not record['upload']:
                continue
            envelope = envelope_from_record(record)
            frame = encode(envelope)
            assert exact(decode(frame), envelope)
            size = len(json.dumps(envelope, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
            assert size == record['payload_bytes']
            json_total += size;total += len(frame);uploads += 1
        assert total == r['binary_v1_bytes'] and json_total == r['payload_bytes']
        assert uploads == r['uploads'] and len(result['records']) == r['samples']
        audited.append(dict(seed=r['seed'], scenario=r['scenario'], method=r['method'],
                            multiplier=r['multiplier'], source_archive_sha256=r['result_sha256'],
                            actual_frames=uploads, binary_bytes=total, json_bytes=json_total,
                            every_envelope_exact=True))
    csv_write(a.out/'per_run_encoding_audit.csv', audited)
    grouped = defaultdict(list)
    for r in rows:
        for g in groups(r):
            grouped[r['method'], r['multiplier'], g].append(r)
    summary = [dict(method=m, multiplier=point, group=g, **aggregate(rs))
               for (m,point,g),rs in sorted(grouped.items())]
    csv_write(a.out/'summary.csv', summary)
    csv_write(a.out/'frozen_rows.csv', rows)
    baseline = {(r['seed'],r['scenario']): r for r in rows if r['method']=='AdaptiveSense+TrustLog'}
    intervals = []
    for point in (.75,1.,1.5):
        paired = defaultdict(list)
        for r in rows:
            if r['method'] != 'GateOnly' or r['multiplier'] != point:
                continue
            b = baseline[r['seed'],r['scenario']]
            for field in ('signals_sha256','observed_sha256','events_sha256','faults_sha256'):
                assert b[field] == r[field]
            for group in groups(r):
                if group in ('overall','same_channel','cross_channel','no_event','profile:short','profile:long') or group.startswith('kind:'):
                    paired[group].append((b,r))
        for group, pairs in sorted(paired.items()):
            for ci in paired_bootstrap(pairs, 10000, 2026101902, family=3):
                ci['gate_minus_trustlog'] = ci.pop('tais_minus_gate')
                intervals.append(dict(gate_multiplier=point, group=group, **ci))
    csv_write(a.out/'paired_intervals.csv', intervals)
    sources = {str(p.relative_to(ROOT)): sha(p) for p in
               (source/'metrics.csv',source/'manifest.json',ROOT/'configs/experiment.yaml',
                ROOT/'docs/BUDGET_MATCHED_EXPERIMENT_REPORT.md',Path(__file__))}
    verification = dict(scope='Historical BM-1 seeds170-199; all45 scenarios; not new validation',
                        runs=len(rows), uploads=sum(r['actual_frames'] for r in audited),
                        actual_binary_bytes_recomputed=sum(r['binary_bytes'] for r in audited),
                        all_frames_lossless=True, scheduler_rerun=False, thresholds_selected=False,
                        baseline='AdaptiveSense+TrustLog multiplier1; NOT resource-matched to GateOnly',
                        gate_points=[.75,1.,1.5], bootstrap='10000 paired whole-seed resamples; 30 clusters',
                        interval_scope='Descriptive historical comparisons, no new superiority test; family3 per metric',
                        bm1_source_commit=manifest['source_commit'], source_sha256=sources,
                        outputs={p.name:sha(p) for p in a.out.iterdir() if p.is_file()})
    (a.out/'manifest.json').write_text(json.dumps(verification, indent=2)+'\n')
    print(json.dumps(verification, indent=2))


if __name__ == '__main__':
    main()
