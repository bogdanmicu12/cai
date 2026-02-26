from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from ..domain.issues import Domain
from ..types.index import NegotiationResult, NegotiationState, Offer, ResponseType, TraceEntry
from ..agents import BaseAgent


@dataclass
class NegotiationMechanism:
    """
    Simplified SAO (Alternating Offers) mechanism:
      - round-robin proposer
      - proposer makes an offer
      - all other agents respond (ACCEPT/REJECT/END)
      - unanimous ACCEPT => agreement
      - END by any agent => termination without agreement
      - deadline: n_steps offers (steps)
    """
    domain: Domain
    n_steps: int = 50

    def __post_init__(self) -> None:
        self._agents: List[BaseAgent] = []
        self._outcomes: List[Offer] = self.domain.outcomes()

    @property
    def agents(self) -> Tuple[BaseAgent, ...]:
        return tuple(self._agents)

    @property
    def outcomes(self) -> Tuple[Offer, ...]:
        return tuple(self._outcomes)

    def add(self, agent: BaseAgent) -> None:
        self._agents.append(agent)

    def run(self) -> NegotiationResult:
        if len(self._agents) < 2:
            raise ValueError("NegotiationMechanism requires at least two agents")

        names = [a.name for a in self._agents]
        for a in self._agents:
            opp = [n for n in names if n != a.name]
            a.on_negotiation_start(domain=self.domain, outcomes=self._outcomes, n_steps=self.n_steps, opponents=opp)

        trace: List[TraceEntry] = []
        agreement: Optional[Offer] = None
        ended_by: Optional[str] = None

        last_offer: Optional[Offer] = None
        last_proposer: Optional[str] = None

        for step in range(int(self.n_steps)):
            proposer = self._agents[step % len(self._agents)]
            state_for_proposer = NegotiationState(
                step=step,
                n_steps=self.n_steps,
                current_offer=last_offer,
                last_proposer=last_proposer,
            )
            offer = proposer.propose(state_for_proposer)

            if not self.domain.is_valid(offer):
                raise ValueError(f"Invalid offer proposed by {proposer.name}: {offer}")

            responses: Dict[str, ResponseType] = {}
            all_accepted = True

            for other in self._agents:
                if other is proposer:
                    continue

                state_for_other = NegotiationState(
                    step=step,
                    n_steps=self.n_steps,
                    current_offer=offer,
                    last_proposer=proposer.name,
                )
                other.receive_offer(offer, from_agent=proposer.name, state=state_for_other)
                r = other.respond(state_for_other)
                responses[other.name] = r

                if r == ResponseType.END:
                    ended_by = other.name
                    all_accepted = False
                    break
                if r != ResponseType.ACCEPT:
                    all_accepted = False

            trace.append(TraceEntry(step=step, proposer=proposer.name, offer=offer, responses=responses))

            if ended_by is not None:
                agreement = None
                break

            if all_accepted:
                agreement = offer
                break

            last_offer = offer
            last_proposer = proposer.name

        utilities: Dict[str, float] = {}
        for a in self._agents:
            if a.ufun is None:
                utilities[a.name] = 0.0
            else:
                utilities[a.name] = float(a.ufun(agreement)) if agreement is not None else 0.0

        return NegotiationResult(
            agreement=agreement,
            utilities=utilities,
            steps=len(trace),
            trace=tuple(trace),
            ended_by=ended_by,
        )