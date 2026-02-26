from __future__ import annotations

from . import TimeBasedAgent


class AgentTwo(TimeBasedAgent):
    """
    Boulware-style time-based agent (concedes late).
    """

    def __init__(self, *args, **kwargs) -> None:
        # larger gamma => slower concession until late
        kwargs.setdefault("gamma", 3.0)
        kwargs.setdefault("alpha", 1.0)
        super().__init__(*args, **kwargs)