"""Bounded causal rechecks; no sentinel, truth, or unsampled observations."""
class Rechecks:
    """Allow at most three meaningful fast rechecks per 120-second window.

    Windows renew lazily at a sampled timestamp; no timer reads hidden data."""
    def __init__(self):
        self.until = -1
        self.left = 0

    def interval(self, t, meaningful, minimum):
        """Consume one recheck if meaningful; otherwise return no interval override.

        Both t and minimum use seconds. The caller combines this request with
        its other sampling bounds; this object does not schedule reads itself."""
        if t >= self.until:
            self.until = t + 120
            self.left = 3
        if meaningful and self.left:
            self.left -= 1
            return minimum
        return None
