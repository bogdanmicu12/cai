from negmas import (
    SAONegotiator,
    PresortingInverseUtilityFunction,
    PreferencesChangeType,
    ResponseType,
)


class MiCRONegotiator(SAONegotiator):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._sorted_outcomes = None     # outcomes sorted by decreasing utility
        self._index = 0                  # current concession level
        self._last_offer = None
        self._seen_offers = set()
        self._reservation = None

    def on_preferences_changed(self, changes):
        changes = [_ for _ in changes if _.type != PreferencesChangeType.Scale]
        if not changes:
            return

        if self.ufun is None:
            return

        # Store reservation value safely
        self._reservation = getattr(self.ufun, "reserved_value", None)

        # Sort outcomes by decreasing utility
        inv = PresortingInverseUtilityFunction(self.ufun)
        inv.init()

        outcomes = list(inv.outcomes)[::-1]

        # Filter outcomes below reservation value
        if self._reservation is not None:
            outcomes = [
                o for o in outcomes
                if self.ufun(o) >= self._reservation
            ]

        self._sorted_outcomes = outcomes

        self._index = 0
        self._last_offer = None
        self._seen_offers = set()

        super().on_preferences_changed(changes)

    def respond(self, state, source=None):

        if not self._sorted_outcomes:
            return ResponseType.REJECT_OFFER

        offer = state.current_offer
        if offer is None:
            return ResponseType.REJECT_OFFER

        progress = state.relative_time
        # max_index = len(self._sorted_outcomes) - 1
        # forced_index = int(progress * max_index)

        current_target = self._sorted_outcomes[self._index]
        current_target_utility = self.ufun(current_target)
        offer_utility = self.ufun(offer)

        accept_threshold = current_target_utility

        if offer_utility >= accept_threshold or offer_utility >= 0.8:
            return ResponseType.ACCEPT_OFFER

        if offer not in self._seen_offers:
            self._seen_offers.add(offer)

            if self._index < len(self._sorted_outcomes) - 1:
                self._index += 1

        

        return ResponseType.REJECT_OFFER
    
    def propose(self, state, dest=None):

        if not self._sorted_outcomes:
            return None

        progress = state.relative_time

        offer = self._sorted_outcomes[self._index]
        self._last_offer = offer
        return offer
    

class MiCRONegotiatorConceder(SAONegotiator):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._sorted_outcomes = None     # outcomes sorted by decreasing utility
        self._index = 0                  # current concession level
        self._last_offer = None
        self._seen_offers = set()
        self._reservation = None

    def on_preferences_changed(self, changes):
        changes = [_ for _ in changes if _.type != PreferencesChangeType.Scale]
        if not changes:
            return

        if self.ufun is None:
            return

        # Store reservation value safely
        self._reservation = getattr(self.ufun, "reserved_value", None)

        # Sort outcomes by decreasing utility
        inv = PresortingInverseUtilityFunction(self.ufun)
        inv.init()

        outcomes = list(inv.outcomes)[::-1]

        # Filter outcomes below reservation value
        if self._reservation is not None:
            outcomes = [
                o for o in outcomes
                if self.ufun(o) >= self._reservation
            ]

        self._sorted_outcomes = outcomes

        self._index = 0
        self._last_offer = None
        self._seen_offers = set()

        super().on_preferences_changed(changes)

    def respond(self, state, source=None):

        if not self._sorted_outcomes:
            return ResponseType.REJECT_OFFER

        offer = state.current_offer
        if offer is None:
            return ResponseType.REJECT_OFFER

        progress = state.relative_time
        max_index = len(self._sorted_outcomes) - 1
        forced_index = int(progress * max_index)

        current_target = self._sorted_outcomes[self._index]
        current_target_utility = self.ufun(current_target)
        offer_utility = self.ufun(offer)

        # Accept more easily near deadline
        if progress < 0.9:
            accept_threshold = current_target_utility
        elif progress < 0.95:
            # Near deadline, accept next concession level
            next_index = min(self._index + 1, len(self._sorted_outcomes) - 1)
            accept_threshold = self.ufun(self._sorted_outcomes[next_index])
        else:
            self._index = max(self._index, forced_index)
            next_index = min(self._index, len(self._sorted_outcomes) - 1)
            accept_threshold = self.ufun(self._sorted_outcomes[next_index])

        if offer_utility >= accept_threshold or offer_utility >= 0.8:
            return ResponseType.ACCEPT_OFFER

        if offer not in self._seen_offers:
            self._seen_offers.add(offer)

            if self._index < len(self._sorted_outcomes) - 1:
                self._index += 1

        

        return ResponseType.REJECT_OFFER

    def propose(self, state, dest=None):

        if not self._sorted_outcomes:
            return None

        progress = state.relative_time

        max_index = len(self._sorted_outcomes) - 1
        forced_index = int(progress * max_index)
        if progress > 0.95:
            self._index = max(self._index, forced_index)

        offer = self._sorted_outcomes[self._index]
        self._last_offer = offer
        return offer