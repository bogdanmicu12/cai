from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Tuple

from ..domain.issues import Domain, make_domain, make_issue
from ..domain.utility_functions import LinearAdditiveUtilityFunction


@dataclass(frozen=True)
class DefaultScenario:
    domain: Domain
    ufun_a: LinearAdditiveUtilityFunction
    ufun_b: LinearAdditiveUtilityFunction


def make_default_scenario(seed: int = 1) -> DefaultScenario:
    rng = random.Random(seed)

    issues = [
        make_issue([20, 30, 40, 50], name="price"),
        make_issue([500, 600, 700], name="speed"),
        make_issue([10, 20, 30], name="data"),
    ]
    domain = make_domain(issues)

    u1 = LinearAdditiveUtilityFunction.random(domain, rng=rng)
    u2 = LinearAdditiveUtilityFunction.random(domain, rng=rng)

    u1.reserved_value = 0.3
    u2.reserved_value = 0.3

    return DefaultScenario(domain=domain, ufun_a=u1, ufun_b=u2)