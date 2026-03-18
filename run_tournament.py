from negmas.tournaments.neg import cartesian_tournament
from negmas.gb.negotiators.timebased import (
    BoulwareTBNegotiator,
    ConcederTBNegotiator,
    LinearTBNegotiator,
    AspirationNegotiator,
)
from negmas import NaiveTitForTatNegotiator

from negmas.inout import Scenario
from negmas.outcomes import make_issue
from negmas.outcomes.outcome_space import make_os
from negmas.preferences import LinearAdditiveUtilityFunction as U
from negmas.tournaments.neg import cartesian_tournament
from negmas.helpers import humanize_time
from negmas.helpers.strings import unique_name
from pathlib import Path
from agent import MiCRONegotiator, MiCRONegotiatorConceder
from group_69_negotiator import Group69Negotiator
from prediction_negotiator import PredictionNegotiator
from SmartNegotiator import SmartAspirationNegotiator
from agent2 import PortfolioTBNegotiator
import time
import multiprocessing
import pandas as pd
import matplotlib.pyplot as plt

def get_scenarios(n) -> list[Scenario]:
    scenarios = []

    # Domain 1: Quantity / Price / Delivery
    issues1 = (
        make_issue([f"{i}" for i in range(6)], "quantity"),
        make_issue([f"{i}" for i in range(4)], "price"),
        make_issue([f"{i}" for i in range(6)], "delivery_time"),
    )

    # Domain 2: Salary negotiation
    issues2 = (
        make_issue([f"{i}" for i in range(5)], "salary_level"),
        make_issue([f"{i}" for i in range(6)], "vacation_days"),
        make_issue([f"{i}" for i in range(4)], "remote_days"),
    )

    # Domain 3: Resource allocation
    issues3 = (
        make_issue([f"{i}" for i in range(8)], "cpu_hours"),
        make_issue([f"{i}" for i in range(6)], "gpu_hours"),
        make_issue([f"{i}" for i in range(8)], "memory_blocks"),
    )

    # Domain 4: Contract terms
    issues4 = (
        make_issue([f"{i}" for i in range(6)], "contract_length"),
        make_issue([f"{i}" for i in range(5)], "bonus"),
        make_issue([f"{i}" for i in range(5)], "penalty"),
    )

    domains = [issues1, issues2, issues3, issues4]

    # distribute scenarios across domains
    for i in range(n):
        issues = domains[i % len(domains)]

        u = (
            U.random(issues=issues, reserved_value=(0.0, 0.6), normalized=True),
            U.random(issues=issues, reserved_value=(0.0, 0.2), normalized=True)
        )

        scenarios.append(
            Scenario(
                outcome_space=make_os(issues, name=f"S{i}"),
                ufuns=u
            )
        )

    return scenarios


def run_tournament():

    tic = time.perf_counter()

    path = Path.home() / "negmas" / unique_name("test")

    results = cartesian_tournament(
        competitors=[
            MiCRONegotiator,
            ConcederTBNegotiator,
            LinearTBNegotiator,
            AspirationNegotiator,
            NaiveTitForTatNegotiator,
            Group69Negotiator,
        ],
        scenarios=get_scenarios(20),
        mechanism_params=dict(n_steps=2000),
        n_repetitions=10,
        path=path,
        njobs = 1,
    )
    print(results.scores_summary.keys())

    metrics = ["utility", "advantage", "social_welfare",
           "modified_kalai_optimality", "modified_ks_optimality"]

    for m in metrics:
        if (m, "mean") in results.scores_summary:
            results.scores_summary[(m, "mean")].plot(kind="bar")
            plt.title(f"Average {m.replace('_',' ').title()} per Agent")
            plt.ylabel("Mean Value")
            plt.xlabel("Agent")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()

    print(f"Done in {humanize_time(time.perf_counter() - tic)}")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_tournament()