from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Dict, Mapping, Optional, Sequence

from ..domain.issues import Domain

Offer = Dict[str, Any]


@dataclass
class LinearAdditiveUtilityFunction:
    """
    u(offer) = sum_i w_i * v_i(offer[i])
    - weights are normalized to sum to 1.0
    - values are assumed in [0, 1] (random() generates that)
    """
    values: Dict[str, Dict[Any, float]]
    weights: Dict[str, float]
    reserved_value: float = 0.0

    def __call__(self, offer: Offer) -> float:
        if offer is None:
            return 0.0
        wsum = sum(float(x) for x in self.weights.values()) or 1.0
        u = 0.0
        for issue, w in self.weights.items():
            w = float(w) / wsum
            val_map = self.values.get(issue, {})
            u += w * float(val_map.get(offer.get(issue), 0.0))
        # clamp for safety
        if u < 0.0:
            return 0.0
        if u > 1.0:
            return 1.0
        return u

    @classmethod
    def random(cls, domain: Domain, rng: Optional[random.Random] = None) -> "LinearAdditiveUtilityFunction":
        rng = rng or random.Random()
        weights = {iss.name: rng.random() for iss in domain.issues}
        # normalize weights later in __call__
        values: Dict[str, Dict[Any, float]] = {}
        for iss in domain.issues:
            # random value per discrete item
            m = {v: rng.random() for v in iss.values}
            # normalize to [0,1]
            mx = max(m.values()) if m else 1.0
            mn = min(m.values()) if m else 0.0
            if mx == mn:
                values[iss.name] = {k: 1.0 for k in m.keys()}
            else:
                values[iss.name] = {k: (vv - mn) / (mx - mn) for k, vv in m.items()}
        return cls(values=values, weights=weights, reserved_value=0.0)