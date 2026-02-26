from negmas import SAOMechanism, TimeBasedConcedingNegotiator, make_issue
from negmas.preferences import LinearAdditiveUtilityFunction as LUFun

issues = [make_issue(name="price", values=list(range(100)))]

session = SAOMechanism(issues=issues, n_steps=50)

buyer_ufun = LUFun({"price": lambda p: -p}, issues=issues, reserved_value=-99)

seller_ufun = LUFun({"price": lambda p: p}, issues=issues, reserved_value=0)

session.add(TimeBasedConcedingNegotiator(name="buyer"), ufun=buyer_ufun)
session.add(TimeBasedConcedingNegotiator(name="seller"), ufun=seller_ufun)

result = session.run()
print(f"Agreement: {result.agreement}, Rounds: {result.step}")