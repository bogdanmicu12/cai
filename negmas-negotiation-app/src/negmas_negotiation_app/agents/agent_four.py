from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Optional, Tuple

from . import TimeBasedAgent
from ..types.index import NegotiationState, Offer, ResponseType


class AgentFour(TimeBasedAgent):
    """
    Time-based agent + tiny frequency-based opponent model:
      - learns value frequencies per issue from received offers
      - estimates opponent utility by normalized frequency
      - proposes offers maximizing:  (1-w)*self + w*opp_est
        where w increases with time (more cooperative near deadline)
    """

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("gamma", 1.0)
        kwargs.setdefault("alpha", 1.0)
        super().__init__(*args, **kwargs)
        self._freq: Dict[str, Dict[Any, int]] = defaultdict(lambda: defaultdict(int))
        self._seen: int = 0

    def receive_offer(self, offer: Offer, from_agent: str, state: NegotiationState) -> None:
        super().receive_offer(offer, from_agent, state)
        if offer is None:
            return
        for k, v in offer.items():
            self._freq[k][v] += 1
        self._seen += 1

    def _opp_est(self, offer: Offer) -> float:
        if not offer or self._seen <= 0:
            return 0.0
        score = 0.0
        n = 0
        for k, v in offer.items():
            n += 1
            score += float(self._freq[k].get(v, 0)) / float(self._seen)
        if n <= 0:
            return 0.0
        # already in [0,1]
        return score / float(n)

    def propose(self, state: NegotiationState) -> Offer:
        if not self._sorted_outcomes or self.ufun is None:
            return {}

        target = self.aspiration(state.relative_time)

        # w increases with time: 0 -> selfish, 1 -> cooperative
        w = state.relative_time
        best = None
        best_score = -1.0

        for o in self._sorted_outcomes:
            u = float(self.ufun(o))
            if u < target:
                # because sorted descending by self utility, remaining will be worse
                break
            s = (1.0 - w) * u + w * self._opp_est(o)
            if s > best_score:
                best_score = s
                best = o

        if best is not None:
            return dict(best)

        # if nothing meets target, fallback to best self outcome
        return dict(self._sorted_outcomes[0])