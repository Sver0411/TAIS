#!/usr/bin/env python3
"""Inventory accessible seed-bearing historical artifacts before allocating a split."""
from pathlib import Path
import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import yaml

ROOT=Path(__file__).resolve().parents[1]
BASE='97feccb36acb6790b40be31e3cee1661e8811a61'
SEED_KEY=re.compile(r'(^seed$|seeds$|random_seed$|bootstrap_seed$|link_seed$)',re.I)


def extract(obj):
    out=set()
    def values(v):
        if type(v) is int:out.add(v)
        elif isinstance(v,list):
            for item in v:values(item)
        elif isinstance(v,dict):
            for item in v.values():values(item)
    def walk(v):
        if isinstance(v,dict):
            for k,item in v.items():
                if SEED_KEY.search(str(k)):values(item)
                else:walk(item)
        elif isinstance(v,list):
            for item in v:walk(item)
    walk(obj)
    return out


def parse_text(data,suffix):
    if suffix=='.json':return extract(json.loads(data))
    if suffix in ('.yaml','.yml'):return extract(yaml.safe_load(data))
    if suffix=='.csv':
        reader=csv.DictReader(io.StringIO(data));fields=[k for k in (reader.fieldnames or []) if SEED_KEY.search(k)]
        if not fields:return set()
        found=set()
        for row in reader:
            for field in fields:
                value=row.get(field,'')
                if value and re.fullmatch(r'\d+',value):found.add(int(value))
        return found
    return set()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'results/budget-matched/seed-audit.json')
    args=p.parse_args()
    if args.output.exists():raise FileExistsError('Never overwrite an audit')
    inventory=[];used=set(range(150));errors=[];scanned=0;gzip_paths=set();raw_signatures=[]
    roots=[ROOT,Path('/Users/mac/Documents/TAIS-external-data')]
    for root in roots:
        if not root.exists():continue
        for parent,dirs,names in os.walk(root):
            dirs[:]=[d for d in dirs if d not in ('.git','.venv','__pycache__','build','node_modules')]
            for name in names:
                path=Path(parent)/name
                # All current gzip paths are inventoried; numeric archive paths identify seed scope.
                if name.endswith('.gz'):
                    rel=str(path.relative_to(root));gzip_paths.add(rel)
                    matches=re.findall(r'(?:^|/)(\d+)(?:/|[-_])',rel)
                    seeds={int(x) for x in matches}
                    if seeds:
                        used.update(seeds);inventory.append(dict(source=str(path),kind='archive_path',seeds=sorted(seeds)))
                suffix=path.suffix
                if suffix in ('.xlsx','.zip','.tar','.bz2') or name in ('data.txt','data.txt.gz'):
                    st=path.stat();raw_signatures.append(dict(path=str(path),bytes=st.st_size,mtime_ns=st.st_mtime_ns))
                try:
                    if suffix in ('.json','.yaml','.yml','.csv'):
                        data=path.read_bytes();seeds=parse_text(data.decode('utf-8-sig'),suffix);scanned+=1
                    elif name.endswith('.csv.gz'):
                        data=gzip.decompress(path.read_bytes());seeds=parse_text(data.decode('utf-8-sig'),'.csv');scanned+=1
                    elif name.endswith('.jsonl.gz'):
                        seeds=set();h=hashlib.sha256()
                        with gzip.open(path,'rb') as f:
                            for line in f:
                                h.update(line)
                                # Complete contexts, no interpretation of numeric sensor samples as seeds.
                                for x in re.findall(rb'"(?:seed|link_seed)":\s*(\d+)',line):seeds.add(int(x))
                        data=None;scanned+=1
                    else:continue
                    if seeds:
                        used.update(seeds);inventory.append(dict(source=str(path),kind='filesystem',seeds=sorted(seeds),sha256=hashlib.sha256(data).hexdigest() if data is not None else h.hexdigest()))
                except (ValueError,UnicodeError,OSError) as exc:
                    errors.append(dict(path=str(path),error=str(exc)))
    # Inspect historical blobs, including deleted/replaced artifacts, across every local/ref history.
    objects=subprocess.check_output(['git','rev-list','--all','--objects','--','results','configs','src','scripts','tests','docs'],cwd=ROOT,text=True)
    git_blobs=0
    for line in objects.splitlines():
        bits=line.split(' ',1)
        if len(bits)!=2:continue
        oid,path=bits;suffix=Path(path).suffix
        if suffix not in ('.json','.yaml','.yml','.csv'):continue
        data=subprocess.check_output(['git','cat-file','blob',oid],cwd=ROOT)
        try:seeds=parse_text(data.decode('utf-8-sig'),suffix)
        except (ValueError,UnicodeError) as exc:
            errors.append(dict(path='git:'+oid+':'+path,error=str(exc)));continue
        git_blobs+=1
        if seeds:
            used.update(seeds);inventory.append(dict(source='git:'+oid+':'+path,kind='historical_blob',seeds=sorted(seeds)))
    candidate=150
    while any(seed in used for seed in range(candidate,candidate+50)):candidate+=50
    proposed=dict(development=list(range(candidate,candidate+10)),validation=list(range(candidate+10,candidate+20)),test=list(range(candidate+20,candidate+50)))
    result=dict(base=BASE,status='PASS' if not errors else 'REVIEW_REQUIRED',scope_roots=list(map(str,roots)),
        previous_0_149_reserved=True,structured_files_scanned=scanned,historical_blobs_scanned=git_blobs,
        gzip_paths_inventoried=len(gzip_paths),gzip_path_inventory_sha256=hashlib.sha256('\n'.join(sorted(gzip_paths)).encode()).hexdigest(),
        all_observed_seed_values=sorted(used),proposed_150_199_collisions=sorted(set(range(150,200))&used),allocated=proposed,
        inventory=inventory,raw_file_stat_signatures=raw_signatures,errors=errors,
        limitations='Accessible local repository, all Git object histories/refs and TAIS-external-data only; cannot audit inaccessible external runs. Numeric observations/row indices are not experiment seeds. Gzip scenario archives use pinned directory/file seed identities; gzip CSV and link JSONL metadata were read. Raw real-data workbooks are not synthetic seed runs.',
        supplementary_source_review='rg reviewed seed/generate references in current scripts/src/tests/config/docs; no executed150-199 synthetic run found. Documentation mentioning150 as a future possibility is not proof of use.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print({k:v for k,v in result.items() if k not in ('inventory','raw_file_stat_signatures','all_observed_seed_values')})
    if errors:raise SystemExit('Audit parse/read errors require resolution before a seed freeze')

if __name__=='__main__':main()
