"""Fixed-plan, paired offline experiments with separately generated interventions."""
from __future__ import annotations

import csv
from datetime import datetime, timedelta
import gzip
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

from .data import Dataset, EPOCH, neighbors, seconds
from .interventions import CASES, schedule, apply_target, apply_references, without_event, without_target_fault
from .methods import features, detect
from .io import gzip_text, safe_json

METHODS = ["HistoryShort", "HistoryExtended", "Spatial", "NullSpatial"]


def dates(config, split):
    start, end = (datetime.fromisoformat(d) for d in config["splits"][split])
    out = []
    while start < end:
        out.append(start); start += timedelta(days=config["episode_stride_days"])
    return out


def settings(config):
    for shift, age in itertools.product(config["reference_shift_seconds"], config["reference_max_age_seconds"]):
        primary = shift == config["primary_shift_seconds"] and age == config["primary_reference_max_age_seconds"]
        yield shift, age, config["multipliers"] if primary else [config["sensitivity_multiplier"]]


def unmatched(a, b, tolerance):
    """Chronological, nearest unused counterpart within a fixed tolerance."""
    available = list(map(int, b)); added = []
    for value in a:
        candidates = [j for j, x in enumerate(available) if abs(x-int(value)) <= tolerance]
        if candidates:
            j = min(candidates, key=lambda j: (abs(available[j]-int(value)), available[j]))
            available.pop(j)
        else:
            added.append(int(value))
    return np.array(added, dtype=np.int64), np.array(available, dtype=np.int64)


