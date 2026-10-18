"""Read frozen research artifacts and redraw portfolio figures; no replay or fitting.

Run from the repository root: .venv/bin/python docs/research-portfolio/build_figures.py
"""
from pathlib import Path
import gzip
import hashlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "figures"
BASE = "f21bc2f0e1d01d0670ce1c1bd4ab5a2aab7e171d"
SOURCES = set()
COLORS = ["#36566f", "#c07a18", "#16806a", "#865c9e"]
HATCH = ["", "//", "..", "xx"]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "svg.fonttype": "none", "savefig.facecolor": "white"})


def read(path):
    SOURCES.add(path)
    return pd.read_csv(ROOT/path, na_values="N/A")


def js(path):
    SOURCES.add(path)
    p = ROOT/path
    with (gzip.open(p, "rt") if p.suffix == ".gz" else p.open()) as f:
        return json.load(f)


def save(fig, name):
    OUT.mkdir(exist_ok=True)
    svg=OUT/(name+".svg")
    fig.savefig(svg, bbox_inches="tight")
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
    fig.savefig(OUT/(name+".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def box(ax, x, y, w, h, text, color="#eef3f6", dashed=False, size=8.5):
    patch = FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.01,rounding_size=0.02",
                          ec="#5a6b76", fc=color, lw=1, linestyle="--" if dashed else "-")
    ax.add_patch(patch); ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=size)


def arrow(ax, a, b):
    ax.annotate("",xy=b,xytext=a,arrowprops=dict(arrowstyle="->",lw=1,color="#455a64"))


def diagrams():
    for p in ["src/tais/scheduler.py","src/tais/trust.py","src/tais/trust_bridge.c",
              "src/tais_v02/evidence.py","src/tais_rearm/evidence.py",
              "src/tais_spatial/methods.py","src/tais/replay.py","src/tais/metrics.py"]:
        SOURCES.add(p)
    fig,ax=plt.subplots(figsize=(8.2,3.3)); ax.set(xlim=(0,1),ylim=(0,1));ax.axis("off")
    fig.subplots_adjust(left=.01,right=.99,bottom=.02,top=.98)
    ax.text(.01,.98,"Implemented research paths (schematic)",weight="bold",va="top",fontsize=11)
    box(ax,.01,.56,.18,.27,"Synthetic signals\n+ independent\nevent / fault labels")
    box(ax,.25,.56,.20,.27,"Scheduled samples\nC11 health +\nchange scores")
    box(ax,.51,.56,.21,.27,"TAIS channel policy\nv0.1 / v0.2 /\noptional Rearm")
    box(ax,.78,.56,.20,.27,"Shared sampling\n+ upload requests\n5-60 s bounds")
    for a,b in [((.19,.69),(.25,.69)),((.45,.69),(.51,.69)),((.72,.69),(.78,.69))]: arrow(ax,a,b)
    box(ax,.01,.12,.18,.26,"Greenhouse-1\nreal background\n+ controlled copies",color="#f3f0f7")
    box(ax,.25,.12,.47,.26,"OSP-1: separate offline information experiment\nFixed 10-min history / spatial / null comparisons\nAssumed proxy clock; separate from TAIS",color="#f3f0f7",dashed=True)
    box(ax,.78,.12,.20,.26,"Separate evaluation\ncoverage + recall\n+ modeled costs",color="#f3f0f7")
    arrow(ax,(.19,.25),(.25,.25)); arrow(ax,(.72,.25),(.78,.25))
    ax.text(.5,.46,"Labels are evaluator inputs; they never enter either detector.",ha="center",fontsize=9)
    save(fig,"fig01_research_framework")
    fig,ax=plt.subplots(figsize=(8.2,3.5));ax.set(xlim=(0,1),ylim=(0,1));ax.axis("off")
    fig.subplots_adjust(left=.01,right=.99,bottom=.02,top=.98)
    box(ax,.01,.35,.16,.34,"Sampled channel\n(time, value,\nvalidity)")
    box(ax,.23,.62,.25,.27,"SensorTrust, pinned C11\nctypes / opaque context\nHEALTHY / DEGRADED\n/ FAULT")
    box(ax,.23,.18,.25,.25,"AdaptiveSense primitives\nPer-channel EMA / STD / ROC\nscore, debounce, ladder",size=8.2)
    arrow(ax,(.17,.60),(.23,.75));arrow(ax,(.17,.43),(.23,.30))
    box(ax,.55,.32,.22,.36,"TAIS integration\nChannel health gate\nCandidate lifecycle\nRecovery baseline reset")
    arrow(ax,(.48,.75),(.55,.58));arrow(ax,(.48,.30),(.55,.42))
    box(ax,.83,.32,.16,.36,"Shared minimum\ninterval +\nheartbeat / health /\nevent uploads")
    arrow(ax,(.77,.50),(.83,.50))
    ax.text(.50,.97,"Health evidence and environmental change are different quantities.",ha="center",fontsize=10,weight="bold")
    ax.text(.50,.02,"v0.2: bounded frozen-reference candidate; Rearm: narrow unconfirmed-return reset.\nNeither changes the upstream C core or score formula; health score is not a fault probability.",ha="center",va="bottom",fontsize=8)
    save(fig,"fig02_algorithm_interfaces")


