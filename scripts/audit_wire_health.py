#!/usr/bin/env python3
"""Health-field compressibility on frozen uploaded envelopes, not internal samples."""
from collections import Counter, defaultdict
import argparse
import csv
import gzip
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark_wire_codec import ROOT, METHODS, check, sha, canonical, source_closure, write_csv
from tais.wire_codec import envelope_from_record, _uvar

BASE = 'b184240226025d86c5e77a74f124c5c788564613'
FIELDS = ('state', 'score', 'flags')


def inputs(smoke=False):
    manifest = json.loads((ROOT/'results/test/manifest.json').read_text())
    check(sha((ROOT/'results/test/metrics.csv').read_bytes()) == manifest['metrics_sha256'], 'Metrics changed')
    check(sha((ROOT/'configs/experiment.yaml').read_bytes()) == manifest['config_sha256'], 'Config changed')
    source_closure(manifest['source_commit'])
    rows = [r for r in csv.DictReader((ROOT/'results/test/metrics.csv').open()) if r['method'] in METHODS]
    if smoke:
        rows = [r for r in rows if r['seed']=='20' and r['scenario'] in ('clean_none','range_same_long','spike_same_short')]
    check(len(rows)==(24 if smoke else 10800), 'Incomplete frozen matrix')
    return manifest, rows


def read_archive(archive, relative, manifest, verified):
    data = (archive/relative).read_bytes()
    check(sha(data)==manifest['artifacts'][relative], f'Archive mismatch: {relative}')
    verified[relative] = sha(data)
    return json.loads(gzip.decompress(data))


def health_statistics(envelopes):
    out = Counter({k:0 for k in ('uploads','health_entries','channel_pairs','health_equal_pairs',
                                'health_pairs','raw_health_bytes','changed_value_bytes',
                                'initial_health_bytes','state_changes','score_changes','flags_changes',
                                'state_HEALTHY','state_DEGRADED','state_FAULT')})
    for a in ('HEALTHY','DEGRADED','FAULT'):
        for b in ('HEALTHY','DEGRADED','FAULT'):
            out[f'transition_{a}_to_{b}'] = 0
    previous = None
    for e in envelopes:
        health = e['health'];out['uploads']+=1
        if previous is not None:
            out['health_pairs']+=1;out['health_equal_pairs']+=health==previous
        for name, h in health.items():
            out['health_entries']+=1;out['state_'+h['state']]+=1
            sizes={'state':1,'score':1,'flags':len(_uvar(h['flags']))}
            out['raw_health_bytes']+=sum(sizes.values())
            before = previous.get(name) if previous is not None else None
            if before is None:
                out['initial_health_bytes']+=sum(sizes.values())
            else:
                out['channel_pairs']+=1
                out[f"transition_{before['state']}_to_{h['state']}"]+=1
                for field in FIELDS:
                    if h[field]!=before[field]:
                        out[field+'_changes']+=1;out['changed_value_bytes']+=sizes[field]
        previous=health
    # Optimistic health-only bound: no session/sequence/CRC/keyframe expense.
    out['ideal_changed_bytes_with_run_initialization']=out['changed_value_bytes']+out['initial_health_bytes']
    out['ideal_health_saving_without_bitmap']=out['raw_health_bytes']-out['ideal_changed_bytes_with_run_initialization']
    out['ideal_health_saving_with_one_bitmap_per_upload']=out['ideal_health_saving_without_bitmap']-out['uploads']
    return dict(out)


def grouped(rows, keys):
    groups=defaultdict(list)
    for row in rows:groups[tuple(row[k] for k in keys)].append(row)
    result=[]
    for key, group in sorted(groups.items()):
        r=dict(zip(keys,key));r['runs']=len(group)
        for field in group[0]:
            if field not in ('method','multiplier','seed','scenario'):
                r[field]=sum(x[field] for x in group)
        r['health_equal_pair_ratio']=r['health_equal_pairs']/r['health_pairs'] if r['health_pairs'] else None
        r['mean_health_bytes_per_upload']=r['raw_health_bytes']/r['uploads']
        for field in FIELDS:r[field+'_change_rate']=r[field+'_changes']/r['channel_pairs'] if r['channel_pairs'] else None
        result.append(r)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,default=ROOT/'results/traces/test')
    p.add_argument('--output',type=Path,default=ROOT/'results/wire-payload-v2/audit')
    args=p.parse_args();check(not args.output.exists(),'Output exists')
    manifest,selected=inputs();args.output.mkdir(parents=True)
    rows=[];verified={}
    for source in selected:
        relative=f"{source['seed']}/{source['scenario']}/{source['method']}-{float(source['multiplier']):g}.json.gz"
        result=read_archive(args.archive,relative,manifest,verified)
        envs=[envelope_from_record(r) for r in result['records'] if r['upload']]
        check(len(envs)==int(source['uploads']),'Upload count mismatch')
        rows.append({k:source[k] for k in ('method','multiplier','seed','scenario')}|health_statistics(envs))
    for name,items in [('per_run.csv',rows),('summary.csv',grouped(rows,('method','multiplier'))),('by_scenario.csv',grouped(rows,('method','multiplier','scenario')))]:write_csv(args.output/name,items)
    record=dict(base=BASE,scope='Health compressibility only, all original test seeds20-49 and native points',
                source_manifest_sha256=sha((ROOT/'results/test/manifest.json').read_bytes()),
                source_config_sha256=manifest['config_sha256'],verified_archives=len(verified),
                verified_archive_index_sha256=sha(canonical(verified)),
                output_sha256={p.name:sha(p.read_bytes()) for p in args.output.iterdir()})
    (args.output/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    for r in grouped(rows,('method','multiplier')):
        print({k:r[k] for k in ('method','multiplier','uploads','health_equal_pair_ratio','state_change_rate','score_change_rate','flags_change_rate','raw_health_bytes','changed_value_bytes','initial_health_bytes','ideal_health_saving_with_one_bitmap_per_upload')})

if __name__=='__main__':main()
