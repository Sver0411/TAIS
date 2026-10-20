#!/usr/bin/env python3
"""Verify publication revision against unchanged experimental evidence."""
import hashlib,json,re,subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/tais-paper-review';P=ROOT/'papers/tais'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
    """Require byte-exact protected files, then audit manuscript cells and cross-references.

    The protected set includes source, so annotation-only maintenance fails
    this historical guard. Preserve its records and diagnose that separately
    from numerical evidence integrity; never refresh frozen hashes to hide it."""
    protection=json.loads((OUT/'protection.json').read_text())
    for p,h in protection['protected_files'].items():assert sha(ROOT/p)==h,p
    delta=subprocess.check_output(['git','diff','--name-only',protection['base'],'--','src','configs','vendor','results/tais-paper','results/tais-transfer'],cwd=ROOT,text=True).splitlines();assert not delta,delta
    manifest=json.loads((OUT/'budget_sensitivity_manifest.json').read_text())
    for p,h in manifest['inputs'].items():assert sha(ROOT/p)==h
    assert sha(OUT/'budget_sensitivity.csv')==manifest['output_sha256']
    b=pd.read_csv(OUT/'budget_sensitivity.csv');assert len(b)==60
    for _,r in b.iterrows():
        gap=r.samples/r.target_samples-1;assert abs(gap-r.relative_gap)<1e-12
        for eps,col in [(.02,'within_2pct'),(.05,'within_5pct'),(.10,'within_10pct')]:assert bool(r[col])==(abs(gap)<=eps)
    audit=pd.read_csv(P/'tables/review_data_audit.csv')
    for path,g in audit.groupby('source'):
        source=pd.read_csv(ROOT/path)
        for _,r in g.iterrows():
            x=float(source.iloc[int(r.row_index)][r.metric]);y=float(r.value)
            assert (np.isnan(x) and np.isnan(y)) or abs(x-y)<=1e-12*max(1,abs(x))
    build=json.loads((OUT/'build_manifest.json').read_text())
    for p,h in build['inputs'].items():assert sha(ROOT/p)==h
    for p,h in build['generated_tex'].items():assert sha(P/'tables'/p)==h
    for p,h in build['figures'].items():assert sha(P/'figures'/p)==h
    files={}
    def read(path):
        path=path.resolve()
        if path in files:return
        text=path.read_text();files[path]=text
        for name in re.findall(r'\\input\{([^}]+)\}',text):read(P/(name if name.endswith('.tex') else name+'.tex'))
    read(P/'manuscript.tex');alltex='\n'.join(files.values());labels=re.findall(r'\\label\{([^}]+)\}',alltex);refs=re.findall(r'\\ref\{([^}]+)\}',alltex)
    assert len(set(labels))==len(labels),'Duplicate labels';assert not set(refs)-set(labels),(set(refs)-set(labels))
    graphics=re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',alltex)
    for name in graphics:
        path=P/name;assert path.is_file() and path.stat().st_size>1000,name
        a=np.asarray(Image.open(path).convert('L'));assert a.std()>5,'Blank figure: '+name
    abstract=(P/'tables/review_abstract.tex').read_text();words=len(abstract.replace('\\%','%').split());assert 150<=words<=220
    assert 'ground-truth interval definitions' in abstract and 'includes zero' in abstract
    assert 'post-outcome editorial choice' in alltex and 'pointwise, unadjusted' in alltex
    assert 'SU40 failed to generalize due to distribution shift' not in alltex
    assert 'Author names and affiliations to be supplied before submission' in alltex
    pdf=OUT/'pdf-validation.json'
    if pdf.exists():
        q=json.loads(pdf.read_text());assert sha(P/'manuscript.pdf')==q['pdf_sha256']
        for p,h in q['source_sha256'].items():assert sha(ROOT/p)==h
    result=dict(status='PASS',protected_source_config_result_files=len(protection['protected_files']),budget_pairs=len(b),audited_review_cells=len(audit),abstract_words=words,referenced_figures=len(graphics)+1,tikz_architecture=True,tex_input_files=len(files),labels=len(labels),references=len(refs),new_simulation_campaign=False)
    print(json.dumps(result,indent=2));return result
if __name__=='__main__':verify()
