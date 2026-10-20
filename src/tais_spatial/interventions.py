"""Independent intervention schedules; detectors never receive this module's labels."""
from __future__ import annotations
import numpy as np

CASES = {
    "untouched": (None, None, None),
    "drift": ("drift", None, None),
    "offset": ("offset", None, None),
    "local_fast": (None, "local_fast", None),
    "local_slow": (None, "local_slow", None),
    "common_fast": (None, "common_fast", None),
    "drift_local_fast": ("drift", "local_fast", None),
    "drift_common_fast": ("drift", "common_fast", None),
    "reference_missing": (None, None, "missing"),
    "reference_missing_local": (None, "local_fast", "missing"),
    "reference_fault": (None, None, "drift"),
    "reference_fault_local": (None, "local_fast", "drift"),
    "drift_reference_missing": ("drift", None, "missing"),
}


def schedule(case, day, node, variable, refs, config):
    """Describe a controlled intervention on unlabeled real background in proxy seconds.

    These labels identify imposed perturbations, not natural field faults/events."""
    fault, event, ref = CASES[case]; spec = config["variables"][variable]
    label = {"case": case, "day": day, "target": node, "variable": variable, "references": refs,
             "target_fault": fault, "event": event, "reference_intervention": ref,
             "fault_start": day + 8*3600, "ramp_end": day + 12*3600,
             "fault_end": day + 20*3600, "fault_amplitude": spec["drift_amplitude"],
             "event_start": day + (8*3600 if event == "local_slow" else 10*3600+1800),
             "event_end": day + (20*3600 if event == "local_slow" else 11*3600+1800),
             "event_amplitude": spec["drift_amplitude"] if event == "local_slow" else spec["event_amplitude"],
             "reference_start": day+10*3600, "reference_end": day+14*3600,
             "reference_fault_node": refs[0], "truth_kind": "controlled intervention on unlabeled real background"}
    return label


def drift(times, label):
    return label["fault_amplitude"] * np.clip((np.asarray(times)-label["fault_start"])/14400, 0, 1)


def event_delta(times, label):
    if label["event"] == "local_slow":
        return drift(times, label)
    if label["event"]:
        return label["event_amplitude"] * ((times >= label["event_start"]) & (times < label["event_end"]))
    return np.zeros(len(times))


def apply_target(values, recorded_times, label):
    """Apply synthetic target perturbations on source-row times, preserving NaNs.

    local_slow intentionally shares drift-only observations despite a different
    physical interpretation; no detector can recover that distinction alone."""
    out = np.array(values, copy=True)
    if label["target_fault"] == "drift":
        out += drift(recorded_times, label)
    elif label["target_fault"] == "offset":
        out += label["fault_amplitude"] * (recorded_times >= label["fault_start"])
    # local_slow deliberately has exactly the drift-only observations.
    out += event_delta(recorded_times, label)
    return out


def apply_references(values, recorded_times, query, label, negative=False):
    """Apply common events or reference interventions before detector evaluation.

    Negative controls omit common-event response; missingness follows query
    time while value perturbations use the recorded source-row proxy time."""
    out = np.array(values, copy=True)
    if label["event"] == "common_fast" and not negative:
        out += event_delta(recorded_times, label)
    if label["reference_intervention"] == "drift":
        out[0] += drift(recorded_times[0], label)
    if label["reference_intervention"] == "missing":
        out[:, (query >= label["reference_start"]) & (query < label["reference_end"])] = np.nan
    return out


def without_event(case):
    fault, _, ref = CASES[case]
    return next(k for k, v in CASES.items() if v == (fault, None, ref))


def without_target_fault(case):
    _, event, ref = CASES[case]
    return next(k for k, v in CASES.items() if v == (None, event, ref))
