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

# create negotiation agenda (issues)
def try_negotiator(buyer_cls, seller_cls, plot=True, n_steps=1000):
    # create negotiation agenda (issues)
    issues = [
        make_issue(name="price", values=10),
        make_issue(name="quantity", values=(1, 11)),
        make_issue(name="delivery_time", values=10),
    ]
    # create the mechanism
    session = SAOMechanism(issues=issues, n_steps=n_steps)
    # define ufuns
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

s1 = try_negotiator(MiCRONegotiator, LinearTBNegotiator)
# s2 = try_negotiator(MiCRONegotiator, NaiveTitForTatNegotiator)
# s3 = try_negotiator(MiCRONegotiator, AspirationNegotiator)
# s4 = try_negotiator(MiCRONegotiator, MiCRONegotiator)
# s5 = try_negotiator(MiCRONegotiatorConceder, MiCRONegotiator)
s6 = try_negotiator(LinearTBNegotiator, MiCRONegotiator)