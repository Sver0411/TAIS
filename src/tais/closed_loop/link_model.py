"""Deterministic closed-loop wireless link simulator for Binary v1 frames.

Supports i.i.d. packet loss (0%-30%+), 2-state Gilbert-Elliott burst loss,
continuous-time byte token-bucket bandwidth limits, and strictly causal
historical telemetry feedback to the sender.
"""
from collections import Counter
from dataclasses import dataclass
import hashlib
import math

from tais.core_stream import CoreReceiver
from tais.wire_codec import MAX_FRAME_BYTES
from .state import LinkProfile, LinkTelemetry


@dataclass(frozen=True)
class LinkOutcome:
    tx_id: int
    t: float
    copy_index: int
    frame_bytes: int
    delivered: bool
    reason: str
    receiver_status: str | None


def _draw_u01(seed: int, label: str, tx_id: int, step: int) -> float:
    token = f"tais-phase5-link:{seed}:{label}:{tx_id}:{step}".encode("utf-8")
    raw = int.from_bytes(hashlib.sha256(token).digest()[:8], "big")
    return raw / float(1 << 64)


class StatefulLinkModel:
    """Binary v1 byte link with loss, burst fading, bandwidth cap and causal feedback."""

    def __init__(
        self,
        profile: LinkProfile,
        receiver: CoreReceiver | None = None,
        seed: int = 0,
        label: str = "default",
        loss_ema_alpha: float = 0.20,
    ):
        profile.validate()
        self.profile = profile
        self.receiver = receiver if receiver is not None else CoreReceiver(layout_id=1)
        self.seed = int(seed)
        self.label = str(label)
        self.loss_ema_alpha = float(loss_ema_alpha)

        self._ge_bad = False
        self._last_t: float | None = None
        if profile.bandwidth_bpm is None:
            self._bucket_cap = math.inf
            self._tokens = math.inf
        else:
            # 6-second burst allowance (at least 2 full Binary v1 frames = 112 B)
            self._bucket_cap = max(2.0 * MAX_FRAME_BYTES, profile.bandwidth_bpm / 10.0)
            self._tokens = self._bucket_cap

        self._loss_ema = 0.0
        self._last_bw_drop_t: float | None = None
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
        self.delivered_frames: list[dict] = []
        self.outcomes: list[LinkOutcome] = []

    def _refill(self, t: float) -> None:
        if self.profile.bandwidth_bpm is None:
            return
        if self._last_t is not None:
            dt = max(0.0, t - self._last_t)
            self._tokens = min(
                self._bucket_cap,
                self._tokens + dt * (self.profile.bandwidth_bpm / 60.0),
            )
        self._last_t = t

    def _channel_drops(self, tx_id: int) -> bool:
        p = self.profile
        if p.burst_mode:
            u_state = _draw_u01(self.seed, self.label, tx_id, 0)
            if self._ge_bad:
                if u_state < p.ge_p_bg:
                    self._ge_bad = False
            else:
                if u_state < p.ge_p_gb:
                    self._ge_bad = True
            drop_prob = p.ge_drop_bad if self._ge_bad else p.ge_drop_good
            return _draw_u01(self.seed, self.label, tx_id, 1) < drop_prob
        if p.loss_rate <= 0.0:
            return False
        return _draw_u01(self.seed, self.label, tx_id, 1) < p.loss_rate

    def telemetry(self, now: float | None = None) -> LinkTelemetry:
        if now is not None:
            self._refill(now)
        if self.profile.bandwidth_bpm is None:
            congested = False
        else:
            recent_bw_drop = (
                now is not None
                and self._last_bw_drop_t is not None
                and (now - self._last_bw_drop_t) <= 30.0
            )
            congested = self._tokens < (1.5 * MAX_FRAME_BYTES) or recent_bw_drop
        return LinkTelemetry(
            loss_ema=self._loss_ema,
            bw_congested=congested,
            bw_tokens_bytes=self._tokens,
            last_confirmed_finite_t=dict(self._last_confirmed_finite_t),
            tx_attempts=self.counts["attempts"],
            tx_delivered=self.counts["delivered"],
            tx_loss_drops=self.counts["loss_drops"],
            tx_bw_drops=self.counts["bw_drops"],
        )

    def send(
        self,
        t: float,
        frame: bytes,
        envelope: dict,
        redundancy_k: int = 1,
    ) -> list[LinkOutcome]:
        """Transmit 1..K copies of a Binary v1 frame and update causal telemetry."""
        if redundancy_k < 1:
            raise ValueError("redundancy_k must be >= 1")
        self._refill(t)
        self.counts["logical_frames"] += 1
        if redundancy_k > 1:
            self.counts["redundant_copies"] += redundancy_k - 1

        frame_len = len(frame)
        batch: list[LinkOutcome] = []
        any_delivered = False

        for copy_idx in range(redundancy_k):
            self.counts["attempts"] += 1
            tx_id = self.counts["attempts"]

            # Bandwidth token-bucket admission
            if self.profile.bandwidth_bpm is not None and self._tokens < frame_len:
                self.counts["bw_drops"] += 1
                self._last_bw_drop_t = t
                outcome = LinkOutcome(
                    tx_id=tx_id,
                    t=t,
                    copy_index=copy_idx,
                    frame_bytes=frame_len,
                    delivered=False,
                    reason="bw_drop",
                    receiver_status=None,
                )
                self.outcomes.append(outcome)
                batch.append(outcome)
                continue

            if self.profile.bandwidth_bpm is not None:
                self._tokens -= frame_len
            self.counts["sent_bytes"] += frame_len

            if self._channel_drops(tx_id):
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
                    reason="loss",
                    receiver_status=None,
                )
                self.outcomes.append(outcome)
                batch.append(outcome)
                continue

            # Delivered to independent Binary v1 CoreReceiver
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
