"""Phase 5 lean 3D Joint Adaptive Closed-Loop Controller (TAIS-JALC).

Strictly causal, zero-CUSUM, Binary v1 compatible, additive wrapper around
the frozen Scheduler (SensorTrust C11 + AdaptiveSense ChangeAnalyzer).
"""
from collections import deque
from copy import deepcopy
from dataclasses import asdict
import json
import math
from statistics import median

from tais.core_stream import CoreSender
from tais.joint_upload import Upload
from tais.replay import finite
from tais.scheduler import Scheduler
from tais.wire_codec import MAX_FRAME_BYTES, encode, envelope_from_record
from .link_model import StatefulLinkModel
from .state import ClosedLoopParams, JointDecision, LinkTelemetry

# Frozen structural constants inherited from Phase 4 / AdaptiveSense (not tuned).
_MIN_INTERVAL_S = 5.0
_MAX_INTERVAL_S = 60.0
_QUIET_INTERVAL_S = 30.0
_WINDOW_SAMPLES = 9
_MAD_MULTIPLIER = 1.4826
_ENTER_Z = 3.0
_RISK_ENTER = 1.0
_RISK_EXIT = 0.5
_HORIZON_S = 30.0
_TREND_CONSISTENCY = 0.75
_CONFIRM_SAMPLES = 2
_FAST_WINDOW_S = 120.0
_FAST_LIMIT = 6
_MAX_BURST_S = 30.0
_FALLBACK_HOLD_S = 30.0
_DEADBAND_MULT = 2.0


