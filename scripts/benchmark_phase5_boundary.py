#!/usr/bin/env python3
"""Phase 5 boundary sweep, seed audit, freeze, and held-out final validation."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import importlib.metadata
import json
import math
import multiprocessing
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from tais.closed_loop import (
    ClosedLoopParams,
    ClosedLoopSender,
    LinkProfile,
    StatefulLinkModel,
)
from tais.config import load
from tais.core_stream import CoreReceiver
from tais.paper_baselines import episodes
from tais.replay import finite
from tais.transfer_signals import counterfactual, generate
from tais.wire_codec import encode, envelope_from_record
from simulator.events import Event, match_events
from ablation_support import deadline_truth, make_trace as ma_trace
from phase4_support import replay as phase4_replay

PLAN_PATH = ROOT / "configs/phase5_boundary.json"
PHASE4_PLAN_PATH = ROOT / "configs/phase4.json"
OUT_ROOT = ROOT / "results/phase5"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def sources() -> dict[str, str]:
    paths = (
        sorted((ROOT / "src/tais/closed_loop").glob("*.py"))
        + [
            PLAN_PATH,
            ROOT / "tests/test_closed_loop.py",
            ROOT / "scripts/benchmark_phase5_boundary.py",
            ROOT / "scripts/analyze_phase5_boundary.py",
        ]
    )
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def audit_seeds(plan: dict, out_root: Path) -> dict:
    used: dict[int, list[str]] = {}
    scanned_files = 0
    for p in sorted(ROOT.rglob("*")):
        if any(
            part in p.parts
            for part in (".git", ".venv", "vendor", "__pycache__", "build")
        ):
            continue
        rel = p.relative_to(ROOT)
        if str(rel) == "configs/phase5_boundary.json" or str(rel).startswith("results/phase5"):
            continue
        if p.suffix not in (".json", ".yaml", ".yml"):
            continue
        scanned_files += 1
        try:
            txt = p.read_text(errors="ignore")
            data = json.loads(txt) if p.suffix == ".json" else yaml.safe_load(txt)
        except Exception:
            continue

        def walk(obj, loc=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if "seed" in str(k).lower():
                        if isinstance(v, int) and 0 <= v < 10000:
                            used.setdefault(v, []).append(f"{rel}:{loc}.{k}")
                        elif isinstance(v, list):
                            for item in v:
                                if isinstance(item, int) and 0 <= item < 10000:
                                    used.setdefault(item, []).append(f"{rel}:{loc}.{k}")
                    walk(v, f"{loc}.{k}")
            elif isinstance(obj, list):
                for item in obj:
                    walk(item, loc)

        walk(data)

    trace_seeds = set()
    traces_dir = ROOT / "results/traces"
    if traces_dir.exists():
        for d in traces_dir.rglob("*"):
            if d.is_dir() and d.name.isdigit() and "phase5" not in d.parts:
                trace_seeds.add(int(d.name))

    eng = plan["engineering_seeds"]
    swp = plan["sweep_seeds"]
    fin = plan["final_seeds"]
    all_cand = eng + swp + fin
    assert len(set(all_cand)) == len(all_cand), "Candidate seed partitions overlap"
    collisions = sorted(s for s in all_cand if s in used)
    dir_collisions = sorted(s for s in all_cand if s in trace_seeds)
    report = dict(
        status="PASS" if not collisions and not dir_collisions else "FAIL",
        scanned_config_manifest_files=scanned_files,
        max_existing_seed=max(set(used) | trace_seeds) if (used or trace_seeds) else None,
        engineering_candidates=eng,
        sweep_candidates=swp,
        final_candidates=fin,
        collisions=collisions,
        directory_collisions=dir_collisions,
    )
    dump_json(out_root / "seed-audit.json", report)
    assert report["status"] == "PASS", report
    return report


def make_axis_a_trace(phase4_plan: dict, plan: dict, seed: int, duration_s: int, amp_factor: float):
    spec = deepcopy(phase4_plan["ma1_plan"]["generator"])
    spec["events"]["onset_ranges"] = deepcopy(plan["axis_a"]["onset_ranges"])
    spec["events"]["duration_ranges"] = {
        "slot0": [duration_s, duration_s],
        "slot1": [duration_s, duration_s],
    }
    spec["events"]["amplitude"] = {
        c: [v * amp_factor for v in bounds]
        for c, bounds in spec["events"]["amplitude"].items()
    }
    if duration_s >= 600:
        spec["events"]["shapes"] = ["smooth_pulse", "smooth_pulse"]
    else:
        spec["events"]["shapes"] = ["step_recovery", "smooth_pulse"]
    tr = generate(spec, seed, "clean_both")
    tr.scenario = f"axisA_d{duration_s}_a{amp_factor}"
    return tr


def _profile_name(loss_id: str, bw_bpm: float | None) -> str:
    bw_tag = "inf" if bw_bpm is None else str(int(bw_bpm))
    return f"{loss_id}_bw_{bw_tag}"


def _make_link_profile(loss_spec: dict, bw_bpm: float | None) -> LinkProfile:
    return LinkProfile(
        name=_profile_name(loss_spec["id"], bw_bpm),
        loss_rate=float(loss_spec["loss_rate"]),
        burst_mode=bool(loss_spec["burst_mode"]),
        bandwidth_bpm=None if bw_bpm is None else float(bw_bpm),
    )


def _receiver_reports(delivered_envelopes: list[dict], channels: tuple[str, ...]) -> list[Event]:
    reports = []
    open_state = {c: False for c in channels}
    for env in delivered_envelopes:
        t = env["timestamp"]
        for c in channels:
            act = bool(env["environment_active"][c])
            if act and not open_state[c]:
                reports.append(Event(c, t, t))
                open_state[c] = True
            elif not act:
                open_state[c] = False
    return reports


def _to_events(reports) -> list[Event]:
    out = []
    for r in reports:
        if isinstance(r, Event):
            out.append(r)
        else:
            out.append(Event(r["channel"], r["start_s"], r["end_s"]))
    return out


def _replay_open_loop_sender(trace, cfg: dict, phase4_plan: dict, params: ClosedLoopParams, method: str) -> dict:
    if method in ("Fixed-20", "A5", "A7", "Risk-T1-U1"):
        return phase4_replay(trace, cfg, method, phase4_plan)
    if method in ("JALC-ObsOnly", "JALC-AoI"):
        variant = "ObsOnly" if method == "JALC-ObsOnly" else "AoI"
        sender = ClosedLoopSender(cfg, params=params, variant=variant, link=None)
        rows = []
        try:
            for source in trace.observed:
                item = sender.push(source)
                if item is not None:
                    rows.append(item["record"])
        finally:
            sender.close()
        return episodes(rows, tuple(cfg["channels"]))
    raise ValueError(f"Not an open-loop method: {method}")


def _replay_through_link(
    trace,
    cfg: dict,
    phase4_plan: dict,
    params: ClosedLoopParams,
    method: str,
    profile: LinkProfile,
    seed: int,
    scenario_label: str,
    sender_cache: dict,
):
    channels = tuple(cfg["channels"])
    rx = CoreReceiver(layout_id=1)
    link = StatefulLinkModel(profile, receiver=rx, seed=seed, label=f"{scenario_label}:{profile.name}")

    if method == "JALC-Full":
        sender = ClosedLoopSender(cfg, params=params, variant="Full", link=link)
        rows = []
        try:
            for source in trace.observed:
                item = sender.push(source)
                if item is not None:
                    rows.append(item["record"])
        finally:
            sender.close()
        result = episodes(rows, channels)
    else:
        if method not in sender_cache:
            sender_cache[method] = _replay_open_loop_sender(
                trace, cfg, phase4_plan, params, method
            )
        result = sender_cache[method]
        for rec in result["records"]:
            if rec["upload"]:
                env = envelope_from_record(rec, layout_id=1)
                frame = encode(env, layout_id=1)
                link.send(float(rec["timestamp"]), frame, env, redundancy_k=1)

    return result, link


def _evaluate_run(trace, result: dict, link: StatefulLinkModel, cfg: dict, plan: dict, cf_bundle=None) -> dict:
    channels = tuple(cfg["channels"])
    tol = cfg["evaluation"]["event_match_tolerance_s"]
    deadline_s = plan["deadline_s"]
    aoi_sla_s = plan["aoi_sla_s"]
    truth = deadline_truth(trace.events, deadline_s, tol)
    sender_reports = _to_events(result["reports"])
    rx_reports = _receiver_reports(link.delivered_frames, channels)

    cf_sender_reports = _to_events(cf_bundle[0]["reports"]) if cf_bundle is not None else []
    cf_rx_reports = _receiver_reports(cf_bundle[1].delivered_frames, channels) if cf_bundle is not None else []

    out = {}
    for side, reports, clean_reports in [
        ("sender", sender_reports, cf_sender_reports),
        ("receiver", rx_reports, cf_rx_reports),
    ]:
        matched = match_events(truth, reports, tol)
        tp, fp, fn = matched.true_positives, matched.false_positives, matched.false_negatives
        fault_false = [
            d
            for d in matched.unmatched_detections
            if any(
                f.channel == d.channel
                and f.start_s <= d.start_s < f.end_s + cfg["evaluation"]["fault_recovery_attribution_s"]
                for f in trace.faults
            )
        ]
        induced = [
            d
            for d in fault_false
            if not any(c.channel == d.channel and abs(c.start_s - d.start_s) <= tol for c in clean_reports)
        ]
        p = side + "_"
        out.update(
            {
                p + "tp": tp,
                p + "fp": fp,
                p + "fn": fn,
                p + "f1": 2 * tp / (len(truth) + tp + fp) if (len(truth) + tp + fp) else np.nan,
                p + "recall": tp / len(truth) if truth else np.nan,
                p + "precision": tp / (tp + fp) if (tp + fp) else np.nan,
                p + "restricted_delay_sum_s": float(sum(matched.latencies) + fn * deadline_s),
                p + "fault_induced_false": len(induced) if cf_bundle is not None else 0,
            }
        )
        # Same-channel fault overlap recall
        same_fault_events = [
            e
            for e in trace.events
            if any(f.channel == e.channel and f.start_s <= e.end_s and f.end_s > e.start_s for f in trace.faults)
        ]
        matched_keys = {(m.ground_truth.channel, m.ground_truth.start_s) for m in matched.matches}
        out[p + "same_fault_n"] = len(same_fault_events)
        out[p + "same_fault_tp"] = sum((e.channel, e.start_s) in matched_keys for e in same_fault_events)

    # Receiver finite-value AoI on 1Hz grid (null frames never refresh finite value age)
    duration_s = len(trace.observed)
    grid = np.arange(duration_s, dtype=float)
    delivered = link.delivered_frames
    value_ages = []
    sla_violations = 0
    total_channel_secs = duration_s * len(channels)
    for ch in channels:
        f_times = np.array(
            [e["timestamp"] for e in delivered if finite(e["values"].get(ch))],
            dtype=float,
        )
        if len(f_times) == 0:
            sla_violations += int(np.count_nonzero(grid > aoi_sla_s))
            continue
        ix = np.searchsorted(f_times, grid, side="right") - 1
        mask = ix >= 0
        ages_covered = grid[mask] - f_times[ix[mask]]
        value_ages.extend(ages_covered.tolist())
        # Before first received finite frame, treat age as elapsed time since t=0
        ages_all = np.where(mask, grid - f_times[np.maximum(ix, 0)], grid)
        sla_violations += int(np.count_nonzero(ages_all > aoi_sla_s))

    rows = result["records"]
    sample_times = np.array([r["timestamp"] for r in rows], dtype=float)
    gaps = np.diff(sample_times) if len(sample_times) > 1 else np.array([])
    fast_mask = np.r_[False, gaps <= 5.0 + 1e-9] if len(sample_times) > 1 else np.array([False])
    fast_ts = sample_times[fast_mask]
    fast_used = (
        np.searchsorted(fast_ts, sample_times, side="right")
        - np.searchsorted(fast_ts, sample_times - 120.0, side="right")
    )

    # Pre-onset coverage within 20s
    pre_covered = sum(
        1
        for e in trace.events
        if len(sample_times[sample_times < e.start_s]) > 0
        and (e.start_s - sample_times[sample_times < e.start_s][-1]) <= 20.0
    )

    out.update(
        duration_s=duration_s,
        n_events=len(trace.events),
        n_faults=len(trace.faults),
        samples=len(rows),
        logical_uploads=link.counts["logical_frames"],
        tx_attempts=link.counts["attempts"],
        redundant_copies=link.counts["redundant_copies"],
        sent_bytes=link.counts["sent_bytes"],
        delivered_frames=link.counts["delivered"],
        loss_drops=link.counts["loss_drops"],
        bw_drops=link.counts["bw_drops"],
        fast_window_max=int(fast_used.max()) if len(fast_used) else 0,
        pre_covered_events=pre_covered,
        finite_value_coverage=len(value_ages) / total_channel_secs,
        finite_age_mean_s=float(np.mean(value_ages)) if value_ages else float(duration_s),
        finite_age_p95_s=float(np.percentile(value_ages, 95)) if value_ages else float(duration_s),
        finite_age_max_s=float(np.max(value_ages)) if value_ages else float(duration_s),
        aoi_violation_45s_rate=sla_violations / total_channel_secs,
    )
    return out


def _seed_worker(seed: int, plan: dict, phase4_plan: dict) -> tuple[int, list[dict]]:
    cfg = load()
    params = ClosedLoopParams(**plan["params"])
    methods = plan["methods"]
    rows: list[dict] = []

    lossless = LinkProfile(name="loss_0_bw_inf", loss_rate=0.0, burst_mode=False, bandwidth_bpm=None)

    # --- Axis A: Event Dynamics Boundary (5 durations x 5 amplitudes) ---
    for dur in plan["axis_a"]["durations_s"]:
        for amp in plan["axis_a"]["amplitude_factors"]:
            tr = make_axis_a_trace(phase4_plan, plan, seed, dur, amp)
            obs_hash = hashlib.sha256(
                json.dumps(tr.observed, sort_keys=True, allow_nan=True).encode()
            ).hexdigest()[:16]
            sender_cache: dict = {}
            for m in methods:
                res, link = _replay_through_link(
                    tr, cfg, phase4_plan, params, m, lossless, seed, tr.scenario, sender_cache
                )
                metrics = _evaluate_run(tr, res, link, cfg, plan, cf_bundle=None)
                rows.append(
                    dict(
                        seed=seed,
                        cohort="axis_a",
                        scenario=tr.scenario,
                        method=m,
                        duration_bin_s=dur,
                        amplitude_factor=amp,
                        loss_id="loss_0",
                        bandwidth_bpm="inf",
                        link_profile=lossless.name,
                        observed_hash=obs_hash,
                        **metrics,
                    )
                )

    # --- Axis B: Communication Degradation Boundary (5 loss x 3 BW x 2 scenarios) ---
    for sc in plan["axis_b"]["scenarios"]:
        tr = ma_trace(phase4_plan["ma1_plan"], seed, sc)
        obs_hash = hashlib.sha256(
            json.dumps(tr.observed, sort_keys=True, allow_nan=True).encode()
        ).hexdigest()[:16]
        sender_cache = {}
        for lspec in plan["axis_b"]["loss_profiles"]:
            for bw in plan["axis_b"]["bandwidth_caps_bpm"]:
                profile = _make_link_profile(lspec, bw)
                for m in methods:
                    res, link = _replay_through_link(
                        tr, cfg, phase4_plan, params, m, profile, seed, sc, sender_cache
                    )
                    metrics = _evaluate_run(tr, res, link, cfg, plan, cf_bundle=None)
                    rows.append(
                        dict(
                            seed=seed,
                            cohort="axis_b",
                            scenario=sc,
                            method=m,
                            duration_bin_s=np.nan,
                            amplitude_factor=np.nan,
                            loss_id=lspec["id"],
                            bandwidth_bpm="inf" if bw is None else str(int(bw)),
                            link_profile=profile.name,
                            observed_hash=obs_hash,
                            **metrics,
                        )
                    )

    # --- Slice C: Noise & Fault Non-Degradation (10 scenarios x 2 link profiles + counterfactual FI) ---
    for sc in plan["slice_c"]["scenarios"]:
        tr = ma_trace(phase4_plan["ma1_plan"], seed, sc)
        cf = counterfactual(tr)
        obs_hash = hashlib.sha256(
            json.dumps(tr.observed, sort_keys=True, allow_nan=True).encode()
        ).hexdigest()[:16]
        sender_cache = {}
        cf_sender_cache = {}
        for lspec in plan["slice_c"]["link_profiles"]:
            profile = _make_link_profile(lspec, lspec["bandwidth_bpm"])
            for m in methods:
                cf_bundle = None
                if tr.faults:
                    cf_bundle = _replay_through_link(
                        cf, cfg, phase4_plan, params, m, profile, seed, sc + ":cf", cf_sender_cache
                    )
                res, link = _replay_through_link(
                    tr, cfg, phase4_plan, params, m, profile, seed, sc, sender_cache
                )
                metrics = _evaluate_run(tr, res, link, cfg, plan, cf_bundle=cf_bundle)
                rows.append(
                    dict(
                        seed=seed,
                        cohort="slice_c",
                        scenario=sc,
                        method=m,
                        duration_bin_s=np.nan,
                        amplitude_factor=np.nan,
                        loss_id=lspec["id"],
                        bandwidth_bpm="inf" if lspec["bandwidth_bpm"] is None else str(int(lspec["bandwidth_bpm"])),
                        link_profile=profile.name,
                        observed_hash=obs_hash,
                        **metrics,
                    )
                )

    return seed, rows


def run_phase(phase: str, out_root: Path, workers: int) -> None:
    plan = json.loads(PLAN_PATH.read_text())
    phase4_plan = json.loads(PHASE4_PLAN_PATH.read_text())

    if phase == "audit":
        report = audit_seeds(plan, out_root)
        print(json.dumps(report, indent=2))
        return

    if phase == "freeze":
        eng_manifest = json.loads((out_root / "engineering/manifest.json").read_text())
        assert eng_manifest["status"] == "COMPLETE" and eng_manifest["sources"] == sources()
        audit = json.loads((out_root / "seed-audit.json").read_text())
        assert audit["status"] == "PASS"
        dump_json(
            out_root / "freeze.json",
            dict(
                status="FROZEN_BEFORE_SWEEP_AND_FINAL",
                sources=sources(),
                engineering_manifest_sha256=sha(out_root / "engineering/manifest.json"),
                seed_audit_sha256=sha(out_root / "seed-audit.json"),
                sweep_seeds=plan["sweep_seeds"],
                final_seeds=plan["final_seeds"],
                code_base=subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip(),
            ),
        )
        print("Frozen Phase 5 sources to", out_root / "freeze.json")
        return

    if phase in ("sweep", "final"):
        lock = json.loads((out_root / "freeze.json").read_text())
        assert lock["sources"] == sources(), "Sources modified after freeze!"

    seeds = plan[f"{phase}_seeds"]
    dest = out_root / phase
    dest.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    with ProcessPoolExecutor(
        max_workers=workers, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        futs = [pool.submit(_seed_worker, s, plan, phase4_plan) for s in seeds]
        for fut in as_completed(futs):
            s, srows = fut.result()
            all_rows.extend(srows)
            print(f"[{phase}] seed {s}: {len(srows)} runs complete", flush=True)

    df = pd.DataFrame(all_rows).sort_values(
        ["seed", "cohort", "scenario", "link_profile", "method"]
    )
    csv_path = dest / "metrics.csv"
    df.to_csv(csv_path, index=False)

    # Sanity invariants
    jalc = df[df["method"].str.startswith("JALC-")]
    assert (jalc["fast_window_max"] <= 6).all(), "JALC violated rolling fast budget <= 6"
    lossless_aoi = df[
        (df["method"].isin(["JALC-AoI", "JALC-Full"]))
        & (df["link_profile"] == "loss_0_bw_inf")
        & (~df["scenario"].str.contains("missing"))
    ]
    assert (lossless_aoi["aoi_violation_45s_rate"] == 0.0).all(), (
        "Lossless finite-channel AoI exceeded 45s hard cap!"
    )

    manifest = dict(
        status="COMPLETE",
        phase=phase,
        seeds=seeds,
        runs=len(df),
        sources=sources(),
        metrics_sha256=sha(csv_path),
        python=platform.python_version(),
        packages={
            n: importlib.metadata.version(n)
            for n in ("numpy", "pandas", "matplotlib", "PyYAML")
        },
    )
    dump_json(dest / "manifest.json", manifest)
    print(f"[{phase}] COMPLETE: {len(df)} runs saved to {csv_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase", choices=["audit", "engineering", "freeze", "sweep", "final"])
    p.add_argument("--out", type=Path, default=OUT_ROOT)
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    run_phase(args.phase, args.out, args.workers)
