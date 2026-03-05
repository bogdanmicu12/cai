from negmas import (
    make_issue,
    SAOMechanism,
    NaiveTitForTatNegotiator,
    TimeBasedConcedingNegotiator,
)
from negmas.gb.negotiators.timebased import (
    BoulwareTBNegotiator,
    ConcederTBNegotiator,
    LinearTBNegotiator,
    AspirationNegotiator,
)
from negmas.preferences import LinearAdditiveUtilityFunction as LUFun
from negmas.preferences.value_fun import LinearFun, IdentityFun, AffineFun
from agent import MiCRONegotiator, MiCRONegotiatorConceder
from bogdan_agent import TrendBoulwareNegotiator


def try_negotiator(buyer_cls, seller_cls, plot=True, n_steps=1000):
    issues = [
        make_issue(name="price", values=10),
        make_issue(name="quantity", values=(1, 11)),
        make_issue(name="delivery_time", values=10),
    ]
    session = SAOMechanism(issues=issues, n_steps=n_steps)

    seller_utility = LUFun(
        values={
            "price": IdentityFun(),
            "quantity": LinearFun(0.2),
            "delivery_time": AffineFun(-1, bias=9),
        },
        weights={"price": 1.0, "quantity": 1.0, "delivery_time": 10.0},
        outcome_space=session.outcome_space,
    ).scale_max(1.0)

    buyer_utility = LUFun(
        values={
            "price": AffineFun(-1, bias=9.0),
            "quantity": LinearFun(0.2),
            "delivery_time": IdentityFun(),
        },
        weights={"price": 1.0, "quantity": 1.0, "delivery_time": 1.0},
        outcome_space=session.outcome_space,
    ).scale_max(1.0)

    seller_utility.reserved_value = 0.4
    buyer_utility.reserved_value = 0.4

    session.add(buyer_cls(name=buyer_cls.__name__ + "_buyer"), ufun=buyer_utility)
    session.add(seller_cls(name=seller_cls.__name__ + "_seller"), ufun=seller_utility)
    session.run()
    if plot:
        session.plot()
    return session


s1 = try_negotiator(TrendBoulwareNegotiator, MiCRONegotiator)
s2 = try_negotiator(MiCRONegotiator, TrendBoulwareNegotiator)
s3 = try_negotiator(TrendBoulwareNegotiator, LinearTBNegotiator)
s4 = try_negotiator(LinearTBNegotiator, TrendBoulwareNegotiator)
s5 = try_negotiator(TrendBoulwareNegotiator, AspirationNegotiator)
s6 = try_negotiator(AspirationNegotiator, TrendBoulwareNegotiator)
s7 = try_negotiator(TrendBoulwareNegotiator, NaiveTitForTatNegotiator)
s8 = try_negotiator(NaiveTitForTatNegotiator, TrendBoulwareNegotiator)
s9 = try_negotiator(TrendBoulwareNegotiator, TrendBoulwareNegotiator)
s10 = try_negotiator(TrendBoulwareNegotiator, MiCRONegotiatorConceder)
#######
s11 = try_negotiator(MiCRONegotiatorConceder, TrendBoulwareNegotiator)
s12 = try_negotiator(MiCRONegotiator, MiCRONegotiatorConceder)
s13 = try_negotiator(MiCRONegotiatorConceder, MiCRONegotiator)
s14 = try_negotiator(MiCRONegotiatorConceder, MiCRONegotiatorConceder)
s15 = try_negotiator(MiCRONegotiatorConceder, LinearTBNegotiator)
s16 = try_negotiator(LinearTBNegotiator, MiCRONegotiatorConceder)
s17 = try_negotiator(MiCRONegotiatorConceder, AspirationNegotiator)
s18 = try_negotiator(AspirationNegotiator, MiCRONegotiatorConceder) 
s19 = try_negotiator(MiCRONegotiatorConceder, NaiveTitForTatNegotiator)
s20 = try_negotiator(NaiveTitForTatNegotiator, MiCRONegotiatorConceder)

import matplotlib.pyplot as plt
plt.show()