"""Bit-exact parity tests between Python JointAdaptiveController and pure C11 tais_jalc.c."""
import ctypes as C
import math
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from tais import ROOT
from tais.closed_loop import (
    OBS_MODES,
    ClosedLoopParams,
    JointAdaptiveController,
    LinkProfile,
    LinkTelemetry,
    StatefulLinkModel,
)
from tais.closed_loop.trace_link import TraceDrivenLinkModel, load_e220_regimes
from tais.config import load
from tais.core_stream import CoreReceiver
from tais.scheduler import Scheduler
from tais.transfer_signals import generate
from tais.wire_codec import encode, envelope_from_record

STATE_TO_INT = {"HEALTHY": 0, "DEGRADED": 1, "FAULT": 2}
VARIANT_TO_INT = {"ObsOnly": 0, "AoI": 1, "Full": 2}


class CParams(C.Structure):
    _fields_ = [
        ("fallback_interval_s", C.c_double),
        ("diag_interval_s", C.c_double),
        ("aoi_cap_quiet_s", C.c_double),
        ("aoi_cap_active_s", C.c_double),
        ("loss_redundancy_threshold", C.c_double),
    ]


class CTelemetry(C.Structure):
    _fields_ = [
        ("present", C.c_bool),
        ("loss_ema", C.c_double),
        ("bw_congested", C.c_bool),
        ("bw_tokens_bytes", C.c_double),
        ("has_confirmed_finite", C.c_bool * 4),
        ("last_confirmed_finite_t", C.c_double * 4),
    ]


class CDecision(C.Structure):
    _fields_ = [
        ("t", C.c_double),
        ("obs_mode", C.c_int),
        ("obs_interval_s", C.c_double),
        ("next_sample_s", C.c_double),
        ("interval_s", C.c_double),
        ("aoi_cap_s", C.c_double),
        ("delta_margin_s", C.c_double),
        ("upload", C.c_bool),
        ("reason_mask", C.c_uint32),
        ("redundancy_k", C.c_int),
        ("score", C.c_double),
        ("fast_used", C.c_int),
        ("fast_blocked", C.c_bool),
        ("diagnostic", C.c_bool),
    ]


