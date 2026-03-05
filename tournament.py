from negmas.tournaments.neg import cartesian_tournament
from negmas.gb.negotiators.timebased import (
    BoulwareTBNegotiator,
    ConcederTBNegotiator,
    LinearTBNegotiator,
    AspirationNegotiator,
)
from negmas.inout import Scenario
from negmas.outcomes import make_issue
from negmas.outcomes.outcome_space import make_os
from negmas.preferences import LinearAdditiveUtilityFunction as U
from negmas.tournaments.neg import cartesian_tournament
from negmas.helpers import humanize_time
from negmas.helpers.strings import unique_name
from pathlib import Path
from agent import MiCRONegotiator, MiCRONegotiatorConceder
from bogdan_agent import TrendBoulwareNegotiator
import time
import multiprocessing


def get_scenarios(n=2) -> list[Scenario]:
    # generates/reads the set of scenarios to be used in the tournament
    # Negotiation Issues
    issues = (
        make_issue([f"{i}" for i in range(10)], "quantity"),
        make_issue([f"{i}" for i in range(4)], "price"),
        make_issue([f"{i}" for i in range(10)], "delivery_time"),
    )
    # Create n ufun groups on the same issues
    ufuns = [
        (
            U.random(issues=issues, reserved_value=(0.0, 0.6), normalized=True),
            U.random(issues=issues, reserved_value=(0.0, 0.2), normalized=True)
        )
        for _ in range(n)
    ]
    # Create a negotiation Scenario for each ufun set
    return [
        Scenario(outcome_space=make_os(issues, name=f"S{i}"), ufuns=u)
        for i, u in enumerate(ufuns)
    ]

if __name__ == "__main__":
    multiprocessing.freeze_support()
    tic = time.perf_counter()
    path = Path.home() / "negmas" / unique_name("test")
    results = cartesian_tournament(
        competitors=[MiCRONegotiator,
                     MiCRONegotiatorConceder,
                     TrendBoulwareNegotiator,
                     BoulwareTBNegotiator,
                     ConcederTBNegotiator,
                     LinearTBNegotiator,
                     AspirationNegotiator,],
        # competitors=[MiCRONegotiator, LinearTBNegotiator],
        scenarios=get_scenarios(),
        # mechanism_params=dict(time_limit=5),  # time per negotiation in seconds and rounds
        mechanism_params=dict(n_steps=1000),
        n_repetitions=1,  # number of repetition of each negotiation (these are not combined in score)
        path=path,
    )
    # results.scores_summary[("advantage",)]
    print(f"Done in {humanize_time(time.perf_counter() - tic)}")
    print("\n=== Score Summary ===")
    print(results.scores_summary.to_string())
    print("\n=== Final Scores ===")
    print(results.final_scores.to_string())