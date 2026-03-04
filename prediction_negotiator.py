from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import math
import random

from negmas import (
    SAONegotiator,
    PresortingInverseUtilityFunction,
    PreferencesChangeType,
    ResponseType,
)

# ---- Opponent type inference (fit observed U_self(offer) vs time to shapes) ----

@dataclass
class FitResult:
    name: str
    sse: float
    a: float
    b: float


class OpponentTypeTracker:
    """
    Classifies the opponent by fitting the sequence of (t, u_self(opponent_offer))
    to a set of concession shapes f(t). Model: u(t) ≈ a + b * f(t).
    Lower SSE => closer match.
    """

    def __init__(self) -> None:
        self.obs: List[Tuple[float, float]] = []  # (t, u_self)
        self.shapes = {
            "boulware": lambda t: t**3,
            "linear": lambda t: t,
            "conceder": lambda t: 1.0 - (1.0 - t) ** 3,
            "aspiration_like": lambda t: t**2,
        }

    def add(self, t: float, u_self: float) -> None:
        t = min(max(float(t), 0.0), 1.0)
        u_self = min(max(float(u_self), 0.0), 1.0)
        self.obs.append((t, u_self))

    @staticmethod
    def _fit_linear(xs: List[float], ys: List[float]) -> Tuple[float, float]:
        n = len(xs)
        if n == 0:
            return 0.0, 0.0
        mx = sum(xs) / n
        my = sum(ys) / n
        denom = sum((x - mx) ** 2 for x in xs)
        if denom <= 1e-12:
            return my, 0.0
        b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
        a = my - b * mx
        return a, b

    def infer(self, min_points: int = 6, smooth_window: int = 5) -> Optional[FitResult]:
        """
        Uses a short moving average over utilities to reduce noise before fitting.
        """
        if len(self.obs) < min_points:
            return None

        ts = [t for t, _ in self.obs]
        us_raw = [u for _, u in self.obs]

        # moving average smoothing over us
        us: List[float] = []
        for i in range(len(us_raw)):
            j0 = max(0, i - smooth_window + 1)
            seg = us_raw[j0 : i + 1]
            us.append(sum(seg) / len(seg))

        best: Optional[FitResult] = None
        for name, f in self.shapes.items():
            xs = [f(t) for t in ts]
            a, b = self._fit_linear(xs, us)
            sse = 0.0
            for x, y in zip(xs, us):
                yhat = a + b * x
                sse += (y - yhat) ** 2
            r = FitResult(name=name, sse=sse, a=a, b=b)
            if best is None or r.sse < best.sse:
                best = r
        return best


# ---- The negotiator: Boulware-like + opponent-aware bid selection + next-offer acceptance ----

