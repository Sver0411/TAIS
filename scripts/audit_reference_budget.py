#!/usr/bin/env python3
"""Reuse the complete FO-1 inventory engine, then reserve0–299 for IRB-1."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import audit_observability_seeds as audit

def main():
    audit.BASE='89aa8341181aa42791f9a4de80739bb7c10fa9e5'
    audit.OUT=audit.ROOT/'results/independent-reference-budget'
    audit.RAW=audit.ROOT/'results/traces/independent-reference-budget'
    with redirect_stdout(StringIO()):audit.main()
    p=audit.OUT/'seed-audit.json';d=json.loads(p.read_text())
    used=set(d['all_observed_seed_values'])
    if not set(range(300))<=used:raise ValueError('Previous0–299 reservation was not fully audited')
    d['reserved_0_299']=True
    d['proposed_300_399_collisions']=sorted(set(range(300,400))&used)
    d['audit_engine_sha256']=audit.sha(Path(audit.__file__))
    d.pop('reserved_0_199');d.pop('proposed_200_299_collisions')
    p.write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps({k:v for k,v in d.items() if k in ('base','status','structured_files','historical_blobs','gzip_paths','proposed_300_399_collisions','allocated')},indent=2))
if __name__=='__main__':main()
