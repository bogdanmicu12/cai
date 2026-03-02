from negmas import (
    make_issue,
    SAOMechanism,
    NaiveTitForTatNegotiator,
    TimeBasedConcedingNegotiator,
)
from negmas.preferences import LinearAdditiveUtilityFunction as LUFun
from negmas.preferences.value_fun import LinearFun, IdentityFun, AffineFun

# create negotiation agenda (issues)
issues = [
    make_issue(name="price", values=10),
    make_issue(name="quantity", values=(1, 11)),
    make_issue(name="delivery_time", values=10),
]
# create the mechanism
session = SAOMechanism(issues=issues, n_steps=5000)
# define buyer and seller utilities
seller_utility = LUFun(
    values=[IdentityFun(), LinearFun(0.2), AffineFun(-1, bias=9.0)],
    weights={"price": 1.0, "quantity": 1.0, "delivery_time": 10.0},
    outcome_space=session.outcome_space,
)
buyer_utility = LUFun(
    values={
        "price": AffineFun(-1, bias=9.0),
        "quantity": LinearFun(0.2),
        "delivery_time": IdentityFun(),
    },
    outcome_space=session.outcome_space,
)

seller_utility = seller_utility.scale_max(1.0)
buyer_utility = buyer_utility.scale_max(1.0)

# create and add buyer and seller negotiators
session.add(TimeBasedConcedingNegotiator(name="buyer", offering_curve="linear"), preferences=buyer_utility)
session.add(TimeBasedConcedingNegotiator(name="seller", offering_curve="linear"), ufun=seller_utility)
# run the negotiation and show the results
print(session.run())
session.plot(ylimits=(0.0, 1.01), show_reserved=False)