class PredictionNegotiator(SAONegotiator):
    """
    Improvements implemented:
      1) Next-offer acceptance: accept if offer >= max(target(t), next_proposal_utility - eps)
      2) Frequency-based opponent model for bid selection among candidates >= target(t)
      3) No-repeat proposals + randomized top-K choice to avoid determinism/cycling
      4) Slightly refined type->exponent mapping + stable updates (don’t change every step)
    """

    def __init__(self, *args, seed: Optional[int] = None, **kwargs):
        super().__init__(*args, **kwargs)

        if seed is not None:
            random.seed(seed)

        self._sorted_outcomes = None
        self._reservation = None
        self._inv = None

        self._opp_type = OpponentTypeTracker()
        self._last_inferred: Optional[FitResult] = None

        # Frequency model: issue -> value -> count
        self._opp_counts: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._opp_total: Dict[str, float] = defaultdict(float)
        self._decay = 0.995  # decay per update (keeps model adaptive)

        # Offer memory
        self._sent_offers = set()
        self._last_offer = None

        # Update inference only occasionally after enough data
        self._infer_every = 25
        self._min_points_to_infer = 8

        # Proposal selection controls
        self._top_k = 12
        self._epsilon_accept = 1e-6

    def on_preferences_changed(self, changes):
        changes = [_ for _ in changes if _.type != PreferencesChangeType.Scale]
        if not changes or self.ufun is None:
            return

        self._reservation = getattr(self.ufun, "reserved_value", 0.0)

        inv = PresortingInverseUtilityFunction(self.ufun)
        inv.init()
        self._inv = inv

        outcomes = list(inv.outcomes)[::-1]  # decreasing utility
        if self._reservation is not None:
            outcomes = [o for o in outcomes if self.ufun(o) >= self._reservation]
        self._sorted_outcomes = outcomes

        self._opp_type = OpponentTypeTracker()
        self._last_inferred = None

        self._opp_counts = defaultdict(lambda: defaultdict(float))
        self._opp_total = defaultdict(float)

        self._sent_offers = set()
        self._last_offer = None

        super().on_preferences_changed(changes)

    # ---- Opponent frequency model ----

    def _decay_counts(self) -> None:
        # light decay for all issues seen so far
        for issue, vals in self._opp_counts.items():
            for v in list(vals.keys()):
                vals[v] *= self._decay
        for issue in list(self._opp_total.keys()):
            self._opp_total[issue] *= self._decay

    def _update_opp_counts(self, offer) -> None:
        """
        Offer in negmas is typically a tuple of values in issue order OR a dict depending on OS.
        We support both.
        """
        if offer is None:
            return

        self._decay_counts()

        # Try dict-like first
        if isinstance(offer, dict):
            for issue, val in offer.items():
                issue = str(issue)
                v = str(val)
                self._opp_counts[issue][v] += 1.0
                self._opp_total[issue] += 1.0
            return

        # Otherwise assume sequence aligned with outcome space issues
        os_issues = None
        try:
            os_issues = list(self.nmi.outcome_space.issues)  # type: ignore[attr-defined]
        except Exception:
            os_issues = None

        if os_issues is None:
            # fallback: use indices as issue keys
            for i, val in enumerate(offer):
                issue = f"issue_{i}"
                v = str(val)
                self._opp_counts[issue][v] += 1.0
                self._opp_total[issue] += 1.0
            return

        for issue_obj, val in zip(os_issues, offer):
            issue = str(getattr(issue_obj, "name", issue_obj))
            v = str(val)
            self._opp_counts[issue][v] += 1.0
            self._opp_total[issue] += 1.0

    def _opp_likelihood_score(self, outcome) -> float:
        """
        Higher if outcome uses values opponent offered frequently.
        Uses log(count+1) per issue.
        """
        score = 0.0

        if outcome is None:
            return score

        if isinstance(outcome, dict):
            for issue, val in outcome.items():
                issue = str(issue)
                v = str(val)
                score += math.log(self._opp_counts[issue].get(v, 0.0) + 1.0)
            return score

        os_issues = None
        try:
            os_issues = list(self.nmi.outcome_space.issues)  # type: ignore[attr-defined]
        except Exception:
            os_issues = None

        if os_issues is None:
            for i, val in enumerate(outcome):
                issue = f"issue_{i}"
                v = str(val)
                score += math.log(self._opp_counts[issue].get(v, 0.0) + 1.0)
            return score

        for issue_obj, val in zip(os_issues, outcome):
            issue = str(getattr(issue_obj, "name", issue_obj))
            v = str(val)
            score += math.log(self._opp_counts[issue].get(v, 0.0) + 1.0)

        return score

    # ---- Utility target schedule ----

    def _choose_concession_exponent(self, inferred: Optional[FitResult]) -> float:
        # Default: boulware-ish
        if inferred is None:
            return 3.0

        # Tuned mapping (stronger separation)
        if inferred.name == "conceder":
            return 5.0
        if inferred.name == "boulware":
            return 1.8
        if inferred.name == "linear":
            return 2.8
        if inferred.name == "aspiration_like":
            return 3.2
        return 3.0

    def _target_utility(self, t: float) -> float:
        if self.ufun is None:
            return 1.0
        r = float(self._reservation or 0.0)
        t = min(max(float(t), 0.0), 1.0)

        p = self._choose_concession_exponent(self._last_inferred)

        return r + (1.0 - r) * (1.0 - (t ** p))

    # ---- Proposal selection ----

    def _alpha(self, t: float) -> float:
        """
        Weight on self-utility vs opponent-likelihood in proposal selection.
        Higher early, lower later.
        """
        if t < 0.7:
            return 0.9
        if t < 0.9:
            return 0.8
        return 0.7

    def _pick_offer(self, u_target: float, t: float):
        """
        Choose an offer with U_self >= u_target maximizing a blend of:
          alpha * U_self + (1-alpha) * normalized_opp_score
        and avoiding repeats; pick randomly among top-K for robustness.
        """
        if not self._sorted_outcomes or self.ufun is None:
            return None

        a = self._alpha(t)

        candidates: List[Tuple[float, object]] = []  # (combined_score, outcome)
        opp_scores: List[float] = []

        # Collect feasible outcomes (>= target) that we haven't sent
        for o in self._sorted_outcomes:
            if o in self._sent_offers:
                continue
            u = float(self.ufun(o))
            if u < u_target:
                continue
            oscore = self._opp_likelihood_score(o)
            opp_scores.append(oscore)
            # temporarily store with placeholder combined; normalize later
            candidates.append((u, o))

        if not candidates:
            # If all feasible are repeats, allow repeats but still try good ones
            for o in self._sorted_outcomes:
                u = float(self.ufun(o))
                if u < u_target:
                    continue
                oscore = self._opp_likelihood_score(o)
                opp_scores.append(oscore)
                candidates.append((u, o))
                if len(candidates) > 50:  # limit scan
                    break

        if not candidates:
            # If nothing meets target, return best remaining above reservation
            for o in self._sorted_outcomes:
                if o not in self._sent_offers:
                    return o
            return self._sorted_outcomes[0]

        # Normalize opponent scores across candidates
        min_os = min(opp_scores) if opp_scores else 0.0
        max_os = max(opp_scores) if opp_scores else 1.0
        denom = (max_os - min_os) if (max_os - min_os) > 1e-12 else 1.0

        scored: List[Tuple[float, object]] = []
        for (u, o), oscore in zip(candidates, opp_scores):
            os_norm = (oscore - min_os) / denom
            score = a * u + (1.0 - a) * os_norm
            scored.append((score, o))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[: self._top_k] if len(scored) > self._top_k else scored
        _, choice = random.choice(top)

        return choice

    # ---- SAO callbacks ----

    def respond(self, state, source=None):
        if self.ufun is None or not self._sorted_outcomes:
            return ResponseType.REJECT_OFFER

        offer = state.current_offer
        if offer is None:
            return ResponseType.REJECT_OFFER

        t = float(state.relative_time)
        u_offer = float(self.ufun(offer))

        # Update opponent models
        self._opp_type.add(t, u_offer)
        self._update_opp_counts(offer)

        # Update inferred type occasionally (stabilizes behavior)
        step = getattr(state, "step", None)
        if step is None:
            # fallback: infer if enough data
            self._last_inferred = self._opp_type.infer(min_points=self._min_points_to_infer)
        else:
            if len(self._opp_type.obs) >= self._min_points_to_infer and (int(step) % self._infer_every == 0):
                self._last_inferred = self._opp_type.infer(min_points=self._min_points_to_infer)

        u_target = self._target_utility(t)

        # Next-offer acceptance: accept if it's at least as good as what we'd propose now
        next_offer = self._pick_offer(u_target=u_target, t=t)
        if next_offer is not None:
            u_next = float(self.ufun(next_offer))
            if u_offer + self._epsilon_accept >= max(u_target, u_next - 1e-9):
                return ResponseType.ACCEPT_OFFER
        else:
            if u_offer >= u_target:
                return ResponseType.ACCEPT_OFFER

        # Very late fallback: accept anything above reservation
        if t >= 0.995 and u_offer >= float(self._reservation or 0.0):
            return ResponseType.ACCEPT_OFFER

        return ResponseType.REJECT_OFFER

    def propose(self, state, dest=None):
        if self.ufun is None or not self._sorted_outcomes:
            return None

        t = float(state.relative_time)
        u_target = self._target_utility(t)

        offer = self._pick_offer(u_target=u_target, t=t)
        if offer is None:
            return None

        self._last_offer = offer
        self._sent_offers.add(offer)
        return offer