#!/usr/bin/env python3
"""Fresh, frozen three-factor campaign; historical studies remain read-only."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import hashlib
import json
import multiprocessing
from pathlib import Path
import shutil
import subprocess
import sys
import platform

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from tais.config import load
from tais.transfer_signals import counterfactual
from ablation_support import FACTORS, cases, make_trace, replay, supplement_metrics
from benchmark_joint_optimization import canon, save, sha, metrics as codec_metrics
from paper_metrics import metrics

DEFAULT = ROOT/'results/module-ablation'
PLAN = ROOT/'configs/module-ablation.json'


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def write_csv(path, rows):
    import csv
    with path.open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sources():
    paths = [*sorted((ROOT/'src/tais').glob('*.[pc]*')),
             ROOT/'configs/experiment.yaml', PLAN,
             ROOT/'results/tais-paper/operating-points.json',
             ROOT/'docs/MODULE_ABLATION_PROTOCOL.md']
    paths += [ROOT/'scripts'/name for name in (
        'ablation_support.py', 'benchmark_ablation.py', 'analyze_ablation.py',
        'paper_metrics.py', 'benchmark_joint_optimization.py', 'benchmark_paper.py',
        'benchmark_su.py')]
    paths += list((ROOT/'vendor/AdaptiveSense/simulator').glob('*.py'))
    paths += [ROOT/'vendor/AdaptiveSense/dataset/generate_dataset.py']
    paths += [ROOT/'vendor/AdaptiveSense/experiments/experiment_config.yaml']
    paths += list((ROOT/'vendor/SensorTrust/core').glob('*.[ch]'))
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(paths))}


def audit_seeds(plan, out):
    """Check accessible current manifests/configs; no inaccessible-history claim."""
    candidates = set(plan['final_seeds'])
    collisions, checked = [], []

    def numbers(value):
        if isinstance(value, int):
            return [value]
        if isinstance(value, list):
            return sum((numbers(x) for x in value), [])
        if isinstance(value, dict):
            return sum((numbers(x) for x in value.values()), [])
        return []

    def inspect(value):
        found = []
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ('seed', 'seeds', 'final_seeds', 'held_out_test_seeds', 'engineering_seeds'):
                    found += numbers(item)
                else:
                    found += inspect(item)
        elif isinstance(value, list):
            for item in value:
                found += inspect(item)
        return found

    paths = list((ROOT/'configs').glob('*.json'))
    paths += [p for p in (ROOT/'results').rglob('manifest.json')
              if not any(x in p.parts for x in ('traces', 'scratch', 'module-ablation'))]
    for p in sorted(paths):
        if p == PLAN:
            continue
        hit = sorted(candidates.intersection(inspect(json.loads(p.read_text()))))
        checked.append(dict(path=str(p.relative_to(ROOT)), sha256=sha(p)))
        if hit:
            collisions.append(dict(path=str(p.relative_to(ROOT)), seeds=hit))
    value = dict(scope='current accessible configs and manifests; seeds0..899 reserved; not an audit of inaccessible machines/history',
                 candidates=sorted(candidates), checked=checked, collisions=collisions)
    dump(out/'seed-audit.json', value)
    if collisions or min(candidates) < 900:
        raise ValueError('Seed collision')


def freeze(out, plan):
    smoke = json.loads((out/'engineering/manifest.json').read_text())
    assert smoke['status'] == 'COMPLETE'
    assert smoke['sources'] == sources(), 'Repeat engineering after any source change'
    assert not (out/'freeze.json').exists()
    audit_seeds(plan, out)
    snapshots = out/'sources'
    for path in sources():
        target = snapshots/path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/path, target)
    dump(out/'freeze.json', dict(status='FROZEN_BEFORE_TEST', sources=sources(),
                                seeds=plan['final_seeds'], cases=cases(plan),
                                methods=list(FACTORS)+plan['baseline_ids'],
                                source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                                engineering_manifest_sha256=sha(out/'engineering/manifest.json')))


def worker(seed, plan, archive):
    cfg = load()
    records, events, inputs, artifacts = [], [], [], {}
    cache = {}
    methods = list(FACTORS)+plan['baseline_ids']
    for case in cases(plan):
        trace = make_trace(plan, seed, case)
        cf = counterfactual(trace)
        signal_path = Path(str(seed))/case/'signals.json.gz'
        artifacts[str(signal_path)] = save(archive/signal_path, asdict(trace))
        observed_hash = hashlib.sha256(canon(trace.observed)).hexdigest()
        cf_hash = hashlib.sha256(canon(dict(observed=cf.observed, events=cf.events))).hexdigest()
        inputs.append(dict(seed=seed, scenario=case, n_events=len(trace.events),
                           n_faults=len(trace.faults), observed_sha256=observed_hash,
                           signal_path=str(signal_path), signals_sha256=artifacts[str(signal_path)]))
        for method in methods:
            key = (cf_hash, method)
            if key not in cache:
                clean_result = replay(cf, cfg, method, plan)
                _, clean_frames = codec_metrics(cf, clean_result, cfg, clean_result)
                path = Path(str(seed))/'counterfactuals'/f'{cf_hash}-{method}.json.gz'
                artifacts[str(path)] = save(archive/path, dict(result=clean_result, frames=clean_frames))
                cache[key] = clean_result, clean_frames
            cr, ff = cache[key]
            result = replay(trace, cfg, method, plan)
            original, frames, rx, _, hist = metrics(trace, result, cfg, cr, ff)
            extra, ee = supplement_metrics(trace, result, frames, cfg, plan, cr, ff)
            path = Path(str(seed))/case/(method+'.json.gz')
            artifacts[str(path)] = save(archive/path, dict(result=result, frames=frames))
            identity = dict(seed=seed, scenario=case, method=method)
            keep = ['samples', 'uploads', 'binary_v1_bytes', 'fault_associated_false',
                    'fault_induced_false', 'important_edges', 'important_edges_unreported',
                    'duration_s', 'n_events', 'fault_episodes', 'fault_detected',
                    'tp', 'false_reports', 'rx_tp', 'rx_false_reports']
            records.append(dict(**identity, cohort='g2' if case not in plan['supplements'] else 'supplement',
                                fault_kind='multi_'+trace.faults[0].kind if case.startswith('multi_') else trace.faults[0].kind if trace.faults else 'clean',
                                **{k: original[k] for k in keep}, **extra,
                                sample_schedule_sha256=hashlib.sha256(canon([r['timestamp'] for r in result['records']])).hexdigest(),
                                observed_sha256=observed_hash, result_sha256=artifacts[str(path)]))
            events.extend(dict(**identity, **e) for e in ee)
    return seed, records, events, inputs, artifacts


def execute(out, phase, workers, plan):
    if phase == 'test':
        lock = json.loads((out/'freeze.json').read_text())
        assert lock['sources'] == sources(), 'Frozen source/config changed'
        assert lock['seeds'] == plan['final_seeds']
    dest = out/phase
    dest.mkdir(parents=True, exist_ok=False)
    archive = ROOT/'results/traces'/out.name/phase
    if archive.exists():
        raise FileExistsError(archive)
    seeds = plan['final_seeds'] if phase == 'test' else plan['engineering_seeds']
    manifest = dict(status='STARTED', phase=phase, seeds=seeds, cases=cases(plan),
                    methods=list(FACTORS)+plan['baseline_ids'], sources=sources(),
                    source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    worktree_status=subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),
                    python=platform.python_version(), archive_root=str(archive),
                    freeze_sha256=sha(out/'freeze.json') if phase == 'test' else None)
    import importlib.metadata
    manifest['packages'] = {name: importlib.metadata.version(name) for name in ('numpy', 'pandas', 'matplotlib', 'PyYAML')}
    dump(dest/'manifest.json', manifest)
    all_rows, all_events, all_inputs, hashes = [], [], [], {}
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn')) as pool:
        tasks = [pool.submit(worker, seed, plan, archive) for seed in seeds]
        for future in as_completed(tasks):
            seed, rr, ee, ii, hh = future.result()
            all_rows += rr
            all_events += ee
            all_inputs += ii
            hashes.update(hh)
            print(phase, seed, len(rr), 'runs complete', flush=True)
    all_rows.sort(key=lambda r: (r['seed'], r['scenario'], r['method']))
    all_events.sort(key=lambda r: (r['seed'], r['scenario'], r['method'], r['side'], r['channel'], r['truth_start']))
    all_inputs.sort(key=lambda r: (r['seed'], r['scenario']))
    for name, values in [('metrics', all_rows), ('events', all_events), ('inputs', all_inputs)]:
        write_csv(dest/(name+'.csv'), values)
    dump(dest/'archives.json', hashes)
    assert len(all_rows) == len(seeds)*len(cases(plan))*len(manifest['methods'])
    manifest.update(status='COMPLETE', runs=len(all_rows),
                    outputs={p.name: sha(p) for p in sorted(dest.iterdir()) if p.name != 'manifest.json'})
    assert manifest['sources'] == sources(), 'Sources changed during execution'
    dump(dest/'manifest.json', manifest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['engineering', 'freeze', 'test', 'replicate'])
    parser.add_argument('--out', type=Path, default=DEFAULT)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        raise ValueError('workers must be1..4')
    plan = json.loads(PLAN.read_text())
    args.out.mkdir(parents=True, exist_ok=True)
    if args.phase == 'replicate':
        lock = json.loads((DEFAULT/'freeze.json').read_text())
        assert sources() == lock['sources'], 'Replica must use frozen sources'
        assert not (args.out/'freeze.json').exists(), 'Use a fresh output'
        shutil.copyfile(DEFAULT/'freeze.json', args.out/'freeze.json')
        shutil.copytree(DEFAULT/'sources', args.out/'sources')
        execute(args.out, 'test', args.workers, plan)
    elif args.phase == 'freeze':
        freeze(args.out, plan)
    else:
        execute(args.out, args.phase, args.workers, plan)