def legacy_figures(facts):
    s=read("results/test/summary.csv"); r=read("results/test/by_relationship.csv")
    methods=["AdaptiveSense","GateOnly","TAIS"]
    point=s[s.multiplier.eq(1)&s.method.isin(methods)].set_index("method").loc[methods]
    assert point.loc["TAIS","tp"]==464 and point.loc["AdaptiveSense","fault_induced_false"]==652
    assert point.loc["TAIS","fault_induced_false"]==458
    facts["v01_default"] = json.loads(point.reset_index().to_json(orient="records"))
    facts["v01_payload_increase_percent"]=(point.loc["TAIS","payload_bytes"]/point.loc["AdaptiveSense","payload_bytes"]-1)*100
    facts["v01_relationships"] = json.loads(r[r.multiplier.eq(1)&r.method.isin(methods)].to_json(orient="records"))
    facts["v01_paired"] = json.loads(read("results/test/paired_bootstrap.csv").query("multiplier == 1").to_json(orient="records"))
    fig,axes=plt.subplots(1,2,figsize=(8.2,2.8),constrained_layout=True)
    for ax,metric,title in zip(axes,["recall","fault_induced_false"],["Reported-event recall (%)","Fault-attributed false reports (count)"]):
        vals=point[metric].to_numpy()*(100 if metric=="recall" else 1)
        for i,(v,c,h) in enumerate(zip(vals,COLORS,HATCH)):
            ax.bar(i,v,color=c,hatch=h,edgecolor="#333",width=.62)
            ax.text(i,v+(1.6 if metric=="recall" else 18),f"{v:.2f}" if metric=="recall" else f"{int(v)}",ha="center",fontsize=9)
        ax.set_xticks(range(3),methods); ax.set_title(title,fontsize=10)
        ax.set_ylim(0,100 if metric=="recall" else 780); ax.grid(axis="y",alpha=.15);ax.set_axisbelow(True)
    fig.suptitle("v0.1 test, seeds 20-49, multiplier 1: 900 labeled events / method",fontsize=10)
    save(fig,"fig03_v01_recall_fault_reports")
    fig,ax=plt.subplots(figsize=(8.2,2.8),constrained_layout=True)
    groups=["clean","same","cross"];x=np.arange(3)
    for j,method in enumerate(methods):
        d=r[r.multiplier.eq(1)&r.method.eq(method)].set_index("relationship").loc[groups]
        b=ax.bar(x+(j-1)*.24,d.recall*100,.23,label=method,color=COLORS[j],hatch=HATCH[j],edgecolor="#333")
        ax.bar_label(b,labels=[f"{v:.1f}" for v in d.recall*100],padding=2,fontsize=8)
    ax.set_xticks(x,["No-fault events\nn=60","Same-channel overlap\nn=360","Cross-channel overlap\nn=360"])
    ax.set(ylabel="Reported-event recall (%)",ylim=(0,90));ax.legend(ncol=3,fontsize=8,loc="upper center")
    ax.grid(axis="y",alpha=.15);ax.set_axisbelow(True)
    save(fig,"fig04_v01_event_strata")


