"""Check frozen sources, numerical transcription, scope, links, and PDF structure.

No policy, simulation, bootstrap, parameter search, or dataset preprocessing runs.
Use a document environment containing pypdf, Pillow and reportlab.
"""
import argparse
from collections import defaultdict
import csv
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import subprocess
from xml.etree import ElementTree

from PIL import Image
from pypdf import PdfReader
from reportlab.pdfbase.ttfonts import TTFont

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE="f21bc2f0e1d01d0670ce1c1bd4ab5a2aab7e171d"


def table(path):
    with (ROOT/path).open() as f: return list(csv.DictReader(f))


def one(path, **selection):
    rows=[r for r in table(path) if all((float(r[k])==v if isinstance(v,(float,int)) else r[k]==v) for k,v in selection.items())]
    assert len(rows)==1,(path,selection,len(rows))
    return rows[0]


def aggregate(raw_path, summary_paths):
    totals=defaultdict(lambda:defaultdict(int))
    columns=["tp","n_events","missed","false_reports","fault_induced_false","samples","uploads","payload_bytes"]
    for row in table(raw_path):
        key=(row.get("suite","main"),row["method"],float(row["multiplier"]))
        for c in columns:totals[key][c]+=int(row[c])
    n=0
    for suite,path in summary_paths.items():
        for row in table(path):
            key=(suite,row["method"],float(row["multiplier"]))
            for c in columns:assert totals[key][c]==int(row[c]),(path,key,c)
            n+=1
    return n


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--visual-review-complete",action="store_true",help="Only after actually viewing every final page image")
    args=parser.parse_args()
    manifest=json.loads((HERE/"SOURCE_MANIFEST.json").read_text())
    for p,sha in manifest["sources_sha256"].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha,p
    protected=0;upstream=[]
    for entry in subprocess.check_output(["git","ls-tree","-rz",BASE],cwd=ROOT).split(b"\0"):
        if not entry:continue
        meta,p=entry.decode().split("\t");mode,kind,sha=meta.split()
        if kind=="commit":
            current=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT/p).decode().strip()
            assert current==sha;assert not subprocess.check_output(["git","status","--porcelain"],cwd=ROOT/p).strip()
            upstream.append({"path":p,"sha":sha})
        elif p!="README.md":
            b=(ROOT/p).read_bytes()
            assert hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()==sha,p
            protected+=1
    changes=subprocess.check_output(["git","status","--porcelain","-z"],cwd=ROOT).decode().split("\0")
    for entry in filter(None,changes):
        p=entry[3:]
        assert p=="README.md" or p.startswith("docs/research-portfolio/"),entry
    summary_rows=aggregate("results/test/metrics.csv",{"main":"results/test/summary.csv"})
    summary_rows+=aggregate("results/v0.2/test/metrics.csv",{"main":"results/v0.2/test/summary.csv"})
    summary_rows+=aggregate("results/blocked-rearm/test/metrics.csv",{
        "main":"results/blocked-rearm/test/main/summary.csv",
        "aligned_recovery":"results/blocked-rearm/test/aligned_recovery/summary.csv"})
    a=one("results/test/summary.csv",method="AdaptiveSense",multiplier=1)
    t=one("results/test/summary.csv",method="TAIS",multiplier=1)
    assert int(a["tp"])==int(t["tp"])==464
    assert int(a["fault_induced_false"])==652 and int(t["fault_induced_false"])==458
    assert round((int(t["payload_bytes"])/int(a["payload_bytes"])-1)*100,2)==60.04
    r=one("results/blocked-rearm/test/main/summary.csv",method="V02-Rearm",multiplier=1)
    old=one("results/blocked-rearm/test/main/summary.csv",method="V02",multiplier=1)
    assert int(old["tp"])==450 and int(r["tp"])==454
    gates={}
    for split in ["development","validation","test"]:
        gates[split]=json.loads((ROOT/f"results/offline-spatial-pilot/{split}/gate.json").read_text())
    assert not gates["test"]["coverage_pass"]
    assert round(gates["test"]["mean_target_coverage"]*100,2)==25.89
    assert round(gates["test"]["mean_reference_quorum_coverage"]*100,2)==24.12
    with gzip.open(ROOT/"results/v0.2/forensics/stable_offset_none_long-TAIS.json.gz","rt") as f:d=json.load(f)
    assert not d["trace"]["events"]
    assert all(r["health"]["temperature"]["state"]=="HEALTHY" for r in d["result"]["records"])
    assert [r["start_s"] for r in d["result"]["reports"]]==[610,1205]
    for name,detected in [("V02",False),("V02-Rearm",True)]:
        with gzip.open(ROOT/f"results/blocked-rearm/diagnosis/{name}.json.gz","rt") as f:d=json.load(f)
        assert any(p["start_s"]==675 for p in d["result"]["reports"])==detected
    checked_links=0
    for p in HERE.glob("*.md"):
        for url in re.findall(r"\]\(([^)]+)\)",p.read_text()):
            if re.match(r"[a-z]+:",url):continue
            path=url.split("#")[0]
            destination=(p.parent/path).resolve()
            assert destination.exists() or destination==HERE/"DOCUMENT_CHECKS.json",(p,url)
            checked_links+=1
    png=list((HERE/"figures").glob("*.png"));svg=list((HERE/"figures").glob("*.svg"))
    assert len(png)==len(svg)==8
    for p in png:
        with Image.open(p) as im:
            # Tight-cropped schematics can be <2000 px at true 300-dpi export.
            # Check declared export and effective full-width A4 print density.
            assert min(im.info["dpi"])>=299
            assert im.width/(174/25.4)>=250 and im.height>600
    for p in svg:ElementTree.parse(p)
    pdfs={}
    standard={"Helvetica","Times-Roman","Courier","Symbol","ZapfDingbats"}
    for name in ["RESEARCH_SUMMARY_JA","TECHNICAL_REPORT_EN"]:
        p=HERE/(name+".pdf");doc=PdfReader(p);jp=name.endswith("JA")
        assert len(doc.pages)==2 if jp else 6<=len(doc.pages)<=10
        links=0;embedded=set();text=""
        for page in doc.pages:
            assert abs(float(page.mediabox.width)-595.2756)<.1
            assert abs(float(page.mediabox.height)-841.8898)<.1
            content=page.extract_text();assert len(content)>150
            assert "\ufffd" not in content and "\u25a0" not in content
            text+=content
            links+=sum(a.get_object().get("/Subtype")=="/Link" for a in page.get("/Annots",[]))
            for font_ref in page["/Resources"]["/Font"].values():
                font=font_ref.get_object();base=str(font["/BaseFont"]).lstrip("/")
                if base in standard:continue
                descriptor=font.get("/FontDescriptor")
                assert descriptor is not None,base
                descriptor=descriptor.get_object()
                assert any(k in descriptor for k in ["/FontFile","/FontFile2","/FontFile3"]),base
                embedded.add(base)
        assert links>0 and len(doc.outline)>0
        assert "25.89" in text and "24.12" in text
        pdfs[p.name]={"pages":len(doc.pages),"live_links":links,"embedded_fonts":sorted(embedded),
                      "a4":True,"replacement_or_tofu_characters":False,
                      "sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
    # Full Japanese text coverage, not only a successful PDF parse.
    import os
    face=TTFont("coverage",os.environ.get("TAIS_JA_FONT","/System/Library/Fonts/Supplemental/Arial Unicode.ttf")).face
    japanese=(HERE/"RESEARCH_SUMMARY_JA.md").read_text()
    missing=sorted({c for c in japanese if ord(c)>127 and ord(c) not in face.charToGlyph})
    assert not missing,missing
    from render_reports import fonts, FALLBACK_SYMBOLS
    fonts()  # Includes all non-ASCII English glyphs and the actual fallback face.
    raw=[];external=ROOT.parent/"TAIS-external-data"
    c0=external/"C0-20261018/C0_MANIFEST.json"
    if c0.exists():
        for item in json.loads(c0.read_text())["original_files"]:
            p=Path(item["file"]);assert hashlib.sha256(p.read_bytes()).hexdigest()==item["sha256"]
            raw.append({"file":p.name,"sha256":item["sha256"]})
    workbook=external/"C1_1-20261018-evidence/A-raw/Greenhouse-1.xlsx"
    if workbook.exists():
        sha=hashlib.sha256(workbook.read_bytes()).hexdigest()
        assert sha=="9b5f48b5f37ebc90052658649de7471b298da7dd4581bf47d0d8ec404cadff19"
        raw.append({"file":workbook.name,"sha256":sha})
    workbook2=external/"C1_1-20261018-evidence/A-raw/Greenhouse-2.xlsx"
    if workbook2.exists():
        sha=hashlib.sha256(workbook2.read_bytes()).hexdigest()
        assert sha=="82a882d0dce0044458c1ac3d787b62c9434fbce48f2ebaa3c55d9330e6c810eb"
        raw.append({"file":workbook2.name,"sha256":sha})
    for arguments in [["git","diff","--check"],["git","diff","--cached","--check"]]:
        checked=subprocess.run(arguments,cwd=ROOT,capture_output=True,text=True)
        assert checked.returncode==0,(checked.stdout+checked.stderr)[:500]
    result={"status":"PASS","base_commit":BASE,"unchanged_existing_files_except_readme":protected,
            "upstream":upstream,"source_hashes_verified":len(manifest["sources_sha256"]),
            "raw_metric_summary_rows_reconciled":summary_rows,"central_numeric_and_failure_assertions":"PASS",
            "local_markdown_links_checked":checked_links,"figures":{"svg":len(svg),"png_300dpi":len(png)},
            "pdf":pdfs,"japanese_font_full_text_coverage":"PASS","original_external_files_verified":raw,
            "english_full_text_glyph_coverage":"PASS_WITH_EMBEDDED_FALLBACK",
            "inline_fallback_symbols":sorted(FALLBACK_SYMBOLS),
            "svg_xml_valid":True,"git_whitespace_check":"PASS; PDF/PNG marked binary",
            "final_page_images_visually_reviewed":args.visual_review_complete,
            "effect_experiments_or_parameter_search_run":False,"ci_for_this_document_branch":"SKIPPED_BY_COMMIT_MESSAGE",
            "python":platform.python_version(),"packages":{p:importlib.metadata.version(p) for p in ["reportlab","pypdf","Pillow"]}}
    (HERE/"DOCUMENT_CHECKS.json").write_text(json.dumps(result,indent=2)+"\n")
    assert (HERE/"DOCUMENT_CHECKS.json").exists()
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
