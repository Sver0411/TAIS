#!/usr/bin/env python3
"""Read-only manuscript provenance, citation and generated-cell checks."""
from pathlib import Path
import hashlib,json,re
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'papers/tais'
source=json.loads((P/'tables/source_fingerprints.json').read_text())
for name,h in source.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h
tex=(P/'manuscript.tex').read_text();bib=(P/'references.bib').read_text()
cited={k.strip() for x in re.findall(r'\\cite[pt]?\{([^}]+)\}',tex) for k in x.split(',')}
keys=set(re.findall(r'@\w+\{([^,]+),',bib));assert cited==keys,(cited,keys)
audit=json.loads((ROOT/'results/tais-paper/literature/audit.json').read_text());assert {r['key'] for r in audit}==keys
for r in audit:
 p=ROOT/'results/tais-paper/literature'/(r['key']+'.json');assert hashlib.sha256(p.read_bytes()).hexdigest()==r['metadata_sha256']
 assert json.loads(p.read_text())['message']['DOI'].lower()==r['doi'].lower()
s=pd.read_csv(ROOT/'results/tais-paper/test/analysis/summary.csv');a=pd.read_csv(P/'tables/data_audit.csv')
count=0
for _,r in a.iterrows():
 if r.metric.endswith('_ci'):continue
 found=s[(s.method==r.method)&(s['view']==r['view'])&(s.group==r.group)]
 assert len(found)==1
 x=found.iloc[0][r.metric];v=float(r.value)
 assert (pd.isna(x) and pd.isna(v)) or abs(x-v)<=1e-9*max(1,abs(x))
 count+=1
pd.testing.assert_frame_equal(pd.read_csv(P/'tables/budget_data_audit.csv'),pd.read_csv(ROOT/'results/tais-paper/test/analysis/budget_comparisons.csv'))
assert (P/'manuscript.pdf').stat().st_size>10000
print(json.dumps(dict(status='PASS',cited_references=len(keys),summary_cells_checked=count,source_fingerprints=len(source),pdf_present=True),indent=2))