class JointAdaptiveController:
    """4+1 state machine coupling observation state, SensorTrust health & link telemetry.

    Ablation modes:
      - 'ObsOnly': 4+1 observation/fallback/diagnostic sampling + frozen 120s Upload.
      - 'AoI':     ObsOnly + AoI-Sampling hard reservation + per-channel finite AoI cap.
      - 'Full':    AoI + closed-loop LinkTelemetry (confirmed AoI, K=2 edge redundancy,
                   bandwidth-aware prioritization).
    """

    def __init__(
        self,
        noise: dict[str, float],
        params: ClosedLoopParams | None = None,
        variant: str = "Full",
    ):
        if variant not in ("ObsOnly", "AoI", "Full"):
            raise ValueError(f"Unsupported JALC variant: {variant}")
        self.params = params or ClosedLoopParams()
        self.params.validate()
        self.variant = variant
        self.noise = dict(noise)
        if not self.noise or any(not math.isfinite(v) or v <= 0 for v in self.noise.values()):
            raise ValueError("Positive finite channel noise scales required")

        # Per-channel bounded healthy finite histories (past-only, no CUSUM)
        self.history: dict[str, deque] = {
            n: deque(maxlen=_WINDOW_SAMPLES) for n in self.noise
        }
        self.fast_times: deque = deque()
        self.last_t: float | None = None
        self.last_interval: float | None = None

        # 4+1 observation state machine
        self.obs_mode: str = "QUIET_ECO"
        self.fallback_until: float = -1.0
        self.burst_start: float | None = None
        self.confirmed: int = 0
        self.lead: tuple | None = None

        # Upload & per-channel finite AoI bookkeeping
        self._legacy_upload = Upload(self.noise, heartbeat=120)
        self._last_sent_snapshot: dict | None = None
        self._last_sent_finite_t: dict[str, float | None] = {n: None for n in self.noise}
        self._pending_snapshot: dict | None = None
        self._last_obs_interval: float = _QUIET_INTERVAL_S
        self._last_aoi_cap: float = self.params.aoi_cap_quiet_s
        self._last_delta_margin: float = 0.0
        self._last_values: dict = {}

    def _extract_features(self, t: float, values: dict, health: dict) -> tuple[dict, bool]:
        features = {}
        diagnostic = False
        for n, nf in self.noise.items():
            v = values.get(n)
            eligible = finite(v) and health[n]["state"] == "HEALTHY"
            h = self.history[n]
            if not eligible:
                h.clear()
                diagnostic = True
                continue
            center = median(x for _, x in h) if h else v
            scale = (
                max(nf, _MAD_MULTIPLIER * median(abs(x - center) for _, x in h))
                if h
                else nf
            )
            slope = 0.0
            prediction = None
            consistency = 0.0
            if len(h) >= 3:
                pts = list(h)
                slopes = [
                    (b - a) / (tb - ta)
                    for i, (ta, a) in enumerate(pts)
                    for tb, b in pts[i + 1 :]
                    if tb > ta
                ]
                if slopes:
                    slope = median(slopes)
                    prediction = median(x - slope * tt for tt, x in pts) + slope * t
                    changes = [b - a for (_, a), (_, b) in zip(pts, pts[1:]) if b != a]
                    consistency = (
                        sum(d * slope > 0 for d in changes) / len(changes)
                        if changes
                        else 0.0
                    )
            delta = v - center
            z = abs(delta) / scale
            trend = (
                abs(slope) * _HORIZON_S / (_ENTER_Z * scale)
                if consistency >= _TREND_CONSISTENCY
                else 0.0
            )
            residual = (
                abs(v - prediction) / (_ENTER_Z * scale)
                if prediction is not None
                else 0.0
            )
            risk = max(z / _ENTER_Z, trend, residual)
            sign = 1 if delta > 0 else (-1 if delta < 0 else 0)
            risk_sign = (
                (1 if slope > 0 else -1)
                if trend >= max(residual, z / _ENTER_Z) and trend > 0
                else sign
            )
            features[n] = dict(
                z=z,
                scale=scale,
                risk=risk,
                sign=risk_sign,
            )
            h.append((t, v))
        return features, diagnostic

    def _enter_fallback(self, t: float) -> float:
        self.obs_mode = "SAFE_FALLBACK"
        self.fallback_until = t + _FALLBACK_HOLD_S
        self.burst_start = None
        self.confirmed = 0
        self.lead = None
        return self.params.fallback_interval_s

    def _step_obs_fsm(
        self, t: float, score: float, lead: tuple | None, diagnostic: bool
    ) -> tuple[float, bool]:
        p = self.params
        fast_blocked = False

        if self.obs_mode == "SAFE_FALLBACK":
            if t < self.fallback_until:
                interval = min(p.fallback_interval_s, p.diag_interval_s) if diagnostic else p.fallback_interval_s
                return interval, False
            self.obs_mode = "QUIET_ECO"

        def _can_admit_fast() -> bool:
            due = t + _MIN_INTERVAL_S
            used = sum(s > due - _FAST_WINDOW_S for s in self.fast_times)
            return used < _FAST_LIMIT

        if self.burst_start is not None:
            if (
                (t - self.burst_start) >= _MAX_BURST_S
                or score < _RISK_EXIT
                or lead != self.lead
            ):
                return self._enter_fallback(t), False
            if not _can_admit_fast():
                return self._enter_fallback(t), True
            self.confirmed += 1
            self.obs_mode = "TRACK" if self.confirmed >= _CONFIRM_SAMPLES else "PROBE"
            return _MIN_INTERVAL_S, False

        if score >= _RISK_ENTER:
            if not _can_admit_fast():
                return self._enter_fallback(t), True
            self.burst_start = t
            self.confirmed = 1
            self.lead = lead
            self.obs_mode = "PROBE"
            return _MIN_INTERVAL_S, False

        if score >= _RISK_EXIT:
            # Merged WATCH + PROBE: moderate risk uses intermediate 15s probe interval
            self.obs_mode = "PROBE"
            return min(p.diag_interval_s, p.fallback_interval_s), False

        if diagnostic:
            self.obs_mode = "DIAG_VERIFY"
            return p.diag_interval_s, False

        self.obs_mode = "QUIET_ECO"
        return _QUIET_INTERVAL_S, False

    def _effective_rx_finite_t(
        self, telemetry: LinkTelemetry | None
    ) -> dict[str, float | None]:
        if self.variant == "Full" and telemetry is not None:
            return {
                n: telemetry.last_confirmed_finite_t.get(n)
                for n in self.noise
            }
        return dict(self._last_sent_finite_t)

    def _decide_upload(
        self,
        t: float,
        values: dict,
        active: dict,
        health: dict,
        aoi_cap_s: float,
        delta_margin_s: float,
        rx_finite_t: dict[str, float | None],
        telemetry: LinkTelemetry | None,
        min_next_gap_s: float = _MIN_INTERVAL_S,
    ) -> tuple[list[str], int]:
        if self.variant == "ObsOnly":
            reasons = self._legacy_upload.decide(t, values, active, health)
            return reasons, 1

        now = dict(
            values={n: v if finite(v) else None for n, v in values.items()},
            active=dict(active),
            health=deepcopy(health),
        )
        critical_reasons: list[str] = []
        routine_reasons: list[str] = []
        edge_critical = False

        if self._last_sent_snapshot is None:
            critical_reasons.append("first")
            edge_critical = True
        else:
            prev = self._last_sent_snapshot
            for n, v in now["values"].items():
                old = prev["values"][n]
                if (v is None) != (old is None):
                    critical_reasons.append("validity:" + n)
                    edge_critical = True
                elif v is not None and abs(v - old) >= _DEADBAND_MULT * self.noise[n]:
                    routine_reasons.append("deadband:" + n)
                if active[n] != prev["active"][n]:
                    critical_reasons.append("event_edge:" + n)
                    edge_critical = True
                h = health[n]
                ph = prev["health"][n]
                if (h["state"], h["flags"]) != (ph["state"], ph["flags"]):
                    critical_reasons.append("health_edge:" + n)
                    edge_critical = True

                # Per-channel finite-value AoI hard cap (null frames never reset finite AoI)
                if v is not None:
                    last_ok = rx_finite_t.get(n)
                    if last_ok is None:
                        critical_reasons.append("aoi_cap:" + n)
                    else:
                        eff_cap = max(_MIN_INTERVAL_S, aoi_cap_s - delta_margin_s)
                        age_now = t - last_ok
                        # Proactive guard: if next admissible sample t+min_next_gap_s would exceed
                        # eff_cap, transmit now to guarantee strict zero-violation under lossless link.
                        if age_now >= eff_cap - 1e-9 or (age_now + min_next_gap_s) > eff_cap + 1e-9:
                            critical_reasons.append("aoi_cap:" + n)

        # In Full mode under bandwidth congestion, suppress routine-only deadband chatter
        if self.variant == "Full" and telemetry is not None and telemetry.bw_congested:
            reasons = critical_reasons
        else:
            reasons = critical_reasons + routine_reasons

        # Weak-link redundancy: K=2 ONLY for critical event_edge / health_edge when lossy
        redundancy_k = 1
        if (
            self.variant == "Full"
            and telemetry is not None
            and telemetry.loss_ema >= self.params.loss_redundancy_threshold
            and any(r.startswith(("event_edge:", "health_edge:")) for r in reasons)
        ):
            if telemetry.bw_tokens_bytes >= 2.0 * MAX_FRAME_BYTES:
                redundancy_k = 2

        if reasons:
            if self.variant == "Full" and telemetry is not None:
                # Commit confirmed snapshot only after causal link delivery feedback
                self._pending_snapshot = now
            else:
                self._last_sent_snapshot = now
                for n, v in now["values"].items():
                    if v is not None:
                        self._last_sent_finite_t[n] = t

        return reasons, redundancy_k

    def update(
        self,
        t: float,
        values: dict,
        active: dict,
        health: dict,
        telemetry: LinkTelemetry | None = None,
    ) -> JointDecision:
        if not math.isfinite(t) or t < 0:
            raise ValueError("Timestamp must be finite and nonnegative")
        if self.last_t is not None and t < self.last_t + self.last_interval - 1e-9:
            raise ValueError("Acquisitions must respect previously scheduled next_sample_s")

        # Update rolling fast acquisition window using actual acquisitions only
        if self.last_t is not None and (t - self.last_t) <= _MIN_INTERVAL_S + 1e-9:
            self.fast_times.append(t)
        while self.fast_times and self.fast_times[0] <= t - _FAST_WINDOW_S:
            self.fast_times.popleft()
        if len(self.fast_times) > _FAST_LIMIT:
            raise ValueError("Actual acquisitions exceeded rolling fast budget")

        features, diagnostic = self._extract_features(t, values, health)
        name = max(features, key=lambda n: features[n]["risk"]) if features else None
        score = features[name]["risk"] if name is not None else 0.0
        lead = (name, features[name]["sign"]) if name is not None else None

        obs_interval, fast_blocked = self._step_obs_fsm(t, score, lead, diagnostic)
        if diagnostic:
            obs_interval = min(obs_interval, self.params.diag_interval_s)
        obs_interval = max(_MIN_INTERVAL_S, min(_MAX_INTERVAL_S, obs_interval))

        # Dynamic AoI cap based on observation activity
        is_active = self.obs_mode in ("PROBE", "TRACK") or any(active.values())
        aoi_cap_s = (
            self.params.aoi_cap_active_s if is_active else self.params.aoi_cap_quiet_s
        )
        is_lossy = (
            self.variant == "Full"
            and telemetry is not None
            and telemetry.loss_ema >= self.params.loss_redundancy_threshold
        )
        delta_margin_s = _MIN_INTERVAL_S if is_lossy else 0.0

        due_fast = t + _MIN_INTERVAL_S
        can_fast_now = sum(s > due_fast - _FAST_WINDOW_S for s in self.fast_times) < _FAST_LIMIT
        min_next_gap_s = _MIN_INTERVAL_S if can_fast_now else (_MIN_INTERVAL_S + 1.0)

        rx_finite_t = self._effective_rx_finite_t(telemetry)
        reasons, redundancy_k = self._decide_upload(
            t,
            values,
            active,
            health,
            aoi_cap_s,
            delta_margin_s,
            rx_finite_t,
            telemetry,
            min_next_gap_s=min_next_gap_s,
        )
        upload = bool(reasons)

        # Compute post-decision expected receiver finite timestamp for next reservation
        next_finite_ref: dict[str, float | None] = {}
        for n in self.noise:
            v = values.get(n)
            if upload and finite(v) and self.variant != "Full":
                next_finite_ref[n] = t
            elif upload and finite(v) and self.variant == "Full":
                # Optimistically assume current tx may succeed; if dropped, telemetry corrects on next tick
                next_finite_ref[n] = t
            else:
                next_finite_ref[n] = rx_finite_t.get(n)

        # AoI-Sampling hard reservation:
        # t_next = min(t + I_obs, max(t + I_min, t_last_rx_finite + T_AoI_max - delta_margin))
        t_next = t + obs_interval
        if self.variant in ("AoI", "Full"):
            finite_refs = [
                ts for n, ts in next_finite_ref.items()
                if ts is not None and finite(values.get(n))
            ]
            if finite_refs:
                oldest_finite_t = min(finite_refs)
                t_aoi_due = oldest_finite_t + aoi_cap_s - delta_margin_s
                t_next = min(t + obs_interval, max(t + min_next_gap_s, t_aoi_due))

        interval = max(min_next_gap_s if not can_fast_now else _MIN_INTERVAL_S, min(_MAX_INTERVAL_S, t_next - t))
        t_next = t + interval
        self.last_t = t
        self.last_interval = interval
        self._last_obs_interval = obs_interval
        self._last_aoi_cap = aoi_cap_s
        self._last_delta_margin = delta_margin_s
        self._last_values = dict(values)

        ch_ages = {
            n: (t - rx_finite_t[n] if rx_finite_t.get(n) is not None else None)
            for n in self.noise
        }
        return JointDecision(
            t=t,
            obs_mode=self.obs_mode,
            obs_interval_s=obs_interval,
            next_sample_s=t_next,
            interval_s=interval,
            aoi_cap_s=aoi_cap_s,
            delta_margin_s=delta_margin_s,
            upload=upload,
            reasons=tuple(reasons),
            redundancy_k=redundancy_k,
            score=score,
            fast_used=len(self.fast_times),
            fast_blocked=fast_blocked,
            diagnostic=diagnostic,
            channel_finite_ages=ch_ages,
        )

    def on_tx_result(
        self, t: float, delivered: bool, telemetry: LinkTelemetry
    ) -> float:
        """Apply strictly causal post-tx ACK/NACK feedback at time t to next_sample_s."""
        if self.variant != "Full":
            return t + (self.last_interval or _QUIET_INTERVAL_S)
        if delivered and self._pending_snapshot is not None:
            self._last_sent_snapshot = self._pending_snapshot
            for n, v in self._pending_snapshot["values"].items():
                if v is not None:
                    self._last_sent_finite_t[n] = t
            self._pending_snapshot = None
            return t + (self.last_interval or _QUIET_INTERVAL_S)

        self._pending_snapshot = None
        if delivered:
            return t + (self.last_interval or _QUIET_INTERVAL_S)

        # Delivery failed: recompute AoI-bounded retry interval using confirmed finite rx times,
        # while strictly obeying rolling fast budget and bandwidth congestion backoff.
        margin = (
            _MIN_INTERVAL_S
            if telemetry.loss_ema >= self.params.loss_redundancy_threshold
            else self._last_delta_margin
        )
        finite_channels = [n for n in self.noise if finite(self._last_values.get(n))]
        refs = [telemetry.last_confirmed_finite_t.get(n) for n in finite_channels]
        if any(r is None for r in refs):
            desired = t + _MIN_INTERVAL_S
        elif refs:
            desired = min(refs) + self._last_aoi_cap - margin
        else:
            desired = t + self._last_obs_interval

        t_next = min(t + self._last_obs_interval, max(t + _MIN_INTERVAL_S, desired))
        interval = max(_MIN_INTERVAL_S, min(_MAX_INTERVAL_S, t_next - t))

        # Respect rolling fast budget and bandwidth congestion so drops never cause a retry storm
        if interval <= _MIN_INTERVAL_S + 1e-9:
            due = t + _MIN_INTERVAL_S
            used = sum(s > due - _FAST_WINDOW_S for s in self.fast_times)
            if used >= _FAST_LIMIT or telemetry.bw_congested:
                interval = min(self._last_obs_interval, self.params.fallback_interval_s)
                interval = max(_MIN_INTERVAL_S, interval)
        self.last_interval = interval
        return t + interval