def traces():
    d=js("results/v0.2/forensics/stable_offset_none_long-TAIS.json.gz")
    tr=d["trace"];rec=pd.DataFrame(d["result"]["records"])
    latent=pd.DataFrame(tr["latent"]);obs=pd.DataFrame(tr["observed"])
    fig,axes=plt.subplots(3,1,figsize=(8.2,3.9),sharex=True,constrained_layout=True,gridspec_kw={"height_ratios":[2,1,1]})
    for ax in axes:
        for f in tr["faults"]:ax.axvspan(f["start_s"],f["end_s"],color="#bb4a4a",alpha=.12)
        ax.grid(alpha=.15)
    axes[0].plot(obs.timestamp,obs.temperature,color="#777",lw=.7,label="Faulted observation (offline view)")
    axes[0].plot(latent.timestamp,latent.temperature,"--",color=COLORS[0],lw=1.4,label="Latent environment")
    axes[0].scatter(rec.t,[v["temperature"] for v in rec["values"]],s=10,marker="o",facecolors="none",edgecolors=COLORS[2],label="Actually sampled")
    for j,p in enumerate(d["result"]["reports"]):
        if p["channel"]=="temperature":axes[0].axvline(p["start_s"],color=COLORS[3],linestyle=":",label="Environment report" if j==0 else None)
    axes[0].set_ylabel("Temperature (C)");axes[0].legend(fontsize=7,ncol=2)
    axes[0].set_title("Archived failure: seed 20, stable_offset_none_long, TAIS v0.1, multiplier 1",fontsize=10)
    axes[1].plot(rec.t,[v["temperature"] for v in rec.scores],"o-",ms=2,color=COLORS[0]);axes[1].axhline(8,ls="--",color="#777")
    axes[1].set_ylabel("Used score")
    levels={"STABLE":0,"ACTIVE":1,"ALERT":2}
    axes[2].step(rec.t,[levels[v] for v in rec.state],where="post",color=COLORS[2]);axes[2].set_yticks([0,1,2],list(levels));axes[2].set_ylim(-.2,2.6)
    axes[2].text(100,.6,"C health remains HEALTHY; no true environment event",fontsize=8)
    axes[2].set(xlabel="Simulation time (s)",xlim=(0,1800))
    save(fig,"fig05_stable_offset_failure")
    before=js("results/blocked-rearm/diagnosis/V02.json.gz")
    after=js("results/blocked-rearm/diagnosis/V02-Rearm.json.gz")
    a=read("results/blocked-rearm/diagnosis/before-samples.csv");b=read("results/blocked-rearm/diagnosis/after-samples.csv")
    a=a[a.method.eq("V02")&a.channel.eq("temperature")];b=b[b.method.eq("V02-Rearm")&b.channel.eq("temperature")]
    fig,axes=plt.subplots(4,1,figsize=(8.2,4.7),sharex=True,constrained_layout=True,gridspec_kw={"height_ratios":[1.8,1,1,1]})
    tr=before["trace"];obs=pd.DataFrame(tr["observed"]);latent=pd.DataFrame(tr["latent"])
    for ax in axes:
        for e in tr["events"]:ax.axvspan(e["start_s"],e["end_s"],color=COLORS[2],alpha=.10)
        for f in tr["faults"]:ax.axvspan(f["start_s"],f["end_s"],color="#bb4a4a",alpha=.30)
        ax.axvline(605,color="#555",linestyle=":",lw=1);ax.grid(alpha=.15)
    axes[0].plot(obs.timestamp,obs.temperature,color="#888",lw=.8,label="Faulted")
    axes[0].plot(latent.timestamp,latent.temperature,"--",color="#444",lw=1,label="Latent")
    for j,(q,d,name) in enumerate([(a,before,"Unfixed V02"),(b,after,"V02-Rearm")]):
        c=COLORS[j+1];axes[0].scatter(q.t,q.value,s=15,marker=["o","x"][j],color=c,label=name+" samples")
        axes[1].plot(q.t,q.raw_score,marker=["o","x"][j],markersize=3,color=c,label=name)
        phase=q.phase.map({"IDLE":0,"PENDING":1,"CONFIRMED":2,"BLOCKED":3})
        axes[2].step(q.t,phase,where="post",color=c,ls=["-","--"][j],label=name)
        axes[3].step(q.t,q.health_state.map({"HEALTHY":0,"DEGRADED":1,"FAULT":2}),where="post",color=c,ls=["-","--"][j])
        for p in d["result"]["reports"]:
            if p["channel"]=="temperature":axes[0].axvline(p["start_s"],color=c,ls=["-","--"][j],lw=1.4)
    axes[0].set(ylabel="Temperature (C)",title="Known regression only: seed 91, spike_same_long, multiplier 1")
    axes[0].legend(ncol=4,fontsize=7,loc="upper center");axes[0].text(608,34,"605 s: cancellation / reseed\nrepair returns to IDLE",fontsize=8)
    axes[1].set_ylabel("Raw score\n(symlog >10)");axes[1].axhline(8,ls=":",color="#777")
    axes[1].set_yscale("symlog",linthresh=10)
    axes[2].set_yticks([0,1,2,3],["IDLE","PENDING","CONFIRMED","BLOCKED"]);axes[2].legend(fontsize=7,ncol=2,loc="upper right")
    axes[3].set_yticks([0,1,2],["HEALTHY","DEGRADED","FAULT"]);axes[3].set_ylim(-.3,2.4)
    axes[3].set(xlabel="Simulation time (s); green band = truth, red band = spike",xlim=(580,905))
    axes[0].text(676,29,"675 s: repaired report",fontsize=8,color=COLORS[2])
    save(fig,"fig06_blocked_rearm")


