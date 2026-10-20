"""Bounded causal rechecks; no sentinel, truth, or unsampled observations."""
class Rechecks:
    def __init__(self):
        self.until = -1
        self.left = 0

    def interval(self, t, meaningful, minimum):
        if t >= self.until:
            self.until = t + 120
            self.left = 3
        if meaningful and self.left:
            self.left -= 1
            return minimum
        return None
