"""Hardware-trace-driven Binary v1 link model for real E220-400T22D logs.

Replays unmodified delivery/timeout outcome sequences and measured physical RF
airtime / ACK RTT statistics extracted from EventGuard-LoRa ESP32-S3 + E220
hardware runs, exposing the exact same causal LinkTelemetry contract as
StatefulLinkModel.
"""
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

from tais.core_stream import CoreReceiver
from .link_model import LinkOutcome
from .state import LinkTelemetry


@dataclass(frozen=True)
class HardwareTraceProfile:
    regime_id: str
    run_id: str
    outcomes: tuple[int, ...]
    mean_tx_airtime_ms: float
    mean_ack_rtt_ms: float
    raw_sha256: str


def load_e220_regimes(path: Path | None = None) -> dict[str, list[HardwareTraceProfile]]:
    if path is None:
        path = Path(__file__).resolve().parents[3] / "configs/e220_hardware_traces.json"
    raw = json.loads(path.read_text())
    out: dict[str, list[HardwareTraceProfile]] = {}
    for rid, runs in raw["regimes"].items():
        out[rid] = [
            HardwareTraceProfile(
                regime_id=rid,
                run_id=r["run_id"],
                outcomes=tuple(int(x) for x in r["outcomes"]),
                mean_tx_airtime_ms=float(r["mean_tx_airtime_ms"] or 0.0),
                mean_ack_rtt_ms=float(r["mean_ack_rtt_ms"] or 0.0),
                raw_sha256=r["raw_sha256"],
            )
            for r in runs
        ]
    return out


class TraceDrivenLinkModel:
    """Replays real E220 hardware 0/1 delivery traces with causal LinkTelemetry."""

    def __init__(
        self,
        profile: HardwareTraceProfile,
        receiver: CoreReceiver | None = None,
        seed: int = 0,
        label: str = "default",
        loss_ema_alpha: float = 0.20,
    ):
        if not profile.outcomes:
            raise ValueError("HardwareTraceProfile must contain at least one outcome")
        self.profile = profile
        self.receiver = receiver if receiver is not None else CoreReceiver(layout_id=1)
        self.seed = int(seed)
        self.label = str(label)
        self.loss_ema_alpha = float(loss_ema_alpha)

        # Deterministic starting phase per (seed, label) so all methods share identical channel calendar
        token = f"tais-e220-trace:{self.seed}:{self.label}:{profile.run_id}".encode("utf-8")
        self._offset = int.from_bytes(hashlib.sha256(token).digest()[:8], "big") % len(profile.outcomes)

        self._loss_ema = 0.0
        self._last_confirmed_finite_t: dict[str, float] = {}
        self.counts = Counter(
            attempts=0,
            logical_frames=0,
            redundant_copies=0,
            delivered=0,
            loss_drops=0,
            bw_drops=0,
            sent_bytes=0,
            delivered_bytes=0,
        )
        self.total_airtime_ms: float = 0.0
        self.delivered_frames: list[dict] = []
        self.outcomes: list[LinkOutcome] = []

    def telemetry(self, now: float | None = None) -> LinkTelemetry:
        return LinkTelemetry(
            loss_ema=self._loss_ema,
            bw_congested=False,
            bw_tokens_bytes=math.inf,
            last_confirmed_finite_t=dict(self._last_confirmed_finite_t),
            tx_attempts=self.counts["attempts"],
            tx_delivered=self.counts["delivered"],
            tx_loss_drops=self.counts["loss_drops"],
            tx_bw_drops=0,
        )

    def send(
        self,
        t: float,
        frame: bytes,
        envelope: dict,
        redundancy_k: int = 1,
    ) -> list[LinkOutcome]:
        if redundancy_k < 1:
            raise ValueError("redundancy_k must be >= 1")
        self.counts["logical_frames"] += 1
        if redundancy_k > 1:
            self.counts["redundant_copies"] += redundancy_k - 1

        frame_len = len(frame)
        batch: list[LinkOutcome] = []
        any_delivered = False
        cal = self.profile.outcomes
        cal_len = len(cal)

        for copy_idx in range(redundancy_k):
            self.counts["attempts"] += 1
            tx_id = self.counts["attempts"]
            self.counts["sent_bytes"] += frame_len
            self.total_airtime_ms += self.profile.mean_tx_airtime_ms

            delivered_flag = cal[(self._offset + tx_id - 1) % cal_len] == 1
            if not delivered_flag:
                self.counts["loss_drops"] += 1
                self._loss_ema = (
                    (1.0 - self.loss_ema_alpha) * self._loss_ema
                    + self.loss_ema_alpha * 1.0
                )
                outcome = LinkOutcome(
                    tx_id=tx_id,
                    t=t,
                    copy_index=copy_idx,
                    frame_bytes=frame_len,
                    delivered=False,
                    reason="hw_trace_drop",
                    receiver_status=None,
                )
                self.outcomes.append(outcome)
                batch.append(outcome)
                continue

            self.counts["delivered"] += 1
            self.counts["delivered_bytes"] += frame_len
            self._loss_ema = (1.0 - self.loss_ema_alpha) * self._loss_ema
            rx = self.receiver.receive(frame)
            if rx["status"] == "updated":
                self.delivered_frames.append(rx["envelope"])
            any_delivered = True
            outcome = LinkOutcome(
                tx_id=tx_id,
                t=t,
                copy_index=copy_idx,
                frame_bytes=frame_len,
                delivered=True,
                reason="ok",
                receiver_status=rx["status"],
            )
            self.outcomes.append(outcome)
            batch.append(outcome)

        if any_delivered:
            for ch, val in envelope["values"].items():
                if val is not None and math.isfinite(val):
                    self._last_confirmed_finite_t[ch] = t

        return batch
