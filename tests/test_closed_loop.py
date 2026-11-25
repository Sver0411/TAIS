"""Unit tests for Phase 5 lean 3D closed-loop controller (TAIS-JALC)."""
import math
import pytest

from tais.config import load
from tais.core_stream import CoreReceiver
from tais.wire_codec import decode
from tais.closed_loop import (
    OBS_MODES,
    ClosedLoopParams,
    ClosedLoopSender,
    JointAdaptiveController,
    LinkProfile,
    LinkTelemetry,
    StatefulLinkModel,
)


def _healthy():
    return {
        "temperature": {"state": "HEALTHY", "score": 100, "flags": 0},
        "humidity": {"state": "HEALTHY", "score": 100, "flags": 0},
    }


def test_params_and_state_set():
    p = ClosedLoopParams()
    p.validate()
    assert set(OBS_MODES) == {"QUIET_ECO", "PROBE", "TRACK", "SAFE_FALLBACK", "DIAG_VERIFY"}
    assert (p.fallback_interval_s, p.diag_interval_s, p.aoi_cap_quiet_s, p.aoi_cap_active_s, p.loss_redundancy_threshold) == (
        20.0,
        15.0,
        45.0,
        20.0,
        0.10,
    )


def test_strict_causality_prefix_invariance():
    """Modifying future source rows must never alter any earlier decision or frame."""
    cfg = load()
    rows_a = [
        {"timestamp": t, "temperature": 24.0 + (3.5 if 200 <= t <= 240 else 0.0), "humidity": 45.0}
        for t in range(400)
    ]
    rows_b = [dict(r) for r in rows_a]
    for t in range(250, 400):
        rows_b[t]["temperature"] = 99.0  # future perturbation after t=250

    def run(rows):
        link = StatefulLinkModel(LinkProfile("loss_15", loss_rate=0.15), seed=1000, label="causal")
        sender = ClosedLoopSender(cfg, variant="Full", link=link)
        out = []
        try:
            for r in rows:
                res = sender.push(r)
                if res is not None and r["timestamp"] < 250:
                    out.append((res["record"]["timestamp"], res["record"]["interval"], res["record"]["upload"], res["frame"]))
        finally:
            sender.close()
        return out

    assert run(rows_a) == run(rows_b)


def test_aoi_hard_cap_invariant_lossless():
    """Under lossless transport, finite-value AoI must never exceed aoi_cap_quiet_s=45s."""
    cfg = load()
    params = ClosedLoopParams()
    link = StatefulLinkModel(LinkProfile("loss_0", loss_rate=0.0), seed=1001, label="aoi")
    sender = ClosedLoopSender(cfg, params=params, variant="AoI", link=link)
    rows = [{"timestamp": t, "temperature": 24.0, "humidity": 45.0} for t in range(600)]
    try:
        for r in rows:
            sender.push(r)
    finally:
        sender.close()

    delivered_ts = [e["timestamp"] for e in link.delivered_frames]
    assert delivered_ts[0] == 0
    for a, b in zip(delivered_ts, delivered_ts[1:]):
        # Strictly <= aoi_cap_quiet_s = 45s between consecutive finite deliveries
        assert b - a <= params.aoi_cap_quiet_s + 1e-9, f"AoI gap {b - a} exceeded {params.aoi_cap_quiet_s}"
    assert (599 - delivered_ts[-1]) <= params.aoi_cap_quiet_s


def test_null_frame_does_not_reset_finite_aoi_and_triggers_diag_verify():
    """Missing/NaN readings trigger DIAG_VERIFY (15s) and do not reset finite AoI."""
    ctrl = JointAdaptiveController({"temperature": 0.15, "humidity": 0.8}, variant="AoI")
    d0 = ctrl.update(0.0, {"temperature": 24.0, "humidity": 45.0}, {"temperature": False, "humidity": False}, _healthy())
    assert d0.upload is True
    assert d0.obs_mode == "QUIET_ECO"

    # At t=30, temperature becomes None (missing); humidity stays finite
    h_miss = {
        "temperature": {"state": "DEGRADED", "score": 70, "flags": 16},
        "humidity": {"state": "HEALTHY", "score": 100, "flags": 0},
    }
    d1 = ctrl.update(30.0, {"temperature": None, "humidity": 45.0}, {"temperature": False, "humidity": False}, h_miss)
    assert d1.obs_mode == "DIAG_VERIFY"
    assert d1.interval_s == 15.0
    assert d1.upload is True  # validity + health_edge
    # Temperature's finite timestamp must STILL be 0.0, NOT 30.0!
    assert ctrl._last_sent_finite_t["temperature"] == 0.0
    assert ctrl._last_sent_finite_t["humidity"] == 30.0

    # At t=45, temperature recovers to finite 24.0: finite age is 45s -> immediate upload
    d2 = ctrl.update(45.0, {"temperature": 24.0, "humidity": 45.0}, {"temperature": False, "humidity": False}, _healthy())
    assert d2.upload is True
    assert any(r in ("validity:temperature", "aoi_cap:temperature") for r in d2.reasons)
    assert ctrl._last_sent_finite_t["temperature"] == 45.0