def packet_residual(target, refs, target_median, ref_medians, minimum):
    """Center target/reference values by calibration medians and require a quorum.

    Return residual and finite reference count; absent quorum yields NaN."""
    finite = np.isfinite(refs) & np.isfinite(ref_medians[:, None])
    count = finite.sum(axis=0)
    centered = np.where(finite, refs - ref_medians[:, None], np.nan)
    ordered = np.sort(np.where(finite, centered, np.inf), axis=0)
    cols = np.arange(refs.shape[1]); n = np.maximum(count, 1)
    med = (ordered[(n-1)//2, cols] + ordered[n//2, cols])/2
    z = np.where((count >= minimum) & np.isfinite(target_median), target-target_median-med, np.nan)
    return z, count


def donor_values(dataset, node, variable, date, query, config, median):
    """Calibration-only day fragments, never validation/test values."""
    start, end = map(seconds, config["calibration"])
    material = f"{config['negative_control_seed']}:{date}:{node}:{variable}".encode()
    day_index = int.from_bytes(hashlib.sha256(material).digest()[:8], "little") % ((end-start)//86400)
    proxy = start + day_index*86400 + (query % 86400)
    assert np.all(proxy < end)
    values, rows, arrival = dataset.asof(node, variable, proxy, 1800)
    return np.where(np.isfinite(values), values, median), rows, arrival


def episode_inputs(dataset, config, node, variable, day, shift, age, medians):
    """Assemble target/reference as-of rows and calibration-only negative controls.

    Availability masks are shared across real and null reference conditions."""
    query = np.arange(day+config["episode_hours"][0]*3600,
                      day+config["episode_hours"][1]*3600+1, config["poll_seconds"], dtype=np.int64)
    x, rows, arrival = dataset.asof(node, variable, query, config["target_max_age_seconds"])
    refs = neighbors(node, config["reference_count"])
    real, refrows, refarrivals, null, donorrows = [], [], [], [], []
    for j in refs:
        v, r, a = dataset.asof(j, variable, query, age, shift)
        donor, dr, _ = donor_values(dataset, j, variable, day, query, config, medians[j])
        real.append(v); refrows.append(r); refarrivals.append(a)
        null.append(np.where(np.isfinite(v), donor, np.nan)); donorrows.append(dr)
    return dict(query=query, target=x, target_rows=rows, target_arrival=arrival, refs=refs,
                real=np.asarray(real), null=np.asarray(null), ref_rows=np.asarray(refrows),
                ref_arrival=np.asarray(refarrivals), donor_rows=np.asarray(donorrows), shift=shift)


def materialize(inputs, label, config):
    """Apply label-defined perturbations offline, then clip to declared physical bounds.

    Clipping can remove a requested observation opportunity; labels are kept
    separate from detector features and are never passed to detect()."""
    variable = label["variable"]; lo, hi = config["variables"][variable]["bounds"]
    # Physical support of a requested controlled perturbation is explicitly bounded.
    # This preserves identical drift/local_slow observations, including saturation.
    raw_x = apply_target(inputs["target"], inputs["target_arrival"], label)
    x = np.clip(raw_x, lo, hi)
    real_raw = apply_references(inputs["real"], inputs["ref_arrival"]-inputs["shift"],
                                inputs["query"], label)
    null_raw = apply_references(inputs["null"], inputs["ref_arrival"]-inputs["shift"],
                                inputs["query"], label, negative=True)
    return x, np.clip(real_raw, lo, hi), np.clip(null_raw, lo, hi), int(np.sum(np.isfinite(raw_x) & (x != raw_x)))


def costs(inputs, x, real, null, method, reports):
    """Count assumed polling/RPC requests and modeled application bytes.

    Reference replies are assumed 36 bytes and event reports 18 bytes. These
    are conditional payload assumptions, not encoded Binary frames, measured
    wireless traffic, physical fresh reads or measured electrical energy."""
    use_ref = method in ("Spatial", "NullSpatial"); refs = null if method == "NullSpatial" else real
    valid = np.isfinite(x); rows = inputs["target_rows"][valid]
    ref_valid = np.isfinite(refs) if use_ref else np.zeros_like(refs, dtype=bool)
    attempts = int(refs.size) if use_ref else 0
    distinct_refs = sum(len(np.unique(r[m & (r >= 0)])) for r, m in zip(inputs["ref_rows"], ref_valid)) if use_ref else 0
    return {"target_poll_attempts": len(x), "target_values_used": int(valid.sum()),
            "target_distinct_rows": len(np.unique(rows)), "target_cached_reuses": int(valid.sum())-len(np.unique(rows)),
            "reference_requests": attempts, "reference_values_used": int(ref_valid.sum()),
            "reference_distinct_current_rows": distinct_refs,
            "reference_payload_bytes": attempts*36, "environment_requests": len(reports),
            "application_requests": attempts+len(reports), "application_bytes": attempts*36+len(reports)*18}


def run_split(dataset, config, split, output, source_root, smoke=False):
    """Exclusively write fixed-plan paired interventions, metrics and provenance.

    Calibration medians and donors never read held-out values. Smoke is
    development-only. Scoring uses controlled window/counterfactual outcomes
    on an unlabeled real background; it is not natural event precision.
    No adaptive Core runtime, live network or actual energy validation occurs."""
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    day_list = dates(config, split)
    nodes = config["nodes"]
    if smoke:
        if split != "development":
            raise ValueError("Smoke is development-only")
        day_list, nodes = day_list[:1], [16, 29, 42]
    medians = {v: dataset.calibration(v) for v in config["variables"]}
    result_rows = []; evidence_rows = []
    labels_path, trace_path = output/"interventions.jsonl.gz", output/"example-traces.jsonl.gz"
    with gzip_text(labels_path) as labels_file, gzip_text(trace_path) as trace_file:
        for date in day_list:
            date_string = date.date().isoformat(); day = int((date-EPOCH).total_seconds())
            print(f"{split} {date_string}", flush=True)
            for node in nodes:
                for variable in config["variables"]:
                    all_settings = list(settings(config))
                    if smoke:
                        all_settings = [(0, 900, [1.0])]
                    for shift, age, multipliers in all_settings:
                        inputs = episode_inputs(dataset, config, node, variable, day, shift, age, medians[variable])
                        query = inputs["query"]; scoring = query >= day+config["scoring_start_hour"]*3600
                        prepared, labels, feat = {}, {}, {}
                        for case in CASES:
                            label = schedule(case, day, node, variable, inputs["refs"], config)
                            x, real, null, clipped = materialize(inputs, label, config)
                            z, ref_count = packet_residual(x, real, medians[variable][node],
                                                         np.array([medians[variable][j] for j in inputs["refs"]]), config["minimum_references"])
                            zn, _ = packet_residual(x, null, medians[variable][node],
                                                   np.array([medians[variable][j] for j in inputs["refs"]]), config["minimum_references"])
                            prepared[case] = x, real, null, ref_count
                            labels[case] = label
                            feat[case] = features(x, inputs["target_rows"], z, zn, config)
                            if shift == 0 and age == 900:
                                enriched = dict(label, date=date_string, target_clipped_poll_values=clipped,
                                                target_available_scoring_polls=int((np.isfinite(x)&scoring).sum()))
                                labels_file.write(json.dumps(enriched, sort_keys=True)+"\n")
                        for multiplier in multipliers:
                            threshold = config["variables"][variable]["threshold"]*multiplier
                            masks, details, reports = {}, {}, {}
                            for case, method in itertools.product(CASES, METHODS):
                                key = case, method
                                masks[key], details[key] = detect(feat[case], threshold, method, config)
                                reports[key] = query[masks[key] & scoring]
                            for case, method in itertools.product(CASES, METHODS):
                                label = labels[case]; key = case, method; onset = reports[key]
                                x, real, null, ref_count = prepared[case]
                                reference_active = real if method != "NullSpatial" else null
                                tol = config["counterfactual_match_tolerance_seconds"]
                                event_control = reports[without_event(case), method]
                                added_event, _ = unmatched(onset, event_control, tol)
                                event_window = (query >= label["event_start"]) & (query <= label["event_start"]+config["event_deadline_seconds"])
                                hit = onset[(onset >= label["event_start"]) & (onset <= label["event_start"]+config["event_deadline_seconds"])]
                                new_hit = added_event[(added_event >= label["event_start"]) & (added_event <= label["event_start"]+config["event_deadline_seconds"])]
                                fault_control = reports[without_target_fault(case), method]
                                fault_added, fault_removed = unmatched(onset, fault_control, tol)
                                controlled_x = prepared[without_event(case)][0]
                                opportunity = np.isfinite(x) & np.isfinite(controlled_x) & (abs(x-controlled_x)>1e-9) & event_window
                                drift_case = label["target_fault"] == "drift"
                                def outside(t):
                                    return np.sum((t < label["event_start"]) | (t > label["event_start"]+config["event_deadline_seconds"])) if label["event"] else len(t)
                                row = {"split": split, "date": date_string, "node": node, "variable": variable,
                                       "case": case, "method": method, "reference_shift_s": shift,
                                       "reference_max_age_s": age, "multiplier": multiplier, "threshold": threshold,
                                       "reports": len(onset), "event_requested": int(bool(label["event"])),
                                       "event_window_hit": int(bool(len(hit))) if label["event"] else None,
                                       "event_incremental_hit": int(bool(len(new_hit))) if label["event"] else None,
                                       "event_realized_opportunity": int(bool(opportunity.any())) if label["event"] else None,
                                       "event_delay_minutes": float((hit[0]-label["event_start"])/60) if label["event"] and len(hit) else None,
                                       "incremental_delay_minutes": float((new_hit[0]-label["event_start"])/60) if label["event"] and len(new_hit) else None,
                                       "drift_extra_net": len(onset)-len(fault_control) if drift_case else None,
                                       "drift_added_reports": len(fault_added) if drift_case else None,
                                       "drift_removed_reports": len(fault_removed) if drift_case else None,
                                       "drift_outside_event_net": int(outside(onset)-outside(fault_control)) if drift_case else None,
                                       "target_scoring_coverage": float(np.mean(np.isfinite(x[scoring]))),
                                       "reference_slot_coverage": float(np.mean(np.isfinite(reference_active[:, scoring]))) if method in ("Spatial", "NullSpatial") else None,
                                       "reference_quorum_coverage": float(np.mean(ref_count[scoring] >= config["minimum_references"])) if method in ("Spatial", "NullSpatial") else None}
                                row.update(costs(inputs, x, real, null, method, onset))
                                result_rows.append(row)
                                if (node == 29 and date == day_list[0] and variable == "temperature"
                                        and shift == 0 and age == 900 and multiplier == 1):
                                    for i, t in enumerate(query):
                                        trace = {"date": date_string, "case": case, "method": method, "t": int(t),
                                                 "minutes": float((t-day)/60), "target": float(x[i]),
                                                 "target_row": int(inputs["target_rows"][i]),
                                                 "target_assumed_available": int(inputs["target_arrival"][i]),
                                                 "reference_rows": inputs["ref_rows"][:, i].tolist(),
                                                 "reference_assumed_available": inputs["ref_arrival"][:, i].tolist(),
                                                 "reference_values": reference_active[:, i].tolist(),
                                                 "negative_control": method == "NullSpatial",
                                                 "negative_donor_rows": inputs["donor_rows"][:, i].tolist() if method == "NullSpatial" else None,
                                                 "score": float(feat[case]["score"][i]),
                                                 "report": bool(masks[key][i] and scoring[i]),
                                                 "suspicious": bool(details[key]["suspicious"][i]),
                                                 "fast_bypass": bool(details[key]["fast_bypass"][i])}
                                        trace_file.write(json.dumps(safe_json(trace), sort_keys=True, allow_nan=False)+"\n")
    columns = list(result_rows[0])
    with gzip_text(output/"node-metrics.csv.gz", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns); writer.writeheader(); writer.writerows(result_rows)
    # The sampled opportunity labels above are independent of detector output.
    source = Path(source_root)
    code_hashes = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted((source/"src/tais_spatial").glob("*.py"))}
    artifacts = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file()}
    manifest = {"split": split, "smoke": smoke, "rows": len(result_rows), "dates": [d.date().isoformat() for d in day_list],
                "nodes": nodes, "source_sha256": config["workbook_sha256"], "config": config,
                "code_sha256": code_hashes, "artifacts": artifacts,
                "claims": "offline exploratory controlled interventions; no natural-fault or online/energy validation"}
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    return manifest