def spatial_figures(facts):
    root="results/offline-spatial-pilot/"
    gates=[js(root+s+"/gate.json") for s in ["development","validation","test"]]
    facts["osp_gates"]=gates
    fig,ax=plt.subplots(figsize=(8.2,2.7),constrained_layout=True);x=np.arange(3)
    for j,(key,label) in enumerate([("mean_target_coverage","Target"),("mean_reference_quorum_coverage","At least 2 references")]):
        vals=[g[key]*100 for g in gates];bars=ax.bar(x+(j-.5)*.28,vals,.27,color=COLORS[j],hatch=HATCH[j],edgecolor="#333",label=label)
        ax.bar_label(bars,fmt="%.2f%%",padding=3,fontsize=9)
    ax.axhline(50,color="#af3333",ls="--",label="Predeclared 50% gate")
    ax.set_xticks(x,["Development\n6 proxy dates","Validation\n5 proxy dates","Held-out: NO-GO\n9 proxy dates"])
    ax.set(ylabel="Coverage (%)",ylim=(0,110));ax.legend(ncol=3,fontsize=8,loc="upper center");ax.grid(axis="y",alpha=.15);ax.set_axisbelow(True)
    save(fig,"fig07_osp_coverage")
    d=read(root+"validation/summary.csv")
    p=d[(d.reference_shift_s==0)&(d.reference_max_age_s==900)&(d.multiplier==1)]
    facts["osp_validation_primary"]=json.loads(p.to_json(orient="records"))
    facts["osp_validation_pairs"]=json.loads(read(root+"validation/paired-differences.csv").query("reference_shift_s == 0 and reference_max_age_s == 900 and multiplier == 1").to_json(orient="records"))
    methods=["HistoryShort","HistoryExtended","Spatial","NullSpatial"];labels=["H-short","H-extended","Spatial","Null"]
    fig,axes=plt.subplots(2,2,figsize=(8.2,5),constrained_layout=True)
    for ax,var in zip(axes[0],["temperature","humidity"]):
        q=p[p.variable.eq(var)&p.case.eq("drift")].set_index("method").loc[methods]
        for i,v in enumerate(q.drift_added_reports):
            ax.bar(i,v,color=COLORS[i],hatch=HATCH[i],edgecolor="#333");ax.text(i,v+.02,f"{v:.3f}",ha="center",fontsize=8)
        ax.set_title(var+": drift-added reports",fontsize=10);ax.set_ylabel("Added onsets / requested node-day")
        ax.set_ylim(0,.53 if var=="temperature" else 1.7)
    ax=axes[1,0]
    for j,case in enumerate(["local_fast","local_slow"]):
        q=p[p.variable.eq("temperature")&p.case.eq(case)].set_index("method").loc[methods]
        ax.bar(np.arange(4)+(j-.5)*.34,q.incremental_recall*100,.32,label=case.replace("local_",""),color=[COLORS[0],"white"][j],hatch=["","//"][j],edgecolor="#333")
    ax.set(ylabel="Incremental recall (%)",ylim=(0,45),title="Temperature: local events");ax.legend(fontsize=8)
    ax=axes[1,1];q=p[p.variable.eq("temperature")&p.case.eq("local_fast")].set_index("method").loc[methods]
    for i,v in enumerate(q.mean_application_bytes):
        ax.bar(i,v,color=COLORS[i],hatch=HATCH[i],edgecolor="#333");ax.text(i,v*1.15,f"{v:,.0f}",ha="center",fontsize=8)
    ax.set(yscale="log",ylim=(10,80000),ylabel="Application bytes / node-day (log)",title="Temperature local-fast: modeled cost")
    for ax in axes.flat:
        ax.set_xticks(range(4),labels,rotation=15,fontsize=8);ax.grid(axis="y",alpha=.15);ax.set_axisbelow(True)
    fig.suptitle("OSP-1 validation only: 5 dates, 135 requested node-days / variable\nProxy shift 0, reference age 15 min, multiplier 1; not held-out confirmation",fontsize=10)
    save(fig,"fig08_spatial_information_cost")


