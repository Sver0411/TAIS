#!/usr/bin/env python3
"""Recompute actual integration journals and protect frozen history; no policy run."""
from collections import Counter
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from tais.wire_codec import encode, envelope_from_record
from tais.budget_eval import sha
from verify_independent_reference_budget import history

BASE = '2ea17b39a502e32136333b0987d72c613cccbd70'
DEST = ROOT/'results/tais-core'


def verify_run(path):
    """Recompute recorded frames, byte totals and receiver outcomes from a saved journal.

    Require the exact source bytes recorded by that run, including comments.
    A source-hash mismatch is a provenance difference, not a metric comparison."""
    manifest=json.loads((path/'manifest.json').read_text())
    for rel,digest in manifest['source_sha256'].items():
        assert sha(ROOT/rel)==digest, rel
    summary=json.loads((path/'summary.json').read_text())
    assert summary['status']=='COMPLETE' and sha(path/'journal.jsonl')==summary['journal_sha256']
    records=[];tx={};rx=[];source=0;drops=[];invalid=[]
    for text in (path/'journal.jsonl').open():
        e=json.loads(text)
        if e['kind']=='source':source+=1
        elif e['kind']=='sample':records.append(e['record'])
        elif e['kind']=='tx':tx[e['harness_tx_id']]=e
        elif e['kind']=='rx':rx.append(e)
        elif e['kind']=='link_drop':drops.append(e['harness_tx_id'])
        elif e['kind']=='link_corrupt':invalid.append(e['harness_tx_id'])
    layout=manifest['layout']['layout_id']
    recomputed=[encode(envelope_from_record(r,layout),layout) for r in records if r['upload']]
    assert [bytes.fromhex(e['frame_hex']) for e in tx.values()]==recomputed
    assert all(len(bytes.fromhex(e['frame_hex']))==e['frame_bytes'] for e in tx.values())
    assert len(records)==summary['sender']['samples'] and source==summary['sender']['source_rows']
    assert sum(map(len,recomputed))==summary['sender']['binary_bytes']==summary['link']['sent_bytes']
    assert len(tx)==summary['sender']['uploads']==summary['link']['sent']
    assert len(drops)==summary['link']['dropped'] and len(invalid)==summary['link']['altered']
    assert set(tx)-set(drops)=={e['harness_tx_id'] for e in rx}
    latest=-1;updates=0
    for e in rx:
        if e['envelope'] is None:
            assert e['harness_tx_id'] in invalid and e['status']=='invalid'
        else:
            assert encode(e['envelope'],layout)==bytes.fromhex(tx[e['harness_tx_id']]['frame_hex'])
            t=e['envelope']['timestamp']
            if t>latest:
                assert e['status']=='updated';latest=t;updates+=1
            else:assert e['status']=='out_of_order'
    assert updates==summary['receiver']['updates']
    assert len(rx)==summary['receiver']['received']
    assert sum(e['envelope'] is not None for e in rx)==summary['receiver']['decoded']
    return dict(run=path.name,source_rows=source,samples=len(records),uploads=len(tx),
                binary_bytes=sum(map(len,recomputed)),received=len(rx),
                decoded=summary['receiver']['decoded'],dropped=len(drops),invalid=len(invalid),
                all_valid_received_exact=True,all_tx_sizes_recomputed=True,
                frozen_gateonly_parity=summary.get('verification',{}).get('frozen_gateonly_records_and_reports_identical'))


def protect():
    """Compare inherited tracked blobs, vendor commits and local archives byte for byte.

    This historical freeze deliberately rejects annotation-only source edits too;
    it does not distinguish source equivalence from original source identity."""
    files=0;submodules=0
    for entry in subprocess.check_output(['git','ls-tree','-rz',BASE],cwd=ROOT).split(b'\0'):
        if not entry:continue
        info,name=entry.split(b'\t');mode,kind,oid=info.split();path=ROOT/name.decode()
        if kind==b'commit':
            assert subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD']).strip()==oid
            assert not subprocess.check_output(['git','-C',str(path),'status','--porcelain']).strip()
            submodules+=1
        else:
            data=path.read_bytes()
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest().encode()==oid,path
            files+=1
    before_irb=history()
    artifacts=chunks=0
    for phase in ('calibrate','development','validation','test'):
        root=ROOT/'results/independent-reference-budget'/phase
        manifest=json.loads((root/'manifest.json').read_text());archive=Path(manifest['archive_root'])
        for rel,digest in manifest['artifacts'].items():
            assert sha(archive/rel)==digest,rel
            artifacts+=1
        # Preserve per-seed scratch CSVs too, using the frozen combined tables.
        for filename in manifest['csv_sha256']:
            with (root/filename).open(newline='') as f:
                reader=csv.DictReader(f)
                for seed,rows in itertools.groupby(reader,key=lambda r:r['seed']):
                    buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=reader.fieldnames)
                    writer.writeheader();writer.writerows(rows)
                    assert (archive/seed/filename).read_bytes()==buffer.getvalue().encode(),(phase,seed,filename)
                    chunks+=1
    return dict(base=BASE,all_original_tracked_files_unchanged=files,unchanged_submodules=submodules,
                pre_irb_history=before_irb,irb_gzip_artifacts_unchanged=artifacts,
                irb_seed_csv_chunks_unchanged=chunks)


def main():
    runs=[verify_run(p) for p in sorted((DEST/'acceptance').iterdir())
          if (p/'journal.jsonl').exists()]
    expected=json.loads((DEST/'acceptance/fault-event/summary.json').read_text())
    standalone=json.loads((DEST/'acceptance/standalone-receiver/summary.json').read_text())
    assert standalone['receiver']==expected['receiver']
    reviewed=json.loads((DEST/'bm1-review/manifest.json').read_text())
    for name,digest in reviewed['outputs'].items():assert sha(DEST/'bm1-review'/name)==digest
    for rel,digest in reviewed['source_sha256'].items():assert sha(ROOT/rel)==digest
    result=dict(status='PASS',acceptance_runs=runs,standalone_receiver_matches=True,
                historical_review_runs=reviewed['runs'],historical_review_frames=reviewed['uploads'],
                history=protect(),no_policy_or_final_research_rerun=True)
    with (DEST/'checks/delivery-verification.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
