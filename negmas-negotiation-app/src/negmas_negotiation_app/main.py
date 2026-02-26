from __future__ import annotations

from .agents.agent_one import AgentOne
from .agents.agent_two import AgentTwo
from .agents.agent_three import AgentThree
from .agents.agent_four import AgentFour
from .mechanisms.negotiation_mechanism import NegotiationMechanism
from .scenarios.default_scenario import make_default_scenario


def main() -> None:
    scenario = make_default_scenario(seed=1)

    a = AgentOne(name="A1", ufun=scenario.ufun_a)
    b = AgentFour(name="A4", ufun=scenario.ufun_b)

    mech = NegotiationMechanism(domain=scenario.domain, n_steps=50)
    mech.add(a)
    mech.add(b)

    result = mech.run()
    print("Agreement:", result.agreement)
    print("Utilities:", result.utilities)
    print("Steps:", result.steps)


if __name__ == "__main__":
    main()