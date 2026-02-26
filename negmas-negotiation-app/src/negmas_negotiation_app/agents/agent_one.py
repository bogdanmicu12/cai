from __future__ import annotations

from . import TimeBasedAgent


class AgentOne(TimeBasedAgent):
    """
    Conceder-style time-based agent (concedes earlier).
    Good baseline "standard time-based approach".
    """

    def __init__(self, *args, **kwargs) -> None:
        # smaller gamma => faster concession
        kwargs.setdefault("gamma", 0.7)
        kwargs.setdefault("alpha", 1.0)
        super().__init__(*args, **kwargs)