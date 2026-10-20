"""Use the frozen scheduler unchanged with one constructor-injected evidence type."""
from unittest.mock import patch
import tais_v02.scheduler as frozen
from .evidence import ReturnedReferenceEvidence

class Scheduler(frozen.Scheduler):
    """Inject the repaired evidence type only while constructing the frozen scheduler.

    The scoped class patch is process-local, so construction is not thread-safe."""
    def __init__(self,cfg,confirmation=True,multiplier=1.0):
        # Constructor-only, process-local patch: no copy of the scheduling policy.
        with patch.object(frozen,'Evidence',ReturnedReferenceEvidence):
            super().__init__(cfg,confirmation=confirmation,multiplier=multiplier)
