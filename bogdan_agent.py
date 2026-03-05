from negmas import (
    SAONegotiator,
    PresortingInverseUtilityFunction,
    PreferencesChangeType,
    ResponseType,
)

#    Negotiation: Boulware time-dependent aspiration curve with dynamic concession based on sliding window trend analysis of opponent offers
#    e determines shape of aspiration curve: low e = slow concession early, high e = faster concession (we never let e go over 0.30)
#    Based on the slope of opponent utility over last 8 offers we determine whether
#      - opponent concedes (positive slope) -> increase e
#      - opponent stagnates (flat) -> decrease e slightly 
#      - opponent gets more stubborn (negative) -> decrease e very slightly (otherwise there's no deal)
#    Acceptance is ACnext with tweaks:
#      - safeguard against accepting too low (<90%) of current target (prevents accpeting a dumb offer due to an e spike)
#      - over the last 5% of time lower acceptance floor gradually to 70% of current target from the initial 90%
#      - in the last 1% accept the best we've seen if above reservation
#    Proposal follows aspiration curve but with tweaks: 
#      - anti-exploitation floor (Baarslag et al. 2016): never target below 95% of best received offer so that our time-based nature doesn't come back to bite us and we aim too low
#      - offer diversity (de Jonge et al. 2022): cycle through offers around the same utility level to trigger concession in reciprocity-based agents (anti-micro)
#      - deadline mirroring: in the last 3% propose back the best received offer if it meets current target
#    Example for logic of offer diversity: instead of saying "I want 50 euros" 10 times, you say "How about 50 euros with free shipping?" "How about 51 euros with a sloppy toppy coupon?" "How about 49 euros and I pick the color?"
class TrendBoulwareNegotiator(SAONegotiator):

    def __init__(self, *args, base_e: float = 0.08, window_size: int = 8, **kwargs):
        super().__init__(*args, **kwargs)
        self._base_e = base_e
        self._current_e = base_e
        self._window_size = window_size

        self._sorted_outcomes = None
        self._reservation = None
        self._opponent_utilities = []
        self._best_opponent_offer = None
        self._best_opponent_offer_utility = -1.0
        self._proposed_set = set()
        self._proposed_count = 0
        self._my_utilities_offered = []

    def on_preferences_changed(self, changes):
        changes = [_ for _ in changes if _.type != PreferencesChangeType.Scale]
        if not changes:
            return
        if self.ufun is None:
            return

        self._reservation = getattr(self.ufun, "reserved_value", None)

        inv = PresortingInverseUtilityFunction(self.ufun)
        inv.init()
        outcomes = list(inv.outcomes)[::-1]

        if self._reservation is not None:
            outcomes = [o for o in outcomes if self.ufun(o) >= self._reservation]

        self._sorted_outcomes = outcomes
        self._current_e = self._base_e
        self._opponent_utilities = []
        self._best_opponent_offer = None
        self._best_opponent_offer_utility = -1.0
        self._proposed_set = set()
        self._proposed_count = 0
        self._my_utilities_offered = []
        self._utility_map = {}

        for o in outcomes:
            u = round(float(self.ufun(o)), 4)
            if u not in self._utility_map:
                self._utility_map[u] = []
            self._utility_map[u].append(o)

        super().on_preferences_changed(changes)

    def _compute_slope(self) -> float:
        window = self._opponent_utilities[-self._window_size:]
        n = len(window)
        if n < 3:
            return 0.0

        sum_x = sum_y = sum_xy = sum_x2 = 0.0
        for i, y in enumerate(window):
            x = float(i)
            sum_x += x
            sum_y += y
            sum_xy += x * y
            sum_x2 += x * x

        denom = n * sum_x2 - sum_x * sum_x
        if abs(denom) < 1e-12:
            return 0.0
        return (n * sum_xy - sum_x * sum_y) / denom

    def _update_exponent(self, progress: float):
        slope = self._compute_slope()
        threshold = 0.004

        if slope > threshold:
# Opponent concedes => get harder
            self._current_e = max(0.03, self._current_e * 0.88)
        elif slope < -threshold:
# Opponent gets harder => chill to avoid deadlock
            if progress > 0.4:
                self._current_e = min(0.30, self._current_e * 1.04)
        else:
