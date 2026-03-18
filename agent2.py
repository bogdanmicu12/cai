from negmas import (
    PreferencesChangeType,
    PresortingInverseUtilityFunction,
    ResponseType,
    SAONegotiator,
)


class PortfolioTBNegotiator(SAONegotiator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sorted_outcomes = None
        self._reservation = None
        self._last_offer = None
        self._seen_offers = set()

    def on_preferences_changed(self, changes):
        changes = [_ for _ in changes if _.type != PreferencesChangeType.Scale]
        if not changes or self.ufun is None:
            return

        self._reservation = getattr(self.ufun, "reserved_value", None)

        inv = PresortingInverseUtilityFunction(self.ufun)
        inv.init()
        outcomes = list(inv.outcomes)[::-1]

        if self._reservation is not None:
            outcomes = [o for o in outcomes if self.ufun(o) >= self._reservation]

        self._sorted_outcomes = outcomes
        self._last_offer = None
        self._seen_offers = set()

        super().on_preferences_changed(changes)

    def _target_utility(self, t: float) -> float:
        base = 1.0 - (t**3) * 0.7
        if self._reservation is not None and isinstance(
            self._reservation, (int, float)
        ):
            return max(base, float(self._reservation))
        return max(base, 0.0)

    def respond(self, state, source=None):
        if not self._sorted_outcomes:
            return ResponseType.REJECT_OFFER

        offer = state.current_offer
        if offer is None:
            return ResponseType.REJECT_OFFER

        t = state.relative_time
        offer_u = self.ufun(offer)
        target_u = self._target_utility(t)

        if offer_u >= max(0.95, target_u + 0.02):
            return ResponseType.ACCEPT_OFFER

        if t > 0.95:
            if self._reservation is not None and isinstance(
                self._reservation, (int, float)
            ):
                if offer_u >= max(target_u, float(self._reservation)):
                    return ResponseType.ACCEPT_OFFER
            else:
                if offer_u >= target_u:
                    return ResponseType.ACCEPT_OFFER

        if t > 0.5 and offer_u >= target_u - 0.02:
            return ResponseType.ACCEPT_OFFER

        self._seen_offers.add(offer)
        return ResponseType.REJECT_OFFER

    def propose(self, state, dest=None):
        if not self._sorted_outcomes:
            return None

        t = state.relative_time
        target_u = self._target_utility(t)

        best = None
        best_diff = 1e9
        for o in self._sorted_outcomes:
            if o in self._seen_offers:
                continue
            u = self.ufun(o)
            diff = abs(u - target_u)
            if diff < best_diff:
                best_diff = diff
                best = o
            if t < 0.3 and best is not None and best_diff < 0.01:
                break

        if best is None:
            best = self._sorted_outcomes[0]

        self._last_offer = best
        self._seen_offers.add(best)
        return best
