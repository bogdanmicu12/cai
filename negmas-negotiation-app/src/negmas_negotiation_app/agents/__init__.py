from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..domain.issues import Domain
from ..domain.utility_functions import LinearAdditiveUtilityFunction
from ..types.index import NegotiationState, Offer, ResponseType


class BaseAgent:
    """
    Minimal SAO-style agent interface:
      - propose(state) -> Offer
      - respond(state) -> ResponseType
      - receive_offer(offer, from_agent, state) hook (optional)
    The mechanism will call `on_negotiation_start(...)` once.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        ufun: Optional[LinearAdditiveUtilityFunction] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.name = name or self.__class__.__name__
        self.ufun = ufun
        self._rng = rng or random.Random()

        self.domain: Optional[Domain] = None
        self.outcomes: List[Offer] = []
        self.n_steps: int = 0
        self.opponents: Tuple[str, ...] = tuple()

        self._sorted_outcomes: List[Offer] = []
        self._last_received_offer: Optional[Offer] = None
        self._last_received_from: Optional[str] = None

    def on_negotiation_start(
        self,
        *,
        domain: Domain,
        outcomes: Sequence[Offer],
        n_steps: int,
        opponents: Sequence[str],
    ) -> None:
        self.domain = domain
        self.outcomes = list(outcomes)
        self.n_steps = int(n_steps)
        self.opponents = tuple(opponents)

        if self.ufun is None:
            # fallback to random utility if not provided
            self.ufun = LinearAdditiveUtilityFunction.random(domain, rng=self._rng)

        # cache outcomes sorted by self utility (descending)
        self._sorted_outcomes = sorted(self.outcomes, key=lambda o: float(self.ufun(o)), reverse=True)

    def receive_offer(self, offer: Offer, from_agent: str, state: NegotiationState) -> None:
        self._last_received_offer = offer
        self._last_received_from = from_agent

    def propose(self, state: NegotiationState) -> Offer:
        # default: best offer
        return dict(self._sorted_outcomes[0]) if self._sorted_outcomes else {}

    def respond(self, state: NegotiationState) -> ResponseType:
        # default: accept if above reservation value
        if state.current_offer is None or self.ufun is None:
            return ResponseType.REJECT
        return ResponseType.ACCEPT if float(self.ufun(state.current_offer)) >= float(self.ufun.reserved_value) else ResponseType.REJECT


class TimeBasedAgent(BaseAgent):
    """
    Standard time-based aspiration agent:
      aspiration(t) = alpha - (alpha - beta) * (t ** gamma)
    Accept if u(offer) >= aspiration(t). Propose an offer meeting aspiration if possible.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        ufun: Optional[LinearAdditiveUtilityFunction] = None,
        *,
        alpha: float = 1.0,
        beta: Optional[float] = None,
        gamma: float = 1.0,
        rng: Optional[random.Random] = None,
    ) -> None:
        super().__init__(name=name, ufun=ufun, rng=rng)
        self.alpha = float(alpha)
        self.beta = beta  # if None -> uses max(reserved_value, 0.0)
        self.gamma = float(gamma)

    def aspiration(self, t: float) -> float:
        if self.ufun is None:
            rv = 0.0
        else:
            rv = float(self.ufun.reserved_value)

        beta = float(self.beta) if self.beta is not None else max(rv, 0.0)
        a = self.alpha
        if beta > a:
            beta = a
        if t < 0.0:
            t = 0.0
        if t > 1.0:
            t = 1.0
        return a - (a - beta) * (t ** self.gamma)

    def _pick_offer_meeting(self, target: float) -> Offer:
        if not self._sorted_outcomes:
            return {}
        assert self.ufun is not None

        # take the best offer that meets the target (fast and stable)
        for o in self._sorted_outcomes:
            if float(self.ufun(o)) >= target:
                return dict(o)

        # if nothing meets target, concede to best available
        return dict(self._sorted_outcomes[0])

    def propose(self, state: NegotiationState) -> Offer:
        target = self.aspiration(state.relative_time)
        return self._pick_offer_meeting(target)

    def respond(self, state: NegotiationState) -> ResponseType:
        if state.current_offer is None or self.ufun is None:
            return ResponseType.REJECT
        target = self.aspiration(state.relative_time)
        return ResponseType.ACCEPT if float(self.ufun(state.current_offer)) >= target else ResponseType.REJECT