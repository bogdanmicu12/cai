from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Dict, Iterable, List, Sequence

Offer = Dict[str, Any]


@dataclass(frozen=True)
class Issue:
    name: str
    values: Sequence[Any]


def make_issue(values: Sequence[Any], name: str) -> Issue:
    return Issue(name=name, values=list(values))


@dataclass(frozen=True)
class Domain:
    issues: Sequence[Issue]

    def outcomes(self) -> List[Offer]:
        """Enumerate the full outcome space Ω (cartesian product)."""
        if not self.issues:
            return [{}]
        names = [i.name for i in self.issues]
        value_lists = [list(i.values) for i in self.issues]
        outs: List[Offer] = []
        for combo in product(*value_lists):
            outs.append({names[k]: combo[k] for k in range(len(names))})
        return outs

    def is_valid(self, offer: Offer) -> bool:
        if offer is None:
            return False
        issue_map = {i.name: set(i.values) for i in self.issues}
        if set(offer.keys()) != set(issue_map.keys()):
            return False
        for k, v in offer.items():
            if v not in issue_map[k]:
                return False
        return True


def make_domain(issues: Sequence[Issue]) -> Domain:
    return Domain(issues=list(issues))