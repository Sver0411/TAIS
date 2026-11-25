"""Phase 5 lean 3D joint adaptive closed-loop subpackage (strictly additive).

Reuses frozen SensorTrust C11, AdaptiveSense ChangeAnalyzer, Scheduler and
stateless Binary v1 without modifying any historical code or wire format.
"""
from .state import (
    OBS_MODES,
    ClosedLoopParams,
    JointDecision,
    LinkProfile,
    LinkTelemetry,
)
from .link_model import LinkOutcome, StatefulLinkModel
from .controller import (
    ClosedLoopPolicy,
    ClosedLoopSender,
    JointAdaptiveController,
)

__all__ = [
    "OBS_MODES",
    "ClosedLoopParams",
    "JointDecision",
    "LinkProfile",
    "LinkTelemetry",
    "LinkOutcome",
    "StatefulLinkModel",
    "JointAdaptiveController",
    "ClosedLoopPolicy",
    "ClosedLoopSender",
]
