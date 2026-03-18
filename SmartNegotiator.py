from __future__ import annotations

from negmas import (
    SAONegotiator,
    PresortingInverseUtilityFunction,
    PreferencesChangeType,
    ResponseType,
)
from random import choice
from negmas import PolyAspiration, PresortingInverseUtilityFunction

class SmartAspirationNegotiator(SAONegotiator):
    _inv = None  # The ufun invertor (finds outcomes in a utility range)
    _partner_first = None  # The best offer of the partner (assumed best for it)
    _min = None  # The minimum of my utility function
    _max = None  # The maximum of my utility function
    _best = None  # The best outcome for me

    def __init__(self, *args, **kwargs):
        # initialize the base SAONegoiator (MUST be done)
        super().__init__(*args, **kwargs)

        # Initialize the aspiration mixin to start at 1.0 and concede slowly
        self._asp = PolyAspiration(1.0, "boulware")

    def on_preferences_changed(self, changes):
        # create an initiaze an invertor for my ufun
        changes = [_ for _ in changes if _.type not in (PreferencesChangeType.Scale,)]
        if not changes:
            return
        self._inv = PresortingInverseUtilityFunction(self.ufun)
        self._inv.init()

        # find worst and best outcomes for me
        worest, self._best = self.ufun.extreme_outcomes()

        # and the correponding utility values
        self._min, self._max = self.ufun(worest), self.ufun(self._best)

        # MUST call parent to avoid being called again for no reason
        super().on_preferences_changed(changes)

    def respond(self, state, source: str):
        offer = state.current_offer
        if offer is None:
            return ResponseType.REJECT_OFFER
        # set the partner's first offer when I receive it
        if not self._partner_first:
            self._partner_first = offer

        # accept if the offer is not worse for me than what I would have offered
        return super().respond(state, source)

    def propose(self, state):
        # calculate my current aspiration level (utility level at which I will offer and accept)
        a = (self._max - self._min) * self._asp.utility_at(
            state.relative_time
        ) + self._min

        # find some outcomes (all if the outcome space is  discrete) above the aspiration level
        outcomes = self._inv.some((a - 1e-6, self._max + 1e-6), False)
        # If there are no outcomes above the aspiration level, offer my best outcome
        if not outcomes:
            return self._best

        # else if I did not  recieve anything from the partner, offer any outcome above the aspiration level
        if not self._partner_first:
            return choice(outcomes)

        # otherwise, offer the outcome most similar to the partner's first offer (above the aspiration level)
        nearest, ndist = None, float("inf")
        for o in outcomes:
            d = sum((a - b) * (a - b) for a, b in zip(o, self._partner_first))
            if d < ndist:
                nearest, ndist = o, d
        return nearest