def test_rolling_fast_budget_and_safe_fallback():
    """Sustained high-risk oscillation must cap fast samples <= 6/120s and enter SAFE_FALLBACK."""
    ctrl = JointAdaptiveController({"temperature": 0.15, "humidity": 0.8}, variant="ObsOnly")
    t = 0.0
    modes = []
    max_fast = 0
    for i in range(40):
        # Step continuously so score stays high
        val = 24.0 + i * 2.5
        d = ctrl.update(t, {"temperature": val, "humidity": 45.0}, {"temperature": False, "humidity": False}, _healthy())
        modes.append(d.obs_mode)
        max_fast = max(max_fast, d.fast_used)
        t = d.next_sample_s
    assert max_fast <= 6
    assert "SAFE_FALLBACK" in modes
    assert "TRACK" in modes


def test_lossy_link_redundancy_and_binary_v1_compatibility():
    """When loss_ema >= 0.10, event_edge uses K=2 Binary v1 copies decoded cleanly by CoreReceiver."""
    ctrl = JointAdaptiveController({"temperature": 0.15, "humidity": 0.8}, variant="Full")
    # Initial sample
    d0 = ctrl.update(0.0, {"temperature": 24.0, "humidity": 45.0}, {"temperature": False, "humidity": False}, _healthy())
    assert d0.redundancy_k == 1

    # Simulate lossy telemetry (loss_ema = 0.25 >= 0.10) with an event onset
    telem = LinkTelemetry(
        loss_ema=0.25,
        bw_congested=False,
        bw_tokens_bytes=500.0,
        last_confirmed_finite_t={"temperature": 0.0, "humidity": 0.0},
    )
    d1 = ctrl.update(
        d0.next_sample_s,
        {"temperature": 28.0, "humidity": 45.0},
        {"temperature": True, "humidity": False},
        _healthy(),
        telemetry=telem,
    )
    assert d1.upload is True
    assert "event_edge:temperature" in d1.reasons
    assert d1.redundancy_k == 2
    assert d1.delta_margin_s == 5.0

    # End-to-end Binary v1 encode/decode + CoreReceiver duplicate handling under K=2
    cfg = load()
    rx = CoreReceiver(layout_id=1)
    link = StatefulLinkModel(LinkProfile("loss_0", loss_rate=0.0), receiver=rx, seed=1002, label="v1")
    sender = ClosedLoopSender(cfg, variant="Full", link=link)
    try:
        res = sender.push({"timestamp": 0, "temperature": 24.0, "humidity": 45.0})
    finally:
        sender.close()
    decoded = decode(res["frame"], expected_layout_id=1)
    assert decoded["timestamp"] == 0
    assert math.isclose(decoded["values"]["temperature"], 24.0)
    # Sending the exact same Binary v1 frame again is handled as duplicate by CoreReceiver
    dup = rx.receive(res["frame"])
    assert dup["status"] == "duplicate"
    assert rx.counts["duplicate"] == 1


def test_bandwidth_token_bucket_and_ge_burst():
    """Token bucket drops excess frames and GE burst model produces drops."""
    rx = CoreReceiver(layout_id=1)
    profile = LinkProfile("tight", loss_rate=0.0, bandwidth_bpm=600.0)
    link = StatefulLinkModel(profile, receiver=rx, seed=1003, label="bw")
    env = {
        "timestamp": 0,
        "values": {"temperature": 24.0, "humidity": 45.0},
        "environment_active": {"temperature": False, "humidity": False},
        "health": _healthy(),
    }
    from tais.wire_codec import encode
    # Burst 10 frames at t=0..9 (10*36=360B > initial 112B bucket + 90B refill)
    for t in range(10):
        e = dict(env, timestamp=t)
        f = encode(e, layout_id=1)
        link.send(float(t), f, e, redundancy_k=1)
    assert link.counts["bw_drops"] > 0
    assert link.telemetry(9.0).bw_congested is True

    # GE burst mode
    ge_link = StatefulLinkModel(LinkProfile("burst", burst_mode=True), seed=1003, label="ge")
    for t in range(100):
        e = dict(env, timestamp=t)
        f = encode(e, layout_id=1)
        ge_link.send(float(t), f, e, redundancy_k=1)
    assert 0 < ge_link.counts["loss_drops"] < 100


def test_total_blackout_respects_fast_budget_and_recovers_after_drop():
    """Sustained 100% loss must never breach rolling fast budget; partial loss triggers retry."""
    cfg = load()
    blackout = StatefulLinkModel(LinkProfile("loss_100", loss_rate=1.0), seed=1003, label="blackout")
    sender = ClosedLoopSender(cfg, variant="Full", link=blackout)
    rows = [{"timestamp": t, "temperature": 24.0, "humidity": 45.0} for t in range(400)]
    max_fast = 0
    try:
        for r in rows:
            res = sender.push(r)
            if res is not None:
                max_fast = max(max_fast, res["record"]["closed_loop"]["fast_used"])
    finally:
        sender.close()
    assert max_fast <= 6
    assert blackout.counts["delivered"] == 0
    assert blackout.counts["loss_drops"] > 0

    # Under 30% loss, Full recovers delivered frames and keeps finite AoI well below open-loop 120s
    lossy = StatefulLinkModel(LinkProfile("loss_30", loss_rate=0.30), seed=1003, label="loss30")
    sender2 = ClosedLoopSender(cfg, variant="Full", link=lossy)
    try:
        for r in rows:
            sender2.push(r)
    finally:
        sender2.close()
    ts = [e["timestamp"] for e in lossy.delivered_frames]
    assert len(ts) >= 5
    max_gap = max(b - a for a, b in zip(ts, ts[1:]))
    assert max_gap < 90.0