# If we stagnate then soften gradually
            if progress > 0.35:
                self._current_e = min(0.30, self._current_e * 1.02)

    def _aspiration_target(self, progress: float) -> float:
        if not self._sorted_outcomes:
            return 0.0

        max_u = float(self.ufun(self._sorted_outcomes[0]))
        min_u = self._reservation if self._reservation is not None else 0.0

        t = max(0.0, min(1.0, progress))
        e = self._current_e

        target = min_u + (max_u - min_u) * (1.0 - t ** (1.0 / e))

# Never target below best received offer but discount it slightly (5%) so we don't lock ourselves to opponent's best
        if self._best_opponent_offer_utility > 0:
            floor = self._best_opponent_offer_utility * 0.95
            target = max(target, floor)

        return max(target, min_u)

    def _outcome_at_target(self, target: float):
        if not self._sorted_outcomes:
            return None

        reservation = self._reservation if self._reservation is not None else 0.0

# Tolerance tweak for more diversity (for micro)
        tolerance = 0.07

        candidates = []
        best_at_or_above = None

        for o in self._sorted_outcomes:
            u = float(self.ufun(o))
            if u >= target - tolerance and u >= reservation:
                candidates.append(o)
                if u >= target and best_at_or_above is None:
                    best_at_or_above = o
            if u < target - tolerance:
                break

        if not candidates:
# If nothing in band, return the outcome closest to target from above
            for o in self._sorted_outcomes:
                u = float(self.ufun(o))
                if u >= reservation:
                    return o
            return self._sorted_outcomes[0] if self._sorted_outcomes else None

# Prioritize outcomes we haven't proposed yet (for micro)
        for o in candidates:
            if o not in self._proposed_set:
                return o

# All in band exhausted => try wider band
        for o in self._sorted_outcomes:
            u = float(self.ufun(o))
            if u >= target - tolerance * 2.5 and u >= reservation and o not in self._proposed_set:
                return o
            if u < target - tolerance * 2.5:
                break
        
        self._proposed_set.clear()
        return candidates[0]

    def respond(self, state, source=None):
        if not self._sorted_outcomes:
            return ResponseType.REJECT_OFFER

        offer = state.current_offer
        if offer is None:
            return ResponseType.REJECT_OFFER

        offer_utility = float(self.ufun(offer))
        progress = state.relative_time

# Track opponent
        self._opponent_utilities.append(offer_utility)
        if offer_utility > self._best_opponent_offer_utility:
            self._best_opponent_offer = offer
            self._best_opponent_offer_utility = offer_utility
        self._update_exponent(progress)

        current_target = self._aspiration_target(progress)
        reservation = self._reservation if self._reservation is not None else 0.0

# Accept if offer >= current aspiration target
        if offer_utility >= current_target:
            return ResponseType.ACCEPT_OFFER

# ACnext
        n_steps_total = getattr(state, 'n_steps', 1000) or 1000
        step_size = 1.0 / n_steps_total
        next_progress = min(1.0, progress + step_size)
        next_target = self._aspiration_target(next_progress)

# Accept if offer >= next target, with 90% of current target safety floor
        if offer_utility >= next_target and offer_utility >= current_target * 0.90:
            return ResponseType.ACCEPT_OFFER

# progressively lower acceptance threshold as last resort
        if progress > 0.95:
            late_fraction = (progress - 0.95) / 0.05  # 0 to 1
            late_threshold = current_target * (1.0 - late_fraction * 0.3)
            late_threshold = max(late_threshold, reservation)

            if offer_utility >= late_threshold:
                return ResponseType.ACCEPT_OFFER

# last bid: accept the best we got if above reservation
        if progress > 0.99 and offer_utility >= reservation and offer_utility > 0:
            return ResponseType.ACCEPT_OFFER

        return ResponseType.REJECT_OFFER

    def propose(self, state, dest=None):
        if not self._sorted_outcomes:
            return None

        progress = state.relative_time

# Deadline: in last 3%, propose back best received if it meets current target
        if progress > 0.97 and self._best_opponent_offer is not None:
            reservation = self._reservation if self._reservation is not None else 0.0
            current_target = self._aspiration_target(progress)
# Lower the bar slightly for mirroring
            if (self._best_opponent_offer_utility >= reservation
                    and self._best_opponent_offer_utility >= current_target * 0.90):
                return self._best_opponent_offer

        target = self._aspiration_target(progress)
        outcome = self._outcome_at_target(target)

        if outcome is not None:
            self._proposed_set.add(outcome)
            self._proposed_count += 1
            self._my_utilities_offered.append(float(self.ufun(outcome)))

        return outcome