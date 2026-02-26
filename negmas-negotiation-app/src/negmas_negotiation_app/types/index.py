from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

Offer = Dict[str, Any]


class ResponseType(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    END = "end"


@dataclass(frozen=True)
class NegotiationState:
    step: int
    n_steps: int
    current_offer: Optional[Offer] = None
    last_proposer: Optional[str] = None

    @property
    def relative_time(self) -> float:
        """Normalized time in [0, 1]."""
        if self.n_steps <= 1:
            return 1.0
        t = self.step / float(self.n_steps - 1)
        if t < 0.0:
            return 0.0
        if t > 1.0:
            return 1.0
        return t


@dataclass(frozen=True)
class TraceEntry:
    step: int
    proposer: str
    offer: Offer
    responses: Dict[str, ResponseType]


@dataclass(frozen=True)
class NegotiationResult:
    agreement: Optional[Offer]
    utilities: Dict[str, float]
    steps: int
    trace: Tuple[TraceEntry, ...] = field(default_factory=tuple)
    ended_by: Optional[str] = None