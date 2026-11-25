"""Compact, C11-portable data structures for Phase 5 closed-loop control."""
from dataclasses import dataclass, field
import math

OBS_MODES = ("QUIET_ECO", "PROBE", "TRACK", "SAFE_FALLBACK", "DIAG_VERIFY")


@dataclass(frozen=True)
class ClosedLoopParams:
    """Exactly 5 primary control hyperparameters; structural bounds stay frozen."""

    fallback_interval_s: float = 20.0
    diag_interval_s: float = 15.0
    aoi_cap_quiet_s: float = 45.0
    aoi_cap_active_s: float = 20.0
    loss_redundancy_threshold: float = 0.10

    def validate(self) -> None:
        values = (
            self.fallback_interval_s,
            self.diag_interval_s,
            self.aoi_cap_quiet_s,
            self.aoi_cap_active_s,
            self.loss_redundancy_threshold,
        )
        if any(not math.isfinite(v) for v in values):
            raise ValueError("ClosedLoopParams values must be finite")
        if not 5.0 <= self.diag_interval_s <= 60.0:
            raise ValueError("diag_interval_s must be in [5, 60]")
        if not 5.0 <= self.fallback_interval_s <= 60.0:
            raise ValueError("fallback_interval_s must be in [5, 60]")
        if not 5.0 <= self.aoi_cap_active_s <= self.aoi_cap_quiet_s:
            raise ValueError("Require 5 <= aoi_cap_active_s <= aoi_cap_quiet_s")
        if not 0.0 < self.loss_redundancy_threshold <= 1.0:
            raise ValueError("loss_redundancy_threshold must be in (0, 1]")


@dataclass(frozen=True)
class LinkProfile:
    """Deterministic communication environment profile for boundary evaluation."""

    name: str = "loss_0_bw_inf"
    loss_rate: float = 0.0
    burst_mode: bool = False
    bandwidth_bpm: float | None = None
    ge_p_gb: float = 0.08
    ge_p_bg: float = 0.35
    ge_drop_good: float = 0.02
    ge_drop_bad: float = 0.85

    def validate(self) -> None:
        if not 0.0 <= self.loss_rate <= 1.0:
            raise ValueError("loss_rate must be in [0, 1]")
        if self.bandwidth_bpm is not None and (
            not math.isfinite(self.bandwidth_bpm) or self.bandwidth_bpm <= 0
        ):
            raise ValueError("bandwidth_bpm must be positive finite or None")


@dataclass(frozen=True)
class LinkTelemetry:
    """Strictly causal historical link telemetry fed back to the controller."""

    loss_ema: float = 0.0
    bw_congested: bool = False
    bw_tokens_bytes: float = math.inf
    last_confirmed_finite_t: dict = field(default_factory=dict)
    tx_attempts: int = 0
    tx_delivered: int = 0
    tx_loss_drops: int = 0
    tx_bw_drops: int = 0


@dataclass(frozen=True)
class JointDecision:
    """Per-sample closed-loop scheduling and transmission decision."""

    t: float
    obs_mode: str
    obs_interval_s: float
    next_sample_s: float
    interval_s: float
    aoi_cap_s: float
    delta_margin_s: float
    upload: bool
    reasons: tuple
    redundancy_k: int
    score: float
    fast_used: int
    fast_blocked: bool
    diagnostic: bool
    channel_finite_ages: dict