class ClosedLoopPolicy:
    """Adapter wrapping unchanged Scheduler with JointAdaptiveController."""

    def __init__(
        self,
        cfg: dict,
        params: ClosedLoopParams | None = None,
        variant: str = "Full",
    ):
        self.base = Scheduler(deepcopy(cfg), confirmation=False, multiplier=1.0)
        self.trust = self.base.trust
        noise = {
            n: self.base.b["adaptive"]["channels"][n]["noise_floor"]
            for n in cfg["channels"]
        }
        self.controller = JointAdaptiveController(noise, params=params, variant=variant)
        self.last_decision: JointDecision | None = None

    def update(self, t: float, values: dict, telemetry: LinkTelemetry | None = None):
        d = self.base.update(t, values)
        jd = self.controller.update(t, values, d.active, d.health, telemetry=telemetry)
        d.interval = jd.interval_s
        d.upload = jd.upload
        d.reasons = list(jd.reasons)
        self.last_decision = jd
        return d


class ClosedLoopSender(CoreSender):
    """Causal stream sender with optional closed-loop StatefulLinkModel feedback."""

    def __init__(
        self,
        cfg: dict,
        params: ClosedLoopParams | None = None,
        variant: str = "Full",
        link: StatefulLinkModel | None = None,
        layout_id: int = 1,
    ):
        super().__init__(cfg, layout_id=layout_id)
        self.close()
        self.scheduler = ClosedLoopPolicy(cfg, params=params, variant=variant)
        self.link = link

    def push(self, row: dict):
        t = row["timestamp"]
        if t <= self.last_source:
            raise ValueError("source timestamps must strictly increase; no sorting or filling")
        self.last_source = t
        self.counts["source_rows"] += 1
        if t < self.next_sample - 1e-9:
            return None
        values = {n: row[n] for n in self.names}
        telemetry = self.link.telemetry(t) if self.link is not None else None
        d = self.scheduler.update(t, values, telemetry=telemetry)
        jd = self.scheduler.last_decision

        record = {"timestamp": t, "values": values, "payload_bytes": 0, **asdict(d)}
        reports = []
        for name in self.names:
            if d.active[name]:
                if not self._open[name]:
                    self._open[name] = True
                    self._sent[name] = False
                if d.upload and not self._sent[name]:
                    reports.append(
                        dict(channel=name, start_s=t, end_s=t, event_type="detected")
                    )
                    self._sent[name] = True
            else:
                self._open[name] = False

        self.next_sample = jd.next_sample_s
        self.counts["samples"] += 1
        for name, health in d.health.items():
            self.health_counts[name + ":" + health["state"]] += 1
        self.last_sample = record

        frame = None
        envelope = None
        link_outcomes = []
        if d.upload:
            envelope = envelope_from_record(record, self.layout_id)
            frame = encode(envelope, self.layout_id)
            record["payload_bytes"] = len(
                json.dumps(envelope, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            )
            self.counts["uploads"] += 1
            self.counts["binary_bytes"] += len(frame) * jd.redundancy_k
            self.last_frame_bytes = len(frame)
            self.last_upload = t
            if self.link is not None:
                link_outcomes = self.link.send(t, frame, envelope, redundancy_k=jd.redundancy_k)
                any_delivered = any(o.delivered for o in link_outcomes)
                post_telem = self.link.telemetry(t)
                self.next_sample = self.scheduler.controller.on_tx_result(
                    t, any_delivered, post_telem
                )
                record["interval"] = self.next_sample - t

        record["closed_loop"] = dict(
            obs_mode=jd.obs_mode,
            obs_interval_s=jd.obs_interval_s,
            aoi_cap_s=jd.aoi_cap_s,
            delta_margin_s=jd.delta_margin_s,
            redundancy_k=jd.redundancy_k,
            score=jd.score,
            fast_used=jd.fast_used,
            fast_blocked=jd.fast_blocked,
            diagnostic=jd.diagnostic,
            link_loss_ema=telemetry.loss_ema if telemetry is not None else 0.0,
            link_bw_congested=telemetry.bw_congested if telemetry is not None else False,
        )
        return dict(
            record=record,
            reports=reports,
            envelope=envelope,
            frame=frame,
            link_outcomes=link_outcomes,
        )