def main():
    facts={"base_commit":BASE,"meaning":"Read-only re-presentation; no new effect experiment"}
    diagrams();legacy_figures(facts);traces();spatial_figures(facts)
    for p,key in [("results/v0.2/test/summary.csv","v02_all_points"),
                  ("results/v0.2/test/by_relationship.csv","v02_relationships"),
                  ("results/v0.2/test/paired_bootstrap.csv","v02_pairs"),
                  ("results/blocked-rearm/test/main/summary.csv","rearm_main"),
                  ("results/blocked-rearm/test/aligned_recovery/by_relationship.csv","rearm_aligned"),
                  ("results/blocked-rearm/test/main/paired_bootstrap.csv","rearm_pairs")]:
        facts[key]=json.loads(read(p).to_json(orient="records"))
    # This is a claim ledger, not a second copy of entire historical CI tables.
    for key,group,reference in [("v02_pairs","group","reference"),("rearm_pairs","group","reference")]:
        df=pd.DataFrame(facts[key])
        groups=["all","relationship:same","relationship:cross","relationship:clean","relationship:same_sequential"]
        df=df[df.metric.eq("recall")&df[group].isin(groups)]
        df=df[df[reference].isin(["TAIS","V02-Passive"] if key=="v02_pairs" else ["V02"])]
        facts[key]=json.loads(df.to_json(orient="records"))
    for p in ["results/test/manifest.json","results/v0.2/test/manifest.json","results/blocked-rearm/test/manifest.json",
              "results/offline-spatial-pilot/freeze.json","results/offline-spatial-pilot/test/manifest.json",
              "configs/experiment.yaml","configs/v02.yaml","configs/blocked_rearm.yaml","configs/offline_spatial_pilot.json"]:
        SOURCES.add(p)
    for name in ["RESEARCH_REPORT.md","RESEARCH_REPORT_V0.2.md","FAILURE_ANALYSIS_V0.1.md","V02_DESIGN.md",
                 "V02_INTERPRETATION.md","BLOCKED_REARM_REPORT.md","BLOCKED_REARM_INTERPRETATION.md",
                 "NEXT_RESEARCH_DECISION.md","REAL_DATA_INTAKE_AUDIT.md","REAL_DATA_EXPERIMENT_PREREGISTRATION.md",
                 "C1_1_DATASET_SELECTION.md","OFFLINE_SPATIAL_PILOT_PROTOCOL.md","OFFLINE_SPATIAL_PILOT_REPORT.md",
                 "RELATED_WORK.md"]:
        SOURCES.add("docs/"+name)
    SOURCES.update(["references.bib","results/offline-spatial-pilot/README.md",
                    "results/v0.2/forensics/identifiability.json","results/test/metrics.csv",
                    "results/v0.2/test/metrics.csv","results/blocked-rearm/test/metrics.csv",
                    "results/blocked-rearm/test/main/by_relationship.csv",
                    "results/blocked-rearm/test/aligned_recovery/paired_bootstrap.csv"])
    fingerprints={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(SOURCES)}
    (HERE/"SOURCE_MANIFEST.json").write_text(json.dumps({"base_commit":BASE,"sources_sha256":fingerprints},indent=2)+"\n")
    (HERE/"VERIFIED_RESULTS.json").write_text(json.dumps(facts,indent=2,allow_nan=False)+"\n")
    print(f"Re-presented 8 figures in SVG/PNG; {len(SOURCES)} source hashes; no experiment executed")


if __name__=="__main__":
    main()