@pytest.fixture(scope="module")
def jalc_lib(tmp_path_factory):
    compiler = shutil.which(os.environ.get("CC", "cc"))
    assert compiler, "C11 compiler required"
    out = tmp_path_factory.mktemp("jalc_c11") / "libtais_jalc.so"
    src = ROOT / "src/tais/closed_loop/c11/tais_jalc.c"
    inc = ROOT / "src/tais/closed_loop/c11"
    subprocess.run(
        [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", "-shared", "-fPIC", "-I", str(inc), str(src), "-lm", "-o", str(out)],
        check=True,
    )
    lib = C.CDLL(str(out))
    lib.tais_jalc_sizeof_ctx.restype = C.c_size_t
    lib.tais_jalc_init.argtypes = [C.c_void_p, C.c_int, C.POINTER(C.c_double), C.POINTER(CParams), C.c_int]
    lib.tais_jalc_init.restype = C.c_bool
    lib.tais_jalc_update.argtypes = [
        C.c_void_p,
        C.c_double,
        C.POINTER(C.c_double),
        C.POINTER(C.c_bool),
        C.POINTER(C.c_bool),
        C.POINTER(C.c_int),
        C.POINTER(C.c_uint32),
        C.POINTER(CTelemetry),
        C.POINTER(CDecision),
    ]
    lib.tais_jalc_update.restype = C.c_bool
    lib.tais_jalc_on_tx_result.argtypes = [C.c_void_p, C.c_double, C.c_bool, C.POINTER(CTelemetry)]
    lib.tais_jalc_on_tx_result.restype = C.c_double
    return lib


def _to_c_telem(telem: LinkTelemetry | None, names: tuple[str, ...]) -> CTelemetry:
    ct = CTelemetry()
    if telem is None:
        ct.present = False
        return ct
    ct.present = True
    ct.loss_ema = telem.loss_ema
    ct.bw_congested = telem.bw_congested
    ct.bw_tokens_bytes = telem.bw_tokens_bytes
    for i, n in enumerate(names):
        if n in telem.last_confirmed_finite_t:
            ct.has_confirmed_finite[i] = True
            ct.last_confirmed_finite_t[i] = telem.last_confirmed_finite_t[n]
        else:
            ct.has_confirmed_finite[i] = False
            ct.last_confirmed_finite_t[i] = 0.0
    return ct


@pytest.mark.parametrize("variant", ["ObsOnly", "AoI", "Full"])
@pytest.mark.parametrize("scenario", ["clean_both", "missing_temperature_cross", "drift_temperature_same"])
@pytest.mark.parametrize("loss_rate,burst", [(0.0, False), (0.30, False), (0.0, True)])
def test_python_c11_exact_parity(jalc_lib, variant, scenario, loss_rate, burst):
    import json

    cfg = load()
    phase4_plan = json.loads((ROOT / "configs/phase4.json").read_text())
    trace = generate(phase4_plan["ma1_plan"]["generator"], 1000, scenario)
    names = tuple(cfg["channels"])

    sched = Scheduler(cfg, confirmation=False, multiplier=1.0)
    noise_map = {n: sched.b["adaptive"]["channels"][n]["noise_floor"] for n in names}
    params = ClosedLoopParams()

    py_ctrl = JointAdaptiveController(noise_map, params=params, variant=variant)
    c_buf = C.create_string_buffer(jalc_lib.tais_jalc_sizeof_ctx())
    c_noise = (C.c_double * 2)(noise_map[names[0]], noise_map[names[1]])
    c_params = CParams(
        params.fallback_interval_s,
        params.diag_interval_s,
        params.aoi_cap_quiet_s,
        params.aoi_cap_active_s,
        params.loss_redundancy_threshold,
    )
    assert jalc_lib.tais_jalc_init(c_buf, 2, c_noise, C.byref(c_params), VARIANT_TO_INT[variant])

    link = StatefulLinkModel(
        LinkProfile("test", loss_rate=loss_rate, burst_mode=burst),
        receiver=CoreReceiver(layout_id=1),
        seed=1000,
        label=f"{variant}:{scenario}",
    )

    next_sample = 0.0
    compared = 0
    try:
        for row in trace.observed:
            t = float(row["timestamp"])
            if t < next_sample - 1e-9:
                continue
            vals = {n: row[n] for n in names}
            d = sched.update(t, vals)
            telem = link.telemetry(t)

            py_dec = py_ctrl.update(t, vals, d.active, d.health, telemetry=telem)

            c_vals = (C.c_double * 2)(
                float(vals[names[0]]) if (vals[names[0]] is not None and math.isfinite(vals[names[0]])) else float("nan"),
                float(vals[names[1]]) if (vals[names[1]] is not None and math.isfinite(vals[names[1]])) else float("nan"),
            )
            c_valid = (C.c_bool * 2)(
                vals[names[0]] is not None and math.isfinite(vals[names[0]]),
                vals[names[1]] is not None and math.isfinite(vals[names[1]]),
            )
            c_active = (C.c_bool * 2)(bool(d.active[names[0]]), bool(d.active[names[1]]))
            c_hstate = (C.c_int * 2)(STATE_TO_INT[d.health[names[0]]["state"]], STATE_TO_INT[d.health[names[1]]["state"]])
            c_hflags = (C.c_uint32 * 2)(int(d.health[names[0]]["flags"]), int(d.health[names[1]]["flags"]))
            c_telem = _to_c_telem(telem, names)
            c_dec = CDecision()

            assert jalc_lib.tais_jalc_update(
                c_buf, t, c_vals, c_valid, c_active, c_hstate, c_hflags, C.byref(c_telem), C.byref(c_dec)
            )

            assert OBS_MODES[c_dec.obs_mode] == py_dec.obs_mode, f"mode mismatch at t={t}"
            assert c_dec.upload == py_dec.upload, f"upload mismatch at t={t}"
            assert c_dec.redundancy_k == py_dec.redundancy_k, f"K mismatch at t={t}"
            assert c_dec.fast_used == py_dec.fast_used
            assert c_dec.fast_blocked == py_dec.fast_blocked
            assert c_dec.diagnostic == py_dec.diagnostic
            assert abs(c_dec.next_sample_s - py_dec.next_sample_s) < 1e-9
            assert abs(c_dec.interval_s - py_dec.interval_s) < 1e-9
            assert abs(c_dec.score - py_dec.score) < 1e-9

            next_sample = py_dec.next_sample_s
            if py_dec.upload:
                rec = {"timestamp": t, "values": vals, "active": d.active, "health": d.health}
                env = envelope_from_record(rec, layout_id=1)
                frame = encode(env, layout_id=1)
                outcomes = link.send(t, frame, env, redundancy_k=py_dec.redundancy_k)
                delivered = any(o.delivered for o in outcomes)
                post = link.telemetry(t)
                py_next = py_ctrl.on_tx_result(t, delivered, post)
                c_post = _to_c_telem(post, names)
                c_next = jalc_lib.tais_jalc_on_tx_result(c_buf, t, delivered, C.byref(c_post))
                assert abs(c_next - py_next) < 1e-9, f"on_tx_result mismatch at t={t}"
                next_sample = py_next
            compared += 1
    finally:
        for tr in sched.trust.values():
            tr.close()
    assert compared > 30


def test_e220_hardware_trace_model_replays_authentic_outcomes():
    regimes = load_e220_regimes()
    assert set(regimes) == {"e220_random_20", "e220_random_30", "e220_burst_20", "e220_burst_30"}
    prof = regimes["e220_burst_30"][0]
    link = TraceDrivenLinkModel(prof, seed=1200, label="smoke")
    env = {
        "timestamp": 0,
        "values": {"temperature": 24.0, "humidity": 45.0},
        "environment_active": {"temperature": False, "humidity": False},
        "health": {
            "temperature": {"state": "HEALTHY", "score": 100, "flags": 0},
            "humidity": {"state": "HEALTHY", "score": 100, "flags": 0},
        },
    }
    for t in range(len(prof.outcomes)):
        e = dict(env, timestamp=t)
        f = encode(e, layout_id=1)
        link.send(float(t), f, e, redundancy_k=1)
    assert link.counts["delivered"] == sum(prof.outcomes)
    assert link.counts["loss_drops"] == len(prof.outcomes) - sum(prof.outcomes)
    assert link.total_airtime_ms > 0.0
