#!/usr/bin/env python3
"""Independently reconcile complete generated event logs and protected history."""
from pathlib import Path
from collections import Counter, defaultdict
import argparse
import csv
import gzip
import hashlib
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from tais.wire_v2 import Receiver


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,default=ROOT/'results/wire-payload-v2/test')
    parser.add_argument('--trace',type=Path,help='Optional relocated log; still must match frozen hash')
    parser.add_argument('--output',type=Path,default=ROOT/'results/wire-payload-v2/checks/result_verification.json')
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError('Verification output exists')
    m=json.loads((args.results/'manifest.json').read_text())
    old=json.loads((ROOT/'results/wire-payload/test/manifest.json').read_text())
    assert m['verified_archive_index_sha256']==old['verified_archive_index_sha256']
    for name,digest in m['outputs'].items():assert sha(args.results/name)==digest,name
    for section in ('source_files','implementation_files'):
        for name,digest in m[section].items():assert sha(ROOT/name)==digest,name
    path=args.trace or Path(m['full_trace']['path'])
    assert sha(path)==m['full_trace']['sha256'],'Full trace hash mismatch'
    expected={(r['method'],float(r['multiplier']),int(r['period']),r['profile']):r for r in csv.DictReader((args.results/'summary.csv').open())}
    count=0;groups=defaultdict(Counter);replayed=0
    with gzip.open(path,'rt') as f:
        header=json.loads(next(f));assert tuple(header['columns'])==tuple(m['event_columns'])
        for line in f:
            batch=json.loads(line);ctx=batch['identity'];key=ctx['method'],ctx['multiplier'],batch['period'],batch['profile']
            sample=ctx['seed']==20 and ctx['scenario'] in ('spike_same_short','clean_none','range_same_long')
            receiver=Receiver() if sample else None
            for row in batch['events']:
                assert len(row)==len(header['columns'])
                index,t,dev,session,seq,kind,b1,b2,action,status,gap,recovered,ehash,wirehex=row
                assert len(wirehex)==2*b2
                count+=1;g=groups[key];g['sent']+=1;g['v1_bytes']+=b1;g['v2_bytes']+=b2
                g['dropped']+=action=='DROP';g['v2_decoded']+=ehash is not None
                g['received_unrestored']+=action=='RECEIVE' and ehash is None
                if sample:
                    if batch['profile']=='receiver_restart' and index==20:receiver.reset()
                    if action=='RECEIVE':
                        r=receiver.receive(bytes.fromhex(wirehex));replayed+=1
                        assert (r.device_id,r.session_id,r.sequence,r.keyframe)==(dev,session,seq,kind=='K')
                        assert (r.status,r.gap,r.recovered)==(status,gap,recovered)
                        if r.envelope is None:assert ehash is None
                        else:
                            payload=json.dumps(r.envelope,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
                            assert hashlib.sha256(payload).hexdigest()==ehash
    assert count==m['full_trace']['events']==8047116
    for key,total in groups.items():
        for field,value in total.items():assert value==int(expected[key][field]),(key,field,value,expected[key][field])
    proof=json.loads((ROOT/'results/wire-payload-v2/checks/scope_verification.json').read_text())
    for path,digest in proof['baseline_file_sha256'].items():assert sha(ROOT/path)==digest,path
    for path in [ROOT/'docs/WIRE_PAYLOAD_V2.md',ROOT/'results/wire-payload-v2/README.md']:
        for label,link in re.findall(r'!?\[([^\]]*)\]\(([^)]+)\)',path.read_text()):
            if not link.startswith(('https:','http:','#')):assert (path.parent/link.split('#')[0]).exists(),link
    result=dict(all_output_source_implementation_hashes_match=True,archive_index_identical_to_v1=True,
                full_gzip_trace_events_checked=count,all_trace_group_counts_and_bytes_reconcile=True,
                independently_replayed_received_frames=replayed,independent_replay_all_statuses_and_envelope_hashes_match=True,
                protected_baseline_files_rechecked=len(proof['baseline_file_sha256']),all_relative_document_links_valid=True,
                verifier_sha256=sha(Path(__file__)))
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
