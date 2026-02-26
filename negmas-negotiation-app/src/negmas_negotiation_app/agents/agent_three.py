from __future__ import annotations

import math
from typing import Any, Dict, Optional

from . import TimeBasedAgent
from ..types.index import NegotiationState, Offer, ResponseType


class AgentThree(TimeBasedAgent):
    """
    Time-based agent with a simple 'near-opponent' bidding heuristic:
      - keep time-based acceptance
      - propose offers meeting aspiration while being "close" to the last received offer
    This often improves agreement rate without full opponent modeling.
    """

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("gamma", 1.2)
        kwargs.setdefault("alpha", 1.0)
        super().__init__(*args, **kwargs)

    def _distance(self, a: Offer, b: Offer) -> float:
        # Hamming distance over issues
        if not a or not b:
            return float("inf")
        keys = set(a.keys()) | set(b.keys())
        return float(sum(1 for k in keys if a.get(k) != b.get(k)))

    def propose(self, state: NegotiationState) -> Offer:
        target = self.aspiration(state.relative_time)
        last = self._last_received_offer

        if not self._sorted_outcomes or self.ufun is None:
            return {}

        # candidates that meet aspiration
        candidates = [o for o in self._sorted_outcomes if float(self.ufun(o)) >= target]
        if not candidates:
            return dict(self._sorted_outcomes[0])

        if last is None:
            # pick best among candidates
            return dict(candidates[0])

        # pick the closest to opponent's last offer (tie-break: higher self utility)
        best = None
        best_key = (float("inf"), -1.0)
        for o in candidates:
            d = self._distance(o, last)
            u = float(self.ufun(o))
            key = (d, -u)
            if key < best_key:
                best_key = key
                best = o
        return dict(best) if best is not None else dict(candidates[0])